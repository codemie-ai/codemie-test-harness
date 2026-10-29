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

import pytest

from codemie_test_harness.tests.ui import TRIGGER_ACTIONS
from codemie_test_harness.tests.ui.pageobject.components.unsaved_changes_dialog import (
    UnsavedChangesDialog,
)
from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceType,
)

DISCARD_ACTIONS = [
    pytest.param(
        "cancel_button",
        lambda create_page: create_page.click_cancel(),
        "/data-sources",
        id="cancel_button",
    ),
    pytest.param(
        "menu_navigation",
        lambda create_page: create_page.menu.navigate_to_integrations(),
        "/integrations",
        id="menu_navigation",
    ),
    pytest.param(
        "back_button",
        lambda create_page: create_page.click_back(),
        "/data-sources",
        id="back_button",
    ),
]


@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action", TRIGGER_ACTIONS)
def test_unsaved_changes_after_adding_name(page, action_name, trigger_action):
    """
    Parametrized test that verifies unsaved changes popup appears after adding datasource name
    when performing different actions (Cancel, menu navigation, or Back button).
    """  # Arrange: Navigate to Create Datasource page
    DataSourcePage(page).navigate_to()
    create_page = CreateEditDatasourcePage(page)
    create_page.navigate_to()

    # Act: Add datasource name to trigger unsaved changes
    create_page.fill_name("Test-Datasource-Name")

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(create_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()
    unsaved_dialog.should_have_correct_message()
    unsaved_dialog.should_have_both_buttons()

    # Act: Click Keep Editing
    unsaved_dialog.click_keep_editing()

    # Assert: Dialog should close and user stays on create datasource page
    unsaved_dialog.should_not_be_visible()


@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action", TRIGGER_ACTIONS)
def test_unsaved_changes_after_adding_description(page, action_name, trigger_action):
    """
    Parametrized test that verifies unsaved changes popup appears after adding description
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Navigate to Create Datasource page
    create_page = CreateEditDatasourcePage(page)
    create_page.navigate_to()

    # Act: Add description to trigger unsaved changes
    create_page.fill_description("Test Datasource Description")

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(create_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()
    unsaved_dialog.should_have_correct_message()
    unsaved_dialog.should_have_both_buttons()

    # Act: Click Keep Editing
    unsaved_dialog.click_keep_editing()

    # Assert: Dialog should close and user stays on create datasource page
    unsaved_dialog.should_not_be_visible()


@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action", TRIGGER_ACTIONS)
def test_unsaved_changes_after_selecting_datasource_type(
    page, action_name, trigger_action
):
    """
    Parametrized test that verifies unsaved changes popup appears after selecting datasource type
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Navigate to Create Datasource page
    create_page = CreateEditDatasourcePage(page)
    create_page.navigate_to()

    # Act: Select datasource type to trigger unsaved changes
    create_page.select_datasource_type(DataSourceType.JIRA)

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(create_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()
    unsaved_dialog.should_have_correct_message()
    unsaved_dialog.should_have_both_buttons()

    # Act: Click Keep Editing
    unsaved_dialog.click_keep_editing()

    # Assert: Dialog should close and user stays on create datasource page
    unsaved_dialog.should_not_be_visible()


# Discard Changes Tests
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action, expected_url", DISCARD_ACTIONS)
def test_unsaved_changes_discard_after_adding_name(
    page, action_name, trigger_action, expected_url
):
    """
    Parametrized test that verifies clicking 'Discard Changes' navigates away after adding name
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Navigate to Create Datasource page
    create_page = CreateEditDatasourcePage(page)
    create_page.navigate_to()

    # Act: Add datasource name to trigger unsaved changes
    create_page.fill_name("Test-Datasource-Name")

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(create_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()

    # Act: Click Discard Changes
    unsaved_dialog.click_discard_changes()

    # Assert: Dialog should close and user navigates away
    unsaved_dialog.should_not_be_visible()

    # Verify navigation URL
    create_page.should_have_url_containing(expected_url)


@pytest.mark.datasource
@pytest.mark.ui
def test_no_unsaved_changes_dialog_when_no_changes(page):
    """
    Test that verifies NO unsaved changes dialog appears when there are no changes made.
    """
    # Arrange: Navigate to Create Datasource page
    create_page = CreateEditDatasourcePage(page)
    create_page.navigate_to()

    # Act: Click cancel WITHOUT making any changes
    create_page.click_cancel()

    # Assert: Verify unsaved changes dialog does NOT appear
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_not_be_visible()

    # Verify navigation happened immediately
    create_page.should_have_url_containing("/data-sources")
