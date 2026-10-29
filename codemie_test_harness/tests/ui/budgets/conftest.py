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

"""UI fixtures for the project budget group distribution tests.

Overrides the `login` autouse fixture from tests/ui/conftest.py so that each
test in this package authenticates as a dynamically created project-admin user.

Fixture hierarchy:
    admin_project_utils  — session-scoped ProjectUtils (admin)
    keycloak_utils       — session-scoped user-management helper
    lite_llm_budget_utils — session-scoped LiteLLM budget helper
    project_admin_setup  — creates project + budget group + project-admin user
    login (autouse)      — overrides ui/conftest.py; logs in as the PA user
"""

import logging
import secrets

import pytest
from hamcrest import assert_that, is_

from codemie_test_harness.tests.test_data.budget_member_override_test_data import (
    MEMBER_OVERRIDE_MAX,
    MEMBER_OVERRIDE_SOFT,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.test_data.budget_test_data import (
    DEFAULT_CLI_BUDGET_ID,
    DEFAULT_PREMIUM_BUDGET_ID,
    project_key_alias,
)
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.project_utils import ProjectUtils


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fixtures not available via tests/conftest.py in the ui/ subtree
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def admin_project_utils(client):
    """Session-scoped ProjectUtils using the admin client."""
    return ProjectUtils(client)


@pytest.fixture(scope="function")
def project_admin_setup(
    admin_project_utils,
    keycloak_utils,
    lite_llm_budget_utils,
):
    """Create an isolated project + budget group + project-admin user.

    Creates the project, then creates a budget group via
    ``POST /v1/admin/project-budget-groups``, then creates a Keycloak user
    and assigns them as project admin.

    Yields:
        tuple: (project_name, group_id, email, password) where ``group_id`` is
        the UUID of the budget group entity and ``email``/``password`` are the
        credentials of the freshly created project-admin user.

    Teardown removes the user from the project, deletes the Keycloak user,
    removes LiteLLM customer records and the project's LiteLLM key for all 3
    categories (tests can redistribute the group to cli/premium_models mid-test,
    creating keys beyond the "platform" one this fixture directly created),
    deletes the budget group, and deletes the project.
    """
    uid = secrets.token_hex(4)
    project_name = f"autotest-pa-ui-{uid}"
    email = f"autotest_pa_ui_{uid}@email.com"
    group_id = None
    user_id = None

    try:
        admin_project_utils.create_project(
            name=project_name, description="Autotest PA UI budget group project"
        )

        # Create the budget group directly via the budget-groups endpoint.
        _admin_client = get_client()
        _group_utils = AdminProjectBudgetGroupUtils(_admin_client)
        group = _group_utils.create_budget_group(
            project_name=project_name,
            total_amount=100.0,
            budget_duration="30d",
            categories={"platform": 100.0},
        )
        group_id = group["group_id"]

        # Create a project-admin user and assign them to the project.
        password = keycloak_utils.create_test_user(
            email=email, project_name=project_name
        )
        user_c = get_client(username=email, password=password)
        user_id = user_c.users.about_me().user_id
        admin_project_utils.assign_user_to_project(
            project_name, user_id, is_project_admin=True
        )
    except Exception:
        if group_id is not None:
            try:
                _group_utils.delete_budget_group(group_id)
            except Exception:
                pass
        try:
            keycloak_utils.delete_user(email)
        except Exception:
            pass
        try:
            admin_project_utils.delete_project(project_name)
        except Exception:
            pass
        raise

    yield project_name, group_id, email, password

    # Teardown — best-effort, never fail the test on cleanup errors.
    try:
        admin_project_utils.remove_user_from_project(project_name, user_id)
    except Exception:
        pass
    try:
        keycloak_utils.delete_user(email)
    except Exception:
        pass
    for customer_id in (
        email,
        f"{email}_{DEFAULT_CLI_BUDGET_ID}",
        f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}",
    ):
        try:
            lite_llm_budget_utils.delete_customer(customer_id)
        except Exception:
            pass
    for category in ("platform", "cli", "premium_models"):
        try:
            lite_llm_budget_utils.delete_key_by_alias(
                project_key_alias(project_name, category)
            )
        except Exception as e:
            logger.warning(
                f"Failed to delete LiteLLM key for project {project_name} "
                f"category {category}: {e}"
            )
    try:
        _group_utils.delete_budget_group(group_id)
    except Exception:
        pass
    try:
        admin_project_utils.delete_project(project_name)
    except Exception:
        pass


@pytest.fixture(scope="function")
def project_admin_setup_client(project_admin_setup):
    """SDK client authenticated as the project-admin user from project_admin_setup."""
    _, _, email, password = project_admin_setup
    return get_client(username=email, password=password)


@pytest.fixture(scope="function")
def member_override_ui_setup(
    project_admin_setup, admin_project_utils, keycloak_regular_user
):
    """Project from project_admin_setup with member tracking on and a developer-only member.

    Yields:
        tuple: (email, password, user_id) of the non-admin project member.
    """
    project_name = project_admin_setup[0]
    email, password = keycloak_regular_user
    user_id = get_client(username=email, password=password).users.about_me().user_id
    admin_project_utils.enable_member_budget_tracking(project_name)
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    yield email, password, user_id
    try:
        admin_project_utils.remove_user_from_project(project_name, user_id)
    except Exception:
        pass


@pytest.fixture(scope="function")
def member_override_ui_ready(
    project_admin_setup, project_admin_setup_client, member_override_ui_setup
):
    """``member_override_ui_setup`` once the project admin is consistently permitted to override.

    Absorbs the propagation lag of the new project admin's membership across
    backend instances before the UI flow depends on it.
    """
    _, group_id, _, _ = project_admin_setup
    _, _, member_id = member_override_ui_setup
    group = AdminProjectBudgetGroupUtils(project_admin_setup_client).get_group(group_id)
    budget_id = AdminProjectBudgetUtils.budget_ids_by_category(group)["platform"]
    permitted = AdminProjectBudgetUtils(
        project_admin_setup_client
    ).wait_until_member_override_permitted(
        budget_id, member_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
    )
    assert_that(
        permitted,
        is_(True),
        "Project admin was not permitted to override a member allocation",
    )
    return member_override_ui_setup


@pytest.fixture(autouse=True)
def login(page, project_admin_setup):
    """Override tests/ui/conftest.py login — authenticate as the project-admin user.

    Depends on ``project_admin_setup`` so the project and user are created before the
    browser session is initialised.
    """
    _, _, email, password = project_admin_setup
    login_page = LoginPage(page)
    user = get_client(username=email, password=password).users.about_me()
    frontend_url = CredentialsManager.get_parameter("FRONTEND_URL", "")
    login_page.login_suppressing_popups(email, password, user.user_id, frontend_url)
