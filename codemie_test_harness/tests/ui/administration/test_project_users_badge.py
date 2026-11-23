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

"""Project Users badges open Members for shared projects, including project admins."""

import pytest
from hamcrest import assert_that, greater_than

from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_members_section import (
    ProjectMembersSection,
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
def test_users_badge_opens_project_members(
    page, project_utils, platform_user, second_platform_user, project
):
    """The project's Members page lists its assigned user and excludes an outsider."""
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

    ProjectDetailsPage(page).should_have_members_url(created.name)
    members = ProjectMembersSection(page)
    members.should_list_member(assigned_email)
    members.should_not_list_member(unassigned_email)


@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.project
@pytest.mark.oss_standalone
def test_members_tab_is_selected_after_badge_navigation(page, project):
    """The Members tab is selected after following the project's Users badge."""
    created = project()
    projects_page = ProjectManagementPage(page).navigate_to()
    projects_page.should_list_project(created.name)

    projects_page.click_users_badge(created.name)

    details = ProjectDetailsPage(page)
    details.should_have_members_url(created.name)
    details.should_have_members_tab_selected()


@pytest.mark.ui
@pytest.mark.project
@pytest.mark.parametrize(
    "acting_credentials",
    [
        pytest.param("cli_project_admin", id="project-admin-link"),
        pytest.param("cli_maintainer", id="maintainer-link"),
    ],
    indirect=["acting_credentials"],
)
@pytest.mark.oss_standalone
def test_shared_project_users_badge_is_a_link_for_project_and_platform_admins(
    page, project_utils, cli_ui_world, acting_credentials
):
    """Both project admins and maintainers can follow a shared project's Members link."""
    target = cli_ui_world.target
    expected_count = project_utils.get_project_detail(target).user_count
    projects_page = ProjectManagementPage(page).navigate_to()

    projects_page.should_list_project(target)

    projects_page.should_see_users_badge(target, expected_count, as_link=True)
    projects_page.click_users_badge(target)
    ProjectDetailsPage(page).should_have_members_url(target)
