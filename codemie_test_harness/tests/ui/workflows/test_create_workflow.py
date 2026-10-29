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

import os

import pytest

from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.create_workflow_page import (
    CreateWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.assistant_node_config_panel import (
    AssistantNodeConfigPanel,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.ui
def test_create_workflow_page_elements_visibility(page):
    """Test that all main elements are visible on Create Workflow page with Visual Editor."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    # Verify we are on the correct page
    create_page.should_be_on_create_workflow_page()

    # Verify header menu elements
    create_page.should_have_menu_elements_visible()

    # Verify Visual Editor sections are visible
    create_page.should_have_all_form_sections_visible()

    # Verify canvas is visible with start and end nodes
    create_page.should_have_canvas_visible()

    # Verify common components
    create_page.should_have_menu_visible()
    create_page.sidebar.should_be_visible()
    create_page.sidebar.should_have_workflows_title()


@pytest.mark.workflow
@pytest.mark.ui
def test_create_workflow_form_interactions(page):
    """Test form field interactions and input validation in Visual Editor."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    # Open workflow config panel
    workflow_config_panel = create_page.open_workflow_config_panel()

    # Switch to Basic tab
    workflow_config_panel.switch_to_basic_tab()

    # Test name field interaction
    test_name = "Test Workflow"
    workflow_config_panel.fill_name(test_name)
    workflow_config_panel.should_have_name_field_value(test_name)

    # Test description field interaction
    test_description = "This is a test workflow description"
    workflow_config_panel.fill_description(test_description)
    workflow_config_panel.should_have_description_field_value(test_description)

    # Test icon URL field interaction
    test_icon_url = "https://example.com/icon.png"
    workflow_config_panel.fill_icon_url(test_icon_url)
    workflow_config_panel.should_have_icon_url_field_value(test_icon_url)

    # Test shared switch interaction
    workflow_config_panel.toggle_shared_switch()
    workflow_config_panel.should_have_shared_switch_checked()

    # Toggle back to unchecked
    workflow_config_panel.toggle_shared_switch()
    workflow_config_panel.should_have_shared_switch_unchecked()


@pytest.mark.workflow
@pytest.mark.ui
def test_create_workflow_dropdowns_interaction(page):
    """Test dropdown interactions for project in Visual Editor."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    # Open workflow config panel
    workflow_config_panel = create_page.open_workflow_config_panel()

    # Switch to Basic tab
    workflow_config_panel.switch_to_basic_tab()

    # Test project dropdown interaction
    workflow_config_panel.should_have_project_dropdown_visible()

    # Test project selection functionality
    workflow_config_panel.select_project(os.getenv("PROJECT_NAME"))
    workflow_config_panel.should_see_project_selected(os.getenv("PROJECT_NAME"))


@pytest.mark.workflow
@pytest.mark.ui
def test_create_workflow_yaml_editor_functionality(page):
    """Test YAML editor functionality in Visual Editor."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    # Open workflow config panel with YAML tab
    workflow_config_panel = create_page.open_yaml_panel()

    # Verify YAML editor section
    workflow_config_panel.should_have_yaml_editor_visible()

    # Test YAML editor interaction
    test_yaml = """
    assistants: []
    states: []"""

    workflow_config_panel.fill_yaml_config(test_yaml)

    # Verify YAML editor content was entered
    workflow_config_panel.should_have_yaml_editor_with_content(test_yaml)

    # Save YAML configuration
    workflow_config_panel.save_yaml_config()

    # Reopen YAML editor to verify the configuration was saved
    workflow_config_panel = create_page.open_yaml_panel()

    # Verify the saved YAML configuration is still there
    workflow_config_panel.should_have_yaml_editor_with_content(test_yaml)


@pytest.mark.workflow
@pytest.mark.ui
def test_create_workflow_canvas_visualization(page):
    """Test workflow canvas visualization in Visual Editor."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    # Verify canvas is visible with default start and end nodes
    create_page.should_have_canvas_visible()

    # Test adding a node to canvas by clicking in palette
    create_page.add_assistant_node()

    # Verify node appears on canvas
    create_page.should_have_assistant_node_visible("Assistant_1")

    # Verify assistant node configuration panel appears
    config_panel = AssistantNodeConfigPanel(page)
    config_panel.should_be_visible()
    config_panel.should_have_assistant_config_section_visible()
    config_panel.should_have_state_settings_section_visible()
    config_panel.should_have_footer_buttons_visible()


@pytest.mark.workflow
@pytest.mark.ui
def test_create_workflow_navigation_buttons(page):
    """Test navigation button interactions."""
    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()
    create_page = workflows_page.click_create_workflow()

    # Verify buttons are enabled/visible
    create_page.should_have_navigation_buttons_visible()

    # Test back button (should navigate away)
    create_page.click_back()
    # Verify we are redirected (URL should change)
    workflows_page.should_have_url_containing("/workflows/my")

    # Navigate back to test cancel button
    create_page = workflows_page.click_create_workflow()
    create_page.click_cancel()
    # Verify we are redirected (URL should change)
    create_page.should_have_url_containing("/workflows/my")


@pytest.mark.workflow
@pytest.mark.ui
def test_create_workflow_sidebar_functionality(page):
    """Test sidebar functionality from Create Workflow page."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    # Test sidebar visibility and structure
    create_page.sidebar.should_be_visible()
    create_page.sidebar.should_have_workflows_title()
    create_page.sidebar.should_have_categories_section()
    create_page.sidebar.filters_should_be_hidden()

    # Navigate to My Workflows
    create_page.sidebar.navigate_to_my_workflows()
    create_page.should_have_url_containing("/workflows/my")

    # Navigate to All Workflows
    create_page.navigate_to()
    create_page.sidebar.navigate_to_all_workflows()
    create_page.should_have_url_containing("/workflows/all")

    # Navigate to Templates
    create_page.navigate_to()
    create_page.sidebar.navigate_to_templates()
    create_page.should_have_url_containing("/workflows/templates")


@pytest.mark.workflow
@pytest.mark.ui
def test_create_workflow_menu_navigation(page):
    """Test menu navigation from Create Workflow page."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    # Test menu component visibility
    create_page.should_have_menu_visible()
    create_page.menu.should_have_complete_navigation_structure()

    # Test navigation to other sections
    create_page.menu.navigate_to_assistants()
    create_page.should_have_url_containing("/assistants")

    create_page.navigate_to()
    create_page.menu.navigate_to_integrations()
    create_page.should_have_url_containing("/integrations")

    create_page.navigate_to()
    create_page.menu.navigate_to_data_sources()
    create_page.should_have_url_containing("/data-sources")


@pytest.mark.workflow
@pytest.mark.ui
def test_create_workflow_default_field_values(page):
    """Test default field values on page load in Visual Editor."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    # Open workflow config panel
    workflow_config_panel = create_page.open_workflow_config_panel()

    # Switch to Basic tab
    workflow_config_panel.switch_to_basic_tab()

    # Test default empty field values
    workflow_config_panel.should_have_empty_name_field()
    workflow_config_panel.should_have_empty_description_field()
    workflow_config_panel.should_have_empty_icon_url_field()

    # Test default shared switch state
    workflow_config_panel.should_have_shared_switch_unchecked()


@pytest.mark.workflow
@pytest.mark.ui
def test_create_workflow_config_panel_basic_tab(page):
    """Test workflow config panel basic tab validations in Visual Editor."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    # Test save button initial state (should be enabled by default)
    create_page.should_have_save_button_enabled()

    # Open workflow config panel
    workflow_config_panel = create_page.open_workflow_config_panel()

    # Test save button after filling required fields
    workflow_config_panel.fill_name("Test Workflow")
    workflow_config_panel.should_have_save_button_enabled()

    # Test name field is required
    workflow_config_panel.fill_name("")
    workflow_config_panel.should_have_name_is_required_message()

    # Test valid Icon URL is required
    workflow_config_panel.fill_icon_url("0")
    workflow_config_panel.should_have_valid_icon_url_is_required_message()


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.ui
def test_create_workflow_complete_workflow_creation(page, ensure_workflow_exists):
    """Test complete workflow creation from Workflows page using YAML config."""
    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()
    workflows_page.should_be_on_workflows_page()

    create_page = workflows_page.click_create_workflow()

    workflow_name = get_random_name()

    yaml_config = """
assistants:
  - id: business_analyst
    system_prompt: "You are a business analyst assistant. Your task is to gather and analyze"
  - id: onboarder
    system_prompt: "You are an onboarding assistant. Your task is to gather all relevant"
  - id: requirement_analyzer
    system_prompt: "You are a requirement analysis assistant. Your task is to analyze"

states:
  - id: onboarder
    assistant_id: onboarder
    task: |
      Find all relevant information about workflow implementation and describe
      like for business analyst as a requirements description.
      Provide a list of main requirement categories to analyze further.
    output_schema: |
      {
        "requirements": "List of main requirement categories"
      }
    next:
      state_id: requirement_analyzer # ID of next state
      iter_key: requirements # Key for iteration, must be same as in schema
  - id: requirement_analyzer # ID of state inside this configuration
    assistant_id: requirement_analyzer
    task: |
      Analyze the given requirement category in detail.
      Provide a comprehensive description for QA engineers, support team, and
      users on how to use this specific aspect of the workflow functionality.
    output_schema: |
      {
        "category": "Name of the requirement category",
        "analysis": "Detailed analysis and description of the requirement"
      }
    next:
      state_id: business_analyst # ID of next state
  - id: business_analyst # ID of state inside this configuration
    assistant_id: business_analyst
    task: |
      Compile all the requirement analyses into a comprehensive description for
      QA engineers, support team, and users on how to use this functionality.
      Create a comment for Jira ticket CODEMIE-1350 with key points.
    output_schema: |
      {
        "success": "Boolean true | false. If you created Jira comment successfully return true, otherwise false",
        "comment_body": "Return comment body which you left in Jira"
      }
    next:
      condition:
        expression: "success == True"
        then: end
        otherwise: business_analyst
"""

    create_page.create_workflow(
        project_name=os.getenv("PROJECT_NAME"),
        name=workflow_name,
        description="This is a complete test workflow",
        icon_url="https://example.com/test-icon.png",
        yaml_config=yaml_config,
        shared=True,
    )

    workflows_page.should_be_on_workflows_page()
    workflows_page.should_see_workflow_card(workflow_name)
