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
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)

DISCARD_ACTIONS = [
    pytest.param(
        "cancel_button",
        lambda create_page: create_page.click_cancel(),
        "/assistants",
        id="cancel_button",
    ),
    pytest.param(
        "menu_navigation",
        lambda create_page: create_page.menu.navigate_to_workflows(),
        "/workflows",
        id="menu_navigation",
    ),
    pytest.param(
        "back_button",
        lambda create_page: create_page.click_back(),
        "/assistants",
        id="back_button",
    ),
]


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action", TRIGGER_ACTIONS)
@pytest.mark.prod_regression
def test_unsaved_changes_after_adding_name(page, action_name, trigger_action):
    """
    Parametrized test that verifies unsaved changes popup appears after adding assistant name
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Start from Assistants page and click Create Assistant
    assistants_page = AssistantsPage(page)
    create_page = assistants_page.click_create_assistant()
    create_page.should_be_on_create_assistant_page()

    # Act: Add assistant name to trigger unsaved changes
    create_page.fill_name("Test Assistant Name")

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(create_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()
    unsaved_dialog.should_have_correct_message()
    unsaved_dialog.should_have_both_buttons()

    # Act: Click Keep Editing
    unsaved_dialog.click_keep_editing()

    # Assert: Dialog should close and user stays on create assistant page
    unsaved_dialog.should_not_be_visible()
    create_page.should_be_on_create_assistant_page()
    create_page.should_have_name_value("Test Assistant Name")


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action", TRIGGER_ACTIONS)
@pytest.mark.prod_regression
def test_unsaved_changes_after_adding_description(page, action_name, trigger_action):
    """
    Parametrized test that verifies unsaved changes popup appears after adding description
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Start from Assistants page and click Create Assistant
    assistants_page = AssistantsPage(page)
    create_page = assistants_page.click_create_assistant()
    create_page.should_be_on_create_assistant_page()

    # Act: Add description to trigger unsaved changes
    create_page.fill_description("Test Assistant Description")

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(create_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()
    unsaved_dialog.should_have_correct_message()
    unsaved_dialog.should_have_both_buttons()

    # Act: Click Keep Editing
    unsaved_dialog.click_keep_editing()

    # Assert: Dialog should close and user stays on create assistant page
    unsaved_dialog.should_not_be_visible()
    create_page.should_be_on_create_assistant_page()
    create_page.should_have_description_value("Test Assistant Description")


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action", TRIGGER_ACTIONS)
@pytest.mark.prod_regression
def test_unsaved_changes_after_adding_system_prompt(page, action_name, trigger_action):
    """
    Parametrized test that verifies unsaved changes popup appears after adding system prompt
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Start from Assistants page and click Create Assistant
    assistants_page = AssistantsPage(page)
    create_page = assistants_page.click_create_assistant()
    create_page.should_be_on_create_assistant_page()

    # Act: Add system prompt to trigger unsaved changes
    test_prompt = "You are a helpful assistant that provides accurate information."
    create_page.fill_system_prompt(test_prompt)

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(create_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()
    unsaved_dialog.should_have_correct_message()
    unsaved_dialog.should_have_both_buttons()

    # Act: Click Keep Editing
    unsaved_dialog.click_keep_editing()

    # Assert: Dialog should close and user stays on create assistant page
    unsaved_dialog.should_not_be_visible()
    create_page.should_be_on_create_assistant_page()
    create_page.should_have_system_prompt_value(test_prompt)


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action", TRIGGER_ACTIONS)
@pytest.mark.prod_regression
def test_edit_assistant_unsaved_changes_after_modifying_name(
    page, assistant, action_name, trigger_action
):
    """
    Parametrized test that verifies unsaved changes popup appears after modifying assistant name
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Navigate to Edit Assistant page via Assistants page
    test_assistant = assistant()
    assistants_page = AssistantsPage(page)
    assistants_page.search_assistants(test_assistant.name)
    edit_page = assistants_page.click_assistant_edit(test_assistant.name)

    # Act: Modify assistant name
    modified_name = f"{test_assistant.name}_modified"
    edit_page.fill_name(modified_name)

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(edit_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()
    unsaved_dialog.should_have_correct_message()
    unsaved_dialog.should_have_both_buttons()

    # Act: Click Keep Editing
    unsaved_dialog.click_keep_editing()

    # Assert: Dialog should close and user stays on edit assistant page
    unsaved_dialog.should_not_be_visible()
    edit_page.should_have_name_value(modified_name)


# Discard Changes Tests
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action, expected_url", DISCARD_ACTIONS)
@pytest.mark.prod_regression
def test_unsaved_changes_discard_after_adding_name(
    page, action_name, trigger_action, expected_url
):
    """
    Parametrized test that verifies clicking 'Discard Changes' navigates away after adding name
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Start from Assistants page and click Create Assistant
    assistants_page = AssistantsPage(page)
    create_page = assistants_page.click_create_assistant()
    create_page.should_be_on_create_assistant_page()

    # Act: Add assistant name to trigger unsaved changes
    create_page.fill_name("Test Assistant Name")

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


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_no_unsaved_changes_dialog_when_no_changes(page):
    """
    Test that verifies NO unsaved changes dialog appears when there are no changes made.
    """
    # Arrange: Start from Assistants page and click Create Assistant
    assistants_page = AssistantsPage(page)
    create_page = assistants_page.click_create_assistant()
    create_page.should_be_on_create_assistant_page()

    # Act: Click cancel WITHOUT making any changes
    create_page.click_cancel()

    # Assert: Verify unsaved changes dialog does NOT appear
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_not_be_visible()

    # Verify navigation happened immediately
    create_page.should_have_url_containing("/assistants")
