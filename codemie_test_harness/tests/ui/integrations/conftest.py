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

"""UI fixtures for the Integrations tests.

Overrides the `login` autouse fixture of tests/ui/conftest.py. A test without a marker signs in
as the harness account, like everywhere else in tests/ui. A test marked
`@pytest.mark.ui_login_as("<role>")` signs in as a fresh user of that role (`UI_LOGIN_USERS`);
the test seeds rows through the API as that user and cleans them up through the API.
"""

import pytest

from codemie_sdk.models.integration import IntegrationType
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils

UI_LOGIN_USERS = {
    "project_admin": "project_admin_user",
    "member": "platform_user",
    "project_admin_member_of_project_b": "project_admin_member_of_project_b",
}


@pytest.fixture
def project_admin_member_of_project_b(
    project_admin_user, default_project_member, user_utils
):
    """The project admin of project A, made a plain member of project B before signing in."""
    user_utils.assign_user_to_project(
        project_admin_user.user_id, default_project_member.project_b
    )
    return project_admin_user


@pytest.fixture
def ui_login_user(request):
    """The user the browser signs in as: the one of the `ui_login_as` marker, else None."""
    marker = request.node.get_closest_marker("ui_login_as")
    if marker is None:
        return None
    role = marker.args[0]
    if role not in UI_LOGIN_USERS:
        raise ValueError(
            f"Unknown ui_login_as role {role!r}; expected one of {sorted(UI_LOGIN_USERS)}"
        )
    return request.getfixturevalue(UI_LOGIN_USERS[role])


@pytest.fixture(autouse=True)
def login(page, ui_login_user):
    """Override tests/ui/conftest.py login: sign in as `ui_login_user`, else as the harness account."""
    frontend_url = CredentialsManager.get_parameter("FRONTEND_URL", "")
    if ui_login_user is None:
        LoginPage(page).login_suppressing_popups(
            CredentialsManager.get_parameter("AUTH_USERNAME"),
            CredentialsManager.get_parameter("AUTH_PASSWORD"),
            get_client().users.about_me().user_id,
            frontend_url,
        )
        return
    LoginPage(page).login_suppressing_popups(
        ui_login_user.email,
        ui_login_user.password,
        ui_login_user.user_id,
        frontend_url,
    )


@pytest.fixture
def project_admin_integrations(fresh_project_admin_client) -> IntegrationUtils:
    """Integration helper of the project admin, logged in after the role was assigned."""
    return IntegrationUtils(fresh_project_admin_client)


@pytest.fixture
def seed_integration(
    project_admin_user,
    default_project_member,
    project_admin_integrations,
    scoped_integrations,
):
    """Factory: create an integration of the project admin through the API; returns its alias.

    A user integration belongs to the admin's own project; a project integration to the project
    the admin administers. The row is deleted after the test.
    """

    def _seed(setting_type: IntegrationType, is_global: bool = False) -> str:
        project = (
            default_project_member.project_a
            if setting_type == IntegrationType.PROJECT
            else project_admin_user.email
        )
        alias = get_random_name()
        scoped_integrations.create(
            project_admin_integrations,
            setting_type,
            project,
            alias,
            is_global=is_global,
        )
        return alias

    return _seed
