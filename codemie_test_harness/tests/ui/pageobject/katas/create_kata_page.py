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
Create Kata page object for the kata creation workflow.
Contains methods for interacting with the kata creation form.
"""

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class CreateKataPage(BasePage):
    """Create Kata page with form handling and help panel support."""

    page_url = "/katas/new"

    def __init__(self, page):
        super().__init__(page)

    # ==================== PROPERTIES ====================
    # Header elements
    @property
    def page_title(self) -> Locator:
        """Page title element showing 'Create New Kata'."""
        return self.page.get_by_role("heading", name="Create New Kata", level=1)

    @property
    def back_button(self) -> Locator:
        """Back button in the header."""
        return self.page.get_by_role("button", name="Back")

    @property
    def cancel_button(self) -> Locator:
        """Cancel button in the action button row."""
        return self.page.get_by_role("button", name="Cancel")

    @property
    def save_as_draft_button(self) -> Locator:
        """Save as Draft button."""
        return self.page.get_by_role("button", name="Save as Draft")

    @property
    def publish_button(self) -> Locator:
        """Publish button."""
        return self.page.get_by_role("button", name="Publish")

    # Help button and panel
    @property
    def help_button(self) -> Locator:
        """Help button in bottom right corner."""
        return self.page.get_by_role("button", name="Help").filter(
            has=self.page.locator("svg")
        )

    @property
    def help_panel_title(self) -> Locator:
        """Help panel title 'CodeMie Helper'."""
        return self.page.get_by_role("heading", name="CodeMie Helper", level=3)

    @property
    def help_panel_close_button(self) -> Locator:
        """Close button in help panel.
        Uses exact=True to avoid matching toast notification 'Close notification' button.
        """
        return self.page.get_by_role("button", name="Close", exact=True)

    @property
    def help_work_with_katas_button(self) -> Locator:
        """'How to work with Katas' button in help panel."""
        return self.page.get_by_role("button", name="How to work with Katas")

    # Form elements
    @property
    def title_input(self) -> Locator:
        """Title input field."""
        return self.page.get_by_placeholder("Enter kata title")

    @property
    def description_input(self) -> Locator:
        """Description textarea."""
        return self.page.get_by_placeholder("Enter kata description")

    @property
    def level_dropdown(self) -> Locator:
        """Level dropdown."""
        return self.page.locator('button:has-text("Level")')

    @property
    def duration_input(self) -> Locator:
        """Duration spinbutton."""
        return self.page.get_by_role("spinbutton", name="Duration (minutes) *")

    # ==================== NAVIGATION METHODS ====================

    @step
    def navigate_to(self):
        """
        Navigate to the Create Kata page.

        Returns:
            self: Returns the page object for method chaining
        """
        self.page.goto(self.page_url)
        self.wait_for_page_load()
        return self

    @step
    def go_back(self):
        """Click the back button to return to previous page."""
        self.back_button.click()
        return self

    # ==================== HELP PANEL METHODS ====================

    @step
    def click_help_button(self):
        """Click the help button in bottom right corner."""
        self.help_button.click()
        expect(self.help_panel_title).to_be_visible()
        return self

    @step
    def close_help_panel(self):
        """Close the help panel."""
        self.help_panel_close_button.click()
        expect(self.help_panel_title).to_be_hidden()
        return self

    @step
    def should_have_help_button_visible(self):
        """Verify that the help button is visible."""
        expect(self.help_button).to_be_visible()
        return self

    @step
    def should_have_help_panel_visible(self):
        """Verify that the help panel is visible."""
        expect(self.help_panel_title).to_be_visible()
        expect(self.help_work_with_katas_button).to_be_visible()
        return self

    # ==================== FORM INTERACTION METHODS ====================

    @step
    def fill_title(self, title: str):
        """Fill the kata title field."""
        self.title_input.fill(title)
        return self

    @step
    def fill_description(self, description: str):
        """Fill the kata description field."""
        self.description_input.fill(description)
        return self

    @step
    def set_duration(self, minutes: int):
        """Set the kata duration in minutes."""
        self.duration_input.fill(str(minutes))
        return self

    # ==================== ACTION METHODS ====================

    @step
    def click_save_as_draft(self):
        """Click the Save as Draft button."""
        self.save_as_draft_button.click()
        return self

    @step
    def click_publish(self):
        """Click the Publish button."""
        self.publish_button.click()
        return self

    @step
    def click_cancel(self):
        """Click the Cancel button."""
        self.cancel_button.click()
        return self

    # ==================== VERIFICATION METHODS ====================

    @step
    def should_be_on_create_kata_page(self):
        """Verify that we are on the Create Kata page."""
        expect(self.page_title).to_be_visible()
        expect(self.save_as_draft_button).to_be_visible()
        expect(self.publish_button).to_be_visible()
        return self
