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

"""UI tests for the Users badge of Projects Management.

The 'Users' column of the projects table stays, but its cell is now a badge (aria-label 'Users',
user icon, count) instead of plain text. The badge of a shared project is a link to the Members tab
of the same project (/settings/administration/projects/<project name>/members) for every role that
can open the list, a project admin without a platform role included; the badge of a personal
project is shown without a link.

Projects and users are created through the API and removed by their fixtures; counts are read
back through the SDK. Role accounts of the non-link case come from the module-scoped
`cli_ui_world` fixture (tests/ui/administration/conftest.py).
"""

import pytest
from hamcrest import assert_that, greater_than

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.user_management_page import (
    UserManagementPage,
)


@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.project
@pytest.mark.oss_standalone
def test_users_cell_shows_badge_with_user_count(page, project_utils, project):
    """The Users cell holds a badge (svg icon + count) equal to
    the project's user count from the API; the Users column header remains.

    The zero-users variant cannot be built: the backend never lets the project creator be
    unassigned (400 "Cannot remove the project creator from the project",
    project_assignment_service._reject_if_creator), so every project has at least one user.
    """
    name = project().name
    expected_count = project_utils.get_project_detail(name).user_count
    assert_that(expected_count, greater_than(0), "Project must have at least one user")
    projects_page = ProjectManagementPage(page).navigate_to()

    projects_page.should_list_project(name)

    projects_page.should_see_users_badge(name, expected_count)


@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.project
@pytest.mark.oss_standalone
def test_users_badge_opens_user_management_filtered_by_project(
    page, project_utils, platform_user, second_platform_user, project
):
    """Clicking the Users badge opens User Management with
    ?projects=<project name>; the assigned user is listed and the unassigned one is not."""
    assigned_email, assigned_id = platform_user.email, platform_user.user_id
    unassigned_email = second_platform_user.email
    created = project()
    project_utils.assign_user_to_project(
        created.name, assigned_id, is_project_admin=False
    )
    project_utils.wait_for_project_member(created.name, assigned_id)
    projects_page = ProjectManagementPage(page).navigate_to()
    projects_page.should_list_project(created.name)

    projects_page.click_users_badge(created.name)

    users_page = UserManagementPage(page)
    users_page.should_be_filtered_by_project_in_url(created.name)
    users_page.should_list_user(assigned_email)
    users_page.should_not_list_user(unassigned_email)


@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.project
@pytest.mark.oss_standalone
def test_project_filter_shows_selected_project_after_badge_navigation(page, project):
    """After navigating through the Users badge the project is
    shown as selected in the User Management project filter, not only present in the URL."""
    created = project()
    projects_page = ProjectManagementPage(page).navigate_to()
    projects_page.should_list_project(created.name)

    projects_page.click_users_badge(created.name)

    users_page = UserManagementPage(page)
    users_page.should_be_filtered_by_project_in_url(created.name)
    users_page.should_show_project_selected_in_filter(created.name)


@pytest.mark.ui
@pytest.mark.project
@pytest.mark.parametrize(
    "acting_credentials, badge_is_link",
    [
        pytest.param("cli_project_admin", False, id="project admin - no link"),
        pytest.param("cli_maintainer", True, id="maintainer - link"),
    ],
    indirect=["acting_credentials"],
)
@pytest.mark.oss_standalone
def test_users_badge_is_a_link_only_for_platform_roles(
    page, project_utils, cli_ui_world, acting_credentials, badge_is_link
):
    """The Users badge always shows the count; it is a link to
    User Management for a maintainer and a plain, non-clickable badge for a project admin
    without a platform role."""
    target = cli_ui_world.target
    expected_count = project_utils.get_project_detail(target).user_count
    projects_page = ProjectManagementPage(page).navigate_to()

    projects_page.should_list_project(target)

    projects_page.should_see_users_badge(target, expected_count, as_link=badge_is_link)


