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
from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)


DISCARD_ACTIONS = [
    pytest.param(
        "cancel_button",
        lambda create_page: create_page.click_cancel(),
        "/workflows",
        id="cancel_button",
    ),
    pytest.param(
        "menu_navigation",
        lambda create_page: create_page.menu.navigate_to_assistants(),
        "/assistants",
        id="menu_navigation",
    ),
    pytest.param(
        "back_button",
        lambda create_page: create_page.click_back(),
        "/workflows",
        id="back_button",
    ),
]


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action", TRIGGER_ACTIONS)
@pytest.mark.prod_regression
def test_unsaved_changes_after_adding_node(page, action_name, trigger_action):
    """
    Parametrized test that verifies unsaved changes popup appears after adding a node
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Start from Workflows page and click Create Workflow
    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()
    create_page = workflows_page.click_create_workflow()
    create_page.should_be_on_create_workflow_page()

    # Act: Add an assistant node to trigger unsaved changes
    create_page.add_assistant_node()
    create_page.should_have_node_on_canvas("Assistant_1")

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(create_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()
    unsaved_dialog.should_have_correct_message()
    unsaved_dialog.should_have_both_buttons()

    # Act: Click Keep Editing
    unsaved_dialog.click_keep_editing()

    # Assert: Dialog should close and user stays on create workflow page
    unsaved_dialog.should_not_be_visible()
    create_page.should_be_on_create_workflow_page()
    create_page.should_have_node_on_canvas("Assistant_1")


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action", TRIGGER_ACTIONS)
@pytest.mark.prod_regression
def test_unsaved_changes_after_adding_workflow_name(page, action_name, trigger_action):
    """
    Parametrized test that verifies unsaved changes popup appears after adding a workflow name
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Start from Workflows page and click Create Workflow
    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()
    create_page = workflows_page.click_create_workflow()
    create_page.should_be_on_create_workflow_page()

    # Act: Open workflow config and add workflow name
    config_panel = create_page.open_workflow_config_panel()
    config_panel.switch_to_basic_tab()
    config_panel.fill_name("Test Workflow Name")

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(create_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()
    unsaved_dialog.should_have_correct_message()
    unsaved_dialog.should_have_both_buttons()

    # Act: Click Keep Editing
    unsaved_dialog.click_keep_editing()

    # Assert: Dialog should close and user stays on create workflow page
    unsaved_dialog.should_not_be_visible()
    create_page.should_be_on_create_workflow_page()


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action", TRIGGER_ACTIONS)
@pytest.mark.prod_regression
def test_unsaved_changes_after_adding_yaml_config(page, action_name, trigger_action):
    """
    Parametrized test that verifies unsaved changes popup appears after adding YAML config
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Start from Workflows page and click Create Workflow
    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()
    create_page = workflows_page.click_create_workflow()
    create_page.should_be_on_create_workflow_page()

    # Act: Open YAML panel and add YAML configuration
    yaml_panel = create_page.open_yaml_panel()
    yaml_config = """
assistants:
  - id: test_assistant
    model: gpt-4
    system_prompt: "You are a helpful assistant"
states:
  - id: test_state
    assistant_id: test_assistant
    """
    yaml_panel.fill_yaml_config(yaml_config)

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(create_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()
    unsaved_dialog.should_have_correct_message()
    unsaved_dialog.should_have_both_buttons()

    # Act: Click Keep Editing
    unsaved_dialog.click_keep_editing()

    # Assert: Dialog should close and user stays on create workflow page
    unsaved_dialog.should_not_be_visible()
    create_page.should_be_on_create_workflow_page()


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action", TRIGGER_ACTIONS)
@pytest.mark.prod_regression
def test_edit_workflow_unsaved_changes_after_modifying_name(
    page, test_workflow, action_name, trigger_action
):
    """
    Parametrized test that verifies unsaved changes popup appears after modifying a workflow name
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Navigate to Edit Workflow page
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)
    edit_page.should_be_on_edit_workflow_page()

    # Act: Open workflow config and modify workflow name
    config_panel = edit_page.open_workflow_config_panel()
    config_panel.switch_to_basic_tab()
    config_panel.fill_name(f"{test_workflow.name}_modified")

    # Act: Perform the parameterized action to trigger unsaved changes dialog
    trigger_action(edit_page)

    # Assert: Verify unsaved changes dialog appears
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()
    unsaved_dialog.should_have_correct_message()
    unsaved_dialog.should_have_both_buttons()

    # Act: Click Keep Editing
    unsaved_dialog.click_keep_editing()

    # Assert: Dialog should close and user stays on edit workflow page
    unsaved_dialog.should_not_be_visible()
    edit_page.should_be_on_edit_workflow_page()


# Discard Changes Tests
@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize("action_name, trigger_action, expected_url", DISCARD_ACTIONS)
@pytest.mark.prod_regression
def test_unsaved_changes_discard_after_adding_node(
    page, action_name, trigger_action, expected_url
):
    """
    Parametrized test that verifies clicking 'Discard Changes' navigates away after adding a node
    when performing different actions (Cancel, menu navigation, or Back button).
    """
    # Arrange: Start from Workflows page and click Create Workflow
    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()
    create_page = workflows_page.click_create_workflow()
    create_page.should_be_on_create_workflow_page()

    # Act: Add an assistant node to trigger unsaved changes
    create_page.add_assistant_node()
    create_page.should_have_node_on_canvas("Assistant_1")

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
