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
Chat Page Object for CodeMie UI Testing

This module implements the Chat page object following the established POM patterns
in the CodeMie test harness. It provides comprehensive support for chat functionality
including chat creation, message handling, and configuration management.

Following the same architecture as other page objects in the framework:
- Property-based element locators with multiple fallbacks
- Comprehensive verification methods
- Integration with ReportPortal via @step decorators
- Method chaining support for fluent API
- Robust error handling and graceful degradation
"""

import re
from typing import List

from hamcrest import assert_that, equal_to
from playwright.sync_api import expect, Locator, Request
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from reportportal_client import step

from codemie_test_harness.tests.ui import conversation_ids
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.components.export_conversation_dialog import (
    ExportConversationDialog,
)
from codemie_test_harness.tests.ui.pageobject.chats.configuration_panel import (
    ConfigurationPanel,
)


# noinspection PyArgumentList
class ChatPage(BasePage):
    """
    Chat page object with comprehensive chat functionality support.

    This class encapsulates all chat-related UI interactions including:
    - Chat creation and management
    - Message composition and sending
    - Configuration handling
    - Navigation and verification methods

    Follows established POM patterns with property-based locators and method chaining.
    """

    chat_id = None

    def __init__(self, page):
        super().__init__(page)
        self.page_url = "/chats"

    # ==================== CORE CHAT ELEMENTS ====================

    @property
    def chat_title(self) -> Locator:
        """Chat title."""
        return self.page.locator("h1.text-2xl")

    @property
    def new_chat_button(self) -> Locator:
        """Primary new chat button - the one at the top of the page"""
        return self.page.get_by_role("button", name="New Chat").first

    @property
    def chat_input(self) -> Locator:
        """Main chat input field. Scoped to contenteditable=true so fill() auto-waits for Quill init."""
        return self.page.locator('.ql-editor[contenteditable="true"]')

    @property
    def send_button(self) -> Locator:
        """Send message button — shown for a fresh turn (chat input idle,
        no prior response in this turn was interrupted via Stop).

        Distinct from continue_button: once Stop is clicked mid-generation,
        this button is replaced by "Continue" (confirmed live: typing new
        text into the input does NOT relabel it back to "Send" — Continue
        remains the only submit action until the next response completes
        normally). Use submit_button where the intent is "click/wait for
        whichever submit control is present", not "assert it says Send".
        """
        return self.page.locator('[data-onboarding="chat-input"]').get_by_role(
            "button", name="Send", exact=True
        )

    @property
    def continue_button(self) -> Locator:
        """Continue button — replaces Send specifically after a response was
        interrupted via Stop; resumes the halted step rather than starting a
        fresh turn. See send_button for why these are kept as separate
        locators instead of one merged concept."""
        return self.page.locator('[data-onboarding="chat-input"]').get_by_role(
            "button", name="Continue", exact=True
        )

    @property
    def submit_button(self) -> Locator:
        """Whichever submit control is currently shown for the chat input —
        Send or Continue. For internal use (clicking to submit, waiting for
        the input to become interactable again) where it doesn't matter
        which of the two is showing; use send_button/continue_button
        directly when a test needs to assert which one it actually is.
        """
        return self.page.locator('[data-onboarding="chat-input"]').get_by_role(
            "button", name=re.compile(r"^(Send|Continue)$")
        )

    @property
    def stop_button(self) -> Locator:
        """
        Stop generation button — visible only while the assistant is generating a response.

        Distinguished from the Send button by its `min-w-0` Tailwind class (Send uses
        `min-w-14`). The idle "Continue" button (shown after a cancelled/completed step)
        also carries `min-w-0`, so it is excluded by its text — the real Stop button is
        icon-only with no text label. When generation ends the locator matches no
        elements and `to_be_hidden()` passes without ambiguity.
        """
        return (
            self.page.locator('[data-onboarding="chat-input"]')
            .locator("button.min-w-0")
            .filter(has_not_text="Continue")
        )

    @property
    def stop_button_row(self) -> Locator:
        """
        The flex row that wraps the Stop / Send button.

        During generation this row carries `pointer-events-auto` to escape the parent
        container's `pointer-events-none`. The opacity-60 dim is applied only to the
        editor wrapper and left-buttons div, so the stop button row is at full opacity
        without needing an explicit opacity-100 class.
        """
        return self.page.locator('[data-onboarding="chat-input"]').locator(
            ".flex.items-center.ml-auto"
        )

    @property
    def chat_history_container(self) -> Locator:
        """Container holding all chat messages - scrollable messages area."""
        return self.page.locator(".flex.flex-col.gap-6.grow.max-w-5xl.mx-auto")

    @property
    def user_message(self) -> Locator:
        """Individual user message element."""
        return self.chat_history_container.locator("p.chat-editor-message")

    @property
    def assistant_message(self) -> Locator:
        """Individual assistant message element."""
        return self.chat_history_container.locator(".markdown.text-text-primary")

    @property
    def assistant_message_images(self) -> Locator:
        """<img> elements rendered inside the assistant's message."""
        return self.assistant_message.locator("img")

    @property
    def blocked_image_badges(self) -> Locator:
        """Blocked-image badges rendered in place of a disallowed <img> element."""
        return self.page.locator(".blocked-image-badge")

    @property
    def tool_blocks(self) -> Locator:
        """Tool execution blocks (expandable buttons showing tool usage)."""
        return self.chat_history_container.locator("button").filter(
            has=self.page.locator('text="Success"')
        )

    @property
    def editable_message_input(self) -> Locator:
        """Editable message input that appears when editing a user message (first .ql-editor in the page)."""
        return self.page.locator(".ql-editor").first

    @property
    def editable_assistant_response(self) -> Locator:
        """
        Editable textbox that appears when editing a short assistant message (in-place edit).

        When edit mode is active for a short assistant message, the response becomes
        an editable textbox within the assistant message container.
        """
        return self.chat_history_container.get_by_role("textbox").last

    @property
    def edit_message_dialog(self) -> Locator:
        """Edit Message dialog that appears when editing long assistant messages."""
        return self.page.get_by_role("dialog")

    @property
    def edit_message_dialog_textbox(self) -> Locator:
        """Textbox inside the Edit Message dialog for long assistant responses."""
        return self.edit_message_dialog.get_by_role(
            "textbox", name="Type your message here"
        )

    @property
    def edit_message_dialog_save_button(self) -> Locator:
        """Save button inside the Edit Message dialog."""
        return self.edit_message_dialog.get_by_role("button", name="Save")

    @property
    def processed_in_field(self) -> Locator:
        return self.page.locator("div.text-text-quaternary:has-text('Processed in')")

    @property
    def message_history_counter(self) -> Locator:
        """
        Message history counter that appears after regenerating (e.g., '2 / 2').

        Located in the assistant message action buttons area, displays as navigation
        with left arrow, counter text (e.g., "2 / 2"), and right arrow.
        """
        # Look for a generic element containing the pattern "N / N" in the chat history
        return self.chat_history_container.locator("div").filter(has_text=" / ").last

    @property
    def search_assistant_list(self) -> Locator:
        return self.page.locator("#quill-mention-list")

    # ==================== ACTION BUTTONS ====================

    @property
    def action_buttons_bar(self) -> Locator:
        """Execution Info button with tooltip."""
        return self.page.locator("div.ml-auto")

    # ==================== CHAT HISTORY CONTAINER ACTION BUTTONS ====================

    @property
    def user_message_copy_button(self) -> Locator:
        """Copy button for user messages - first button in user message actions."""
        return self.page.locator('button[data-tooltip-content="Copy message"]').first

    @property
    def user_message_edit_button(self) -> Locator:
        """Edit button for user messages - second button in user message actions."""
        return self.page.locator('button[data-tooltip-content="Edit message"]').first

    @property
    def user_message_regenerate_button(self) -> Locator:
        """Resend/regenerate button for user messages - triggers new assistant response."""
        return self.page.get_by_role("button", name="Resend message").first

    @property
    def user_message_delete_button(self) -> Locator:
        """Delete button for user messages - fourth button in user message actions."""
        return self.page.locator('button[data-tooltip-content="Delete message"]').first

    @property
    def assistant_message_copy_button(self) -> Locator:
        """Copy button for assistant messages - first button in assistant message actions."""
        return self.page.locator('button[data-tooltip-content="Copy message"]').nth(1)

    @property
    def assistant_message_edit_button(self) -> Locator:
        """Edit button for assistant messages - second button in assistant message actions."""
        return self.page.locator('button[data-tooltip-content="Edit message"]').nth(1)

    @property
    def assistant_message_share_button(self) -> Locator:
        """Share/export button for assistant messages - button with export icon."""
        return self.page.locator('button[data-tooltip-content="Export message"]').first

    @property
    def assistant_message_like_button(self) -> Locator:
        """Like button for assistant messages."""
        return self.page.get_by_role(
            "button", name="Like this response", exact=True
        ).first

    @property
    def assistant_message_remove_like_button(self) -> Locator:
        """Remove like button (appears after liking a message)."""
        return self.page.get_by_role(
            "button", name="Click to remove your positive feedback"
        ).first

    @property
    def assistant_message_dislike_button(self) -> Locator:
        """Dislike button for assistant messages."""
        return self.page.get_by_role("button", name="Dislike this response").first

    @property
    def delete_feedback_dialog(self) -> Locator:
        """Delete Feedback dialog that appears when removing like."""
        return self.page.get_by_role("dialog", name="Delete Feedback")

    @property
    def delete_feedback_confirm_button(self) -> Locator:
        """Delete Feedback button inside the delete dialog."""
        return self.delete_feedback_dialog.get_by_role("button", name="Delete Feedback")

    @property
    def submit_feedback_dialog(self) -> Locator:
        """Submit Feedback dialog that appears when clicking dislike."""
        return self.page.get_by_role(
            "dialog", name="Submit Feedback About This Assistant"
        )

    @property
    def assistant_message_remove_dislike_button(self) -> Locator:
        """Remove dislike button (active state after disliking)."""
        return self.page.get_by_role(
            "button", name="Click to remove your negative feedback"
        ).first

    @property
    def submit_feedback_send_button(self) -> Locator:
        """Send button in Submit Feedback dialog."""
        return self.submit_feedback_dialog.get_by_role("button", name="Send")

    @property
    def confirm_changes_button(self) -> Locator:
        """Confirm Changes button that appears when editing a message."""
        return self.page.get_by_role("button", name="Confirm Changes")

    @property
    def cancel_changes_button(self) -> Locator:
        """Cancel changes button that appears when editing a message."""
        return self.page.get_by_role("button", name="Cancel changes")

    @property
    def confirm_delete_button(self) -> Locator:
        """
        Confirm Delete button that appears in the confirmation dialog when deleting a message.

        Scoped to the dialog to avoid ambiguity with the "Delete message" action button.
        """
        return self.page.get_by_role("dialog", name="Delete message").get_by_role(
            "button", name="Delete"
        )

    @property
    def execution_info_button(self) -> Locator:
        """Usage details / Execution Info button."""
        return self.page.locator('button[aria-label="Usage details"]')

    @property
    def share_chat_button(self) -> Locator:
        """Share chat button with share icon."""
        return self.page.locator('button[aria-label="Share Chat"]')

    @property
    def export_chat_button(self) -> Locator:
        """Export chat button with export icon."""
        return self.page.locator('button[aria-label="Export Conversation"]')

    @property
    def clear_chat_button(self) -> Locator:
        """Clear chat button with clear/delete icon."""
        return self.page.locator('button[data-tooltip-content="Clear Chat"]')

    @property
    def add_attachment_button(self) -> Locator:
        """Add attachment button with paperclip icon."""
        return self.page.locator(
            'button[data-tooltip-content*="Attach up to 20 files"]'
        )

    @property
    def file_input(self) -> Locator:
        """Native hidden file input backing the attach-file control."""
        return self.page.locator('input[type="file"]')

    @property
    def attachment_remove_buttons(self) -> Locator:
        """Remove buttons for any file attachment previews currently rendered in the composer.

        Scoped to the chat-input wrapper (the composer container) so this
        locator cannot be satisfied by unrelated "Remove" controls elsewhere
        on the chat page.
        """
        return self.chat_input_wrapper.locator(
            'button[aria-label*="Remove"], button:has-text("Remove")'
        )

    @property
    def dynamic_tools_button(self) -> Locator:
        """Dynamic tools button - opens tools settings panel."""
        return self.page.locator(
            'button[data-tooltip-content*="Configure dynamic tools"]'
        )

    @property
    def tools_settings_panel(self) -> Locator:
        """Tools Settings panel container."""
        return self.page.locator('text="Tools Settings"').locator("..")

    @property
    def web_search_toggle(self) -> Locator:
        """Web Search toggle - the label wrapping the sr-only peer checkbox."""
        return self.tools_settings_panel.locator("label").filter(has_text="Web Search")

    @property
    def model_selector_button(self) -> Locator:
        """Model selector button in chat input area - shows current model selection."""
        return self.page.get_by_role("button", name="Default", exact=True)

    @property
    def skills_button(self) -> Locator:
        """Skills button - opens skills selection."""
        return self.page.get_by_role("button", name="Skills")

    @property
    def skills_dialog(self) -> Locator:
        """Skills dialog container."""
        return self.page.get_by_role("dialog", name="Attach Skills")

    @property
    def skills_confirm_button(self) -> Locator:
        """Confirm button in skills dialog."""
        return self.skills_dialog.get_by_role("button", name="Confirm")

    @property
    def start_conversation_invitation(self) -> Locator:
        """Start conversation invitation text and elements."""
        return self.page.locator("h1").filter(
            has_text="Start a conversation with an assistant"
        )

    @property
    def conversation_invitation_subtitle(self) -> Locator:
        """Conversation subtitle text."""
        return self.page.get_by_text(
            "Ask anything or type @ and choose assistant from the list"
        )

    # ==================== CONFIGURATION ELEMENTS ====================

    @property
    def configuration_button(self) -> Locator:
        """Configuration button with text and icon."""
        return self.page.locator("button[aria-label='Chat configuration']")

    @property
    def chat_configuration_panel(self):
        """Chat configuration component."""
        return ConfigurationPanel(self.page)

    # ==================== NAVIGATION METHODS ====================

    @step
    def navigate_to(self, chat_id: str):
        """Navigate to the main chat page."""
        self.page.goto(f"{self.page_url}/{chat_id}")
        self.wait_for_page_load()
        self.chat_id = chat_id
        return self

    @step
    def navigate_to_shared_conversation(self, share_token: str):
        """Open the read-only shared view of a conversation (/share/conversations/<token>)."""
        self.page.goto(f"/share/conversations/{share_token}")
        self.wait_for_page_load()
        return self

    @step
    def open_conversation_with_export_button(self, chat_id: str):
        """Open an existing conversation on a desktop-sized viewport and wait for the header Export button."""
        self.page.set_viewport_size({"width": 1920, "height": 980})
        self.navigate_to(chat_id)
        expect(self.export_chat_button).to_be_visible(timeout=30000)
        return self

    @step
    def start_new_chat(self):
        """Start a new chat conversation."""
        if self.new_chat_button.is_visible():
            self.new_chat_button.click()
            self.wait_for_page_load()
            _id = self.get_id_from_url(self.evaluate_current_url())
            if _id == "chats":
                self.chat_id = None
                return None
            conversation_ids.append(_id)
            self.chat_id = _id
            return _id
        return None

    # ==================== ACTION BUTTON METHODS ====================

    @step
    def click_execution_info(self):
        """Click the execution info button."""
        self.execution_info_button.click()
        return self

    @step
    def click_share_chat(self):
        """Click the share chat button."""
        self.share_chat_button.click()
        return self

    @step
    def click_export_chat(self):
        """Click the export chat button."""
        self.export_chat_button.click()
        return self

    @step
    def open_export_conversation_dialog(self) -> ExportConversationDialog:
        """Open the Export Conversation dialog from the chat header."""
        self.click_export_chat()
        return ExportConversationDialog(self.page).should_be_visible()

    @step
    def click_clear_chat(self):
        """Click the clear chat button."""
        self.clear_chat_button.click()
        return self

    @step
    def click_add_attachment(self):
        """Click the add attachment button."""
        self.add_attachment_button.click()
        return self

    @step
    def attach_file(self, file_path: str):
        """
        Attach a file to the chat input.

        Args:
            file_path: Absolute path to the file to attach
        """
        with self.page.expect_response(
            lambda r: "files/bulk" in r.url and r.request.method == "POST",
            timeout=15000,
        ):
            self.page.locator('input[type="file"]').set_input_files(file_path)
        return self

    @step
    def attach_multiple_files(self, file_paths: list):
        """
        Attach multiple files to the chat input at once.

        Args:
            file_paths: List of absolute paths to files to attach
        """
        with self.page.expect_response(
            lambda r: "files/bulk" in r.url and r.request.method == "POST",
            timeout=15000,
        ):
            self.page.locator('input[type="file"]').set_input_files(file_paths)
        return self

    @step
    def remove_first_attachment(self):
        """Remove the first attached file."""
        remove_button = self.page.locator(
            'button[aria-label*="Remove"], button:has-text("Remove")'
        ).first
        remove_button.click()
        return self

    @step
    def click_dynamic_tools(self):
        """Click the dynamic tools button to open tools settings panel."""
        self.dynamic_tools_button.click()
        return self

    @step
    def enable_web_search(self):
        """Enable Web Search tool in tools settings panel."""
        self.web_search_toggle.locator("span.switch").click()
        # Wait for the underlying checkbox to reflect the enabled state rather
        # than sleeping an arbitrary 500 ms (Switch.tsx: input[type=checkbox]).
        expect(self.web_search_toggle.locator("input[type='checkbox']")).to_be_checked(
            timeout=5000
        )
        return self

    @step
    def should_not_have_web_search_toggle(self):
        """Assert the Web Search option is absent from the Tools Settings panel.

        The panel only renders this option when features:webSearch is enabled
        in customer config.
        """
        expect(self.web_search_toggle).to_have_count(0)
        return self

    @step
    def should_have_web_search_toggle(self):
        """Assert the Web Search option is present in the Tools Settings panel."""
        expect(self.web_search_toggle).to_have_count(1)
        return self

    @step
    def close_tools_settings(self):
        """Close tools settings panel by clicking outside or the button again."""
        self.dynamic_tools_button.click()
        return self

    @step
    def select_model(self, model_name: str):
        """
        Select a specific model from the model dropdown.

        Args:
            model_name: Name of the model to select (e.g., "GPT-4o 2024-08-06", "Bedrock Claude 4.5 Sonnet")
        """
        self.model_selector_button.click()
        search_input = self.page.get_by_role("combobox", name="Search LLM models")
        search_input.wait_for(state="visible", timeout=5000)
        search_input.fill(model_name)

        model_option = self.page.get_by_role(
            "option", name=model_name, exact=True
        ).first
        model_option.wait_for(state="visible", timeout=5000)
        model_option.click()
        return self

    @step
    def click_skills_button(self):
        """Click the skills button to open skills selection dialog."""
        self.skills_button.click()
        self.skills_dialog.wait_for(state="visible", timeout=5000)
        return self

    @step
    def select_skill(self, skill_name: str):
        """
        Select a skill by checking its checkbox in the skills dialog.

        Args:
            skill_name: Name of the skill to select
        """
        # Search for the skill
        search_input = self.skills_dialog.get_by_placeholder("Search skills...")
        search_input.fill(skill_name)

        # Select the skill checkbox
        skill_checkbox = self.skills_dialog.get_by_role("checkbox", name=skill_name)
        skill_checkbox.check()
        return self

    @step
    def confirm_skills_selection(self):
        """Confirm the selected skills by clicking Confirm button."""
        self.skills_confirm_button.click()
        self.skills_dialog.wait_for(state="hidden", timeout=5000)
        return self

    @step
    def should_have_skill_selected(self, skill_name: str):
        """
        Verify that a skill is selected (checkbox is checked) in the skills dialog.

        Args:
            skill_name: Name of the skill to verify
        """
        skill_checkbox = self.skills_dialog.get_by_role("checkbox", name=skill_name)
        expect(skill_checkbox).to_be_checked()
        return self

    @step
    def click_configuration(self):
        """Click the configuration button."""
        self.configuration_button.click()
        return self

    @step
    def open_configuration(self):
        """Open the configuration panel and wait for it to be visible."""
        if not self.chat_configuration_panel.panel.is_visible():
            self.click_configuration()
            expect(self.chat_configuration_panel.panel).to_be_visible(timeout=5000)
        return self

    @step
    def close_configuration(self):
        """Close the configuration panel and wait for it to disappear.

        Without the explicit wait the panel close-animation can still be running
        when the next action fires, causing locators that overlap with the panel
        (e.g. the chat input) to time out.
        """
        if self.chat_configuration_panel.panel.is_visible():
            self.click_configuration()
            expect(self.chat_configuration_panel.panel).to_be_hidden(timeout=5000)
        return self

    # ==================== CHAT HISTORY MESSAGE ACTION METHODS ====================

    @step
    def click_user_message_copy(self):
        """Click the copy button for user message."""
        self.user_message_copy_button.click()
        return self

    @step
    def click_user_message_edit(self):
        """Click the edit button for user message."""
        self.user_message_edit_button.click()
        return self

    @step
    def click_user_message_delete(self):
        """Click the delete button for user message."""
        self.user_message_delete_button.click()
        return self

    @step
    def click_user_message_regenerate(self):
        """Click the regenerate button for user message."""
        self.user_message_regenerate_button.click()
        return self

    @step
    def click_assistant_message_copy(self):
        """Click the copy button for assistant message."""
        self.assistant_message_copy_button.click()
        return self

    @step
    def click_assistant_message_edit(self):
        """Click the edit button for assistant message."""
        self.assistant_message_edit_button.click()
        return self

    @step
    def click_assistant_message_share_export(self):
        """Click the share/export button for assistant message."""
        self.assistant_message_share_button.click()
        return self

    @step
    def click_assistant_message_like(self):
        """Click the like button and wait for response."""
        with self.page.expect_response(
            lambda r: "v1/feedback" in r.url and r.request.method == "POST",
            timeout=15000,
        ):
            self.assistant_message_like_button.click()
        return self

    @step
    def click_assistant_message_remove_like(self):
        """Click the button to remove like from assistant message."""
        self.assistant_message_remove_like_button.click()
        return self

    @step
    def confirm_delete_feedback(self):
        """Confirm deletion and wait for response."""
        with self.page.expect_response(
            lambda r: "v1/feedback" in r.url and r.request.method == "DELETE",
            timeout=15000,
        ):
            self.delete_feedback_confirm_button.click()
        return self

    @step
    def click_assistant_message_dislike(self):
        """Click the dislike button for assistant message (opens feedback dialog)."""
        self.assistant_message_dislike_button.click()
        return self

    @step
    def click_assistant_message_remove_dislike(self):
        """Click the remove dislike button (after dislike has been submitted)."""
        self.assistant_message_remove_dislike_button.click()
        return self

    @step
    def select_feedback_option(self, option_name: str):
        """Select a feedback option."""
        self.submit_feedback_dialog.get_by_role("button", name=option_name).click()
        return self

    @step
    def send_feedback(self):
        """Click Send button and wait for response."""
        with self.page.expect_response(
            lambda r: "v1/feedback" in r.url and r.request.method == "POST",
            timeout=15000,
        ):
            self.submit_feedback_send_button.click()
        return self

    @step
    def click_confirm_changes(self):
        """Click the Confirm changes button after editing a message."""
        self.confirm_changes_button.click()
        return self

    @step
    def click_cancel_changes(self):
        """Click the Cancel changes button to cancel message editing."""
        self.cancel_changes_button.click()
        return self

    @step
    def confirm_delete(self):
        """
        Confirm the delete action if a confirmation dialog appears.

        This method attempts to find and click the Delete button in the confirmation dialog.
        If no dialog appears (or button is not visible), the method completes silently.
        """
        if self.confirm_delete_button.is_visible(timeout=2000):
            self.confirm_delete_button.click()
        return self

    # ==================== CHAT INTERACTION METHODS ====================

    @step
    def send_message(self, message: str, assistant_name=""):
        """
        Send a message in the chat.

        Args:
            message: The message text to send
            assistant_name: assistant_name
        """
        if not assistant_name == "":
            self.chat_input.fill(f"@{assistant_name}")
            self._dismiss_release_notification_if_present()
            self.get_assistant_item_in_list(assistant_name).click()
            self.chat_input.type(message)
            self.submit_button.click()
            return self
        else:
            self.chat_input.fill(message)
            self.submit_button.click()
            return self

    @step
    def send_message_and_capture_model_request(self, message: str, assistant_name=""):
        """
        Send a message and capture the outgoing request to the model endpoint
        (POST .../assistants/{assistant_id}/model or .../assistants/virtual/model).

        Returns the Playwright Request so callers can assert on
        ``request.post_data_json["skill_ids"]`` and ``request.response().status``
        (e.g. regression coverage for the `skill_ids: [null]` -> 422 case).

        Args:
            message: The message text to send
            assistant_name: assistant_name to @-mention, if any
        """
        with self.page.expect_request(
            re.compile(r"/assistants/(?:virtual|[^/]+)/model(?:\?.*)?$"),
            timeout=30000,
        ) as request_info:
            self.send_message(message, assistant_name=assistant_name)
        return request_info.value

    @step
    def capture_requests_during(self, action) -> List[Request]:
        """Capture all HTTP requests fired during an action.

        Use to assert a request was NOT sent (opposite of expect_request).
        Action must include waits for async work (e.g. lambda: (send_message(), wait_for_generation_to_start()))
        to avoid race conditions where click() returns before fetch fires.
        """
        captured: List[Request] = []

        def _record(request: Request):
            captured.append(request)

        self.page.on("request", _record)
        try:
            action()
        finally:
            self.page.wait_for_timeout(50)  # Let in-flight requests land
            self.page.remove_listener("request", _record)
        return captured

    @step
    def should_not_have_requested(self, url_pattern: str):
        """Documentation placeholder: use capture_requests_during() + manual re.search filter."""
        return self

    @step
    def clear_chat_input(self):
        """Clear the chat input field."""
        self.chat_input.fill("")
        return self

    @step
    def type_message_without_sending(self, message: str):
        """Type a message without sending it."""
        self.chat_input.fill(message)
        return self

    @step
    def send_test_message(self, message: str = "Test message"):
        """Send a test message for verification purposes."""
        self.send_message(message)
        return self

    @step
    def get_assistant_item_in_list(self, name: str) -> Locator:
        return self.search_assistant_list.locator("p").filter(has_text=name)

    @step
    def edit_message_text(self, new_message: str):
        """
        Edit the message text when in edit mode.

        When edit mode is active (after clicking edit button), the message
        becomes editable in place. This method clears and updates that text.

        Args:
            new_message: The new message text to replace the current message
        """
        # Focus the editable area
        self.editable_message_input.click()

        # Clear existing text
        self.editable_message_input.clear()

        # Type new message
        self.editable_message_input.fill(new_message)
        return self

    @step
    def edit_assistant_response(self, new_response: str):
        """
        Edit the assistant response text when in edit mode.

        Handles two scenarios:
        1. Short responses - Edit in-place with textbox (confirm with Confirm Changes button)
        2. Long responses - Edit in popup dialog with textbox (confirm with Save button)

        Args:
            new_response: The new response text to replace the current assistant response
        """
        # Check if dialog appeared (for long responses)
        if self.edit_message_dialog.is_visible(timeout=2000):
            # Long response - use dialog
            self.edit_message_dialog_textbox.click()
            self.edit_message_dialog_textbox.clear()
            self.edit_message_dialog_textbox.fill(new_response)
            self.edit_message_dialog_save_button.click()
        else:
            # Short response - edit in-place
            self.editable_assistant_response.click()
            self.editable_assistant_response.clear()
            self.editable_assistant_response.fill(new_response)
            self.confirm_changes_button.click()
        return self

    # ==================== ACTION BUTTON VERIFICATION METHODS ====================

    @step
    def should_have_execution_info_button_visible(self):
        """Verify that the execution info button is visible."""
        expect(self.execution_info_button).to_be_visible()
        return self

    @step
    def should_have_share_chat_button_visible(self):
        """Verify that the share chat button is visible."""
        expect(self.share_chat_button).to_be_visible()
        return self

    @step
    def should_have_export_chat_button_visible(self):
        """Verify that the export chat button is visible."""
        expect(self.export_chat_button).to_be_visible()
        return self

    @step
    def should_have_clear_chat_button_visible(self):
        """Verify that the clear chat button is visible."""
        expect(self.clear_chat_button).to_be_visible()
        return self

    @step
    def should_have_configuration_button_visible(self):
        """Verify that the configuration button is visible."""
        expect(self.configuration_button).to_be_visible()
        return self

    @step
    def should_have_add_attachment_button_visible(self):
        """Verify that the add attachment button is visible."""
        expect(self.add_attachment_button).to_be_visible()
        return self

    @step
    def should_have_add_attachment_button_visible_and_enabled(self):
        """Verify the Attach File control is visible and interactive (AC-2, enabled/default path)."""
        expect(self.add_attachment_button).to_be_visible()
        expect(self.add_attachment_button).to_be_enabled()
        return self

    @step
    def should_have_add_attachment_button_hidden_or_disabled(self):
        """
        Verify the Attach File control is not available to the user (AC-2).

        The control may either be entirely absent from the DOM or rendered
        but non-interactive (disabled) — both satisfy "not available".
        """
        if self.add_attachment_button.count() == 0:
            expect(self.add_attachment_button).to_have_count(0)
        else:
            expect(self.add_attachment_button).to_be_disabled()
        return self

    @step
    def should_not_open_file_picker_when_attach_file_clicked(self, timeout: int = 3000):
        """
        Verify that clicking (or attempting to click) the Attach File control
        does NOT open a native file-picker dialog (AC-3).

        AC-2 allows the control to be either entirely absent from the DOM or
        present-but-disabled. Both branches must evaluate a real, verifiable
        expectation rather than silently short-circuiting:
          - If the control is absent, assert that absence explicitly (there
            is nothing to click, and the assertion records that fact).
          - If the control is present but disabled, a real trusted Playwright
            click is issued with ``force=True`` (bypassing only the
            actionability check that would otherwise refuse to click a
            disabled element, while still going through the genuine input
            pipeline and user activation Chromium requires to open a native
            file chooser) to confirm that even a forced click does not
            request a file chooser.

        Args:
            timeout: Milliseconds to wait for a 'filechooser' page event before
                concluding that none was requested.
        """
        if self.add_attachment_button.count() == 0:
            expect(self.add_attachment_button).to_have_count(0)
            return self
        try:
            with self.page.expect_file_chooser(timeout=timeout):
                self.add_attachment_button.click(force=True)
        except PlaywrightTimeoutError:
            return self
        raise AssertionError(
            "A file chooser dialog was requested despite the attach-file "
            "setting being disabled"
        )

    @step
    def should_have_no_attachments_in_composer(self):
        """
        Verify no file attachment preview/chip is present in the message
        composer (AC-3) — i.e. no upload was initiated and no attachment was
        added to the pending message.
        """
        expect(self.attachment_remove_buttons).to_have_count(0)
        return self

    @step
    def should_have_start_conversation_invitation_visible(self):
        """Verify that the start conversation invitation is visible."""
        expect(self.start_conversation_invitation).to_be_visible()
        return self

    @step
    def should_have_conversation_subtitle_visible(self):
        """Verify that the conversation subtitle is visible."""
        expect(self.conversation_invitation_subtitle).to_be_visible()
        return self

    @step
    def should_have_file_attached(self, file_name: str):
        """
        Verify that a file is attached and visible in the UI.

        Args:
            file_name: Name of the file to verify
        """
        file_indicator = self.page.get_by_text(file_name, exact=False)
        expect(file_indicator.first).to_be_visible(timeout=5000)
        return self

    @step
    def should_not_have_file_attached(self, file_name: str):
        """
        Verify that a file is not attached (removed from UI).

        Args:
            file_name: Name of the file to verify is removed
        """
        file_indicator = self.page.locator(f'text="{file_name}"')
        expect(file_indicator).to_be_hidden()
        return self

    # ==================== CHAT HISTORY CONTAINER BUTTON VERIFICATION METHODS ====================

    @step
    def should_have_user_message_copy_button_visible(self):
        """Verify that the user message copy button is visible."""
        expect(self.user_message_copy_button).to_be_visible()
        return self

    @step
    def should_have_user_message_edit_button_visible(self):
        """Verify that the user message edit button is visible."""
        expect(self.user_message_edit_button).to_be_visible()
        return self

    @step
    def should_have_user_message_regenerate_button_visible(self):
        """Verify that the user message regenerate button is visible."""
        expect(self.user_message_regenerate_button).to_be_visible()
        return self

    @step
    def should_have_user_message_delete_button_visible(self):
        """Verify that the user message delete button is visible."""
        expect(self.user_message_delete_button).to_be_visible()
        return self

    @step
    def should_have_assistant_message_copy_button_visible(self):
        """Verify that the assistant message copy button is visible."""
        expect(self.assistant_message_copy_button).to_be_visible()
        return self

    @step
    def should_have_assistant_message_edit_button_visible(self):
        """Verify that the assistant message edit button is visible."""
        expect(self.assistant_message_edit_button).to_be_visible()
        return self

    @step
    def should_have_assistant_message_share_button_visible(self):
        """Verify that the assistant message share button is visible."""
        expect(self.assistant_message_share_button).to_be_visible()
        return self

    @step
    def should_have_confirm_changes_button_visible(self):
        """Verify that the Confirm changes button is visible."""
        expect(self.confirm_changes_button).to_be_visible()
        return self

    @step
    def should_have_cancel_changes_button_visible(self):
        """Verify that the Cancel changes button is visible."""
        expect(self.cancel_changes_button).to_be_visible()
        return self

    # ==================== VERIFICATION METHODS ====================

    @step
    def should_be_on_chat_page(self):
        """Verify that we are on the chat page."""
        if self.chat_id is None:
            self.should_have_url_containing(self.page_url)
        else:
            expect(self.page).to_have_url(f"{self.page_url}/{self.chat_id}")
        return self

    @step
    def should_have_chat_title(self, title):
        """Verify that the chat title is visible."""
        expect(self.chat_title).to_be_visible()
        expect(self.chat_title).to_have_text(title)
        return self

    @step
    def should_have_new_chat_button_visible(self):
        """Verify that the new chat button is visible."""
        expect(self.new_chat_button).to_be_visible()
        return self

    @step
    def should_have_chat_input_visible(self, timeout: int = 15000):
        """Verify that the chat input field is visible.

        The editor mounts after data fetch + lazy Quill load, which on slow
        local dev environments (Vite dev server, full page reloads) can exceed
        Playwright's 5s default — same rationale as the 15s timeout in
        should_have_history_visible.
        """
        expect(self.chat_input).to_be_visible(timeout=timeout)
        return self

    @step
    def should_have_send_button_visible(self):
        """Verify that the send button is visible."""
        expect(self.send_button).to_be_visible()
        return self

    @step
    def should_have_send_button_enabled(self):
        """Verify that the send button is enabled."""
        expect(self.send_button).to_be_enabled()
        return self

    @step
    def should_have_send_button_disabled(self):
        """Verify that the send button is disabled."""
        expect(self.send_button).to_be_disabled()
        return self

    @step
    def should_have_continue_button_visible(self):
        """Verify that the Continue button is visible (shown after a
        response was interrupted via Stop)."""
        expect(self.continue_button).to_be_visible()
        return self

    # ==================== STOP GENERATION METHODS ====================

    @step
    def click_stop_generation(self):
        """Click the Stop generation button to interrupt assistant response."""
        self.stop_button.click()
        return self

    @step
    def wait_for_generation_to_start(self, timeout: int = 10000):
        """
        Wait until the assistant starts generating a response.

        The Send button is replaced by the Stop button when generation begins.
        """
        expect(self.stop_button).to_be_visible(timeout=timeout)
        return self

    @step
    def wait_for_idle_state(self, timeout: int = 30000):
        """
        Wait until the chat returns to idle state after generation ends or is stopped.

        Idle state is indicated by a submit control being visible again —
        "Send" after a normal completion, "Continue" if this turn's response
        was interrupted via Stop. Callers that need to know which one it
        actually is should assert on send_button/continue_button directly.
        """
        expect(self.submit_button).to_be_visible(timeout=timeout)
        return self

    @step
    def should_not_have_error_toast(self):
        """Assert no error toast visible — regression guard.
        Must be called during the action (inside capture_requests_during lambda) to catch transient toasts."""
        expect(self.error_toast).to_be_hidden()
        return self

    @step
    def should_have_stop_button_visible(self):
        """Verify that the Stop generation button is visible (generation is in progress)."""
        expect(self.stop_button).to_be_visible()
        return self

    @step
    def should_have_stop_button_enabled(self):
        """Verify that the Stop generation button is enabled (not disabled by pointer-events)."""
        expect(self.stop_button).to_be_enabled()
        return self

    @step
    def should_not_have_stop_button_visible(self):
        """Verify that the Stop generation button is hidden (generation has ended)."""
        expect(self.stop_button).to_be_hidden()
        return self

    @step
    def should_have_stop_button_row_full_opacity(self):
        """
        Verify the stop button row is rendered at full opacity.

        The revised CSS applies opacity-60 only to the editor wrapper and left-button
        children, not to the outer container. The stop button row has no opacity class
        and no dimmed ancestor, so its computed opacity must be 1.
        """
        opacity = self.stop_button_row.evaluate(
            "el => parseFloat(getComputedStyle(el).opacity)"
        )
        assert opacity == 1.0, f"Expected stop button row opacity 1.0, got {opacity}"
        return self

    @step
    def should_have_stop_button_row_pointer_events_auto(self):
        """
        Verify the stop button row has pointer-events-auto applied.

        This confirms the CSS fix that overrides the parent container's pointer-events-none
        while generation is in progress, ensuring click events reach the Stop button.
        """
        expect(self.stop_button_row).to_have_class(re.compile(r"pointer-events-auto"))
        return self

    @step
    def should_have_message_sent(self, message_text: str):
        """
        Verify that a specific message was sent and appears in chat.

        Args:
            message_text: The message text to verify
        """
        message_locator = self.user_message.filter(has_text=message_text)
        expect(message_locator.first).to_be_visible()
        return self

    @step
    def should_have_assistant_response(self):
        """Verify that assistant has provided a response."""
        expect(self.assistant_message.first).to_be_visible()
        return self

    @step
    def should_have_non_blank_assistant_response(self, timeout: int = 30000):
        """Verify the assistant message node contains actual reply text, not just an
        empty placeholder (e.g. reply lost/blank after a mid-generation
        page reload)."""
        non_blank_response = self.assistant_message.filter(has_text=re.compile(r"\S"))
        expect(non_blank_response.first).to_be_visible(timeout=timeout)
        return self

    @step
    def should_have_blocked_image_badge_count(self, count: int):
        """Verify the number of blocked-image badges rendered on the page."""
        expect(self.blocked_image_badges).to_have_count(count)
        return self

    @step
    def should_have_blocked_image_badge_hostname(self, hostname: str, index: int = 0):
        """Verify the nth blocked-image badge records the blocked hostname."""
        expect(self.blocked_image_badges.nth(index)).to_have_attribute(
            "data-blocked-image-hostname", hostname
        )
        return self

    @step
    def should_have_assistant_image_count(self, count: int):
        """Verify the number of <img> elements rendered in the assistant's message."""
        expect(self.assistant_message_images).to_have_count(count)
        return self

    @step
    def should_have_assistant_data_url_image(self):
        """Verify a data:image/* <img> rendered in the assistant's message — a
        data: URL never issues a network request, so it is always allowed."""
        expect(self.assistant_message.locator("img[src^='data:image']")).to_have_count(
            1
        )
        return self

    @step
    def should_not_have_assistant_image_with_src_containing(self, substring: str):
        """Verify no <img> in the assistant's message has a src containing
        `substring` — i.e. the browser never requested that host."""
        expect(
            self.assistant_message.locator(f"img[src*='{substring}']")
        ).to_have_count(0)
        return self

    @step
    def should_have_tool_used(self, tool_name_pattern: str, timeout: int = 30000):
        """
        Verify that a specific tool was used in the conversation.

        Args:
            tool_name_pattern: Tool name or pattern to match (e.g., "Code Execute", "Web Search")
            timeout: Timeout in milliseconds (default 30000ms). Code execution can take time
                     to render even after processed_in_field is visible.
        """
        tool_block = self.tool_blocks.filter(has_text=tool_name_pattern)
        expect(tool_block.first).to_be_visible(timeout=timeout)
        return self

    @step
    def should_have_any_tool_used(self, *tool_name_patterns: str, timeout: int = 30000):
        """
        Verify that at least one of the specified tools was used in the conversation.

        Args:
            tool_name_patterns: One or more tool name patterns to match (e.g., "Search", "Web Scrapper")
            timeout: Timeout in milliseconds (default 30000ms).
        """
        locators = [self.tool_blocks.filter(has_text=p) for p in tool_name_patterns]
        combined = locators[0]
        for loc in locators[1:]:
            combined = combined.or_(loc)
        expect(combined.first).to_be_visible(timeout=timeout)
        return self

    def _dismiss_release_notification_if_present(self):
        """Dismiss modal dialogs that may block chat interactions.

        Handles two known dialogs that intercept pointer events during send_message:
        1. 'New CodeMie Release' notification (button 'Got It, Thanks!')
        2. PrimeVue modal dialogs (.p-dialog-mask), e.g. the 'Guided Tour Available'
           dialog that appears and sits at z-index 50 blocking all viewport clicks.
        """
        btn = self.page.get_by_role("button", name="Got It, Thanks!")
        try:
            btn.wait_for(state="visible", timeout=2000)
            btn.click()
        except Exception:
            pass
        # Dismiss any remaining PrimeVue modal overlay (e.g. Guided Tour dialog).
        # The dialog appears unpredictably and blocks all pointer events when present.
        dialog_mask = self.page.locator(".p-dialog-mask")
        try:
            if dialog_mask.is_visible():
                # Try Escape first (works for most dismissible PrimeVue dialogs)
                self.page.keyboard.press("Escape")
                try:
                    dialog_mask.wait_for(state="hidden", timeout=2000)
                except Exception:
                    # Escape did not close it — try clicking the header close button
                    close_btn = self.page.locator(
                        ".p-dialog .p-dialog-header button"
                    ).first
                    if close_btn.is_visible():
                        close_btn.click()
                        dialog_mask.wait_for(state="hidden", timeout=2000)
        except Exception:
            pass

    @step
    def should_not_have_tool_output_blocks(self):
        """Assert ThoughtsBlock is DOM-absent (count=0).

        Used when hideToolOutputs=True — the component is conditionally not rendered,
        so to_have_count(0) is the correct assertion (not to_be_hidden).
        """
        expect(self.tool_blocks).to_have_count(0)
        return self

    @step
    def should_have_tool_output_blocks(self):
        """Assert ThoughtsBlock is visible in the chat history.

        Used when hideToolOutputs=False (default) — the tool execution block should
        be rendered and visible after the assistant uses a tool.
        """
        expect(self.tool_blocks.first).to_be_visible()
        return self

    @step
    def should_have_assistant_message_history_indicator_visible(self):
        """Verify that the assistant message history indicator is visible (appears after regeneration)."""
        expect(self.message_history_counter).to_be_visible()
        return self

    @step
    def should_have_assistant_message_history_indicator_count(
        self, expected_count: int
    ):
        """
        Verify that the assistant message history indicator shows the expected count.

        Args:
            expected_count: The expected total number of message versions
        """
        counter_text = self.get_message_history_counter_text()
        # Counter format is "X / Y" where Y is the total count
        assert_that(counter_text, equal_to(f"{expected_count} / {expected_count}"))
        return self

    @step
    def should_have_new_chat_created(self):
        """Verify that a new chat has been successfully created."""
        # Check that we can interact with chat elements
        self.should_have_chat_input_visible()
        self.should_have_send_button_visible()

        # Verify that messages are visible (at least user message)
        expect(self.user_message.first).to_be_visible()
        return self

    @step
    def should_have_configuration_panel_opened(self):
        # Verify that configuration panel is opened
        expect(self.chat_configuration_panel.panel).to_be_visible()
        return self

    @step
    def should_have_configuration_panel_closed(self):
        # Verify that configuration panel is closed
        expect(self.chat_configuration_panel.panel).to_be_hidden()
        return self

    @step
    def should_have_history_visible(self):
        """Verify that the chat messages container is visible."""
        expect(self.chat_history_container).to_be_visible(timeout=15000)
        return self

    @step
    def should_have_empty_chat_input(self):
        """Verify that the visible chat editor is empty.

        Uses the input wrapper scope rather than contenteditable="true" so the
        assertion passes even while generation is in progress (Quill sets
        contenteditable="false" during streaming).
        """
        chat_editor = self.page.locator(
            '[data-onboarding="chat-input"] .ql-editor:visible'
        )
        expect(chat_editor).to_have_text("")
        return self

    @step
    def should_have_chat_input_value(self, expected_value: str):
        """
        Verify that the chat input has a specific value.

        Args:
            expected_value: The expected input value
        """
        expect(self.chat_input).to_have_text(expected_value)
        return self

    @step
    def should_have_draft_cleared_immediately_after_send(self, timeout: int = 5000):
        """Verify the draft was cleared right after sending.

        The .ql-editor is temporarily unmounted while the assistant response is
        generating, so its absence during that window also counts as a cleared
        draft here -- only an editor still showing the draft text is a failure.
        Narrow to the immediately-after-send moment; general emptiness checks
        should keep using should_have_empty_chat_input.
        """
        self.page.wait_for_function(
            """() => {
                const el = document.querySelector('.ql-editor[contenteditable="true"]');
                return !el || el.textContent.trim() === '';
            }""",
            timeout=timeout,
        )
        return self

    @step
    def should_have_draft_preserved(self, expected_text: str):
        """Verify the prompt box still contains the unsent draft text after chat navigation.

        Args:
            expected_text: The draft text that should still be present in the prompt box.
        """
        expect(self.chat_input).to_have_text(expected_text)
        return self

    # ==================== UTILITY METHODS ====================

    @step
    def get_user_message_count(self) -> int:
        """Get the number of user messages."""
        return self.user_message.count()

    @step
    def get_assistant_message_count(self) -> int:
        """Get the number of assistant messages."""
        return self.assistant_message.count()

    @step
    def get_last_user_message_text(self) -> str:
        """Get the text of the last user message."""
        return self.user_message.last.inner_text()

    @step
    def get_last_assistant_message_text(self) -> str:
        """Get the text of the last assistant message."""
        return self.assistant_message.last.inner_text()

    @step
    def get_chat_input_value(self) -> str:
        """Get the current value of the chat input field."""
        return self.chat_input.input_value()

    @step
    def get_message_history_counter_text(self) -> str:
        """Get the message history counter text (e.g., '2 / 2')."""
        return self.message_history_counter.inner_text()

    @step
    def wait_for_assistant_response(self, timeout: int = 60000):
        """
        Wait for assistant response to complete.

        Args:
            timeout: Timeout in milliseconds
        """
        self.processed_in_field.last.wait_for(state="visible", timeout=timeout)
        return self

    @step
    def scroll_to_bottom_of_chat(self):
        """Scroll to the bottom of the chat messages."""
        self.chat_history_container.evaluate(
            "element => element.scrollTop = element.scrollHeight"
        )
        return self

    @step
    def scroll_to_top_of_chat(self):
        """Scroll to the top of the chat messages."""
        self.chat_history_container.evaluate("element => element.scrollTop = 0")
        return self

    # ==================== INTEGRATION VERIFICATION ====================

    @step
    def verify_all_essential_elements_visible(self):
        """Comprehensive verification of all essential chat page elements."""
        self.should_have_new_chat_button_visible()
        self.should_have_chat_input_visible()
        self.should_have_send_button_visible()
        self.should_have_add_attachment_button_visible()
        self.should_have_configuration_button_visible()
        return self

    @step
    def verify_all_action_buttons_visible(self):
        """Verify all action buttons in the toolbar are visible."""
        self.should_have_execution_info_button_visible()
        self.should_have_share_chat_button_visible()
        self.should_have_export_chat_button_visible()
        self.should_have_clear_chat_button_visible()
        self.should_have_configuration_button_visible()
        return self

    @step
    def verify_empty_chat_state(self):
        """Verify the empty chat state with invitation message."""
        self.should_have_start_conversation_invitation_visible()
        self.should_have_conversation_subtitle_visible()
        self.should_have_chat_input_visible()
        self.should_have_send_button_visible()
        return self

    @step
    def verify_all_chat_history_action_buttons_visible(self):
        """Verify all chat history action buttons are visible (copy, edit, delete, export)."""
        (
            self.should_have_user_message_copy_button_visible()
            .should_have_user_message_edit_button_visible()
            .should_have_user_message_regenerate_button_visible()
            .should_have_user_message_delete_button_visible()
            .should_have_assistant_message_copy_button_visible()
            .should_have_assistant_message_edit_button_visible()
            .should_have_assistant_message_share_button_visible()
        )
        return self

    # ==================== CHAT MESSAGE ACTION VERIFICATION METHODS ====================

    @step
    def verify_clipboard_content(self, expected_text: str):
        """
        Verify clipboard content matches expected text.

        Args:
            expected_text: The expected clipboard text
        """
        clipboard_text = self.page.evaluate("navigator.clipboard.readText()")
        clipboard_text = clipboard_text.replace("\r\n", "\n")
        expected_text = expected_text.replace("\r\n", "\n")
        assert_that(
            clipboard_text, equal_to(expected_text), "Clipboard content mismatch"
        )
        return self

    @step
    def should_have_edit_mode_active(self):
        """Verify that edit mode is active (input field visible in message area)."""
        # Edit mode shows the chat input in the message area
        edit_input = self.page.locator(".ql-editor").first
        expect(edit_input).to_be_visible()
        return self

    @step
    def should_have_message_deleted(self, original_count: int):
        """
        Verify that a message was deleted by checking message count decreased.

        Args:
            original_count: The original message count before deletion
        """
        expect(self.user_message).to_have_count(original_count - 1, timeout=10000)
        return self

    @step
    def should_have_export_popup_menu_visible(self):
        """
        Verify that export/share popup menu is visible with all menu items.

        Checks for the presence of:
        - Export to DOCX
        - Export to PDF
        - Export to PPTX
        """
        # Verify the export menu is visible
        export_menu = self.page.get_by_role("menu", name="Options")
        expect(export_menu).to_be_visible(timeout=5000)

        # Verify all three export menu items are visible
        expect(self.page.get_by_role("menuitem", name="Export to DOCX")).to_be_visible()
        expect(self.page.get_by_role("menuitem", name="Export to PDF")).to_be_visible()
        expect(self.page.get_by_role("menuitem", name="Export to PPTX")).to_be_visible()
        return self

    @step
    def should_have_like_button_active(self):
        """Verify that the like button is in active state (after being clicked)."""
        expect(self.assistant_message_remove_like_button).to_be_visible()
        return self

    @step
    def should_have_like_button_inactive(self):
        """Verify that the like button is in inactive state (default)."""
        expect(self.assistant_message_like_button).to_be_visible()
        return self

    @step
    def should_have_dislike_button_active(self):
        """Verify that the dislike button is in active state (shows remove button)."""
        expect(self.assistant_message_remove_dislike_button).to_be_visible()
        return self

    @step
    def should_have_dislike_button_inactive(self):
        """Verify that the dislike button is in inactive state (default)."""
        expect(self.assistant_message_dislike_button).to_be_visible()
        return self

    @step
    def should_not_see_nested_subagent_spawn(self):
        """Verify that no second-level (nested) subagent spawn indicator is visible.

        Under the recursion guard, the spawned subagent cannot call spawn_subagent
        again.  This method checks that tool blocks do not contain a nested
        'spawn_subagent' invocation (which would indicate a recursion guard failure).
        """
        nested_spawn = self.chat_history_container.locator(
            'button:has-text("spawn_subagent"), button:has-text("Spawn Subagent")'
        )
        expect(nested_spawn).to_have_count(0, timeout=10_000)
        return self

    @step
    def should_have_builtin_subagent_triggered(self, timeout: int = 120_000):
        """Verify that the Built-in General Purpose Subagent was invoked and completed.

        The subagent's tool block appears in the chat history with the author name
        'Builtin  General Purpose Subagent' (double space) and a Success status.
        """
        self.should_have_tool_used("Builtin  General Purpose Subagent", timeout=timeout)
        return self

    @step
    def should_see_block_message(self, pattern: str):
        """Verify that a block/error message matching the given pattern is visible.

        Used to confirm that a recursion-guard block or skill-permission denial
        message is surfaced to the user with identifiable context rather than a
        generic error.

        Args:
            pattern: Text pattern (substring) to match anywhere in the chat history.
        """
        block_message = self.chat_history_container.locator(f'*:has-text("{pattern}")')
        expect(block_message.first).to_be_visible(timeout=10_000)
        return self

    @step
    def should_have_delete_feedback_dialog_visible(self):
        """Verify that the Delete Feedback dialog is visible."""
        expect(self.delete_feedback_dialog).to_be_visible(timeout=5000)
        return self

    @step
    def should_have_submit_feedback_dialog_visible(self):
        """Verify that the Submit Feedback dialog is visible."""
        expect(self.submit_feedback_dialog).to_be_visible(timeout=5000)
        return self

    # ==================== PREMIUM MODEL ELEMENTS ====================

    PREMIUM_TOOLTIP_TEXT = "Premium model — higher usage rates apply"

    @property
    def chat_input_wrapper(self) -> Locator:
        """Chat input wrapper — carries amber ring class when a premium model is active."""
        return self.page.locator('[data-onboarding="chat-input"]')

    @property
    def premium_notice(self) -> Locator:
        """The 'Premium model active' notice shown when a premium model is selected."""
        return self.page.get_by_text("Premium model active")

    @property
    def premium_notice_dismiss_button(self) -> Locator:
        """Dismiss button for the premium model notice."""
        return self.page.get_by_role("button", name="Dismiss premium model tip")

    @property
    def premium_notice_details_link(self) -> Locator:
        """'View models and rates' link in the premium model notice."""
        return self.page.get_by_role("link", name="View models and rates")

    @property
    def premium_tooltip_element(self) -> Locator:
        """Any element on the page carrying the premium tooltip content attribute."""
        return self.page.locator(
            f'[data-tooltip-content="{self.PREMIUM_TOOLTIP_TEXT}"]'
        )

    def premium_badge_in_picker(self, model_name: str) -> Locator:
        """Premium meta label inside the model picker option for a given model name.

        The premium indicator is rendered as
        ``<span data-testid="llm-option-meta">...<span class="text-aborted-primary">Premium</span>...</span>``
        — there is no ``role="status"`` element.
        """
        return self.page.get_by_role("option", name=f"{model_name} Premium").locator(
            '[data-testid="llm-option-meta"]'
        )

    def premium_tooltip_wrapper_in_picker(self, model_name: str) -> Locator:
        """Row span that carries ``data-tooltip-content`` for a premium model picker option.

        The tooltip is on ``<span data-testid="llm-option-row" data-tooltip-content="…">``.
        """
        return self.page.get_by_role("option", name=f"{model_name} Premium").locator(
            '[data-testid="llm-option-row"]'
        )

    def active_model_selector_button(self, model_name: str) -> Locator:
        """Model selector button showing a specific non-premium model label."""
        return self.page.get_by_role("button", name=model_name, exact=True)

    def active_premium_model_selector_button(self, model_name: str) -> Locator:
        """Model selector button when a premium model is active.

        The button's accessible name is just the model name — premium status is
        conveyed by the amber ring highlight, not a ' Premium' text suffix on the
        button itself (that suffix only appears on picker options)."""
        return self.page.get_by_role("button", name=model_name, exact=True)

    # ==================== PREMIUM MODEL INTERACTION METHODS ====================

    @step
    def select_premium_model(self, model_name: str):
        """
        Select a premium model from the model picker starting from the Default state.

        Args:
            model_name: Display name of the premium model (without the ' Premium' suffix).
        """
        self.model_selector_button.click()
        search_input = self.page.get_by_role("combobox", name="Search LLM models")
        search_input.wait_for(state="visible", timeout=5000)
        search_input.fill(model_name)
        option = self.page.get_by_role("option", name=f"{model_name} Premium")
        option.wait_for(state="visible", timeout=5000)
        option.click()
        return self

    @step
    def open_model_picker_for_model(self, model_name: str, is_premium: bool = False):
        """
        Open the model picker when a specific model is currently selected.

        Args:
            model_name: Display name of the currently selected model.
            is_premium: True if the currently selected model is premium.
        """
        if is_premium:
            btn = self.active_premium_model_selector_button(model_name)
        else:
            btn = self.active_model_selector_button(model_name)
        btn.click()
        self.page.get_by_role("combobox", name="Search LLM models").wait_for(
            state="visible", timeout=5000
        )
        return self

    @step
    def select_model_in_open_picker(self, model_name: str, is_premium: bool = False):
        """
        Select a model from an already-open model picker.

        Args:
            model_name: Display name of the model to select.
            is_premium: True if the target model is premium.
        """
        search_input = self.page.get_by_role("combobox", name="Search LLM models")
        search_input.fill(model_name)
        if is_premium:
            option = self.page.get_by_role("option", name=f"{model_name} Premium")
        else:
            option = self.page.get_by_role("option", name=model_name, exact=True).first
        option.wait_for(state="visible", timeout=5000)
        option.click()
        return self

    @step
    def dismiss_premium_notice(self):
        """Click the dismiss button on the premium model notice."""
        self.premium_notice_dismiss_button.click()
        return self

    # ==================== PREMIUM MODEL VERIFICATION METHODS ====================

    @step
    def should_show_premium_badge_in_picker(self, model_name: str):
        """Assert premium badge is visible in the model picker option for a given model."""
        expect(self.premium_badge_in_picker(model_name)).to_be_visible()
        return self

    @step
    def should_not_show_premium_badge_in_picker(self, model_name: str):
        """Assert no premium badge is present in the model picker option for a given model."""
        option = self.page.get_by_role("option", name=model_name)
        expect(option.locator('[data-testid="llm-option-meta"]')).to_have_count(0)
        return self

    @step
    def should_show_correct_premium_tooltip_in_picker(self, model_name: str):
        """Assert the premium badge tooltip text is correct for a model in the picker."""
        actual = self.premium_tooltip_wrapper_in_picker(model_name).get_attribute(
            "data-tooltip-content"
        )
        assert_that(
            actual, equal_to(self.PREMIUM_TOOLTIP_TEXT), "Premium tooltip text mismatch"
        )
        return self

    @step
    def should_show_premium_notice(self):
        """Assert the premium model active notice is visible."""
        expect(self.premium_notice).to_be_visible()
        return self

    @step
    def should_not_show_premium_notice(self):
        """Assert the premium model active notice is not visible."""
        expect(self.premium_notice).to_be_hidden()
        return self

    @step
    def should_show_premium_notice_details_link(self):
        """Assert the 'View models and rates' link is visible in the premium notice."""
        expect(self.premium_notice_details_link).to_be_visible()
        return self

    @step
    def should_show_premium_notice_dismiss_button(self):
        """Assert the dismiss button is visible in the premium notice."""
        expect(self.premium_notice_dismiss_button).to_be_visible()
        return self

    @step
    def should_show_premium_highlight(self):
        """Assert chat input wrapper carries the amber ring indicating premium model is active."""
        expect(self.chat_input_wrapper).to_have_class(
            re.compile(r"ring-aborted-primary")
        )
        return self

    @step
    def should_not_show_premium_highlight(self):
        """Assert chat input wrapper does NOT carry the amber ring."""
        expect(self.chat_input_wrapper).not_to_have_class(
            re.compile(r"ring-aborted-primary")
        )
        return self

    @step
    def should_show_premium_tooltip_on_active_selector(self):
        """Assert the premium tooltip marker is present on the active model selector area."""
        expect(self.premium_tooltip_element.first).to_be_attached()
        return self

    @step
    def should_not_show_premium_indicators(self):
        """Assert all premium UI indicators (highlight and notice) are absent."""
        self.should_not_show_premium_highlight()
        self.should_not_show_premium_notice()
        return self

    # ==================== TOOL-CALL CONFIRMATION ELEMENTS ====================
    # Rendered by ChatAiMessage.tsx when thought.interrupted===true
    #

    _TOOL_CALL_PENDING_MESSAGE = "Interrupted"

    @property
    def interrupted_thought_text(self) -> Locator:
        """The 'Interrupted' status badge rendered when thought.interrupted===true.

        The badge is <div role='status' aria-label='Interrupted'> nested inside
        the collapsed Wikipedia spoiler <button>.  Playwright's get_by_role()
        cannot reach it because the browser accessibility tree flattens button
        children.  A CSS attribute selector searches the raw DOM and always finds
        it.  CSS text-transform:uppercase makes it visually display as 'INTERRUPTED'.
        """
        return self.chat_history_container.locator(
            '[role="status"][aria-label="Interrupted"]'
        )

    @property
    def allow_tool_call_button(self) -> Locator:
        """The Allow button rendered inline below the interrupted thought.

        Uses ButtonType.PRIMARY with CheckSvg icon and label 'Allow'.
        Only visible in regular chats (not workflow / shared-page contexts).
        """
        return self.chat_history_container.get_by_role("button", name="Allow")

    @property
    def deny_tool_call_button(self) -> Locator:
        """The Deny button rendered inline below the interrupted thought.

        Uses ButtonType.DELETE with CrossSvg icon and label 'Deny'.
        Only visible in regular chats (not workflow / shared-page contexts).
        """
        return self.chat_history_container.get_by_role("button", name="Deny")

    @property
    def tool_call_policy_picker(self) -> Locator:
        """Policy picker dropdown rendered by ChatPromptToolCallPolicy.tsx.

        The element has no data-testid; it is a PrimeVue Dropdown
        (data-pc-name="dropdown") that immediately follows the 'Tool calls:'
        label in the prompt toolbar.  Located via the sibling XPath so the
        selector survives class-name refactors.
        """
        return self.page.get_by_text("Tool calls:", exact=True).locator(
            "xpath=following-sibling::div//div[@data-pc-name='dropdown']"
        )

    @step
    def wait_for_tool_call_confirmation(self, timeout: int = 60000):
        """Wait until the tool-call confirmation dialog appears.

        The Interrupted badge (role=status) is the primary anchor — it is
        visible inside the collapsed tool-call spoiler without needing a click.
        Allow/Deny follow with a short timeout because they render at the same
        time as the badge.

        Args:
            timeout: Maximum wait time in milliseconds (default 60 s).
        """
        expect(self.interrupted_thought_text).to_be_visible(timeout=timeout)
        expect(self.allow_tool_call_button).to_be_visible(timeout=5000)
        expect(self.deny_tool_call_button).to_be_visible(timeout=5000)
        return self

    @step
    def click_allow_tool_call(self):
        """Click the Allow button on the pending tool-call confirmation."""
        self.allow_tool_call_button.click()
        return self

    @step
    def click_deny_tool_call(self):
        """Click the Deny button on the pending tool-call confirmation."""
        self.deny_tool_call_button.click()
        return self

    @step
    def should_have_tool_call_confirmation_visible(self):
        """Assert the interrupted thought and Allow/Deny buttons are all visible.

        Button-type contract (AC-2; ChatAiMessage.tsx:~252–263):
          Allow → ButtonType.PRIMARY → emits bg-button-primary-bg
                  (Button.tsx line 75: PRIMARY branch)
          Deny  → ButtonType.DELETE  → emits border-failed-delete-default
                  (Button.tsx line 87: DELETE branch)
        Class names verified against Button.tsx at time of generation.
        """
        expect(self.interrupted_thought_text).to_be_visible(timeout=60000)
        expect(self.allow_tool_call_button).to_be_visible()
        expect(self.deny_tool_call_button).to_be_visible()
        # Button-type contract assertions (AC-2)
        expect(self.allow_tool_call_button).to_have_class(
            re.compile(r"bg-button-primary-bg")
        )
        expect(self.deny_tool_call_button).to_have_class(
            re.compile(r"border-failed-delete-default")
        )
        return self

    @step
    def should_not_have_tool_call_confirmation_visible(self, timeout: int = 5000):
        """Assert no tool-call confirmation controls are present in the chat."""
        expect(self.interrupted_thought_text).to_be_hidden(timeout=timeout)
        expect(self.allow_tool_call_button).to_be_hidden(timeout=timeout)
        expect(self.deny_tool_call_button).to_be_hidden(timeout=timeout)
        return self

    @step
    def should_have_interrupted_thought_visible(self, timeout: int = 10000):
        """Assert that the interrupted-thought element is visible.

        Call this as a precondition *before* should_not_have_allow_deny_buttons()
        so that a vacuous pass (empty/wrong page) is ruled out.
        """
        expect(self.interrupted_thought_text).to_be_visible(timeout=timeout)
        return self

    def pending_tool_call_button(self, tool_name: str) -> Locator:
        """Button named after the tool awaiting approval, next to Allow/Deny.

        For a pending approval the message renders a `button "<tool name>"` followed
        directly by the `Deny` and `Allow` buttons (confirmed in the ARIA snapshot of
        a live run). The tool button is scoped to the innermost container that also
        holds the Deny button, so a button of another message cannot match. Inner
        locators are page-rooted because `filter(has=...)` queries them relative to
        each candidate container.
        """
        tool_pattern = re.compile(re.escape(tool_name), re.IGNORECASE)
        pending_group = (
            self.chat_history_container.locator("div")
            .filter(has=self.page.get_by_role("button", name="Deny"))
            .filter(has=self.page.get_by_role("button", name=tool_pattern))
            .last
        )
        return pending_group.get_by_role("button", name=tool_pattern)

    @step
    def should_have_pending_tool_call_for(self, tool_name: str, timeout: int = 10000):
        """Assert the tool awaiting approval is shown by name next to Allow/Deny.

        The tool name stays visible for a pending approval even when the assistant
        hides tool outputs (the interrupted thought is kept so Allow/Deny can work).
        """
        expect(self.pending_tool_call_button(tool_name)).to_be_visible(timeout=timeout)
        return self

    @step
    def should_not_have_allow_deny_buttons(self, timeout: int = 5000):
        """Assert the Allow and Deny buttons are absent (count == 0).

        Used when testing workflow / shared-page contexts where the buttons
        must be suppressed even when the interrupted thought is visible.
        """
        expect(self.allow_tool_call_button).to_have_count(0, timeout=timeout)
        expect(self.deny_tool_call_button).to_have_count(0, timeout=timeout)
        return self

    @step
    def get_tool_call_policy_picker_value(self) -> str:
        """Return the text content of the policy picker (e.g. 'Manual', 'Auto')."""
        return (
            self.tool_call_policy_picker.locator(".p-dropdown-label")
            .inner_text()
            .strip()
        )

    @step
    def should_have_tool_call_policy(self, expected_value: str):
        """Assert the policy picker shows the expected policy label.

        Args:
            expected_value: Expected label text, e.g. 'Manual' or 'Auto'.
        """
        actual = self.get_tool_call_policy_picker_value()
        assert actual == expected_value, (
            f"Expected tool-call policy picker to show '{expected_value}', "
            f"got '{actual}'"
        )
        return self

    # ==================== CHAT INTRO DESCRIPTION (assistant & workflow) ====================

    @property
    def chat_intro_description(self) -> Locator:
        """Description paragraph in the chat intro area.

        Rendered by ChatPromptStarters.tsx for both assistant and workflow chats
        when a description is configured.
        """
        return self.page.locator('p[data-tooltip-id="react-tooltip"].line-clamp-3')

    @property
    def empty_description_placeholder(self) -> Locator:
        """A description-styled element with empty tooltip content — indicates broken rendering."""
        return self.page.locator(
            'p[data-tooltip-id="react-tooltip"][data-tooltip-content=""]'
        )

    @step
    def should_show_chat_description(self, description_text: str):
        """Assert the description text is visible in the chat intro area."""
        expect(
            self.chat_intro_description.filter(has_text=description_text)
        ).to_be_visible(timeout=10000)
        return self

    @step
    def should_not_show_empty_description_placeholder(self):
        """Assert no empty/broken description placeholder element is present."""
        expect(self.empty_description_placeholder).to_have_count(0)
        return self

    # ==================== WORKFLOW PROGRESS RESTORE AFTER RELOAD ====================
    # ChatAiMessage.tsx renders a per-thought StatusBadge as
    # <div role="status" aria-label="{label}">{label}</div> (ThoughtHeader.tsx via
    # StatusStatus) — the same pattern already used by interrupted_thought_text above.
    # A thought whose in_progress is true carries the "In Progress" label.

    @property
    def in_progress_thought_status(self) -> Locator:
        """Status badge rendered for a thought whose status is 'In Progress'.

        Present when a workflow step is currently running — including right after a
        page reload, once the GET-conversation hydrate restores the in-progress state.
        """
        return self.chat_history_container.locator(
            '[role="status"][aria-label="In Progress"]'
        )

    @property
    def thinking_loader(self) -> Locator:
        """'Thinking...' loader shown in the assistant message header while inProgress is true.

        Rendered by ThinkingLoader.tsx (`className="thinking-loader ..."`).
        """
        return self.chat_history_container.locator(".thinking-loader")

    @property
    def workflow_restore_failed_message(self) -> Locator:
        """Markdown content shown when workflow progress could not be restored (AC-3).

        Rendered inside the same `.markdown.text-text-primary` node used by
        `assistant_message` when ChatAiMessage's `showRestoreFailed` is true.
        """
        return self.assistant_message.filter(
            has_text="Workflow progress could not be restored."
        )

    @step
    def should_have_in_progress_thought_visible(self, timeout: int = 15000):
        """Verify a thought card shows the 'In Progress' status badge (AC-2)."""
        expect(self.in_progress_thought_status.first).to_be_visible(timeout=timeout)
        return self

    @step
    def should_have_non_blank_workflow_progress(self, timeout: int = 15000):
        """Verify the answer node shows workflow progress rather than being empty (AC-4).

        Satisfied by any of: an in-progress thought status badge, the Thinking loader,
        or a non-empty assistant response — matching AC-4's "answer node is not empty".
        """
        non_blank_answer = self.in_progress_thought_status.or_(
            self.thinking_loader
        ).or_(self.assistant_message.filter(has_text=re.compile(r"\S")))
        expect(non_blank_answer.first).to_be_visible(timeout=timeout)
        return self

    @step
    def should_have_workflow_restore_failed_message_visible(self, timeout: int = 15000):
        """Verify the AC-3 fallback copy is rendered instead of a blank answer node."""
        expect(self.workflow_restore_failed_message.first).to_be_visible(
            timeout=timeout
        )
        return self

    @step
    def intercept_unrestorable_conversation(
        self, conversation_id: str, workflow_id: str
    ):
        """Intercept GET v1/conversations/{id} with a payload whose workflow turn
        cannot be restored (AC-3): executionStatus "Not Started", no thoughts, no output.

        The exact combination of fields required to trigger this fallback (a workflow
        turn stuck in a non-running, non-terminal execution status with empty thoughts
        and output) is not reliably reproducible through timing alone, so the response
        is replaced with this real, schema-valid payload shape (verbatim field
        names/casing taken from
        src/store/__tests__/chats.refreshWorkflowExecutionIds.test.ts) — the actual
        shipped frontend code (ChatAiMessage/chatHelpers) still does all the rendering.
        """

        def handle_get_conversation(route):
            route.fulfill(
                status=200,
                json={
                    "id": conversation_id,
                    "conversation_name": "restore-failed repro",
                    "assistant_ids": [],
                    "initial_assistant_id": workflow_id,
                    "assistant_data": [],
                    "is_workflow": True,
                    "history": [
                        {
                            "historyIndex": 0,
                            "message": "hi",
                            "date": "2026-09-08T00:00:00Z",
                            "executionId": None,
                        },
                        {
                            "historyIndex": 0,
                            "message": "",
                            "date": "2026-09-08T00:00:01Z",
                            "executionId": "unrestorable-exec-1",
                            "workflowExecutionRef": True,
                            "executionStatus": "Not Started",
                            "thoughts": [],
                        },
                    ],
                },
            )

        self.page.route(
            f"**/v1/conversations/{conversation_id}", handle_get_conversation
        )
        return self
