"""UI tests for the Users badge of Projects Management.

The 'Users' column of the projects table stays, but its cell is now a badge (aria-label 'Users',
user icon, count) instead of plain text. For a platform admin / maintainer / auditor the badge is
a link to User Management filtered by the project (?projects=<project name>); for anyone else
(e.g. a project admin without a platform role) it is shown without a link.

Projects and users are created through the API and removed by their fixtures; counts are read
back through the SDK. Role accounts of the non-link case come from the module-scoped
`cli_ui_world` fixture (tests/ui/administration/conftest.py).
"""

import pytest
from hamcrest import assert_that, greater_than

from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.user_management_page import (
    UserManagementPage,
)


@pytest.mark.ui
@pytest.mark.project
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
@pytest.mark.project
def test_users_badge_opens_user_management_filtered_by_project(
    page, project_utils, non_admin_user, keycloak_regular_user, project
):
    """Clicking the Users badge opens User Management with
    ?projects=<project name>; the assigned user is listed and the unassigned one is not."""
    assigned_email, assigned_id, _ = non_admin_user
    unassigned_email, _ = keycloak_regular_user
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
@pytest.mark.project
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
