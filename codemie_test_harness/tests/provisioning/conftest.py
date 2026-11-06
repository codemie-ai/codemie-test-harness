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

"""Fixtures for the provisioning API tests.

A provisioning client is a registered third-party caller with its own bearer token. The
harness cannot register one, so it logs in as the user behind each client (username and
password from settings) and a test whose login is not configured is skipped by the
capability gate (``requires_setting``).
"""

import pytest

from codemie_test_harness.cli.constants import (
    KEY_PROVISIONING_BUDGETS_PASSWORD,
    KEY_PROVISIONING_BUDGETS_USERNAME,
    KEY_PROVISIONING_FULL_EMAIL,
    KEY_PROVISIONING_FULL_NAME,
    KEY_PROVISIONING_FULL_PASSWORD,
    KEY_PROVISIONING_FULL_USERNAME,
    KEY_PROVISIONING_READ_PASSWORD,
    KEY_PROVISIONING_READ_USERNAME,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.provisioning_utils import ProvisioningUtils


def _login(username_key: str, password_key: str):
    """Client logged in as the user behind a provisioning client, the way the harness logs in
    every other user. It caches its token and logs in again before the token expires."""
    return get_client(
        username=CredentialsManager.get_required_parameter(username_key),
        password=CredentialsManager.get_required_parameter(password_key),
    )


@pytest.fixture(scope="session")
def provisioning_full_login():
    """Login of the client holding manage-budgets and manage-projects."""
    return _login(KEY_PROVISIONING_FULL_USERNAME, KEY_PROVISIONING_FULL_PASSWORD)


@pytest.fixture(scope="session")
def provisioning_full_token(provisioning_full_login):
    """Token source of the client holding manage-budgets and manage-projects; each call returns
    a token that is still valid."""
    return lambda: provisioning_full_login.token


@pytest.fixture(scope="session")
def provisioning_full(client, provisioning_full_token):
    """Provisioning service for the client holding manage-budgets and manage-projects."""
    return client.provisioning.with_token(provisioning_full_token)


@pytest.fixture(scope="session")
def provisioning_budgets(client):
    """Provisioning service for the client holding manage-budgets only."""
    login = _login(KEY_PROVISIONING_BUDGETS_USERNAME, KEY_PROVISIONING_BUDGETS_PASSWORD)
    return client.provisioning.with_token(lambda: login.token)


@pytest.fixture(scope="session")
def provisioning_read(client):
    """Provisioning service for the client holding read-projects only."""
    login = _login(KEY_PROVISIONING_READ_USERNAME, KEY_PROVISIONING_READ_PASSWORD)
    return client.provisioning.with_token(lambda: login.token)


@pytest.fixture(scope="session")
def provisioning_client_name() -> str:
    """Registered name of the manage-budgets and manage-projects client."""
    return CredentialsManager.get_required_parameter(KEY_PROVISIONING_FULL_NAME)


@pytest.fixture(scope="session")
def provisioning_client_email() -> str:
    """Email of the user behind the manage-budgets and manage-projects client."""
    return CredentialsManager.get_required_parameter(KEY_PROVISIONING_FULL_EMAIL)


@pytest.fixture
def provisioning_utils(client, project_utils, cost_center_utils, project_budget_groups):
    """Admin-side helper that creates and reads projects; removes what the test and the
    provisioning calls created, after the user fixtures requested before it are still alive."""
    utils = ProvisioningUtils(
        client, project_utils, cost_center_utils, project_budget_groups
    )
    yield utils
    utils.cleanup()
