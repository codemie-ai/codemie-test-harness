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

"""UI fixtures for the administration package.

`login` is overridden so a test can choose the acting platform role through the
`acting_credentials` fixture (indirect parametrization); without it the behaviour is
identical to tests/ui/conftest.py (the default AUTH_USERNAME user).

Users and projects with a default project come from the shared fixtures of tests/conftest.py
(`default_project_member`, `maintainer_credentials`).
"""

import os
import secrets
from dataclasses import dataclass

import pytest

from codemie_test_harness.tests.test_data.admin_users_order_test_data import (
    PROJECT_MEMBERS,
)
from codemie_test_harness.tests.test_data.budget_test_data import project_key_alias
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.ui.test_data.project_budget_platform_test_data import (
    starting_budget_categories,
)
from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    assert_principal_is,
    assert_roles_are_real,
    assert_stored_roles,
    wait_until_accessible,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.logger_util import setup_logger
from codemie_test_harness.tests.utils.project_visibility_utils import ProjectFlagUtils
from codemie_test_harness.tests.utils.user_utils import UserUtils

logger = setup_logger(__name__)


def _delete_project_with_members(project_utils, project_name):
    try:
        project_utils.delete_project_with_all_members(project_name)
    except Exception as e:
        logger.warning(f"Failed to delete project {project_name}: {e}")


@pytest.fixture
def extra_project(request, admin_utils, project_utils):
    """A project the member is not part of yet (for the Add project dialog)."""
    name = get_random_name()
    admin_utils.create_project(name)
    request.addfinalizer(lambda: _delete_project_with_members(project_utils, name))
    return name


def _project_member_credentials(request, is_project_admin):
    """(email, password) of a plain platform user assigned to `ownership_project`.

    The user is unassigned and deleted before the project is torn down.
    """
    keycloak_utils = request.getfixturevalue("keycloak_utils")
    project_utils = request.getfixturevalue("project_utils")
    project = request.getfixturevalue("ownership_project")

    email = f"autotest_member_{secrets.token_hex(4)}@email.com"
    password = keycloak_utils.create_platform_user(email=email)
    user_id = get_client(username=email, password=password).users.about_me().user_id
    project_utils.assign_user_to_project(
        project.name, user_id, is_project_admin=is_project_admin
    )

    def _cleanup():
        try:
            project_utils.remove_user_from_project(project.name, user_id)
        except Exception as e:
            logger.warning(f"Failed to unassign {email} from {project.name}: {e}")
        keycloak_utils.delete_user(email)

    request.addfinalizer(_cleanup)
    return email, password


@pytest.fixture
def project_with_ordered_members(ordered_users, project, project_utils):
    """(project name, OrderedUsers): a project the users of PROJECT_MEMBERS are assigned to.

    `ordered_users` is requested first, so the project is deleted before its users are.
    """
    users = ordered_users(PROJECT_MEMBERS)
    created = project()
    for user in users.users:
        project_utils.assign_user_to_project(
            created.name, user.id, is_project_admin=False
        )
        project_utils.wait_for_project_member(created.name, user.id)
    return created.name, users


@pytest.fixture
def acting_credentials(request):
    """(username, password) the browser logs in with. Override via indirect parametrization.

    Roles: admin (default), maintainer, auditor, plain_user, plus two project-scoped roles
    that create a fresh user in `ownership_project`: project_admin_member, plain_member.
    """
    role = getattr(request, "param", "admin")
    if role == "cli_auditor":
        auditor = request.getfixturevalue("verified_auditor_client")
        username, password = request.getfixturevalue("cli_auditor_credentials")
        return (
            username,
            password,
            auditor.users.about_me().user_id,
        )
    if role.startswith("cli_"):
        return request.getfixturevalue("cli_ui_world").credentials[role]
    if role == "project_admin_member":
        return _project_member_credentials(request, is_project_admin=True)
    if role == "plain_member":
        return _project_member_credentials(request, is_project_admin=False)
    if role == "maintainer":
        return request.getfixturevalue("maintainer_credentials")
    if role == "auditor":
        # Existing user-management tests retain their configured auditor. CLI Analytics
        # uses cli_auditor above, with a separately provisioned and verified account.
        return (
            CredentialsManager.get_parameter("AUDITOR_USERNAME"),
            CredentialsManager.get_parameter("AUDITOR_PASSWORD"),
        )
    if role == "plain_user":
        return (
            CredentialsManager.get_parameter("AUTH_USERNAME_DEFAULT"),
            CredentialsManager.get_parameter("AUTH_PASSWORD_DEFAULT"),
        )
    return (
        CredentialsManager.get_parameter("AUTH_USERNAME"),
        CredentialsManager.get_parameter("AUTH_PASSWORD"),
    )


