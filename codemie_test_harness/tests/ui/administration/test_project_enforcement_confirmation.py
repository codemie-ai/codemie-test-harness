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

"""UI regression tests for the enforcement confirmation inside Edit Project.

Changing 'Enforce member spend limits' and pressing Save opens a confirmation above Edit Project.
Escape on that confirmation must behave like Cancel: close only the confirmation. Once only Edit
Project is open, Escape closes it. While the confirmed save is in flight, nothing the user does
on either dialog sends a second save or closes a dialog.

The project is created through the API; the browser performs the action under test; the
stored state is read back through the API.
"""

import pytest
from hamcrest import assert_that, equal_to, is_

from codemie_test_harness.tests.ui.pageobject.administration.enforcement_confirmation_dialog import (
    EnforcementConfirmationDialog,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_modal_page import (
    ProjectModal,
)
from codemie_test_harness.tests.ui.test_data.project_enforcement_test_data import (
    DESCRIPTION_SUFFIX,
    ORIGINAL_DESCRIPTION,
)


# @case project-admin-enforcement-switch-confirmation_TC_005
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_escape_on_enforcement_confirmation_keeps_edit_project_open(
    page, project, project_utils
):
    """Escape on the enforcement confirmation closes only the confirmation: Edit Project stays
    open with the unsaved description edit, the switch returns to its stored value and nothing
    is saved.
    """
    created = project(description=ORIGINAL_DESCRIPTION)
    edited_description = ORIGINAL_DESCRIPTION + DESCRIPTION_SUFFIX
    stored_enforcement = project_utils.get_project_detail(
        created.name
    ).enforce_member_spend_limits

    management_page = ProjectManagementPage(page)
    modal = ProjectModal(page)
    confirmation = EnforcementConfirmationDialog(page)

    management_page.navigate_to()
    # the table is paged; filter it so the fresh project's row is on the visible page
    management_page.search_for(created.name)
    management_page.click_edit_project(created.name)
    modal.should_show_enforcement_switch()
    modal.should_have_enforcement_value(stored_enforcement)
    modal.should_have_edit_description(ORIGINAL_DESCRIPTION)

    modal.append_to_edit_description(DESCRIPTION_SUFFIX)
    modal.toggle_enforcement()
    modal.should_have_enforcement_value(not stored_enforcement)

    modal.click_save_to_confirm_enforcement()
    confirmation.should_be_visible()
    modal.should_remain_open_for_editing()

    confirmation.press_escape()

    confirmation.should_be_closed()
    modal.should_remain_open_for_editing()
    modal.should_have_edit_description(edited_description)
    modal.should_have_enforcement_value(stored_enforcement)

    detail = project_utils.get_project_detail(created.name)
    assert_that(
        detail.description,
        equal_to(ORIGINAL_DESCRIPTION),
        "Escape must not save the edited description",
    )
    assert_that(
        detail.enforce_member_spend_limits,
        is_(stored_enforcement),
        "Escape must not change the stored enforcement setting",
    )


# @case project-admin-enforcement-switch-confirmation_TC_007
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_escape_while_enforcement_save_is_pending_keeps_edit_project_open(
    page, project, project_utils
):
    """While the confirmed save is still in flight: a double click on Confirm sends exactly one
    project PATCH, Confirm and Edit Project's Save are disabled, and Escape and Cancel change
    nothing (both dialogs stay open with the user's edits). Once the real backend answers, both
    dialogs close, the user is told the project was updated and the save stores both the
    description and the enforcement setting; no second PATCH follows.

    The save request is held in the browser and then sent unchanged to the backend, so the
    pending state lasts exactly as long as the test needs.
    """
    created = project(description=ORIGINAL_DESCRIPTION)
    edited_description = ORIGINAL_DESCRIPTION + DESCRIPTION_SUFFIX
    stored_enforcement = project_utils.get_project_detail(
        created.name
    ).enforce_member_spend_limits

    management_page = ProjectManagementPage(page)
    modal = ProjectModal(page)
    confirmation = EnforcementConfirmationDialog(page)

    management_page.navigate_to()
    # the table is paged; filter it so the fresh project's row is on the visible page
    management_page.search_for(created.name)
    management_page.click_edit_project(created.name)
    modal.should_show_enforcement_switch()
    modal.should_have_enforcement_value(stored_enforcement)

    modal.append_to_edit_description(DESCRIPTION_SUFFIX)
    modal.toggle_enforcement()
    modal.click_save_to_confirm_enforcement()
    confirmation.should_be_visible()

    modal.start_counting_save_requests(created.name)
    modal.hold_save_requests(created.name)
    confirmation.double_click_confirm_capturing_save(created.name)
    confirmation.should_be_pending()
    modal.should_have_save_disabled()

    confirmation.press_escape()

    modal.should_remain_open_for_editing()
    confirmation.should_be_pending()

    confirmation.click_cancel_while_pending()

    modal.should_remain_open_for_editing()
    modal.should_have_save_disabled()
    confirmation.should_be_pending()
    modal.should_have_edit_description(edited_description)
    modal.should_have_enforcement_value(not stored_enforcement)
    assert_that(
        modal.sent_save_count,
        equal_to(1),
        "a double click on Confirm, Escape and Cancel send one project PATCH in total",
    )
    assert_that(
        project_utils.get_project_detail(created.name).description,
        equal_to(ORIGINAL_DESCRIPTION),
        "nothing is stored while the save is held",
    )
    # Checked again after the API read, which outlasts PrimeReact's dialog exit transition:
    # a dialog that Escape or Cancel started closing would be gone by now.
    modal.should_remain_open_for_editing()
    modal.should_have_save_disabled()
    modal.should_have_enforcement_value(not stored_enforcement)
    confirmation.should_be_pending()

    modal.release_held_save_requests()

    modal.should_show_project_updated_toast(created.name)
    confirmation.should_be_closed()
    modal.should_not_have_edit_dialog()
    assert_that(
        modal.stop_counting_save_requests(),
        equal_to(1),
        "no second project PATCH follows once the backend answers",
    )
    detail = project_utils.get_project_detail(created.name)
    assert_that(
        detail.description,
        equal_to(edited_description),
        "The confirmed save must store the edited description",
    )
    assert_that(
        detail.enforce_member_spend_limits,
        is_(not stored_enforcement),
        "The confirmed save must store the new enforcement setting",
    )


# @case project-admin-enforcement-switch-confirmation_TC_006
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_escape_closes_edit_project_once_no_confirmation_is_above_it(
    page, project, project_utils
):
    """After Cancel on the enforcement confirmation, Escape closes Edit Project and stores
    nothing. Escape also closes an Edit Project that never had a confirmation above it."""
    created = project(description=ORIGINAL_DESCRIPTION)
    stored_enforcement = project_utils.get_project_detail(
        created.name
    ).enforce_member_spend_limits

    management_page = ProjectManagementPage(page)
    modal = ProjectModal(page)
    confirmation = EnforcementConfirmationDialog(page)

    management_page.navigate_to()
    # the table is paged; filter it so the fresh project's row is on the visible page
    management_page.search_for(created.name)
    management_page.click_edit_project(created.name)
    modal.should_show_enforcement_switch()
    modal.append_to_edit_description(DESCRIPTION_SUFFIX)
    modal.toggle_enforcement()
    modal.click_save_to_confirm_enforcement()
    confirmation.should_be_visible()
    confirmation.cancel()

    confirmation.should_be_closed()
    modal.should_remain_open_for_editing()

    modal.press_escape()

    modal.should_not_have_edit_dialog()
    detail = project_utils.get_project_detail(created.name)
    assert_that(
        detail.description,
        equal_to(ORIGINAL_DESCRIPTION),
        "Escape on Edit Project must not save the edited description",
    )
    assert_that(
        detail.enforce_member_spend_limits,
        is_(stored_enforcement),
        "Escape on Edit Project must not change the stored enforcement setting",
    )

    management_page.search_for(created.name)
    management_page.click_edit_project(created.name)
    modal.should_show_enforcement_switch()
    modal.should_have_enforcement_value(stored_enforcement)
    modal.should_have_edit_description(ORIGINAL_DESCRIPTION)

    modal.press_escape()

    modal.should_not_have_edit_dialog()
