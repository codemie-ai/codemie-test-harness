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

import copy

import pytest
from hamcrest import assert_that, contains_string
from playwright.sync_api import expect

from codemie_test_harness.tests.ui.pageobject.components import UnsavedChangesDialog
from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.constants import test_project_name

original_yaml_config = """
assistants:
  - id: branch_creator
    model: gpt-5-2-2025-12-11
    system_prompt: You are helpful assistant

tools: []

custom_nodes: []

states:
  - id: branch_creator
    assistant_id: branch_creator
    next:
      state_id: end
    resolve_dynamic_values_in_prompt: true
"""

expected_yaml_config = """
custom_nodes: []
tools: []
assistants:
  - id: branch_creator
    model: gpt-5-2-2025-12-11
    system_prompt: You are helpful assistant
states:
  - id: branch_creator
    assistant_id: branch_creator
    next:
      state_id: end
    resolve_dynamic_values_in_prompt: true
"""


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_workflow_page_elements_visibility(page, test_workflow):
    """Test that all main elements are visible on Edit Workflow page."""
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)

    # Verify we are on the correct page (includes save button, cancel button, canvas checks)
    edit_page.should_be_on_edit_workflow_page()

    # Verify page has "Edit Workflow" title
    expect(edit_page.page_title).to_have_text("Edit Workflow")

    # Verify all form sections are visible (canvas and nodes sidebar)
    edit_page.should_have_all_form_sections_visible()

    # Open workflow config panel and verify workflow name is pre-populated
    config_panel = edit_page.open_workflow_config_panel()
    config_panel.should_have_name_field_value(test_workflow.name)

    # Verify common components
    edit_page.menu.should_have_complete_navigation_structure()
    edit_page.sidebar.should_be_visible()
    edit_page.sidebar.should_have_workflows_title()


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_workflow_form_pre_populated_data(page, test_workflow):
    """Test that form fields are pre-populated with existing workflow data."""
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)

    # Open workflow config panel to access form fields
    config_panel = edit_page.open_workflow_config_panel()

    # Verify pre-populated data in Basic tab
    config_panel.should_see_project_selected(test_workflow.project)
    config_panel.should_have_name_field_value(test_workflow.name)
    config_panel.should_have_description_field_value(test_workflow.description)
    config_panel.should_have_shared_switch_checked()

    # Open YAML panel (closes config panel and opens YAML editor)
    yaml_panel = edit_page.open_yaml_panel()
    # Verify pre-populated YAML configuration
    yaml_panel.should_have_yaml_editor_with_content(original_yaml_config)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_workflow_form_interactions(page, test_workflow):
    """Test form field interactions and input validation."""
    # Start from Workflows page
    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()
    workflows_page.should_be_on_workflows_page()

    workflows_page.search_workflows(test_workflow.name)
    workflows_page.should_see_workflow_card(test_workflow.name)
    edit_page = workflows_page.edit_workflow(test_workflow.name)
    edit_page.should_be_on_edit_workflow_page()

    # Open workflow config panel to access form fields
    config_panel = edit_page.open_workflow_config_panel()

    # Test name field interaction
    new_name = get_random_name()
    config_panel.fill_name(new_name)
    config_panel.should_have_name_field_value(new_name)

    # Test description field interaction
    new_description = "This is an updated test workflow description"
    config_panel.fill_description(new_description)
    config_panel.should_have_description_field_value(new_description)

    # Test icon URL field interaction
    test_icon_url = "https://example.com/updated-icon.png"
    config_panel.fill_icon_url(test_icon_url)
    config_panel.should_have_icon_url_field_value(test_icon_url)

    # Test project dropdown interaction
    config_panel.should_have_project_dropdown_visible()
    config_panel.select_project(test_project_name)
    config_panel.should_see_project_selected(test_project_name)

    # Test shared switch interaction - toggle to unchecked
    config_panel.toggle_shared_switch()
    config_panel.should_have_shared_switch_unchecked()

    # Save the workflow with all changes
    config_panel.click_save()
    edit_page.click_save()

    # Verify we're on workflows page (just check URL, not all elements)
    workflows_page = WorkflowsPage(page)
    workflows_page.search_workflows(new_name)
    workflows_page.should_see_workflow_card(new_name)

    # Navigate back to edit workflow page
    edit_page.navigate_to(test_workflow.id)
    edit_page.should_be_on_edit_workflow_page()

    # Open config panel again to verify persistence
    config_panel = edit_page.open_workflow_config_panel()

    # Verify all edited fields are persisted
    config_panel.should_have_name_field_value(new_name)
    config_panel.should_have_description_field_value(new_description)
    config_panel.should_have_icon_url_field_value(test_icon_url)
    config_panel.should_have_shared_switch_unchecked()
    config_panel.should_see_project_selected(test_project_name)

    # Test shared switch interaction
    config_panel.toggle_shared_switch()
    config_panel.should_have_shared_switch_checked()


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_workflow_yaml_editor_functionality_with_history(page, test_workflow):
    """Test YAML editor functionality - edit, save, and verify changes persist."""
    # Step 1 & 2: Start from Workflows page, find and open workflow for edit
    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()
    workflows_page.should_be_on_workflows_page()

    workflows_page.search_workflows(test_workflow.name)
    workflows_page.should_see_workflow_card(test_workflow.name)
    edit_page = workflows_page.edit_workflow(test_workflow.name)
    edit_page.should_be_on_edit_workflow_page()

    # Step 3: Open YAML config panel
    yaml_panel = edit_page.open_yaml_panel()

    # Verify YAML tabs are visible
    yaml_panel.should_have_yaml_tabs_visible()

    # Verify YAML editor is visible
    yaml_panel.should_have_yaml_editor_visible()

    # Step 4: Update config with new valid YAML
    # Modify the existing YAML by replacing the system prompt
    new_yaml_config = test_workflow.yaml_config.replace(
        "You are helpful assistant", "Updated system prompt for testing"
    )

    yaml_panel.fill_yaml_config(new_yaml_config)

    # Step 5: Click 'Save' on YAML panel (closes the panel)
    yaml_panel.click_save()

    # Step 6: Save the workflow (click main Save button)
    edit_page.click_save()

    # Wait for navigation to workflows page
    workflows_page.should_be_on_workflows_page()

    # Step 7: Open Workflow Edit page again and verify YAML config was updated
    edit_page.navigate_to(test_workflow.id)
    edit_page.should_be_on_edit_workflow_page()

    # Open YAML panel to verify the changes persisted
    yaml_panel = edit_page.open_yaml_panel()
    expected_config = copy.copy(original_yaml_config).replace(
        "You are helpful assistant", "Updated system prompt for testing"
    )
    yaml_panel.should_have_yaml_editor_with_content(expected_config)

    # Step 8: Open the Version History popup via the header-actions 'Version History' button.
    # The popup replaces the old tab-based history UI.
    popup = yaml_panel.open_version_history_popup()

    # Step 9: Verify popup shows version entries in [NN] + datetime + author format.
    popup.should_have_version_entries(min_count=1)
    popup.should_have_version_entry_format()

    # Step 10: Version [01] is auto-selected when popup opens; diff already renders.
    popup.select_version_entry(index=0)

    # Verify diff view is rendered; both comparison buttons are visible.
    popup.should_have_diff_view_visible()
    popup.should_have_diff_tabs_visible()
    # Note: 'Previous Version' is disabled for entry [01] (no predecessor exists);
    # 'Current Version' compares [01] against the current editor state.

    # Step 11: Click 'Current Version' to verify the comparison button is interactive.
    popup.click_current_version_tab()
    popup.should_have_diff_view_visible()

    # Step 13: Click Restore — ConfirmationModal appears with exact warning text.
    popup.click_restore()
    popup.should_have_restore_confirmation_visible()

    # Step 14: Confirm the restoration; confirmation modal closes.
    popup.confirm_restore()
    popup.should_have_restore_confirmation_hidden()
    # Wait for the version history popup itself to close before interacting with the
    # page — restoring triggers an auto-save that dismisses the popup.
    popup.should_not_be_visible()

    # Step 15: Navigate back to the edit page and verify the restored YAML persisted.
    # Restore triggers an auto-save that may close the YAML panel; navigating fresh
    # ensures a stable page state.  Version [01] represents the state AT the time of
    # the save in Step 5 ("Updated system prompt for testing").
    edit_page.navigate_to(test_workflow.id)
    edit_page.should_be_on_edit_workflow_page()
    yaml_panel = edit_page.open_yaml_panel()
    restored_content = yaml_panel.get_yaml_content()
    assert_that(
        restored_content,
        contains_string("Updated system prompt for testing"),
        f"Expected restored YAML to contain 'Updated system prompt for testing', "
        f"got: {restored_content!r}",
    )


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_workflow_sidebar_functionality(page, test_workflow):
    """Test sidebar functionality from Edit Workflow page."""
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)

    # Test sidebar visibility and structure
    edit_page.sidebar.should_be_visible()
    edit_page.sidebar.should_have_workflows_title()
    edit_page.sidebar.should_have_categories_section()

    # Test category navigation from sidebar
    edit_page.sidebar.navigate_to_my_workflows()
    edit_page.should_have_url_containing("/workflows/my")

    # Navigate back to edit workflow
    edit_page.navigate_to(test_workflow.id)
    edit_page.sidebar.navigate_to_all_workflows()
    edit_page.should_have_url_containing("/workflows/all")


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_workflow_menu_navigation(page, test_workflow):
    """Test menu navigation from Edit Workflow page."""
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)

    # Test menu component visibility
    edit_page.should_have_menu_visible()
    edit_page.menu.should_be_visible()
    edit_page.menu.should_have_complete_navigation_structure()

    # Test navigation to other sections
    edit_page.menu.navigate_to_assistants()
    edit_page.should_have_url_containing("/assistants")

    # Navigate back to edit workflow
    edit_page.navigate_to(test_workflow.id)
    edit_page.menu.navigate_to_workflows()
    edit_page.should_have_url_containing("/workflows/my")


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_workflow_tabs_navigation(page, test_workflow):
    """Test that form data persists when switching between tabs with unsaved changes warning."""
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)

    # Step 1: Open YAML panel
    yaml_panel = edit_page.open_yaml_panel()

    # Step 2: Switch to Basic tab
    yaml_panel.switch_to_basic_tab()

    # Step 3: Update name and description
    test_name = "Modified Workflow Name"
    test_description = "Modified workflow description"
    yaml_panel.fill_name(test_name)
    yaml_panel.fill_description(test_description)

    # Step 4: Switch to YAML panel (should trigger unsaved changes popup)
    yaml_panel.switch_to_yaml_tab()

    # Step 5: Observe unsaved message popup
    unsaved_dialog = UnsavedChangesDialog(page)
    unsaved_dialog.should_be_visible()

    # Step 6: Click Save and Proceed button on popup
    unsaved_dialog.click_save_and_proceed()

    # Step 7: Switch to Basic tab
    yaml_panel.switch_to_basic_tab()

    # Step 8: Verify updates are saved
    yaml_panel.should_have_name_field_value(test_name)
    yaml_panel.should_have_description_field_value(test_description)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_workflow_config_panel_basic_tab(page, test_workflow):
    """Test workflow config panel basic tab validations in Edit Workflow page."""
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)

    # Test save button initial state (should be enabled with existing data)
    edit_page.should_have_save_button_enabled()

    # Open workflow config panel
    config_panel = edit_page.open_workflow_config_panel()

    # Test save button after filling required fields
    config_panel.fill_name("Test Workflow Updated")
    config_panel.should_have_save_button_enabled()

    # Test name field is required
    config_panel.fill_name("")
    config_panel.should_have_name_is_required_message()

    # Test valid Icon URL is required
    config_panel.fill_icon_url("0")
    config_panel.should_have_valid_icon_url_is_required_message()
