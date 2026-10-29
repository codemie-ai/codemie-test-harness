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

"""UI tests for changing a project's owner from the projects list.

Covers:
  TC-001  "Change ownership" in the row actions menu: shown to a platform admin and to a
          project admin of the project, hidden from a plain member
  TC-002  Changing the owner through the popup: toast, closed popup, new owner on the details page

Projects and users are created through the API (`ownership_project`, `non_admin_user`) and
removed by their fixtures; the browser only drives the flow under test.
"""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.ui.pageobject.administration.change_ownership_modal_page import (
    ChangeOwnershipModalPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.test_data.project_ownership_ui_test_data import (
    CHANGE_OWNERSHIP_VISIBILITY,
    CHANGE_OWNERSHIP_VISIBILITY_IDS,
)


@pytest.mark.ui
@pytest.mark.project
@pytest.mark.parametrize(
    "acting_credentials, change_ownership_visible",
    CHANGE_OWNERSHIP_VISIBILITY,
    ids=CHANGE_OWNERSHIP_VISIBILITY_IDS,
    indirect=["acting_credentials"],
)
def test_change_ownership_menu_item_visibility(
    page, ownership_project, acting_credentials, change_ownership_visible
):
    """
    platform admin and a project admin, and does not offer it to a plain member.
    """
    projects_page = ProjectManagementPage(page).navigate_to()
    projects_page.search_for(ownership_project.name)

    projects_page.open_row_action_menu(ownership_project.name)

    projects_page.should_offer_change_ownership(change_ownership_visible)


@pytest.mark.ui
@pytest.mark.project
def test_change_project_owner_through_popup(
    page, client, project_utils, non_admin_user, ownership_project
):
    """
    until a new owner is picked, confirming shows the toast and closes the popup, and the new
    owner is persisted and shown as "Owned by" on the project details page.
    """
    new_owner_email, new_owner_id, new_owner_client = non_admin_user
    current_owner = client.users.about_me()
    new_owner_name = new_owner_client.users.about_me().name
    projects_page = ProjectManagementPage(page).navigate_to()
    projects_page.search_for(ownership_project.name)
    modal = ChangeOwnershipModalPage(page)

    projects_page.click_change_ownership(ownership_project.name)

    modal.should_be_visible()
    modal.should_show_current_owner(f"{current_owner.name} ({current_owner.email})")
    modal.should_have_new_owner_select()
    modal.should_have_confirm_disabled()

    modal.select_new_owner(new_owner_email)
    modal.should_have_confirm_enabled()
    modal.confirm()

    projects_page.should_see_ownership_transferred_toast(new_owner_name)
    modal.should_be_closed()
    assert_that(
        project_utils.get_project_detail(ownership_project.name).created_by,
        equal_to(new_owner_id),
        "The new owner must be persisted after Confirm",
    )
    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(ownership_project.name)
    details_page.should_show_owner(new_owner_name)
