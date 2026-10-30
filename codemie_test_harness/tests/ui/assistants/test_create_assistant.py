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

"""
UI Test Suite for Create Assistant Feature - Critical Happy Path Scenarios

This test suite implements UI automated tests for the "create assistant" feature
following Page Object Model (POM) best practices as specified in the ticket.

Test Coverage:
- Critical happy path for assistant creation workflow
- Form field interactions and validation
- Navigation and UI component verification
- Essential assistant creation scenarios
- AI Generator modal handling

Exclusions (as per requirements):
- Edge cases and negative scenarios
- Advanced configuration testing
- Complex error handling scenarios

Architecture:
- Follows Page Object Model (POM) pattern
- Reusable UI components abstracted into dedicated classes
- Comprehensive locator strategies with fallbacks
- Property-based element access for maintainability
- Integration with AIAssistantGeneratorPage modal
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    get_minimal_assistant_data,
)


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_create_assistant_page_elements_visibility(page):
    """
    Test that all main elements are visible on Create Assistant page.

    This test verifies the basic page structure and essential UI components
    are properly rendered and accessible to users.

    Critical Elements Verified:
    - Page title and navigation
    - Essential form fields (name, description, system prompt)
    - Action buttons (create, cancel)
    - Common page components (header, navigation)
    """
    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()

    # Verify we are on the correct page
    create_page.should_be_on_create_assistant_page()

    # Verify essential form fields are visible
    create_page.should_have_all_form_fields_visible()

    # Verify action buttons are present
    create_page.should_have_action_buttons_visible()

    # Verify common page components
    create_page.should_have_page_content_visible()
    create_page.should_not_have_loading_indicator()


@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_create_assistant_navigation_from_assistants_page(page):
    """
    Test navigation to Create Assistant page from main Assistants page.

    This test verifies the critical navigation path that users follow
    to access the assistant creation functionality.

    Navigation Flow:
    1. Navigate to Assistants page
    2. Click "Create Assistant" button
    3. Verify arrival at Create Assistant page
    """
    # Start from the main assistants page
    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.should_be_on_assistants_page()

    # Navigate to create assistant page
    create_page = assistants_page.click_create_assistant()

    # Verify we're on the create assistant page
    create_page.should_be_on_create_assistant_page()


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_ai_generator_modal_visibility_and_handling(page, clear_asst_ai_popup):
    """
    Test AI Generator modal visibility and proper handling when navigating to Create Assistant page.

    This test verifies that the AI Assistant Generator modal is properly handled
    when it appears during navigation to the Create Assistant page.

    Modal Handling Flow:
    1. Navigate to Create Assistant page
    2. Check if AI Generator modal appears
    3. Verify modal can be closed or handled appropriately
    4. Ensure manual form is accessible after modal handling
    """
    create_page = CreateEditAssistantPage(page)

    # Navigate to create assistant page - this will handle the modal automatically
    create_page.navigate_to()

    # After navigation, modal should be handled and not visible
    create_page.verify_ai_generator_modal_not_visible()

    # Verify we can proceed with manual form
    create_page.should_be_on_create_assistant_page()
    create_page.should_have_all_form_fields_visible()


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_ai_generator_modal_create_manually_workflow(page, clear_asst_ai_popup):
    """
    Test the workflow of using 'Create Manually' option from AI Generator modal.

    This test verifies that users can properly choose manual creation
    when the AI Generator modal appears.

    Manual Creation Flow:
    1. Navigate to Create Assistant page
    2. If AI Generator modal appears, click 'Create Manually'
    3. Verify modal closes and manual form is accessible
    4. Proceed with manual assistant creation
    """
    create_page = CreateEditAssistantPage(page)

    # Navigate without automatic modal handling
    page.goto(create_page.page_url)
    create_page.wait_for_page_load()

    # Verify modal appears and is properly displayed
    create_page.verify_ai_generator_modal_visible()

    # Choose manual creation and verify modal closes
    create_page.create_manually_from_ai_modal()
    create_page.verify_ai_generator_modal_not_visible()

    # Verify manual form is accessible
    create_page.should_be_on_create_assistant_page()
    create_page.should_have_all_form_fields_visible()


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_create_assistant_form_field_interactions(page, client):
    """
    Test form field interactions and input handling.

    This test verifies that users can successfully interact with all
    essential form fields and that input values are properly retained.

    Form Fields Tested:
    - Assistant name input
    - Description textarea
    - System prompt textarea
    - Icon URL input
    - Shared toggle switch
    """
    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()

    # Test shared toggle interaction
    create_page.toggle_shared_assistant(True)
    create_page.should_have_shared_checked()

    # Toggle back to private
    create_page.toggle_shared_assistant(False)
    create_page.should_have_shared_unchecked()

    # Get test data using the factory
    test_data = get_minimal_assistant_data()

    # Test name field interaction
    test_name = test_data.name
    create_page.fill_name(test_name)
    create_page.should_have_name_value(test_name)

    # Test description field interaction
    test_description = test_data.description
    create_page.fill_description(test_description)
    create_page.should_have_description_value(test_description)

    # Test system prompt field interaction
    test_prompt = test_data.system_prompt
    create_page.fill_system_prompt(test_prompt)
    create_page.should_have_system_prompt_value(test_prompt)

    # Test icon URL field interaction
    test_icon_url = test_data.icon_url
    create_page.fill_icon_url(test_icon_url)
    create_page.should_have_icon_url_value(test_icon_url)


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_create_assistant_default_field_values(page):
    """
    Test default field values on page load.

    This test verifies that form fields have appropriate default values
    when the Create Assistant page is first loaded.

    Default Values Verified:
    - Empty name field
    - Empty description field
    - Empty system prompt field
    - Unchecked shared toggle
    - Default assistant type selection
    """
    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()

    # Verify default empty field values
    create_page.should_have_empty_fields()

    # Verify default buttons availability
    create_page.should_have_create_button_enabled()
    create_page.should_have_cancel_button_enabled()

    # Verify default shared toggle state (should be unchecked/private)
    create_page.should_have_shared_unchecked()


"""
Test suite for critical happy path scenarios.

