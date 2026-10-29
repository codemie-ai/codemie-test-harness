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

import logging

from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)


class AIAssistantGeneratorPage:
    """
    Page Object Model for the Generate Assistant with AI form.

    This form allows users to create AI assistants by describing their requirements
    and configuring various options including tool integrations.
    """

    def __init__(self, page: Page):
        """
        Initialize the AI Assistant Generator page object.

        Args:
            page: Playwright page instance
        """
        self.page = page
        self._setup_locators()

    def _setup_locators(self) -> None:
        """Define all locators for the AI Assistant Generator form.

        Updated for redesigned UI based on live DOM inspection:
        - Modal is a native dialog[role="dialog"] element
        - Title is h4 inside the dialog header
        - Close button identified by aria-label="Close" or role="button" name="Close"
        - "Include tools" is now a switch role (not checkbox)
        - "Do not show this popup" is a plain checkbox (role="checkbox")
        - Textarea is identified by role="textbox" with aria-label
        """

        # Modal container - role="dialog" with the title text
        self.modal_container = self.page.get_by_role(
            "dialog", name="Generate Assistant with AI"
        )

        # Header elements
        self.modal_header = self.modal_container.locator(".p-dialog-header")
        # Title is h4 inside the dialog header
        self.modal_title = self.modal_container.get_by_role(
            "heading", name="Generate Assistant with AI", level=4
        )
        # Close button - aria-label="Close"
        self.close_button = self.modal_container.get_by_role("button", name="Close")

        # Modal body
        self.modal_body = self.modal_container.locator(".p-dialog-content")

        # Description elements - first and second <p> in the modal body
        self.description_text = self.modal_body.locator("p").first
        self.assistant_description_label = self.modal_body.locator("p").nth(1)

        # Main textarea - identified by aria-label in the redesigned UI
        self.assistant_description_textarea = self.modal_container.get_by_role(
            "textbox", name="What should your assistant do?"
        )

        # "Do not show this popup" checkbox - role="checkbox"
        self.do_not_show_checkbox = self.modal_container.get_by_role(
            "checkbox", name="Do not show this popup"
        )
        self.do_not_show_label = self.modal_body.get_by_text("Do not show this popup")

        # Include tools toggle - now a switch role in the redesigned UI
        # The switch has role="switch" (aria-label="Include tools" or identified by label text)
        self.include_tools_toggle = self.modal_container.get_by_role(
            "switch", name="Include tools"
        )
        self.include_tools_label = self.modal_body.get_by_text("Include tools")

        # Action buttons
        # Note: button text "Create Manualy" is a known typo in the UI (missing 'l')
        self.create_manually_button = self.modal_container.get_by_role(
            "button", name="Create Manualy"
        )
        self.generate_with_ai_button = self.modal_container.get_by_role(
            "button", name="Generate with AI"
        )

        # Note text about tool integrations
        self.integration_note = self.modal_body.locator(
            'div:has-text("Note: Please select tool integrations")'
        ).first
        self.info_icon = self.integration_note.locator("svg").first

    # Navigation and state methods

    def wait_for_modal_to_load(self, timeout: float = 10000) -> None:
        """
        Wait for the AI Assistant Generator modal to be fully loaded and visible.

        Args:
            timeout: Maximum time to wait in milliseconds
        """
        logger.info("Waiting for AI Assistant Generator modal to load")
        expect(self.modal_container).to_be_visible(timeout=timeout)
        expect(self.modal_title).to_be_visible()
        expect(self.assistant_description_textarea).to_be_visible()
        logger.info("AI Assistant Generator modal loaded successfully")

    def is_modal_visible(self) -> bool:
        """
        Check if the AI Assistant Generator modal is currently visible.

        Returns:
            True if modal is visible, False otherwise
        """
        return self.modal_container.is_visible()

    def close_modal(self) -> None:
        """Close the AI Assistant Generator modal using the close button."""
        logger.info("Closing AI Assistant Generator modal")
        self.close_button.click()
        expect(self.modal_container).not_to_be_visible()
        logger.info("AI Assistant Generator modal closed successfully")

    # Form interaction methods

    def enter_assistant_description(self, description: str) -> None:
        """
        Enter description text in the assistant description textarea.

        Args:
            description: The assistant description text to enter
        """
        logger.info(f"Entering assistant description: {description[:50]}...")
        self.assistant_description_textarea.click()
        self.assistant_description_textarea.clear()
        self.assistant_description_textarea.fill(description)

        # Verify the text was entered correctly
        expect(self.assistant_description_textarea).to_have_value(description)
        logger.info("Assistant description entered successfully")

    def get_assistant_description(self) -> str:
        """
        Get the current value of the assistant description textarea.

        Returns:
            Current text value in the description textarea
        """
        return self.assistant_description_textarea.input_value()

    def toggle_do_not_show_popup(self, enabled: bool = True) -> None:
        """
        Toggle the "Do not show this popup" checkbox.

        Args:
            enabled: True to check the checkbox, False to uncheck
        """
        logger.info(f"Setting 'Do not show popup' to: {enabled}")

        if enabled and not self.do_not_show_checkbox.is_checked():
            self.do_not_show_checkbox.click()
        elif not enabled and self.do_not_show_checkbox.is_checked():
            self.do_not_show_checkbox.click()

        # Verify the state
        if enabled:
            expect(self.do_not_show_checkbox).to_be_checked()
        else:
            expect(self.do_not_show_checkbox).not_to_be_checked()

        logger.info(f"'Do not show popup' checkbox set to: {enabled}")

    def is_do_not_show_popup_checked(self) -> bool:
        """
        Check if the "Do not show this popup" checkbox is checked.

        Returns:
            True if checkbox is checked, False otherwise
        """
        return self.do_not_show_checkbox.is_checked()

    def toggle_include_tools(self, enabled: bool = True) -> None:
        """
        Toggle the "Include Tools" switch.
        Note: In the redesigned UI this is a switch role element (not a plain checkbox).

        Args:
            enabled: True to enable tools inclusion, False to disable
        """
        logger.info(f"Setting 'Include Tools' to: {enabled}")

        # Use is_checked() which works for both checkbox and switch roles
        if enabled and not self.include_tools_toggle.is_checked():
            self.include_tools_toggle.click()
        elif not enabled and self.include_tools_toggle.is_checked():
            self.include_tools_toggle.click()

        # Verify the state
        if enabled:
            expect(self.include_tools_toggle).to_be_checked()
        else:
            expect(self.include_tools_toggle).not_to_be_checked()

        logger.info(f"'Include Tools' toggle set to: {enabled}")

    def is_include_tools_enabled(self) -> bool:
        """
        Check if the "Include Tools" toggle is enabled.

        Returns:
            True if toggle is enabled, False otherwise
        """
        return self.include_tools_toggle.is_checked()

    # Action methods

    def click_create_manually(self) -> None:
        """Click the 'Create Manually' button."""
        logger.info("Clicking 'Create Manually' button")
        expect(self.create_manually_button).to_be_enabled(timeout=15000)
        self.create_manually_button.click()
        logger.info("'Create Manually' button clicked")

    def click_generate_with_ai(self) -> None:
        """Click the 'Generate with AI' button."""
        logger.info("Clicking 'Generate with AI' button")
        expect(self.generate_with_ai_button).to_be_enabled()
        self.generate_with_ai_button.click()
        logger.info("'Generate with AI' button clicked")

    # Validation methods

    def is_generate_button_enabled(self) -> bool:
        """
        Check if the 'Generate with AI' button is enabled.

        Returns:
            True if button is enabled, False otherwise
        """
        return self.generate_with_ai_button.is_enabled()

    def is_create_manually_button_enabled(self) -> bool:
        """
        Check if the 'Create Manually' button is enabled.

        Returns:
            True if button is enabled, False otherwise
        """
        return self.create_manually_button.is_enabled()

    def validate_form_elements_visible(self) -> None:
        """Validate that all expected form elements are visible and accessible."""
        logger.info("Validating AI Assistant Generator form elements visibility")

        # Check modal structure
        expect(self.modal_container).to_be_visible()
        expect(self.modal_title).to_be_visible()
        expect(self.close_button).to_be_visible()

        # Check form elements
        expect(self.assistant_description_label).to_be_visible()
        expect(self.assistant_description_textarea).to_be_visible()
        expect(self.do_not_show_label).to_be_visible()
        expect(self.do_not_show_checkbox).to_be_visible()
        expect(self.include_tools_label).to_be_visible()
        expect(self.include_tools_toggle).to_be_visible()

        # Check action buttons
        expect(self.create_manually_button).to_be_visible()
        expect(self.generate_with_ai_button).to_be_visible()

        # Check note text
        expect(self.integration_note).to_be_visible()

        logger.info("All form elements are visible and accessible")

    def validate_textarea_placeholder(self) -> None:
        """Validate that the textarea has the expected placeholder text."""
        placeholder_text = self.assistant_description_textarea.get_attribute(
            "placeholder"
        )
        expected_text = "For example: I need a project assistant that helps track deadlines, work with Jira and help with business requirements..."

        assert expected_text in placeholder_text, (
            f"Placeholder text mismatch. Expected: {expected_text}, Got: {placeholder_text}"
        )
        logger.info("Textarea placeholder validation passed")

    def verify_modal_title(self) -> None:
        """Verify the modal has the correct title."""
        expect(self.modal_title).to_have_text("Generate Assistant with AI")
        logger.info("Modal title verification passed")

    def verify_description_text(self) -> None:
        """Verify the main description text is present."""
        expect(self.description_text).to_contain_text("Describe your ideal assistant")
        logger.info("Description text verification passed")

    def verify_prompt_label(self) -> None:
        """Verify the prompt question is displayed."""
        expect(self.assistant_description_label).to_have_text(
            "What should your assistant do?"
        )
        logger.info("Prompt label verification passed")

    def verify_note_text(self) -> None:
        """Verify the note about tool integrations."""
        expect(self.integration_note).to_contain_text(
            "Note: Please select tool integrations after generation"
        )
        logger.info("Note text verification passed")

    # Composite action methods

    def fill_and_generate_assistant(
        self,
        description: str,
        include_tools: bool = True,
        do_not_show_again: bool = False,
    ) -> None:
        """
        Complete workflow to fill the form and generate an AI assistant.

        Args:
            description: Assistant description text
            include_tools: Whether to include tools in the assistant
            do_not_show_again: Whether to check "do not show popup" option
        """
        logger.info("Starting complete assistant generation workflow")

        # Wait for modal to be ready
        self.wait_for_modal_to_load()

        # Fill form fields
        self.enter_assistant_description(description)
        self.toggle_include_tools(include_tools)
        self.toggle_do_not_show_popup(do_not_show_again)

        # Generate the assistant
        self.click_generate_with_ai()

        logger.info("Assistant generation workflow completed")

    def fill_and_create_manually(
        self,
        description: str,
        include_tools: bool = True,
        do_not_show_again: bool = False,
    ) -> None:
        """
        Complete workflow to fill the form and create assistant manually.

        Args:
            description: Assistant description text
            include_tools: Whether to include tools in the assistant
            do_not_show_again: Whether to check "do not show popup" option
        """
        logger.info("Starting manual assistant creation workflow")

        # Wait for modal to be ready
        self.wait_for_modal_to_load()

        # Fill form fields
        self.enter_assistant_description(description)
        self.toggle_include_tools(include_tools)
        self.toggle_do_not_show_popup(do_not_show_again)

        # Create manually
        self.click_create_manually()

        logger.info("Manual assistant creation workflow completed")