# @case project-management-open-project-members_TC_001
@pytest.mark.prod_regression
@pytest.mark.project
@pytest.mark.oss_standalone
@pytest.mark.ui
def test_users_badge_opens_members_tab_of_same_project(
    page, project_utils, platform_user, project
):
    """The Users badge links to the same project's Members tab (the assigned user is
    listed there) and does not open User Management."""
    created = project()
    project_utils.assign_user_to_project(
        created.name, platform_user.user_id, is_project_admin=False
    )
    project_utils.wait_for_project_member(created.name, platform_user.user_id)
    projects_page = ProjectManagementPage(page).navigate_to()
    projects_page.should_list_project(created.name)
    projects_page.should_link_users_badge_to_members_tab(created.name)

    projects_page.click_users_badge(created.name)

    details_page = ProjectDetailsPage(page)
    details_page.should_be_on_members_tab(created.name)
    details_page.should_list_member(platform_user.email)
    details_page.should_not_be_in_user_management()


# @case project-management-open-project-members_TC_002
@pytest.mark.prod_regression
@pytest.mark.project
@pytest.mark.oss_standalone
@pytest.mark.ui
def test_members_tab_stays_selected_on_reload_and_direct_navigation(
    page, project_utils, platform_user, project
):
    """After arriving through the Users badge, a browser reload and a fresh navigation to the
    same Members URL both show the same project with the Members tab selected."""
    created = project()
    project_utils.assign_user_to_project(
        created.name, platform_user.user_id, is_project_admin=False
    )
    project_utils.wait_for_project_member(created.name, platform_user.user_id)
    projects_page = ProjectManagementPage(page).navigate_to()
    projects_page.should_list_project(created.name)
    projects_page.click_users_badge(created.name)
    details_page = ProjectDetailsPage(page)
    details_page.should_be_on_members_tab(created.name)

    details_page.reload()

    details_page.should_be_on_members_tab(created.name)
    details_page.should_list_member(platform_user.email)

    details_page.navigate_to_members(created.name)

    details_page.should_be_on_members_tab(created.name)
    details_page.should_list_member(platform_user.email)


# @case project-management-open-project-members_TC_003
@pytest.mark.prod_regression
@pytest.mark.project
@pytest.mark.oss_standalone
@pytest.mark.ui
def test_project_name_opens_details_on_overview_tab(page, project):
    """Clicking the project name still opens the project details on the default Overview
    tab, not on the Members tab."""
    created = project()
    projects_page = ProjectManagementPage(page).navigate_to()
    projects_page.should_list_project(created.name)

    projects_page.open_project(created.name)

    ProjectDetailsPage(page).should_be_on_overview_tab(created.name)


# @case project-management-open-project-members_TC_004
@pytest.mark.prod_regression
@pytest.mark.project
@pytest.mark.oss_standalone
@pytest.mark.ui
def test_personal_project_users_badge_is_not_a_link(page, platform_user):
    """The Users badge of a personal project (named after its owner's e-mail) is shown
    without a link."""
    personal_project = platform_user.email
    projects_page = ProjectManagementPage(page).navigate_to()

    projects_page.should_list_project(personal_project)

    projects_page.should_see_users_badge_without_link(personal_project)


# @case project-management-open-project-members_TC_005
@pytest.mark.project
@pytest.mark.parametrize("acting_credentials", ["cli_project_admin"], indirect=True)
@pytest.mark.oss_standalone
@pytest.mark.ui
def test_project_admin_without_platform_role_users_link_opens_members_tab(
    page, cli_ui_world, acting_credentials
):
    """A project admin without a platform role gets the Users badge as a link, and it opens
    the Members tab of that project."""
    target = cli_ui_world.target
    projects_page = ProjectManagementPage(page).navigate_to()
    projects_page.should_list_project(target)
    projects_page.should_link_users_badge_to_members_tab(target)

    projects_page.click_users_badge(target)

    ProjectDetailsPage(page).should_be_on_members_tab(target)
