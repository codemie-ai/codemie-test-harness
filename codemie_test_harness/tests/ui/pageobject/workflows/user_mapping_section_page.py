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

"""Page object for the 'Your Integration Settings' user mapping section.

This section appears inside the AssistantNodePanel on workflow screens when
the assistant has at least one user-selectable (non-pinned) integration slot.

Covers: Per-workflow scope for personal integration settings.
"""

from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class UserMappingSectionPage(BasePage):
    """Encapsulates the 'Your Integration Settings' section within the assistant panel.

    Contains:
    - Integration selection dropdowns (comboboxes)
    - 'Apply to the whole assistant' scope-control checkbox (workflow screens only)
    - Save button
    """

    # ==================== PROPERTIES ====================

    @property
    def section_heading(self) -> Locator:
        """'Your Integration Settings' heading within the assistant panel."""
        return self.page.get_by_text("Your Integration Settings", exact=True)

    @property
    def apply_to_assistant_checkbox(self) -> Locator:
        """'Apply to the whole assistant' scope-control checkbox."""
        return self.page.get_by_label("Apply to the whole assistant")

    @property
    def integration_dropdown(self) -> Locator:
        """First integration selection combobox (visible in the user mapping section)."""
        return self.page.get_by_role("combobox").first

    @property
    def save_button(self) -> Locator:
        """Save button within the user mapping section."""
        return self.page.get_by_role("button", name="Save")

    # ==================== ASSERTION METHODS ====================

    @step
    def should_be_visible(self, timeout: int = 15000):
        """Assert that the 'Your Integration Settings' section heading is visible.

        The section is rendered after the panel fetches the assistant's slots and the
        user's effective mapping, which can exceed Playwright's 5s expect default on a
        loaded workflow canvas — hence the more generous default.
        """
        expect(self.section_heading).to_be_visible(timeout=timeout)

    @step
    def should_not_be_visible(self):
        """Assert that the 'Your Integration Settings' section heading is not visible."""
        expect(self.section_heading).to_be_hidden()

    @step
    def should_have_checkbox_visible(self):
        """Assert that the 'Apply to the whole assistant' checkbox is visible."""
        expect(self.apply_to_assistant_checkbox).to_be_visible()

    @step
    def should_have_no_checkbox(self):
        """Assert that the 'Apply to the whole assistant' checkbox is absent."""
        expect(self.apply_to_assistant_checkbox).to_have_count(0)

    @step
    def should_checkbox_be_checked(self):
        """Assert that the 'Apply to the whole assistant' checkbox is pre-ticked.

        Expected when user has no existing assistant-scoped selection (AC8).
        """
        expect(self.apply_to_assistant_checkbox).to_be_checked()

    @step
    def should_checkbox_be_unchecked(self):
        """Assert that the 'Apply to the whole assistant' checkbox is not checked.

        Expected when user already has an assistant-scoped selection (AC9).
        """
        expect(self.apply_to_assistant_checkbox).not_to_be_checked()

    @step
    def should_have_integration_dropdown_visible(self):
        """Assert that the integration selection dropdown is visible."""
        expect(self.integration_dropdown).to_be_visible()

    @step
    def should_have_save_button_visible(self):
        """Assert that the Save button is visible."""
        expect(self.save_button).to_be_visible()

    # ==================== INTERACTION METHODS ====================

    @step
    def tick_apply_to_whole_assistant(self):
        """Tick the 'Apply to the whole assistant' checkbox."""
        self.apply_to_assistant_checkbox.check()

    @step
    def untick_apply_to_whole_assistant(self):
        """Untick the 'Apply to the whole assistant' checkbox."""
        self.apply_to_assistant_checkbox.uncheck()

    @step
    def select_integration(self, integration_name: str):
        """Select an integration from the first integration dropdown by label.

        Args:
            integration_name: Display label of the integration to select.
        """
        self.integration_dropdown.select_option(label=integration_name)

    @step
    def save(self):
        """Click the Save button within the user mapping section."""
        self.save_button.click()
