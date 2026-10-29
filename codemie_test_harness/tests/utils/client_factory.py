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

"""Client factory utilities for tests."""

from typing import Optional
import pytest
import requests
from codemie_sdk import CodeMieClient
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


def get_client(
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    """Create a test client instance."""
    try:
        return CodeMieClient(
            auth_server_url=CredentialsManager.get_parameter("AUTH_SERVER_URL", ""),
            auth_client_id=CredentialsManager.get_parameter("AUTH_CLIENT_ID", ""),
            auth_client_secret=CredentialsManager.get_parameter(
                "AUTH_CLIENT_SECRET", ""
            ),
            auth_realm_name=CredentialsManager.get_parameter("AUTH_REALM_NAME", ""),
            codemie_api_domain=CredentialsManager.get_parameter("CODEMIE_API_DOMAIN"),
            verify_ssl=CredentialsManager.get_parameter("VERIFY_SSL", "false").lower()
            == "true",
            username=username or CredentialsManager.get_parameter("AUTH_USERNAME"),
            password=password or CredentialsManager.get_parameter("AUTH_PASSWORD"),
        )
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 404:
            pytest.exit(
                "Authentication failed: local-auth feature is not enabled on the backend "
                "(got 404 from /v1/local-auth/login). "
                "Check your configuration — the backend may not support local authentication.",
                returncode=3,
            )
        if status == 401:
            username_val = username or CredentialsManager.get_parameter("AUTH_USERNAME")
            pytest.exit(
                f"Authentication failed: invalid credentials (got 401 from /v1/local-auth/login). "
                f"Ensure that user '{username_val}' exists in the database and the password is correct.",
                returncode=3,
            )
        raise
