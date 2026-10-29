# Copyright 2026 EPAM Systems, Inc. (“EPAM”)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

STORE_NAME = "aws-parameter-store"


class SecretStoreError(RuntimeError):
    """The enabled secret store is misconfigured, unreachable or rejects credentials."""


def _store_error(region: str, prefix: str, reason: str) -> SecretStoreError:
    return SecretStoreError(
        f"Secret store '{STORE_NAME}' failed (region={region or '<unset>'}, "
        f"prefix={prefix or '<unset>'}): {reason}"
    )


@dataclass(frozen=True)
class AwsStoreConfig:
    """Settings of the opt-in AWS Parameter Store. Read from the environment only."""

    region: str
    path_prefix: str
    role_arn: str = ""
    dotenv_path: str = ""

    @classmethod
    def from_env(cls) -> Optional["AwsStoreConfig"]:
        """None when the store is not enabled; raises SecretStoreError when it is enabled
        without its required settings."""
        selected = os.getenv("HARNESS_SECRET_STORE", "").strip()
        if not selected:
            return None
        region = os.getenv("AWS_PS_REGION", "").strip()
        prefix = os.getenv("AWS_PS_PATH_PREFIX", "").strip()
        if selected != STORE_NAME:
            raise SecretStoreError(
                f"HARNESS_SECRET_STORE='{selected}' is not supported; use '{STORE_NAME}'."
            )
        for name, value in (("AWS_PS_REGION", region), ("AWS_PS_PATH_PREFIX", prefix)):
            if not value:
                raise _store_error(
                    region, prefix, f"required setting {name} is not set"
                )
        return cls(
            region=region,
            # Names are built as prefix + group, so the prefix must start and end with "/".
            path_prefix="/" + prefix.strip("/") + "/",
            role_arn=os.getenv("AWS_PS_ROLE_ARN", "").strip(),
            dotenv_path=os.getenv("AWS_PS_DOTENV_PATH", "").strip(),
        )


class AwsParameterStore:
    """AWS Parameter Store client. Created only when the store is enabled."""

    _instance = None

    def __init__(self, config: AwsStoreConfig):
        self.config = config
        self._connect()

    def _connect(self) -> None:
        """Build the SSM client. With a role, the STS credentials last one hour, so
        get_parameter calls this again when they expire."""
        config = self.config
        try:
            session = boto3.Session(**self._base_credentials())
            if config.role_arn:
                assumed = session.client("sts", region_name=config.region).assume_role(
                    RoleArn=config.role_arn, RoleSessionName="HarnessSecretStore"
                )["Credentials"]
                session = boto3.Session(
                    aws_access_key_id=assumed["AccessKeyId"],
                    aws_secret_access_key=assumed["SecretAccessKey"],
                    aws_session_token=assumed["SessionToken"],
                )
            self.ssm_client = session.client("ssm", region_name=config.region)
        except (ClientError, BotoCoreError) as e:
            raise _store_error(config.region, config.path_prefix, str(e)) from e

    @staticmethod
    def _base_credentials() -> dict:
        """Store credentials: explicit keys, else AWS_PROFILE, else the boto3 default chain."""
        access_key = os.getenv("AWS_ACCESS_KEY", "")
        secret_key = os.getenv("AWS_SECRET_KEY", "")
        if access_key and secret_key:
            creds = {
                "aws_access_key_id": access_key,
                "aws_secret_access_key": secret_key,
            }
            token = os.getenv("AWS_SESSION_TOKEN", "")
            if token:
                creds["aws_session_token"] = token
            return creds
        profile = os.getenv("AWS_PROFILE", "")
        return {"profile_name": profile} if profile else {}

    @classmethod
    def get_instance(cls, config: AwsStoreConfig) -> "AwsParameterStore":
        """Singleton per configuration."""
        if cls._instance is None or cls._instance.config != config:
            cls._instance = cls(config)
        return cls._instance

    def check(self) -> None:
        """Read one (normally missing) parameter under the path prefix, so an unreachable
        store or rejected credentials fail at startup instead of during collection.
        It needs only ssm:GetParameter on the prefix, like the real reads.

        Raises:
            SecretStoreError: when the store is unreachable or rejects the credentials.
        """
        self.get_parameter(self.config.path_prefix + "healthcheck")

    def get_parameter(self, parameter_name: str, _retry: bool = True) -> Optional[str]:
        """Parameter value, or None when the parameter does not exist.

        Raises:
            SecretStoreError: when the store is unreachable or rejects the credentials.
        """
        try:
            response = self.ssm_client.get_parameter(Name=parameter_name)
            return response["Parameter"]["Value"]
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ParameterNotFound":
                return None
            code = e.response.get("Error", {}).get("Code", "ClientError")
            if _retry and self.config.role_arn and code.startswith("ExpiredToken"):
                self._connect()
                return self.get_parameter(parameter_name, _retry=False)
            raise _store_error(
                self.config.region, self.config.path_prefix, f"{code}: {e}"
            ) from e
        except BotoCoreError as e:
            raise _store_error(
                self.config.region, self.config.path_prefix, str(e)
            ) from e
