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

import base64
import json
import time

import boto3
import jwt
import msal
import requests

from codemie_test_harness.tests.utils.cloud_seed import (
    AWS_SEED_BUCKET_NAME,
    AZURE_SEED_RESOURCE_GROUP_NAME,
    GCP_SEED_BUCKET_NAME,
    KUBERNETES_SEED_NAMESPACE,
    KUBERNETES_SEED_SERVICE,
    SeedAwsBucket,
    SeedAzureResourceGroup,
    SeedGcpBucket,
    SeedKubernetesService,
    aws_bucket_from_api,
    azure_resource_group_from_api,
    gcp_bucket_from_api,
    kubernetes_service_from_api,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

REQUEST_TIMEOUT_SECONDS = 60


def _raise_for_status(response: requests.Response, action: str) -> None:
    if response.ok:
        return
    raise RuntimeError(
        f"{action} failed: HTTP {response.status_code} {response.text[:500]}"
    )


class AwsUtils:
    """Reads the existing S3 seed bucket. Never creates or changes anything."""

    def __init__(self):
        # The CodeMie AWS tool signs its calls with the access key pair alone
        # (no session token), so the seed uses exactly the same credentials.
        session = boto3.Session(
            aws_access_key_id=CredentialsManager.get_parameter("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=CredentialsManager.get_parameter(
                "AWS_SECRET_ACCESS_KEY"
            ),
            region_name=CredentialsManager.get_parameter("AWS_REGION"),
        )
        self.s3 = session.client("s3")

    def get_seed_bucket(self) -> SeedAwsBucket:
        bucket = next(
            (
                b
                for b in self.s3.list_buckets()["Buckets"]
                if b["Name"] == AWS_SEED_BUCKET_NAME
            ),
            None,
        )
        if bucket is None:
            raise RuntimeError(
                f"AWS seed bucket '{AWS_SEED_BUCKET_NAME}' not found in the account"
            )
        location = self.s3.get_bucket_location(Bucket=AWS_SEED_BUCKET_NAME)
        return aws_bucket_from_api(bucket, location.get("LocationConstraint"))


class AzureUtils:
    """Reads the existing Azure resource group over the ARM API. Never creates or changes anything."""

    MANAGEMENT_API = "https://management.azure.com"
    # Client-credentials flow needs the resource's own scope, not a specific
    # permission string.
    SCOPE = "https://management.azure.com/.default"
    API_VERSION = "2021-04-01"

    def __init__(self):
        self.subscription_id = CredentialsManager.get_parameter("AZURE_SUBSCRIPTION_ID")
        self.resource_group_name = AZURE_SEED_RESOURCE_GROUP_NAME
        # Same client-credentials flow as OAuthAzureTokenRetriever, against the ARM
        # scope and the general app registration behind azure_credentials().
        app = msal.ConfidentialClientApplication(
            client_id=CredentialsManager.get_parameter("AZURE_CLIENT_ID"),
            authority=(
                f"https://login.microsoftonline.com/"
                f"{CredentialsManager.get_parameter('AZURE_TENANT_ID')}"
            ),
            client_credential=CredentialsManager.get_parameter("AZURE_CLIENT_SECRET"),
        )
        result = app.acquire_token_for_client(scopes=[self.SCOPE])
        if "access_token" not in result:
            raise RuntimeError(
                "Failed to acquire Azure access token: "
                f"{result.get('error')} - {result.get('error_description')}"
            )
        self.headers = {"Authorization": f"Bearer {result['access_token']}"}

    def get_seed_resource_group(self) -> SeedAzureResourceGroup:
        response = requests.get(
            f"{self.MANAGEMENT_API}/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{self.resource_group_name}",
            params={"api-version": self.API_VERSION},
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        _raise_for_status(
            response,
            f"Get Azure seed resource group '{self.resource_group_name}'",
        )
        return azure_resource_group_from_api(response.json(), self.subscription_id)


class GcpUtils:
    """Reads the existing Cloud Storage seed bucket over the JSON API. Never creates or changes anything."""

    STORAGE_API = "https://storage.googleapis.com/storage/v1"
    SCOPE = "https://www.googleapis.com/auth/devstorage.read_only"
    DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"

    def __init__(self):
        sa_key_in_base64 = CredentialsManager.get_parameter("GCP_SA_KEY_BASE64")
        self.service_account = json.loads(base64.b64decode(sa_key_in_base64))

    def _access_token(self) -> str:
        token_uri = self.service_account.get("token_uri", self.DEFAULT_TOKEN_URI)
        now = int(time.time())
        assertion = jwt.encode(
            {
                "iss": self.service_account["client_email"],
                "scope": self.SCOPE,
                "aud": token_uri,
                "iat": now,
                "exp": now + 3600,
            },
            self.service_account["private_key"],
            algorithm="RS256",
        )
        response = requests.post(
            token_uri,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        _raise_for_status(response, "GCP service account token request")
        return response.json()["access_token"]

    def get_seed_bucket(self) -> SeedGcpBucket:
        response = requests.get(
            f"{self.STORAGE_API}/b/{GCP_SEED_BUCKET_NAME}",
            headers={"Authorization": f"Bearer {self._access_token()}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        _raise_for_status(
            response,
            f"Get GCP seed bucket '{GCP_SEED_BUCKET_NAME}'",
        )
        return gcp_bucket_from_api(response.json())


class KubernetesUtils:
    """Reads the existing seed service over the Kubernetes API. Never creates or changes anything."""

    def __init__(self):
        self.url = CredentialsManager.get_parameter("KUBERNETES_URL").rstrip("/")
        token = CredentialsManager.get_parameter("KUBERNETES_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        # Clusters commonly use a private CA; opt out with verifySsl=false in the
        # kubernetes integration parameter, or KUBERNETES_VERIFY_SSL=false locally.
        # Parameter Store may return a JSON boolean, so compare the string form.
        verify_raw = CredentialsManager.get_parameter("KUBERNETES_VERIFY_SSL", "true")
        self.verify = str(verify_raw).strip().lower() != "false"

    def get_seed_service(self) -> SeedKubernetesService:
        response = requests.get(
            f"{self.url}/api/v1/namespaces/{KUBERNETES_SEED_NAMESPACE}"
            f"/services/{KUBERNETES_SEED_SERVICE}",
            headers=self.headers,
            verify=self.verify,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        _raise_for_status(
            response,
            f"Get Kubernetes seed service "
            f"'{KUBERNETES_SEED_NAMESPACE}/{KUBERNETES_SEED_SERVICE}'",
        )
        return kubernetes_service_from_api(response.json())
