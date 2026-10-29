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
UI Test Suite for Chat Input Field Functionality

This test suite implements UI automated tests for advanced chat input field features:
- File attachment
- Dynamic tools configuration
- Model selection/changing
- Skills attachment

Test Coverage (AC-to-Test Mapping):
- AC#1, AC#2: test_chat_input_file_attachment - File attachment displays in UI before sending
- AC#1, AC#3: test_chat_input_dynamic_tools_adding - Dynamic tools can be added and used
- AC#1, AC#4: test_chat_input_default_model_changing - Model changes take effect for subsequent messages
- AC#1, AC#5: test_chat_input_skills_attachment - Skills can be attached and are functional

All tests follow Page Object Model pattern with no direct locators, expect() calls, or waits in tests.
"""

import os

import pytest
from hamcrest import assert_that, greater_than, contains_string

_WEB_SEARCH_COMPONENT_ID = "features:webSearch"


def _reset_web_search(customer_config_utils):
    try:
        customer_config_utils.reset_setting(_WEB_SEARCH_COMPONENT_ID)
    except Exception:
        pass


@pytest.fixture(scope="function")
def web_search_enabled(customer_config_utils):
    """Guarantee features:webSearch resolves to enabled=True (YAML default)
    for the duration of the test, and restore that state after."""
    customer_config_utils.reset_setting(_WEB_SEARCH_COMPONENT_ID)
    yield
    _reset_web_search(customer_config_utils)


@pytest.mark.ui
@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.assistant
def test_chat_input_file_attachment(page, navigate_to_new_chat_page):
    """
    Test that files can be attached via chat input field and display in UI before sending.

    AC#2: Attachment test verifies attached file(s) are visible in UI prior to sending.

    Test Flow:
    1. Navigate to chat page (via fixture)
    2. Attach a test file
    3. Verify file is displayed in UI
    4. Remove file and verify it's gone
    """
    chat_page = navigate_to_new_chat_page(page)

    # Use existing test file
    test_file_path = os.path.join(
        os.path.dirname(__file__), "../../test_data/files/test.pdf"
    )
    test_file_path = os.path.abspath(test_file_path)
    file_name = os.path.basename(test_file_path)

    # Attach file and verify it's visible
    chat_page.attach_file(test_file_path)
    chat_page.should_have_file_attached(file_name)

    # Remove file and verify it's gone
    chat_page.remove_first_attachment()
    chat_page.should_not_have_file_attached(file_name)


@pytest.mark.sanity
@pytest.mark.ui
@pytest.mark.assistant
@pytest.mark.customer_configuration
def test_chat_input_dynamic_tools_adding_web_search(
    page, navigate_to_new_chat_page_with_assistant, web_search_enabled
):
    """
    Test that tools can be added dynamically to chat session and are usable in conversation.

    AC#3: Dynamic tools test verifies a tool can be added and is usable in conversation.

    Test Flow:
    1. Create assistant via API
    2. Navigate to chat page with that assistant
    3. Click dynamic tools button
    4. Verify Web Search option is offered, then enable it
    5. Close tools settings
    6. Send message and verify tool is used
    """
    chat_page = navigate_to_new_chat_page_with_assistant(page)

    # Open tools settings; the Web Search option is only offered when
    # features:webSearch is enabled in customer config (web_search_enabled).
    chat_page.click_dynamic_tools()
    chat_page.should_have_web_search_toggle()
    chat_page.enable_web_search()
    chat_page.close_tools_settings()

    # Send message that would trigger web search
    test_message = "On the https://www.artificialintelligence-news.com/ search for the latest news about AI developments"
    chat_page.send_message(test_message)
    chat_page.wait_for_assistant_response(timeout=60000)

    # Verify tool was used - assistant should provide meaningful response
    chat_page.should_have_assistant_response()
    assistant_response = chat_page.get_last_assistant_message_text()
    assert_that(
        len(assistant_response),
        greater_than(50),
        "Assistant should provide a meaningful response using web search tool",
    )

    # Verify web search tool was actually used (check tool block)
    chat_page.should_have_any_tool_used("Search", "Web Scrapper")


@pytest.mark.ui
@pytest.mark.assistant
@pytest.mark.customer_configuration
def test_chat_input_dynamic_web_search_unavailable_when_disabled_via_customer_config(
    page, navigate_to_new_chat_page_with_assistant, web_search_disabled
):
    """
    Gap coverage: the dynamic auto-injection path for web search
    is gated by features:webSearch. With the flag forced to disabled, the Web
    Search option must not even be offered in the Tools Settings panel, even
    though the same panel offers it under the YAML default (see
    test_chat_input_dynamic_tools_adding_web_search).
    """
    chat_page = navigate_to_new_chat_page_with_assistant(page)

    chat_page.click_dynamic_tools()
    chat_page.should_not_have_web_search_toggle()


@pytest.mark.sanity
@pytest.mark.ui
@pytest.mark.assistant
def test_chat_input_default_model_changing(page, navigate_to_new_chat_page):
    """
    Test that default model can be changed and subsequent messages use the selected model.

    AC#4: Default model changing test verifies subsequent message uses the selected model.

    Test Flow:
    1. Navigate to chat page (via fixture)
    2. Click model selector in chat input area
    3. Select a different model
    4. Send message and verify response
    """
    chat_page = navigate_to_new_chat_page(page)

    # Select different model from chat input area
    chat_page.select_model("GPT-4.1 mini 2025-04-14")

    # Send test message
    test_message = "What LLM do you use?"
    chat_page.send_message(test_message)
    chat_page.wait_for_assistant_response()

    # Verify response was received with new model
    chat_page.should_have_assistant_response()
    assistant_response = chat_page.get_last_assistant_message_text()
    assert_that(assistant_response, contains_string("GPT-4"))


@pytest.mark.ui
@pytest.mark.assistant
def test_chat_input_skills_attachment(page, navigate_to_new_chat_page, skill):
    """
    Test that skills can be attached to chat session and are accessible/functional.

    AC#5: Skills attachment test verifies attached skill is accessible and functional in chat.

    Test Flow:
    1. Create a new skill via fixture
    2. Navigate to chat page (via fixture)
    3. Click Skills button in chat input area
    4. Select the created skill
    5. Confirm selection
    6. Re-open skills dialog to verify skill is selected
    """
    # Create a skill
    created_skill = skill()

    # Navigate to chat page
    chat_page = navigate_to_new_chat_page(page)

    # Open skills dialog and select the skill
    chat_page.click_skills_button()
    chat_page.select_skill(created_skill.name)
    chat_page.confirm_skills_selection()

    # Re-open skills dialog to verify skill is selected
    chat_page.click_skills_button()
    chat_page.should_have_skill_selected(created_skill.name)
