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

"""UI tests for the default project in User Management.

Covers:
  TC-21  Admin sets another project as default in the user details table; the list marker follows
  TC-22  'Add project' dialog: with / without 'Set as default'
  TC-23  Users list marks the default project (and only it); without a stored default the personal one
  TC-24  A maintainer (not a platform admin) can set the default
  TC-25  Auditor sees markers but cannot change them; a plain user cannot open the page
  TC-26  With no stored default the details table selects the personal project only
  TC-27  Project column is wide enough for long project names
  TC-28  Unassigning the default project falls back to the personal project as the default

Deployed behaviour: without a stored default the backend reports the personal project (else
the first project by name) as the default everywhere; the fallback is never persisted.

State is seeded and verified through the SDK; the browser only drives what a test is about.
"""

import pytest
from hamcrest import assert_that, contains_exactly, has_item, not_

from codemie_test_harness.tests.ui.pageobject.administration.user_management_page import (
    UserManagementPage,
)


@pytest.mark.ui
@pytest.mark.user
@pytest.mark.smoke
def test_admin_sets_default_project_in_user_details(
    page, user_utils, default_project_member
):
    """TC-21: details rows show the current default; picking another one persists it and moves
    the marker in the users list."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)
    users_page = UserManagementPage(page).navigate_to()

    users_page.open_user_details(member.email)
    users_page.should_see_default_selected_only_for(member.project_a)
    users_page.set_default_project(member.project_b)
    users_page.should_see_default_selected_only_for(member.project_b)
    users_page.close_user_details()

    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_b),
        "The new default must be persisted and replace the previous one",
    )
    users_page.should_see_default_in_users_list(member.email, member.project_b)


@pytest.mark.ui
@pytest.mark.user
@pytest.mark.parametrize("set_as_default", [True, False], ids=["marked", "unmarked"])
def test_add_project_dialog_default_option(
    page, user_utils, default_project_member, extra_project, set_as_default
):
    """TC-22: the Add Project dialog adds the membership and, only when asked, makes it the default."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)
    users_page = UserManagementPage(page).navigate_to()
    users_page.open_user_details(member.email)

    users_page.add_project(extra_project, set_as_default=set_as_default)

    expected_default = extra_project if set_as_default else member.project_a
    assert_that(
        user_utils.get_user_project_names(member.user_id),
        has_item(extra_project),
        "The project must be added to the user",
    )
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(expected_default),
        "Default must change only when 'Set as default' was switched on",
    )
    users_page.should_see_default_selected_only_for(expected_default)


@pytest.mark.ui
@pytest.mark.user
def test_users_list_marks_only_the_default_project(
    page, user_utils, default_project_member
):
    """TC-23: the Projects cell marks exactly one project: the personal one while no default is
    stored, the stored default once one is set."""
    member = default_project_member
    users_page = UserManagementPage(page).navigate_to()
    users_page.search_user(member.email)
    users_page.should_see_default_in_users_list(member.email, member.personal_project)

    user_utils.set_default_project(member.user_id, member.project_a)
    users_page.navigate_to()
    users_page.search_user(member.email)

    users_page.should_see_default_in_users_list(member.email, member.project_a)


@pytest.mark.ui
@pytest.mark.user
@pytest.mark.parametrize("acting_credentials", ["maintainer"], indirect=True)
def test_maintainer_can_set_default_project(page, user_utils, default_project_member):
    """TC-24: the maintainer role (without platform admin) can manage the default in the UI."""
    member = default_project_member
    users_page = UserManagementPage(page).navigate_to()
    users_page.open_user_details(member.email)
    users_page.should_see_default_controls_enabled()

    users_page.set_default_project(member.project_a)

    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_a),
        "Maintainer's change must be stored",
    )


@pytest.mark.ui
@pytest.mark.user
@pytest.mark.parametrize("acting_credentials", ["auditor"], indirect=True)
def test_auditor_sees_default_project_but_cannot_change_it(
    page, user_utils, default_project_member
):
    """TC-25a: the auditor sees the markers in the list and in the details; no write controls are
    offered and a forced click on another project's Default control changes nothing."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)
    users_page = UserManagementPage(page).navigate_to()
    users_page.should_not_see_write_controls()

    users_page.search_user(member.email)
    users_page.should_see_default_in_users_list(member.email, member.project_a)
    users_page.open_user_details(member.email)
    users_page.should_see_default_selected_only_for(member.project_a)
    users_page.should_see_default_read_only()
    users_page.click_default_control_forcing(member.project_b)

    users_page.should_see_default_selected_only_for(member.project_a)
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_a),
        "A forced click must not change the stored default",
    )


@pytest.mark.ui
@pytest.mark.user
@pytest.mark.parametrize("acting_credentials", ["plain_user"], indirect=True)
def test_plain_user_cannot_open_user_management(page):
    """TC-25b: a user without a user-management role gets 'Not found' instead of the page."""
    page.goto(UserManagementPage.PATH)

    UserManagementPage(page).should_see_not_found()


@pytest.mark.ui
@pytest.mark.user
def test_personal_project_is_shown_as_default_when_none_is_stored(
    page, default_project_member
):
    """TC-26: with no stored default the details table selects the personal project
    only."""
    member = default_project_member
    users_page = UserManagementPage(page).navigate_to()

    users_page.open_user_details(member.email)

    users_page.should_see_default_selected_only_for(member.personal_project)


@pytest.mark.ui
@pytest.mark.user
def test_projects_table_fits_long_project_names_on_one_row(
    page, default_project_member
):
    """TC-27: long names (personal email) stay on one row; columns do not overlap."""
    member = default_project_member
    users_page = UserManagementPage(page).navigate_to()

    users_page.open_user_details(member.email)

    users_page.should_see_project_names_on_single_line([member.personal_project])
    users_page.should_see_projects_table_columns_laid_out(member.personal_project)


@pytest.mark.ui
@pytest.mark.user
def test_unassigning_default_project_falls_back_to_personal_project(
    page, user_utils, default_project_member
):
    """TC-28: after the default project is unassigned in the details dialog, the personal project
    is the reported default, in the SDK and in the users list."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)
    users_page = UserManagementPage(page).navigate_to()
    users_page.open_user_details(member.email)
    users_page.should_see_default_selected_only_for(member.project_a)

    users_page.unassign_project(member.project_a)
    users_page.close_user_details()

    assert_that(
        user_utils.get_user_project_names(member.user_id),
        not_(has_item(member.project_a)),
        "The user must be unassigned from the project",
    )
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.personal_project),
        "The default must fall back to the personal project",
    )
    users_page.should_see_default_in_users_list(member.email, member.personal_project)