@pytest.fixture(autouse=True)
def login(page, acting_credentials):
    """Override tests/ui/conftest.py login — authenticate as the requested role."""
    username, password, *known_user_id = acting_credentials
    # a role whose user id is known from fixture set-up (3-tuple) logs in once, in the browser
    user_id = (
        known_user_id[0]
        if known_user_id
        else get_client(username=username, password=password).users.about_me().user_id
    )
    LoginPage(page).login_suppressing_popups(
        username,
        password,
        user_id,
        os.getenv("FRONTEND_URL", ""),
    )


@dataclass
class CliAnalyticsUiWorld:
    """Projects and role users the CLI Analytics UI tests of one module share."""

    target: str  # administered by project_admin, member belongs to it
    other: str  # administered by other_project_admin only
    personal: str  # personal project of the unrelated user
    credentials: dict  # role -> (email, password, user_id)
    own_project: dict  # role -> a project that role sees in the list


def _new_user(keycloak_utils, label):
    """Create a plain platform user; returns (email, password, client, user_id)."""
    email = f"autotest_{label}_{secrets.token_hex(4)}@email.com"
    password = keycloak_utils.create_platform_user(email=email)
    client = get_client(username=email, password=password)
    return email, password, client, client.users.about_me().user_id


@pytest.fixture(scope="module")
def cli_ui_world(keycloak_utils, user_utils, admin_utils, project_utils, client):
    """Projects `target` and `other` and one account per role, created once per module (and per
    xdist worker) so the browser logs in once per test. Real roles are asserted before any
    grant: an unrelated user must get 404 (ENV=local makes everyone a global admin), the
    maintainer holds the maintainer flag only."""
    emails = []
    names = [get_random_name() for _ in range(2)]
    try:
        accounts = {}
        for role, label in (
            ("cli_maintainer", "uimaint"),
            ("cli_project_admin", "uipa"),
            ("cli_other_project_admin", "uipa2"),
            ("cli_member", "uimember"),
            ("cli_unrelated_user", "uiunrelated"),
        ):
            email, password, user_client, user_id = _new_user(keycloak_utils, label)
            emails.append(email)
            accounts[role] = (email, password, user_client, user_id)
        for name in names:
            admin_utils.create_project(name)
        assert_roles_are_real(accounts["cli_unrelated_user"][2], names[0])
        maintainer = accounts["cli_maintainer"]
        user_utils.update_admin_user(maintainer[3], is_maintainer=True)
        UserUtils(maintainer[2]).wait_until_user_management_effective()
        assert_principal_is(maintainer[2], maintainer[0])
        # the backend stores is_admin=true for every maintainer ("maintainer implies admin")
        assert_stored_roles(
            user_utils, maintainer[3], is_maintainer=True, is_admin=True
        )
        for role in ("cli_project_admin", "cli_other_project_admin", "cli_member"):
            assert_stored_roles(
                user_utils, accounts[role][3], is_maintainer=False, is_admin=False
            )
        user_utils.assign_user_to_project(
            accounts["cli_project_admin"][3], names[0], is_project_admin=True
        )
        user_utils.assign_user_to_project(
            accounts["cli_other_project_admin"][3], names[1], is_project_admin=True
        )
        user_utils.assign_user_to_project(accounts["cli_member"][3], names[0])
        wait_until_accessible(accounts["cli_project_admin"][2], names[:1])
        wait_until_accessible(accounts["cli_other_project_admin"][2], names[1:])
        wait_until_accessible(accounts["cli_member"][2], names[:1])
        credentials = {role: (a[0], a[1], a[3]) for role, a in accounts.items()}
        credentials["cli_global_admin"] = (
            CredentialsManager.get_parameter("AUTH_USERNAME"),
            CredentialsManager.get_parameter("AUTH_PASSWORD"),
            client.users.about_me().user_id,
        )
        personal = accounts["cli_unrelated_user"][0]
        yield CliAnalyticsUiWorld(
            target=names[0],
            other=names[1],
            personal=personal,
            credentials=credentials,
            own_project={
                "cli_global_admin": names[0],
                "cli_maintainer": names[0],
                "cli_project_admin": names[0],
                "cli_other_project_admin": names[1],
                "cli_member": names[0],
                "cli_unrelated_user": personal,
            },
        )
    finally:
        for name in names:
            _delete_project_with_members(project_utils, name)
        for email in emails:
            try:
                keycloak_utils.delete_user(email)
            except Exception as e:
                logger.warning(f"Failed to delete user {email}: {e}")


