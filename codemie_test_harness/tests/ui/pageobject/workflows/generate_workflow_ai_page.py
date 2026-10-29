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

"""Page object for the "Generate Workflow with AI" popup on the Create Workflow page."""

from playwright.sync_api import Locator, Page, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class GenerateWorkflowAIPage(BasePage):
    """Page object for the "Generate Workflow with AI" dialog.

    This dialog auto-opens on the Create Workflow page (``/workflows/new``)
    unless previously dismissed via "Do not show again" (persisted per-user in
    localStorage key ``<userId>_codemie-new-workflow-ai-popup``). It mirrors the
    existing "Generate Assistant with AI" dialog pattern
    (``AIAssistantGeneratorPage``), reusing the same underlying Popup component.
    """

    def __init__(self, page: Page):
        super().__init__(page)

    # ==============================================
    # PROPERTIES - UI ELEMENTS
    # ==============================================

    @property
    def modal(self) -> Locator:
        """The "Generate Workflow with AI" dialog."""
        return self.page.get_by_role("dialog", name="Generate Workflow with AI")

    @property
    def description_textarea(self) -> Locator:
        """Main "What should your workflow do?" textarea."""
        return self.modal.get_by_role("textbox", name="What should your workflow do?")

    @property
    def do_not_show_checkbox(self) -> Locator:
        """ "Do not show again" checkbox."""
        return self.modal.get_by_role("checkbox", name="Do not show again")

    @property
    def cancel_button(self) -> Locator:
        """ "Cancel" button."""
        return self.modal.get_by_role("button", name="Cancel")

    @property
    def generate_button(self) -> Locator:
        """ "Generate with AI" button (disabled until the textarea has text)."""
        return self.modal.get_by_role("button", name="Generate with AI")

    # ==============================================
    # METHODS - ACTIONS & INTERACTIONS
    # ==============================================

    @step
    def wait_for_modal_to_load(self, timeout: float = 10000):
        """Wait for the dialog to be visible with its textarea ready for input."""
        expect(self.modal).to_be_visible(timeout=timeout)
        expect(self.description_textarea).to_be_visible()
        return self

    @step
    def enter_description(self, description: str):
        """Enter the workflow description text in the textarea."""
        self.description_textarea.click()
        self.description_textarea.fill(description)
        expect(self.description_textarea).to_have_value(description)
        return self

    @step
    def toggle_do_not_show_again(self, enabled: bool = True):
        """Toggle the "Do not show again" checkbox."""
        if enabled != self.do_not_show_checkbox.is_checked():
            self.do_not_show_checkbox.click()
        return self

    @step
    def click_cancel(self):
        """Click the "Cancel" button, closing the dialog without generating."""
        self.cancel_button.click()
        expect(self.modal).not_to_be_visible()
        return self

    @step
    def click_generate_with_ai(self):
        """Click "Generate with AI" to submit the description for generation."""
        expect(self.generate_button).to_be_enabled()
        self.generate_button.click()
        return self

    @step
    def generate_workflow(self, description: str, timeout: float = 120000):
        """Fill the description and generate, waiting for the dialog to close.

        Generation runs a multi-step LLM chain server-side and can take up to
        ~20s; the dialog closes automatically once generation succeeds and the
        result has been fed into the visual editor.
        """
        self.wait_for_modal_to_load()
        self.enter_description(description)
        self.click_generate_with_ai()
        expect(self.modal).not_to_be_visible(timeout=timeout)
        return self

    # ==============================================
    # METHODS - VERIFICATION & ASSERTIONS
    # ==============================================

    @step
    def should_be_visible(self):
        """Verify the dialog and its form elements are visible."""
        expect(self.modal).to_be_visible()
        expect(self.description_textarea).to_be_visible()
        expect(self.do_not_show_checkbox).to_be_visible()
        expect(self.cancel_button).to_be_visible()
        expect(self.generate_button).to_be_visible()
        return self

    @step
    def should_not_be_visible(self):
        """Verify the dialog is not visible."""
        expect(self.modal).not_to_be_visible()
        return self

    @step
    def should_have_generate_button_disabled(self):
        """Verify "Generate with AI" is disabled (e.g. empty description)."""
        expect(self.generate_button).to_be_disabled()
        return self
