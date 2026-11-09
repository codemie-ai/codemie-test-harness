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

A provisioning client is a registered third-party caller: a Keycloak service account with its
own bearer token. The harness cannot register one, so it mints a token for each client from the
client id and secret in the settings, and a test whose settings are not configured is skipped
by the capability gate (``requires_setting``).
"""

import pytest

from codemie_test_harness.cli.constants import (
    KEY_PROVISIONING_BUDGETS_ID,
    KEY_PROVISIONING_BUDGETS_SECRET,
    KEY_PROVISIONING_FULL_ID,
    KEY_PROVISIONING_FULL_SECRET,
    KEY_PROVISIONING_READ_ID,
    KEY_PROVISIONING_READ_SECRET,
)
from codemie_test_harness.tests import VERIFY_SSL
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.provisioning_utils import (
    ClientCredentialsTokenSource,
    ClientNameRecorder,
    ProvisioningUtils,
    resolve_client_email,
)


def _token_source(id_key: str, secret_key: str) -> ClientCredentialsTokenSource:
    """Token source of a client, minting from the same Keycloak realm the harness logs in to."""
    return ClientCredentialsTokenSource(
        CredentialsManager.get_required_parameter("AUTH_SERVER_URL"),
        CredentialsManager.get_required_parameter("AUTH_REALM_NAME"),
        CredentialsManager.get_required_parameter(id_key),
        CredentialsManager.get_required_parameter(secret_key),
        VERIFY_SSL,
    )


@pytest.fixture(scope="session")
def provisioning_full_token():
    """Token source of the client holding manage-budgets and manage-projects; each call returns
    a token that is still valid."""
    return _token_source(KEY_PROVISIONING_FULL_ID, KEY_PROVISIONING_FULL_SECRET).token


@pytest.fixture(scope="session")
def provisioning_full(client, provisioning_full_token):
    """Provisioning service for the client holding manage-budgets and manage-projects."""
    return client.provisioning.with_token(provisioning_full_token)


@pytest.fixture(scope="session")
def provisioning_budgets(client):
    """Provisioning service for the client holding manage-budgets only."""
    source = _token_source(KEY_PROVISIONING_BUDGETS_ID, KEY_PROVISIONING_BUDGETS_SECRET)
    return client.provisioning.with_token(source.token)


@pytest.fixture(scope="session")
def provisioning_read(client):
    """Provisioning service for the client holding read-projects only."""
    source = _token_source(KEY_PROVISIONING_READ_ID, KEY_PROVISIONING_READ_SECRET)
    return client.provisioning.with_token(source.token)


@pytest.fixture(scope="session")
def provisioning_client_names():
    """Collects the client name read back from the budgets the full client creates."""
    return ClientNameRecorder()


@pytest.fixture(scope="session")
def provisioning_client_email(provisioning_full_token, user_utils):
    """CodeMie e-mail of the user behind the full client, confirmed through the admin API.

    Skips the test that needs it when the e-mail cannot be confirmed.
    """
    email = resolve_client_email(
        user_utils,
        provisioning_full_token(),
        CredentialsManager.get_required_parameter(KEY_PROVISIONING_FULL_ID),
    )
    if email is None:
        pytest.skip(
            "the full client's CodeMie e-mail cannot be confirmed: no CodeMie user has the "
            "token's subject as id, or that user has no e-mail the admin list confirms"
        )
    return email


@pytest.fixture
def provisioning_utils(client, project_utils, cost_center_utils, project_budget_groups):
    """Admin-side helper that creates and reads projects; removes what the test and the
    provisioning calls created, after the user fixtures requested before it are still alive."""
    utils = ProvisioningUtils(
        client, project_utils, cost_center_utils, project_budget_groups
    )
    yield utils
    utils.cleanup()
