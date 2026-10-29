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

"""Delete Confirmation Dialog component for confirming integration deletion."""

from playwright.sync_api import Locator, Page, expect
from reportportal_client import step


class DeleteConfirmationDialog:
    """Component for the Delete Confirmation dialog."""

    def __init__(self, page: Page):
        self.page = page

    # ====================
    # PROPERTIES
    # ====================

    @property
    def dialog(self) -> Locator:
        """Main dialog container."""
        return self.page.locator('[role="dialog"]')

    @property
    def heading(self) -> Locator:
        """Dialog heading."""
        return self.dialog.get_by_role("heading", level=4)

    @property
    def message(self) -> Locator:
        """Dialog message paragraph."""
        return self.dialog.locator("p, .p-confirm-popup-message")

    @property
    def confirm_button(self) -> Locator:
        """Confirm deletion button."""
        return self.dialog.get_by_role("button", name="Delete")

    @property
    def cancel_button(self) -> Locator:
        """Cancel deletion button."""
        return self.dialog.get_by_role("button", name="Cancel")

    # ====================
    # ACTION METHODS
    # ====================

    @step
    def click_confirm(self):
        """Click the confirm button to proceed with deletion."""
        self.confirm_button.click()
        return self

    @step
    def click_cancel(self):
        """Click the cancel button to abort deletion."""
        self.cancel_button.click()
        return self

    # ====================
    # VERIFICATION METHODS
    # ====================

    @step
    def should_be_visible(self):
        """Verify that the delete confirmation dialog is visible."""
        expect(self.dialog).to_be_visible(timeout=10000)
        expect(self.heading).to_be_visible()
        return self

    @step
    def should_not_be_visible(self):
        """Verify that the delete confirmation dialog is not visible."""
        expect(self.dialog).not_to_be_visible()
        return self

    @step
    def should_have_correct_heading(self, expected_heading: str = "Confirm Delete"):
        """
        Verify that the dialog displays the correct heading.

        Args:
            expected_heading: Expected heading text (default: "Confirm Delete")
        """
        expect(self.heading).to_have_text(expected_heading)
        return self

    @step
    def should_have_message_containing(self, expected_text: str):
        """
        Verify that the dialog message contains expected text.

        Args:
            expected_text: Expected text in the message
        """
        expect(self.message).to_contain_text(expected_text)
        return self

    @step
    def should_have_both_buttons(self):
        """Verify that both confirm and cancel buttons are visible."""
        expect(self.confirm_button).to_be_visible()
        expect(self.cancel_button).to_be_visible()
        return self
