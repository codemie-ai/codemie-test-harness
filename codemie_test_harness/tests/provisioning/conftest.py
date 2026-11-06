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
harness cannot register one, so the tokens come from settings and a test whose token is not
configured is skipped by the capability gate (``requires_setting``).
"""

import pytest

from codemie_test_harness.cli.constants import (
    KEY_PROVISIONING_BUDGETS_TOKEN,
    KEY_PROVISIONING_FULL_EMAIL,
    KEY_PROVISIONING_FULL_NAME,
    KEY_PROVISIONING_FULL_TOKEN,
    KEY_PROVISIONING_READ_TOKEN,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.provisioning_utils import ProvisioningUtils


@pytest.fixture(scope="session")
def provisioning_full_token() -> str:
    """Token of the client holding manage-budgets and manage-projects."""
    return CredentialsManager.get_required_parameter(KEY_PROVISIONING_FULL_TOKEN)


@pytest.fixture(scope="session")
def provisioning_full(client, provisioning_full_token):
    """Provisioning service for the client holding manage-budgets and manage-projects."""
    return client.provisioning.with_token(provisioning_full_token)


@pytest.fixture(scope="session")
def provisioning_budgets(client):
    """Provisioning service for the client holding manage-budgets only."""
    token = CredentialsManager.get_required_parameter(KEY_PROVISIONING_BUDGETS_TOKEN)
    return client.provisioning.with_token(token)


@pytest.fixture(scope="session")
def provisioning_read(client):
    """Provisioning service for the client holding read-projects only."""
    token = CredentialsManager.get_required_parameter(KEY_PROVISIONING_READ_TOKEN)
    return client.provisioning.with_token(token)


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