@pytest.fixture
def own_project(request, cli_ui_world):
    """A project the acting role sees in the list (positive control for absence checks)."""
    return cli_ui_world.own_project[request.node.callspec.params["acting_credentials"]]


@pytest.fixture
def project_flag_api(client):
    """Raw project reads and flag writes as the harness admin."""
    return ProjectFlagUtils(client)


@pytest.fixture
def budget_group_utils(client):
    """AdminProjectBudgetGroupUtils for reading back what the budget popup saved."""
    return AdminProjectBudgetGroupUtils(client)


@pytest.fixture
def project_with_distributed_budget(
    project_utils, admin_project_budget_utils, lite_llm_budget_utils
):
    """Project with a 1000 budget group split Platform 300 / CLI 600 / Premium Models 100.

    Yields:
        tuple: (project_name, group_id).

    Teardown deletes the LiteLLM keys of all 3 categories (the popup can move budget
    to any of them), the budget group and the project.
    """
    project = project_utils.create_project(
        name=get_random_name(),
        description="autotest platform minimum budget project",
    )
    group_id = None
    try:
        group = admin_project_budget_utils.create_budget_group(
            project_name=project.name,
            name=f"autotest-pm-{secrets.token_hex(4)}",
            categories=starting_budget_categories().categories,
        )
        group_id = group["group_id"]
    except Exception:
        try:
            project_utils.delete_project(project.name)
        except Exception:
            pass
        raise

    yield project.name, group_id

    for category in ("platform", "cli", "premium_models"):
        try:
            lite_llm_budget_utils.delete_key_by_alias(
                project_key_alias(project.name, category)
            )
        except Exception as e:
            logger.warning(
                f"Failed to delete LiteLLM key for project {project.name} "
                f"category {category}: {e}"
            )
    try:
        admin_project_budget_utils.delete_budget_group(group_id)
    except Exception:
        pass
    try:
        project_utils.delete_project(project.name)
    except Exception:
        pass


@pytest.fixture(scope="function")
def disposable_project(project_utils):
    """Create a plain disposable project (no budget group) — the API caller
    becomes its admin, which is all that's required for the Overview tab's
    Budgets/Integrations tabs and summary cards to render (confirmed via live
    inspection: no budget needed). Keeping this separate from a budgeted project
    avoids the hidden LiteLLM integration that budget group creation auto-adds,
    which would otherwise inflate integration counts.
    """
    created = []

    def _make():
        proj = project_utils.create_project(
            name=get_random_name(),
            description="autotest overview summary project (no budget)",
        )
        created.append(proj.name)
        return proj

    yield _make

    for project_name in created:
        try:
            project_utils.delete_project(project_name)
        except Exception as e:
            logger.warning(f"Failed to delete project {project_name}: {e}")
