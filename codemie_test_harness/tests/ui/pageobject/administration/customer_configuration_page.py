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

"""Page object for the Customer Configuration administration page.

URL: /settings/administration/customer-configuration

Locators derived from live UI inspection on 2026-08-31.
The page renders a list of setting cards driven by the declarations API.
Each card has a state marker (``Default from config`` or ``Overridden``),
field controls (switch, textarea), and Save / Reset to default buttons.
"""

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

_URL = "/settings/administration/customer-configuration"


class CustomerConfigurationPage(BasePage):
    """Page object for Settings → Administration → Customer Configuration."""

    # ── Navigation ────────────────────────────────────────────────────────────

    @step
    def navigate_to(self):
        """Navigate directly to the Customer Configuration page."""
        self.page.goto(_URL)
        expect(self.page_heading).to_be_visible(timeout=15000)
        return self

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def page_heading(self):
        """Main page heading 'Customer Configuration'."""
        return self.page.get_by_role("heading", name="Customer Configuration")

    @property
    def chat_disclaimer_card(self):
        """Container section for the Chat disclaimer setting card."""
        return self.page.locator("section").filter(has_text="Chat disclaimer")

    @property
    def chat_disclaimer_card_heading(self):
        """'Chat disclaimer' card heading (level 3)."""
        return self.chat_disclaimer_card.get_by_role("heading", name="Chat disclaimer")

    @property
    def default_from_config_marker(self):
        """Marker element showing 'Default from config' (no active override)."""
        return self.chat_disclaimer_card.get_by_text("Default from config")

    @property
    def overridden_marker(self):
        """Marker element showing 'Overridden' (an active override is set)."""
        return self.chat_disclaimer_card.get_by_text("Overridden")

    @property
    def show_disclaimer_switch(self):
        """'Show disclaimer' toggle switch."""
        return self.chat_disclaimer_card.get_by_role("switch", name="Show disclaimer")

    @property
    def disclaimer_text_field(self):
        """Disclaimer text textarea input."""
        return self.chat_disclaimer_card.get_by_role("textbox")

    @property
    def save_button(self):
        """'Save' button for the chatDisclaimer setting card."""
        return self.chat_disclaimer_card.get_by_role("button", name="Save")

    @property
    def reset_to_default_button(self):
        """'Reset to default' button — visible only when an override is active."""
        return self.chat_disclaimer_card.get_by_role("button", name="Reset to default")

    @property
    def save_success_status(self):
        """Status message shown after a successful save."""
        return self.page.get_by_role("status").filter(has_text="Setting saved")

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def enable_disclaimer_switch(self):
        """Click the Show disclaimer switch to enable it (if not already on)."""
        if self.show_disclaimer_switch.get_attribute("aria-checked") != "true":
            self.show_disclaimer_switch.locator("..").click()
        return self

    @step
    def fill_disclaimer_text(self, text: str):
        """Clear and fill the disclaimer text textarea.

        Args:
            text: The disclaimer text to enter.
        """
        self.disclaimer_text_field.fill(text)
        return self

    @step
    def click_save(self):
        """Click the Save button and wait for the success status to appear."""
        self.save_button.click()
        expect(self.save_success_status).to_be_visible(timeout=10000)
        return self

    @step
    def click_reset_to_default(self):
        """Click the Reset to default button and wait for the default marker."""
        self.reset_to_default_button.click()
        expect(self.default_from_config_marker).to_be_visible(timeout=10000)
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_see_page_heading(self):
        """Assert the Customer Configuration heading is visible."""
        expect(self.page_heading).to_be_visible()
        return self

    @step
    def should_see_chat_disclaimer_card(self):
        """Assert the Chat disclaimer setting card is visible."""
        expect(self.chat_disclaimer_card_heading).to_be_visible()
        return self

    @step
    def should_see_default_marker(self):
        """Assert the 'Default from config' marker is visible (no override active)."""
        expect(self.default_from_config_marker).to_be_visible(timeout=10000)
        return self

    @step
    def should_see_overridden_marker(self):
        """Assert the 'Overridden' marker is visible (an active override is set)."""
        expect(self.overridden_marker).to_be_visible(timeout=10000)
        return self

    @step
    def should_not_see_overridden_marker(self):
        """Assert the 'Overridden' marker is not present in the DOM."""
        expect(self.overridden_marker).to_have_count(0)
        return self

    @step
    def should_see_disclaimer_switch(self):
        """Assert the Show disclaimer switch control is visible."""
        expect(self.show_disclaimer_switch).to_be_visible()
        return self

    @step
    def should_see_disclaimer_text_field(self):
        """Assert the disclaimer text textarea is visible."""
        expect(self.disclaimer_text_field).to_be_visible()
        return self

    @step
    def should_have_disclaimer_text(self, expected_text: str):
        """Assert the textarea contains the expected disclaimer text.

        Args:
            expected_text: Expected content of the textarea.
        """
        expect(self.disclaimer_text_field).to_have_value(expected_text)
        return self
