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

"""
Utility functions for managing environment variables and dotenv files with caching prevention.
"""

import os
import time
from pathlib import Path
from io import StringIO
from urllib.parse import urlparse
from dotenv import dotenv_values, load_dotenv

from codemie_test_harness.cli.utils import OVERRIDABLE_KEYS
from codemie_test_harness.tests.utils.aws_parameters_store import (
    STORE_NAME,
    AwsParameterStore,
    AwsStoreConfig,
    SecretStoreError,
)

LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "0.0.0.0")
AWS_CREDENTIAL_VARS = ("AWS_ACCESS_KEY", "AWS_ACCESS_KEY_ID", "AWS_PROFILE")


def load_env_file(env_file_path: Path) -> None:
    """Load ``env_file_path``; if it is missing, fall back to the shipped ``.env.template``.

    The template carries local-stack defaults (default admin credentials,
    VERIFY_SSL=False), so it is used only when the API domain is unset or
    local and no AWS credentials are configured. Existing environment
    variables are never overridden.
    """
    before = set(os.environ)
    try:
        _load_env_file(env_file_path)
    finally:
        OVERRIDABLE_KEYS.update(set(os.environ) - before)


def _load_env_file(env_file_path: Path) -> None:
    if env_file_path.exists():
        load_dotenv(env_file_path, override=False)
        return
    template_path = env_file_path.with_name(".env.template")
    domain = os.getenv("CODEMIE_API_DOMAIN", "")
    host = urlparse(domain if "//" in domain else f"//{domain}").hostname
    is_local = not domain or host in LOCAL_HOSTS
    uses_aws = bool(os.getenv("HARNESS_SECRET_STORE")) or any(
        os.getenv(var) for var in AWS_CREDENTIAL_VARS
    )
    if template_path.exists() and is_local and not uses_aws:
        load_dotenv(template_path, override=False)


class EnvManager:
    """
    Manages environment variables with proper caching prevention.
    """

    @staticmethod
    def write_env_file_safely(env_file_path: Path, content: str) -> None:
        """
        Write content to .env file with proper flushing and sync.

        Args:
            env_file_path: Path to the .env file
            content: Content to write
        """
        # Ensure parent directory exists
        env_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write with proper flushing
        with open(env_file_path, "w", encoding="utf-8") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())

    @staticmethod
    def load_env_with_retry(
        env_file_path: Path,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        override: bool = True,
    ) -> bool:
        """
        Load .env file with retry mechanism to handle caching issues.

        Args:
            env_file_path: Path to the .env file
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            override: Whether to override existing environment variables

        Returns:
            bool: True if successfully loaded, False otherwise
        """
        for attempt in range(max_retries):
            try:
                # Small delay to ensure file system consistency
                if attempt > 0:
                    time.sleep(retry_delay)

                # Verify file exists and is readable
                if not env_file_path.exists():
                    raise FileNotFoundError(f".env file not found: {env_file_path}")

                # Read file content to verify it's accessible
                with open(env_file_path, "r") as f:
                    content = f.read()

                if not content.strip():
                    raise ValueError("Empty .env file")

                # Load environment variables
                success = load_dotenv(env_file_path, override=override)

                if success:
                    return True

            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(
                        f"Failed to load .env file after {max_retries} attempts: {e}"
                    )
                continue

        return False

    @staticmethod
    def apply_downloaded_env(new_content: str) -> None:
        """
        Apply a downloaded .env in memory. Nothing is written to disk, so a rotated
        secret applies on the next run.

        Values already set in os.environ are never overwritten: env vars, config-file
        values and the local .env outrank the store.

        Args:
            new_content: .env content from the secret store
        """
        for name, value in dotenv_values(stream=StringIO(new_content)).items():
            if value is not None and name not in os.environ:
                os.environ[name] = value
                OVERRIDABLE_KEYS.add(name)

    @staticmethod
    def download_from_secret_store() -> bool:
        """
        When the AWS Parameter Store is enabled, connect to it and (if AWS_PS_DOTENV_PATH
        is set) download that parameter and apply it to the environment.

        Returns:
            True if a .env file was downloaded, False if the store is disabled or has no
            AWS_PS_DOTENV_PATH.

        Raises:
            SecretStoreError: if the store is misconfigured, unreachable, rejects the
                credentials or lacks the configured .env parameter.
        """
        config = AwsStoreConfig.from_env()
        if config is None:
            return False
        store = AwsParameterStore.get_instance(config)
        store.check()
        if not config.dotenv_path:
            return False
        content = store.get_parameter(config.dotenv_path)
        if content is None:
            raise SecretStoreError(
                f"Secret store '{STORE_NAME}' (region={config.region}, "
                f"prefix={config.path_prefix}): parameter '{config.dotenv_path}' "
                "(AWS_PS_DOTENV_PATH) was not found"
            )
        EnvManager.apply_downloaded_env(content)
        return True