This test class focuses on the most important user workflows for creating assistants,
ensuring that the essential functionality works correctly for end users.
"""


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_create_assistant_minimal_required_fields(page):
    """
    Test assistant creation with minimal required fields - Critical Happy Path.

    This test represents the core scenario outlined in the ticket:
    1. User navigates to Create Assistant page
    2. Fills essential fields (name, description, system prompt)
    3. Saves and publishes the assistant
    4. Verifies assistant appears in the assistants list

    This is the most critical test case for the feature.
    """
    # Get test data using the factory
    test_data = get_minimal_assistant_data()

    # Navigate to create assistant page
    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()

    # Use the comprehensive create_assistant method with test data
    create_page.create_assistant(
        name=test_data.name,
        description=test_data.description,
        system_prompt=test_data.system_prompt,
        shared=test_data.shared,
    )

    # Verify successful creation
    assistants_page = AssistantsPage(page)
    assert_assistant_created_successfully(assistants_page, test_data.name)


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_create_assistant_button_states_and_validation(page):
    """
    Test create button states and form field interactions.

    This test ensures that form fields can be filled and the Save button
    remains available for interaction. Note: The new UI keeps the Save button
    enabled at all times, with validation happening server-side on submission.
    """
    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()

    # Get test data using the factory
    test_data = get_minimal_assistant_data()

    # Verify Save button is enabled before filling any fields
    create_page.should_have_create_button_enabled()

    # Fill required fields and verify button remains enabled
    create_page.fill_name(test_data.name)
    create_page.should_have_create_button_enabled()

    create_page.fill_description(test_data.description)
    create_page.should_have_create_button_enabled()

    create_page.fill_system_prompt(test_data.system_prompt)
    create_page.should_have_create_button_enabled()


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_create_assistant_cancel_navigation(page):
    """
    Test cancel functionality returns user to assistants list.

    This test verifies that users can abort the assistant creation process
    and return to the main assistants page without creating an assistant.

    Navigation Flow:
    1. Navigate to Create Assistant page
    2. Fill some fields (simulate user input)
    3. Click Cancel button
    4. Verify return to Assistants page
    """
    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()

    # Get test data using the factory
    test_data = get_minimal_assistant_data()

    # Simulate some user input
    create_page.fill_name(test_data.name)
    create_page.fill_description(test_data.description)

    # Cancel the creation process
    create_page.click_cancel()

    # Verify we're back on the assistants page
    assistants_page = AssistantsPage(page)
    assistants_page.should_be_on_assistants_page()


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_create_assistant_back_button_navigation(page):
    """
    Test back button functionality returns user to previous page.

    This test verifies that the back button works correctly and provides
    users with an alternative way to return to the assistants list.

    Navigation Flow:
    1. Start from Assistants page
    2. Navigate to Create Assistant page
    3. Click Back button
    4. Verify return to Assistants page
    """
    # Start from assistants page to establish navigation history
    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    create_page = assistants_page.click_create_assistant()

    # Now on create assistant page
    create_page.should_be_on_create_assistant_page()

    # Use back button to return
    create_page.click_back()

    # Verify we're back on assistants page
    assistants_page.should_be_on_assistants_page()


# ==================== HELPER METHODS FOR CUSTOM ASSERTIONS ====================


# noinspection PyArgumentList
def assert_assistant_created_successfully(
    assistants_page: AssistantsPage, assistant_name: str
):
    """
    Helper method to verify successful assistant creation.

    Args:
        assistants_page: The AssistantsPage instance
        assistant_name: Name of the assistant to verify
    """
    assistants_page.should_be_on_assistants_page()
    assistants_page.should_see_assistant_with_name(assistant_name)
