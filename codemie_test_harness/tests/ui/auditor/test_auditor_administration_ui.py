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

"""Auditor role — Administration UI tests (Projects, Users, Budgets, Write-denial).

Covers:
  TC-004  Auditor accesses Projects section — sidebar visible, project table visible (UI)
  TC-005  Auditor accesses Users section — sidebar visible, user list visible, details openable (UI)
  TC-006  Auditor accesses Budgets section — sidebar visible, budget list visible (UI)
  TC-013  Auditor has no write controls visible in UI across projects, users, budgets (UI)

API tests live in tests/auditor/.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.budgets_management_page import (
    BudgetsManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.settings_sidebar_page import (
    SettingsSidebarPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.user_management_page import (
    UserManagementPage,
)
from codemie_test_harness.tests.ui.test_data.auditor_test_data import (
    SIDEBAR_ITEM_BUDGETS,
    SIDEBAR_ITEM_PROJECTS,
    SIDEBAR_ITEM_USERS,
)


# ── TC-004 ────────────────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_sees_projects_sidebar_item(page):
    """TC-004 (UI): 'Projects management' item is visible in the Settings sidebar.

    Navigates to the Projects Management page first so the settings sidebar is rendered,
    then asserts the sidebar item is present.

    AC-5: Auditor can navigate to the Projects section from the sidebar.
    """
    projects_page = ProjectManagementPage(page)
    projects_page.navigate_to()
    sidebar = SettingsSidebarPage(page)
    sidebar.should_see_sidebar_item(SIDEBAR_ITEM_PROJECTS)


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_can_view_projects_list(page):
    """TC-004 (UI): Auditor can open the Projects Management page and see a project table.

    AC-6: The projects table is rendered with rows — the auditor can read all projects.
    """
    projects_page = ProjectManagementPage(page)
    projects_page.navigate_to()
    projects_page.should_see_project_table()


# ── TC-005 ────────────────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_sees_users_sidebar_item(page):
    """TC-005 (UI): 'Users management' item is visible in the Settings sidebar.

    Navigates to the Users Management page first so the settings sidebar is rendered.

    AC-8: Auditor can navigate to the Users section from the sidebar.
    """
    users_page = UserManagementPage(page)
    users_page.navigate_to()
    sidebar = SettingsSidebarPage(page)
    sidebar.should_see_sidebar_item(SIDEBAR_ITEM_USERS)


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_can_view_users_list(page):
    """TC-005 (UI): Auditor can open the Users Management page and see at least one user.

    AC-9: The users table is rendered with rows — the auditor can read all users.
    """
    users_page = UserManagementPage(page)
    users_page.navigate_to()
    users_page.should_see_user_list_not_empty()


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_can_open_user_details(page):
    """TC-005 (UI): Auditor can open the User Details dialog for a user.

    AC-9: Auditor has read-only access to individual user details including
    project memberships.  The user table is paginated so we open the first
    user visible on page 1 rather than searching for a specific email address.
    """
    users_page = UserManagementPage(page)
    users_page.navigate_to()
    users_page.open_first_user_detail()
    users_page.should_see_user_detail_fields()


# ── TC-006 ────────────────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_sees_budgets_sidebar_item(page):
    """TC-006 (UI): 'Budgets management' item is visible in the Settings sidebar.

    Navigates to the Budgets Management page first so the settings sidebar is rendered.

    AC-11: Auditor can navigate to the Budgets section from the sidebar.
    """
    budgets_page = BudgetsManagementPage(page)
    budgets_page.navigate_to()
    sidebar = SettingsSidebarPage(page)
    sidebar.should_see_sidebar_item(SIDEBAR_ITEM_BUDGETS)


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_can_view_budgets_list(page):
    """TC-006 (UI): Auditor navigates to Budgets page and sees budget rows.

    AC-12: The Budgets page renders without redirect and the budget table contains rows.
    """
    budgets_page = BudgetsManagementPage(page)
    budgets_page.navigate_to()
    budgets_page.should_see_budget_list_not_empty()


# ── TC-013 ────────────────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_has_no_project_write_controls_in_ui(page):
    """TC-013 (Projects): Auditor action menu for projects shows View only — no Edit/Delete.

    AC-7: Write controls (Edit, Delete, Manage members) are absent from the project row
    action menu when the session belongs to an auditor.
    """
    projects_page = ProjectManagementPage(page)
    projects_page.navigate_to()
    first_row = projects_page.project_rows.first
    first_row.wait_for(state="visible", timeout=15000)
    project_name_cell = first_row.locator("td").first
    raw_text = project_name_cell.text_content() or ""
    project_name = raw_text.strip().split(" ")[0]
    if not project_name:
        pytest.skip("No project name found in first row — cannot verify write controls")
    projects_page.should_not_see_write_controls(project_name)


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_has_no_user_write_controls_in_ui(page):
    """TC-013 (Users): Auditor Users Management page has no create/invite button.

    AC-10: No 'Create user' / 'Invite' button is exposed to an auditor.
    """
    users_page = UserManagementPage(page)
    users_page.navigate_to()
    users_page.should_not_see_write_controls()


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_has_no_budget_write_controls_in_ui(page):
    """TC-013 (Budgets): Auditor Budgets Management page has no create/sync button.

    AC-13: No 'Create budget' or 'Sync' button is exposed to an auditor.
    """
    budgets_page = BudgetsManagementPage(page)
    budgets_page.navigate_to()
    budgets_page.should_not_see_write_controls()
