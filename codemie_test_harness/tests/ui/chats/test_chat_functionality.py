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
UI Test Suite for Chat Feature - Critical Happy Path Scenarios

This test suite implements UI automated tests for the "chat" feature
following Page Object Model (POM) best practices as specified in the ticket.

Test Coverage:
- Critical happy path for chat creation workflow
- Message sending and receiving functionality
- Basic chat interface interactions
- Navigation and UI component verification

Exclusions (as per requirements):
- Edge cases and negative scenarios
- Advanced error handling scenarios
- Complex multi-user scenarios

Architecture:
- Follows Page Object Model (POM) pattern
- Reusable UI components abstracted into dedicated classes
- Comprehensive locator strategies with fallbacks
- Property-based element access for maintainability
- Integration with ChatConfigurationModal component
"""

import pytest
from hamcrest import equal_to, assert_that

from codemie_test_harness.tests.ui.pageobject.chats.chats_sidebar import ChatsSidebar
from codemie_test_harness.tests.ui.test_data.chat_test_data import (
    get_simple_test_message,
    get_coding_question_message,
    get_coding_help_message,
    get_long_running_prompt_message,
)


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.ui
def test_chat_page_elements_visibility(page, navigate_to_new_chat_page):
    """
    Test that all main elements are visible on Chat page.

    This test verifies the basic page structure and essential UI components
    are properly rendered and accessible to users.

    Critical Elements Verified:
    - Chat input field and send button
    - Messages container
    - Configuration access
    - Navigation elements
    """
    chat_page = navigate_to_new_chat_page(page)

    # Verify common page components
    chat_page.should_have_page_content_visible()
    chat_page.should_not_have_loading_indicator()

    # Verify we are on the correct page
    chat_page.should_be_on_chat_page()

    # Verify essential chat elements are visible
    chat_page.verify_all_essential_elements_visible()
    chat_page.verify_all_action_buttons_visible()


@pytest.mark.chat
@pytest.mark.ui
def test_new_chat_button_visibility_and_interaction(page, navigate_to_new_chat_page):
    """
    Test new chat button visibility and basic interaction.

    This test verifies that users can access the new chat functionality
    and that the button responds appropriately to user interaction.

    Interaction Flow:
    1. Navigate to chat page
    2. Verify new chat button is visible
    3. Test new chat button interaction
    4. Verify chat interface is ready for use
    """
    chat_page = navigate_to_new_chat_page(page)

    # Verify new chat button is accessible
    chat_page.should_have_new_chat_button_visible()

    # Test new chat interaction
    chat_page.start_new_chat()

    # Verify we are on the correct page
    chat_page.should_be_on_chat_page()

    # Verify chat interface is ready
    chat_page.should_have_chat_input_visible()
    chat_page.should_have_send_button_visible()


@pytest.mark.chat
@pytest.mark.ui
def test_chats_sidebar_elements(page):
    """
    Test chats sidebar elements.

    This test verifies that the chat history sidebar is accessible.

    Sidebar Tests:
    - Sidebar visibility
    - Chat sections (Assistants, Chats, Folders)
    - Active chat item (test_user always has existing chats)
    """
    # Navigate via menu — redirects to the most recent existing chat
    chats_sidebar = ChatsSidebar(page)
    chats_sidebar.go_to_chats_page()

    chats_sidebar.verify_all_sidebar_sections_visibility()


@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.ui
def test_hover_sidebar_toggle_button_shows_and_hides_ctrl_b_tooltip(page):
    """Test the Ctrl+B tooltip on the Chats page sidebar toggle button.

    Verifies:
    - Hover-and-hold over the sidebar toggle button shows the tooltip with the
      exact text "Toggle Sidebar (Ctrl + B)" (AC1).
    - Moving the mouse away hides the tooltip (AC3).
    - The toggle button still collapses and re-expands the sidebar after the
      tooltip interaction, confirming no regression to existing behavior (AC5).
    """
    chats_sidebar = ChatsSidebar(page)
    chats_sidebar.go_to_chats_page()

    chats_sidebar.should_have_sidebar_visible()

    # Checkpoint A: hover-and-hold shows the tooltip with the exact text
    chats_sidebar.hover_sidebar_toggle_button()
    chats_sidebar.should_have_tooltip_visible("Toggle Sidebar (Ctrl + B)")

    # Checkpoint B: moving the mouse away hides the tooltip
    chats_sidebar.move_mouse_away_from_sidebar_toggle_button()
    chats_sidebar.should_have_tooltip_hidden()

    # Checkpoint C: clicking the toggle button collapses the sidebar
    chats_sidebar.click_hide_sidebar()
    chats_sidebar.should_have_sidebar_collapsed()

    # Checkpoint D: clicking the toggle button again expands the sidebar
    chats_sidebar.click_open_sidebar()
    chats_sidebar.should_have_sidebar_visible()


@pytest.mark.chat
@pytest.mark.ui
def test_chat_input_field_interactions(page, navigate_to_new_chat_page):
    """
    Test chat input field interactions and input handling.

    This test verifies that users can successfully interact with the
    chat input field and that input values are properly handled.

    Input Field Tests:
    - Text input and retention
    - Input clearing functionality
    - Input field state management
    """
    chat_page = navigate_to_new_chat_page(page)

    # Test input field interaction
    test_message = get_simple_test_message()
    chat_page.type_message_without_sending(test_message.content)
    chat_page.should_have_chat_input_value(test_message.content)
    chat_page.should_have_send_button_visible()

    # Test input clearing
    chat_page.clear_chat_input()
    chat_page.should_have_empty_chat_input()


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.ui
def test_message_sending_functionality(page, navigate_to_new_chat_page):
    """
    Test message sending functionality with different message types.

    This test verifies that different types of messages can be sent
    successfully and that the chat interface handles them appropriately.
    """
    chat_page = navigate_to_new_chat_page(page)

    # Send the test message
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)

    # Verify message was sent and appears in chat
    chat_page.should_have_history_visible()
    chat_page.should_have_message_sent(test_message.content)

    # Verify assistant response is appeared
    chat_page.wait_for_assistant_response()
    chat_page.should_have_assistant_response()


@pytest.mark.chat
@pytest.mark.ui
def test_multiple_messages_workflow(page, navigate_to_new_chat_page):
    """
    Test sending multiple messages in sequence.

    This test verifies that the chat can handle multiple messages
    and maintains proper conversation flow.

    Multi-Message Flow:
    1. Send initial message
    2. Send follow-up message
    3. Verify both messages are preserved
    4. Verify conversation continuity
    """
    chat_page = navigate_to_new_chat_page(page)

    # Send first message
    first_message = get_coding_help_message()
    chat_page.send_message(first_message.content)
    chat_page.should_have_message_sent(first_message.content)
    chat_page.wait_for_assistant_response()

    # Send second message
    second_message = get_coding_question_message()
    chat_page.send_message(second_message.content)
    chat_page.should_have_message_sent(second_message.content)
    chat_page.wait_for_assistant_response()

    # Verify both messages are present
    user_messages = chat_page.get_user_message_count()
    assistant_messages = chat_page.get_assistant_message_count()
    assert_that(user_messages, equal_to(2))
    assert_that(assistant_messages, equal_to(2))


@pytest.mark.chat
@pytest.mark.ui
def test_chat_history_action_buttons_visibility(page, navigate_to_new_chat_page):
    """Test that chat history action buttons are visible after sending a message."""
    chat_page = navigate_to_new_chat_page(page)
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)
    chat_page.wait_for_assistant_response()

    # Verify chat messages action buttons
    chat_page.verify_all_chat_history_action_buttons_visible()


# ==================== CHAT MESSAGE ACTION BUTTON FUNCTIONALITY TESTS ====================


@pytest.mark.chat
@pytest.mark.ui
def test_user_message_copy_to_clipboard(page, navigate_to_new_chat_page):
    """
    Test copying user message to clipboard.

    Scenario: User clicks copy button on their message
    Expected: Message text is copied to clipboard and can be verified
    """
    chat_page = navigate_to_new_chat_page(page)

    # 1. Send a test message
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)
    chat_page.wait_for_assistant_response()

    # 2. Grant clipboard permissions to the context
    context = page.context
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    chat_page.click_user_message_copy()

    # 4. Verify clipboard content matches user message
    chat_page.verify_clipboard_content(test_message.content)


@pytest.mark.chat
@pytest.mark.ui
def test_user_message_edit_and_regenerate(page, navigate_to_new_chat_page):
    """
    Test editing user message and regenerating assistant response.

    Scenario: User edits their message and triggers regeneration
    Expected: Edit mode opens, message updates, new assistant response is generated
    """
    chat_page = navigate_to_new_chat_page(page)

    # 1. Send initial message
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)
    chat_page.wait_for_assistant_response()

    # Get initial assistant response count
    initial_assistant_count = chat_page.get_assistant_message_count()

    # 2. Click edit button (buttons are always visible)
    chat_page.click_user_message_edit()

    # 3. Verify edit mode is active - Confirm and Cancel buttons appear
    chat_page.should_have_edit_mode_active()
    chat_page.should_have_confirm_changes_button_visible()
    chat_page.should_have_cancel_changes_button_visible()

    # 4. Edit the message (append text) - message becomes editable in place
    edited_message = f"{test_message.content} - edited"
    chat_page.edit_message_text(edited_message)

    # 5. Click Confirm Changes button to save the edit and regenerate
    chat_page.click_confirm_changes()

    # 6. Wait for new assistant response
    chat_page.wait_for_assistant_response()

    # 7. Verify edited message appears in chat
    chat_page.should_have_message_sent(edited_message)

    # 8. Verify new assistant response was generated (count should stay the same - regeneration replaces)
    final_assistant_count = chat_page.get_assistant_message_count()
    assert_that(final_assistant_count, equal_to(initial_assistant_count))

    # 9. Assistant message history indicator becomes visible and has correct count
    chat_page.should_have_assistant_message_history_indicator_visible()
    chat_page.should_have_assistant_message_history_indicator_count(2)


@pytest.mark.chat
@pytest.mark.ui
def test_user_message_regenerate_assistant_response(page, navigate_to_new_chat_page):
    """
    Test regenerating assistant response from user message.

    Scenario: User clicks regenerate button on their message
    Expected: New assistant response is generated
    """
    chat_page = navigate_to_new_chat_page(page)

    # 1. Send a test message
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)
    chat_page.wait_for_assistant_response()

    # 2. Click regenerate button
    chat_page.click_user_message_regenerate()

    # 3. Wait for new assistant response
    chat_page.wait_for_assistant_response()

    # 4. Verify assistant response was regenerated
    chat_page.should_have_assistant_response()
    # Response count should remain the same (regeneration replaces)
    assert_that(chat_page.get_assistant_message_count(), equal_to(1))

    # Assistant message history indicator becomes visible and has correct count
    chat_page.should_have_assistant_message_history_indicator_visible()
    chat_page.should_have_assistant_message_history_indicator_count(2)


@pytest.mark.chat
@pytest.mark.ui
def test_user_message_delete(page, navigate_to_new_chat_page):
    """
    Test deleting user message from chat history.

    Scenario: User clicks delete button on their message
    Expected: Message is removed from visible chat history
    """
    chat_page = navigate_to_new_chat_page(page)

    # 1. Send a test message
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)
    chat_page.wait_for_assistant_response()

    # Get initial message count
    initial_user_count = chat_page.get_user_message_count()

    # 2. Click delete button (buttons are always visible)
    chat_page.click_user_message_delete()

    # 3. Confirm deletion in the confirmation dialog
    chat_page.confirm_delete()

    # 4. Verify message was deleted (count decreased)
    chat_page.should_have_message_deleted(initial_user_count)


@pytest.mark.chat
@pytest.mark.ui
def test_assistant_message_copy_to_clipboard(page, navigate_to_new_chat_page):
    """
    Test copying assistant message to clipboard.

    Scenario: User clicks copy button on assistant's message
    Expected: Assistant message text is copied to clipboard
    """
    chat_page = navigate_to_new_chat_page(page)

    # 1. Send a test message and wait for assistant response
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)
    chat_page.wait_for_assistant_response()

    # Get assistant message text
    assistant_response = chat_page.get_last_assistant_message_text()

    # 2. Grant clipboard permissions and click copy
    context = page.context
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    chat_page.click_assistant_message_copy()

    # 4. Verify clipboard content matches assistant message
    chat_page.verify_clipboard_content(assistant_response)


@pytest.mark.chat
@pytest.mark.ui
def test_assistant_message_edit(page, navigate_to_new_chat_page):
    """
    Test editing assistant message.

    Scenario: User clicks edit button on assistant's message
    Expected: Edit mode opens for assistant message
    """
    chat_page = navigate_to_new_chat_page(page)

    # 1. Send a test message and wait for assistant response
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)
    chat_page.wait_for_assistant_response()
    assistant_response = chat_page.get_last_assistant_message_text()

    # 2. Click edit button (buttons are always visible)
    chat_page.click_assistant_message_edit()

    # 3. Verify edit mode is active
    chat_page.should_have_edit_mode_active()

    # 4. Edit the assistant message text
    edited_response = f"{assistant_response} - edited"
    chat_page.edit_assistant_response(edited_response)
    assistant_response = chat_page.get_last_assistant_message_text()

    assert_that(assistant_response, equal_to(edited_response))


@pytest.mark.chat
@pytest.mark.ui
def test_assistant_message_export_menu(page, navigate_to_new_chat_page):
    """
    Test assistant message export menu.

    Scenario: User clicks export button on assistant's message
    Expected: Export menu appears
    """
    chat_page = navigate_to_new_chat_page(page)

    # 1. Send a test message and wait for assistant response
    test_message = get_simple_test_message()
    chat_page.send_message(test_message.content)
    chat_page.wait_for_assistant_response()

    # 2. Click export button
    chat_page.click_assistant_message_share_export()

    # 3. Verify export popup menu is visible
    chat_page.should_have_export_popup_menu_visible()


# ==================== STOP GENERATION BUTTON TESTS ====================


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.sanity
def test_stop_generation_button_css_state_and_halt_flow(
    page, navigate_to_new_chat_page
):
    chat_page = navigate_to_new_chat_page(page)

    chat_page.should_not_have_stop_button_visible()

    long_prompt = get_long_running_prompt_message()
    chat_page.send_message(long_prompt.content)

    chat_page.wait_for_generation_to_start()

    chat_page.should_have_stop_button_visible()
    chat_page.should_have_stop_button_enabled()
    chat_page.should_have_stop_button_row_full_opacity()
    chat_page.should_have_stop_button_row_pointer_events_auto()

    chat_page.click_stop_generation()

    chat_page.wait_for_idle_state()
    # Generation was interrupted via Stop, so the submit control comes back
    # as "Continue" (resume this step), not "Send" (start a fresh turn).
    chat_page.should_have_continue_button_visible()
    chat_page.should_not_have_stop_button_visible()


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.sanity
def test_stop_button_visible_after_resend_first_message_in_multi_message_chat(
    page, navigate_to_new_chat_page
):
    chat_page = navigate_to_new_chat_page(page)

    first_message = get_long_running_prompt_message()

    chat_page.send_message(first_message.content)
    chat_page.wait_for_generation_to_start()
    chat_page.should_have_stop_button_visible()
    chat_page.should_have_stop_button_enabled()
    chat_page.wait_for_assistant_response()

    second_message = get_simple_test_message()

    chat_page.send_message(second_message.content)
    chat_page.wait_for_generation_to_start()
    chat_page.should_have_stop_button_visible()
    chat_page.should_have_stop_button_enabled()
    chat_page.wait_for_idle_state()
    chat_page.should_have_send_button_visible()
    chat_page.should_not_have_stop_button_visible()

    chat_page.click_user_message_regenerate()
    chat_page.wait_for_generation_to_start()
    chat_page.should_have_stop_button_visible()

    chat_page.click_stop_generation()
    chat_page.wait_for_idle_state()
    chat_page.should_not_have_stop_button_visible()
    # Interrupted via Stop again, so "Continue" is expected here too.
    chat_page.should_have_continue_button_visible()


@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.ui
def test_chat_displays_assistant_description(page, chat_with_described_assistant):
    """Assistant with a configured description shows it in the chat intro area."""
    chat_page, description_text = chat_with_described_assistant(page)
    chat_page.should_have_chat_input_visible()
    chat_page.should_show_chat_description(description_text)
    chat_page.should_not_show_empty_description_placeholder()
