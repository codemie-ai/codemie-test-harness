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

from playwright.sync_api import Locator, Page, expect
from reportportal_client import step


class UnsavedChangesDialog:
    """Component for the Unsaved Changes confirmation dialog."""

    def __init__(self, page: Page):
        self.page = page

    # ====================
    # PROPERTIES
    # ====================

    @property
    def dialog(self) -> Locator:
        """Main dialog container."""
        # Dialog is a div with role="dialog", not a <dialog> element
        return self.page.locator('[role="dialog"]:has(h4:text-is("Unsaved Changes"))')

    @property
    def heading(self) -> Locator:
        """Dialog heading 'Unsaved Changes'."""
        return self.dialog.get_by_role("heading", name="Unsaved Changes", level=4)

    @property
    def message(self) -> Locator:
        """Dialog message paragraph."""
        return self.dialog.locator("p")

    @property
    def keep_editing_button(self) -> Locator:
        """'Keep Editing' button."""
        return self.dialog.get_by_role("button", name="Keep Editing")

    @property
    def discard_changes_button(self) -> Locator:
        """'Discard Changes' button."""
        return self.dialog.get_by_role("button", name="Discard Changes")

    @property
    def save_and_proceed_button(self) -> Locator:
        """'Save and Proceed' button."""
        return self.dialog.get_by_role("button", name="Save and Proceed")

    # ====================
    # ACTION METHODS
    # ====================

    @step
    def click_keep_editing(self):
        """Click the 'Keep Editing' button."""
        self.keep_editing_button.click()

    @step
    def click_discard_changes(self):
        """Click the 'Discard Changes' button."""
        self.discard_changes_button.click()

    @step
    def click_save_and_proceed(self):
        """Click the 'Save and Proceed' button."""
        self.save_and_proceed_button.click()

    # ====================
    # VERIFICATION METHODS
    # ====================

    @step
    def should_be_visible(self):
        """Verify that the unsaved changes dialog is visible."""
        # Wait for dialog to appear with extended timeout
        expect(self.dialog).to_be_visible(timeout=10000)
        expect(self.heading).to_be_visible()

    @step
    def should_not_be_visible(self):
        """Verify that the unsaved changes dialog is not visible."""
        expect(self.dialog).not_to_be_visible()

    @step
    def should_have_correct_message(self):
        """Verify that the dialog displays the correct warning message."""
        expected_message = (
            "You have unsaved changes that will be lost. "
            "Are you sure you want to discard them?"
        )
        expect(self.message).to_have_text(expected_message)

    @step
    def should_have_keep_editing_button(self):
        """Verify that the 'Keep Editing' button is visible."""
        expect(self.keep_editing_button).to_be_visible()

    @step
    def should_have_discard_changes_button(self):
        """Verify that the 'Discard Changes' button is visible."""
        expect(self.discard_changes_button).to_be_visible()

    @step
    def should_have_both_buttons(self):
        """Verify that both buttons are visible."""
        self.should_have_keep_editing_button()
        self.should_have_discard_changes_button()
