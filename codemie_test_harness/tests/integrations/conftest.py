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

import secrets
from typing import Optional

import pytest
from requests import HTTPError

from codemie_sdk.models.integration import CredentialTypes, Integration, IntegrationType
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils
from codemie_test_harness.tests.utils.keycloak_utils import KeycloakUtils
from codemie_test_harness.tests.utils.local_user_utils import LocalUserUtils


@pytest.fixture(scope="module")
def litellm_keycloak_utils(client):
    if EnvironmentResolver.is_localhost():
        return LocalUserUtils(client)
    return KeycloakUtils()


@pytest.fixture
def non_admin_user(litellm_keycloak_utils):
    uid = secrets.token_hex(4)
    email = f"autotest_litellm_{uid}@email.com"
    password = litellm_keycloak_utils.create_platform_user(email=email)
    member_client = get_client(username=email, password=password)
    member_id = member_client.users.about_me().user_id
    yield email, member_id, member_client
    litellm_keycloak_utils.delete_user(email)


@pytest.fixture
def non_admin_integration_utils(non_admin_user):
    _, _, member_client = non_admin_user
    return IntegrationUtils(member_client)


@pytest.fixture
def disposable_maintainer_client(litellm_keycloak_utils, user_utils):
    """A CodeMie client for a disposable user promoted to platform maintainer.

    ``is_maintainer=True`` satisfies the ``admin_or_maintainer_access_only``
    guard on POST /v1/settings/transfer regardless of project membership --
    used for TC-09's "maintainer" positive-role row.
    """
    uid = secrets.token_hex(4)
    email = f"autotest_maintainer_{uid}@email.com"
    password = litellm_keycloak_utils.create_test_user(email=email, project_name=email)
    user_client = get_client(username=email, password=password)
    user_id = user_client.users.about_me().user_id
    user_utils.update_admin_user(user_id, is_maintainer=True)
    yield user_client
    litellm_keycloak_utils.delete_user(email)


@pytest.fixture
def admin_client(litellm_keycloak_utils, user_utils):
    """A CodeMie client for a disposable user promoted to platform admin.

    ``is_admin=True`` satisfies the ``admin_or_maintainer_access_only`` guard
    on POST /v1/settings/transfer -- used for TC-09's "admin"
    positive-role row.
    """
    uid = secrets.token_hex(4)
    email = f"autotest_admin_{uid}@email.com"
    password = litellm_keycloak_utils.create_test_user(email=email, project_name=email)
    user_client = get_client(username=email, password=password)
    user_id = user_client.users.about_me().user_id
    user_utils.update_admin_user(user_id, is_admin=True)
    yield user_client
    litellm_keycloak_utils.delete_user(email)


@pytest.fixture
def non_admin_general_integration(non_admin_user, non_admin_integration_utils):
    email, _, _ = non_admin_user
    created_integration: Optional[Integration] = None

    def _create(
        integration_type: IntegrationType,
        credential_type: CredentialTypes,
        credential_values: list,
        integration_alias: str = None,
    ):
        nonlocal created_integration
        created_integration = non_admin_integration_utils.create_integration(
            credential_type=credential_type,
            credential_values=credential_values,
            setting_type=integration_type,
            integration_alias=integration_alias,
            project_name=email,
        )
        return created_integration

    yield _create

    if created_integration:
        try:
            non_admin_integration_utils.delete_integration(created_integration)
        except HTTPError:
            pass
