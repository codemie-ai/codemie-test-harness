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

"""Page object for the Config tab of Administration -> Marketplace management.

URL: /settings/administration/marketplace-management (Config tab: .../settings)

The tab lists one settings card per marketplace declaration. The thresholds
card ("Marketplace Thresholds") holds five text inputs, its own "Default from
config" / "Overridden" marker, a Save button (disabled while a field is
invalid or a request is running) and a "Reset to default" button that only
exists while an override is stored. Reset has no confirmation dialog.
"""

import re

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.marketplace_thresholds_ui_test_data import (
    TAB_LABEL_PATTERNS,
    THRESHOLDS_CARD_HEADING,
)

_URL = "/settings/administration/marketplace-management"
_TAB_COUNT = len(TAB_LABEL_PATTERNS)


class MarketplaceSettingsPage(BasePage):
    """Page object for the Marketplace management Config tab."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def config_tab(self):
        """'Config' tab button."""
        return self.page.get_by_test_id("mm-tab-settings")

    @property
    def tab_strip(self):
        """All Marketplace management tab buttons, in DOM order."""
        return self.page.locator("[data-testid^='mm-tab-']")

    @property
    def settings_tab(self):
        """Container of the settings cards."""
        return self.page.get_by_test_id("marketplace-settings-tab")

    @property
    def thresholds_card_heading(self):
        """'Marketplace Thresholds' card heading (level 3), within the tab."""
        return self.settings_tab.get_by_role(
            "heading", name=THRESHOLDS_CARD_HEADING, exact=True
        )

    @property
    def thresholds_card(self):
        """Section of the thresholds card, found through its heading.

        The inner locator of ``filter(has=...)`` is resolved relative to each
        section, so it must not be re-scoped by the tab test id (an ancestor of
        the section) and is built from the page-level role lookup instead.
        """
        heading_inside_section = self.page.get_by_role(
            "heading", name=THRESHOLDS_CARD_HEADING, exact=True
        )
        return self.settings_tab.locator("section").filter(has=heading_inside_section)

    def marker(self, text: str):
        """State marker of the thresholds card with the given text."""
        return self.thresholds_card.get_by_text(text, exact=True)

    @property
    def save_button(self):
        """'Save' button of the thresholds card."""
        return self.thresholds_card.get_by_role("button", name="Save", exact=True)

    @property
    def reset_button(self):
        """'Reset to default' button of the thresholds card (override only)."""
        return self.thresholds_card.get_by_role(
            "button", name="Reset to default", exact=True
        )

    def field(self, label: str):
        """Threshold input identified by its visible label."""
        return self.thresholds_card.get_by_label(label, exact=True)

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def navigate_to_config_tab(self):
        """Open Marketplace management and switch to the Config tab."""
        self.page.goto(_URL)
        expect(self.config_tab).to_be_visible(timeout=15000)
        self.config_tab.click()
        expect(self.thresholds_card_heading).to_be_visible(timeout=15000)
        return self

    @step
    def fill_field(self, label: str, value: str):
        """Replace the value of the threshold input with the given label."""
        self.field(label).fill(value)
        return self

    @step
    def click_save(self):
        """Click Save on the thresholds card."""
        self.save_button.click()
        return self

    @step
    def click_reset_to_default(self):
        """Click Reset to default on the thresholds card."""
        self.reset_button.click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_see_config_tab_last(self):
        """Assert the Config tab follows Overview, Review queue and Cleanup
        queue."""
        expect(self.tab_strip).to_have_count(_TAB_COUNT)
        expect(self.tab_strip).to_have_text(
            [re.compile(pattern) for pattern in TAB_LABEL_PATTERNS]
        )
        return self

    @step
    def should_see_thresholds_card(self):
        """Assert the thresholds card is shown."""
        expect(self.thresholds_card_heading).to_be_visible()
        return self

    @step
    def should_have_field_values(self, expected: dict):
        """Assert each input holds its expected value.

        Args:
            expected: Mapping of input label to expected value.
        """
        for label, value in expected.items():
            expect(self.field(label)).to_have_value(value)
        return self

    @step
    def should_see_marker(self, text: str, other_text: str):
        """Assert the card shows the marker ``text`` and not ``other_text``.

        Args:
            text: Marker expected to be visible.
            other_text: The opposite marker, expected to be absent.
        """
        expect(self.marker(text)).to_be_visible(timeout=10000)
        expect(self.marker(other_text)).to_have_count(0)
        return self

    @step
    def should_have_reset_button(self):
        """Assert the Reset to default button is shown (an override is stored)."""
        expect(self.reset_button).to_be_visible(timeout=10000)
        return self

    @step
    def should_not_have_reset_button(self):
        """Assert the Reset to default button is absent (no override stored)."""
        expect(self.reset_button).to_have_count(0)
        return self
