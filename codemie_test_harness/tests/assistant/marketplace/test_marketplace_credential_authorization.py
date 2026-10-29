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

"""API tests for marketplace credential-picker authorization.

Fixed by MR !4278 ("Scope marketplace credential access by project
membership"): GET /v1/settings/user/available?scope=marketplace previously
returned every PROJECT integration on the platform to any authenticated user,
regardless of project access. The fix makes PROJECT integration visibility
for this endpoint role/access-driven, same as everywhere else (admin/
maintainer -> all projects; applications admin -> their admin projects;
everyone else -> their own project_names).

Uses the shared `non_admin_user` fixture (root conftest.py — disposable
`create_platform_user`, developer role only, "applications" attribute =
their own personal project) rather than the static AUTH_USERNAME_DEFAULT
persona: that persona has a pre-existing ProjectMember row for the default
PROJECT, but access here is driven by the "applications" Keycloak attribute,
not that DB row, and its attribute doesn't include PROJECT — so it can't
tell apart "correctly scoped" from "coincidentally empty".

Scope note: this file only covers the credential-picker listing endpoint
(client.integrations.list_available). A separate, still-open finding was
raised for PUT /v1/assistants/{id}: a marketplace assistant's toolkit
settings can be updated to reference a PROJECT integration the caller has no
access to, without the update being rejected. That save-path gap is tracked
separately and is intentionally not asserted against here.
"""

import pytest
from hamcrest import assert_that, has_item, is_not

from codemie_sdk.models.integration import CredentialTypes
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.fixture
def isolated_project_credential(admin_utils, integration_utils, project_utils):
    """A fresh project (only the admin `client` is a member of) with one
    PROJECT-scoped credential in it — a credential `non_admin_user` has no
    legitimate access to."""
    project_name = get_random_name()
    admin_utils.create_project(project_name)
    integration = integration_utils.create_project_integration(
        CredentialTypes.FILESYSTEM,
        CredentialsManager.file_system_credentials(),
        project_name,
    )
    yield integration
    integration_utils.delete_integration(integration)
    project_utils.delete_project(project_name)


@pytest.fixture
def accessible_project_credential(non_admin_user, integration_utils):
    """A PROJECT-scoped credential in `non_admin_user`'s own personal
    project — a credential they genuinely have access to."""
    email, _member_id, _member_client = non_admin_user
    integration = integration_utils.create_project_integration(
        CredentialTypes.FILESYSTEM,
        CredentialsManager.file_system_credentials(),
        email,
    )
    yield integration
    integration_utils.delete_integration(integration)


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_marketplace_credential_picker_excludes_inaccessible_project(
    non_admin_user, isolated_project_credential
):
    """TC-01: a user with no access to a project must not see that project's
    PROJECT credential in the marketplace credential picker — the exact
    cross-project leak this ticket fixes."""
    _email, _member_id, member_client = non_admin_user
    leaked_integration = isolated_project_credential

    available = member_client.integrations.list_available(scope="marketplace")

    assert_that(
        [item.id for item in available],
        is_not(has_item(leaked_integration.id)),
        "Marketplace credential picker leaked a PROJECT credential from a "
        "project the caller has no access to.",
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_marketplace_credential_picker_includes_accessible_project_integration(
    non_admin_user, accessible_project_credential
):
    """TC-02 (regression guard, AC-8): a PROJECT credential from a project
    the caller genuinely has access to (their own personal project) must
    still appear in the marketplace credential picker — the fix must not
    over-correct into hiding legitimately accessible credentials."""
    _email, _member_id, member_client = non_admin_user

    available = member_client.integrations.list_available(scope="marketplace")

    assert_that(
        [item.id for item in available],
        has_item(accessible_project_credential.id),
        "Credential picker should include PROJECT credentials from a "
        "project the caller has access to.",
    )
