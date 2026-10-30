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
UI Test Suite for Chat Configuration Feature - Critical Happy Path Scenarios

This test suite implements UI automated tests for the chat configuration feature
following Page Object Model (POM) best practices as specified in the ticket.

Test Coverage:
- Configuration tab access and navigation
- Configuration update workflows (save/cancel)
- configuration panel interaction
- Critical path for configuration management

Exclusions (as per requirements):
- Edge cases and negative scenarios
- Advanced configuration validation
- Complex error handling scenarios

Architecture:
- Follows Page Object Model (POM) pattern
- Reusable UI components abstracted into dedicated classes
- Property-based element access for maintainability
"""

import pytest

from codemie_test_harness.tests.conftest import COMMON_ASSISTANT_SYSTEM_PROMPT
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    get_minimal_assistant_data,
)
from codemie_test_harness.tests.ui.test_data.chat_test_data import (
    get_simple_test_message,
)


@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_configuration_panel_visibility_and_access(page, navigate_to_new_chat_page):
    """
    Test that configuration tab is visible and accessible.

    This test verifies that users can access the configuration functionality
    through the configuration tab or button.

    Configuration Access Tests:
    - Configuration tab/button visibility
    - Configuration opening functionality
    """
    chat_page = navigate_to_new_chat_page(page)

    # Verify configuration access is available
    chat_page.should_have_configuration_button_visible()

    # Test opening configuration
    chat_page.open_configuration()

    # Verify configuration panel appears (if implemented)
    chat_page.should_have_configuration_panel_opened()


@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_configuration_panel_structure_and_elements(page, navigate_to_new_chat_page):
    """
    Test configuration panel structure and essential elements.

    This test verifies that the configuration panel has proper structure
    and contains essential configuration fields and controls.
    """
    chat_page = navigate_to_new_chat_page(page)
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)
    chat_page.wait_for_assistant_response()

    chat_page.open_configuration()

    # Verify panel structure
    config_panel = chat_page.chat_configuration_panel
    config_panel.should_have_all_sections_visible()


@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_configuration_panel_closing_functionality(page, navigate_to_new_chat_page):
    """
    This test verifies that users can close the configuration panel
    """
    chat_page = navigate_to_new_chat_page(page)
    chat_page.open_configuration()
    chat_page.should_have_configuration_panel_opened()

    chat_page.close_configuration()

    chat_page.should_have_configuration_panel_closed()


@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_chat_configuration_llm_update(
    page, navigate_to_new_chat_page, first_available_llm_label
):
    """
    Test that LLM can be changed in Chat configuration.
    """
    chat_page = navigate_to_new_chat_page(page)
    chat_page.open_configuration()

    chat_page.chat_configuration_panel.select_llm_engine_option(
        first_available_llm_label
    )
    chat_page.close_configuration()

    # Verify LLM Engine
    chat_page.open_configuration()
    chat_page.chat_configuration_panel.should_have_llm_engine_selection(
        first_available_llm_label
    )


@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_assistant_configuration_save_button_functionality(
    page, navigate_to_new_chat_page, assistant
):
    """
    Test Assistant configuration Save button functionality.

    This test verifies that the save button works correctly and
    properly processes configuration changes.

    Save Button Tests:
    - Button visibility and accessibility
    - Save action execution
    - Post-save state
    """
    chat_page = navigate_to_new_chat_page(page)

    test_assistant = assistant()
    test_message = get_simple_test_message()

    chat_page.send_message(
        message=test_message.content, assistant_name=test_assistant.name
    )
    chat_page.wait_for_assistant_response()

    chat_page.open_configuration()
    assistant_config = chat_page.chat_configuration_panel.open_assistant_configuration(
        test_assistant.name
    )

    # System prompt update
    test_data = get_minimal_assistant_data()
    assistant_config.update_system_prompt(test_data.system_prompt).save_changes()

    # Verify changes are saved
    chat_page.open_configuration()
    assistant_config = chat_page.chat_configuration_panel.open_assistant_configuration(
        test_assistant.name
    )
    assistant_config.should_have_system_prompt(test_data.system_prompt)


@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_assistant_configuration_cancel_button_functionality(
    page, navigate_to_new_chat_page, assistant
):
    """
    Test Assistant configuration Cancel button functionality.

    This test verifies that the cancel button works correctly and
    properly discards configuration changes.

    Cancel Button Tests:
    - Button visibility and accessibility
    - Cancel action execution
    - Post-cancel state management (changes discarded)
    """
    chat_page = navigate_to_new_chat_page(page)

    test_assistant = assistant()
    test_message = get_simple_test_message()

    chat_page.send_message(
        message=test_message.content, assistant_name=test_assistant.name
    )
    chat_page.wait_for_assistant_response()

    chat_page.open_configuration()
    assistant_config = chat_page.chat_configuration_panel.open_assistant_configuration(
        test_assistant.name
    )

    # System prompt update
    test_data = get_minimal_assistant_data()
    assistant_config.update_system_prompt(test_data.system_prompt).cancel_changes()

    # Verify changes are saved
    chat_page.open_configuration()
    assistant_config = chat_page.chat_configuration_panel.open_assistant_configuration(
        test_assistant.name
    )
    assistant_config.should_have_system_prompt(COMMON_ASSISTANT_SYSTEM_PROMPT)
