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

"""Page object for the session detail modal of Analytics > CLI Analytics.

Opened by clicking a row in the Sessions table (also used by Cost "Most expensive
sessions"). Locators verified against the live UI on 2026-10-12
and the codemie-ui ``SessionModal`` / ``SessionBody`` components.
"""

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class CLIAnalyticsSessionModal(BasePage):
    """Session detail dialog: cost, tokens, activity and timeline widgets."""

    WIDGET_TITLES = (
        "Cost & Time",
        "Token usage",
        "Activity",
        "Token & cost growth",
        "Timeline",
    )
    NO_DATA_TEXT = "No data for this session."

    # ── Locators ─────────────────────────────────────────────────────────────────

    @property
    def root(self) -> Locator:
        """The session dialog (it has no accessible name)."""
        return self.page.get_by_role("dialog")

    @property
    def close_button(self) -> Locator:
        """Dialog 'Close' button."""
        return self.root.get_by_role("button", name="Close", exact=True)

    def widget_heading(self, title: str) -> Locator:
        """Heading of a session widget by exact title."""
        return self.root.get_by_role("heading", name=title, exact=True)

    @property
    def load_error(self) -> Locator:
        """Error message SessionModal shows instead of the session body."""
        return self.root.locator("p.text-text-failed")

    @property
    def no_data_message(self) -> Locator:
        """Message shown when the session detail came back empty."""
        return self.root.get_by_text(self.NO_DATA_TEXT, exact=True)

    # ── Actions ──────────────────────────────────────────────────────────────────

    @step
    def close(self):
        """Close the dialog with its 'Close' button."""
        self.close_button.click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self):
        """Assert the session dialog is open."""
        expect(self.root).to_be_visible(timeout=15000)
        expect(self.close_button).to_be_visible(timeout=15000)
        return self

    @step
    def should_have_title(self, prompt: str):
        """Assert the dialog header shows the session's first prompt (truncated to 80 chars)."""
        expect(
            self.root.get_by_text(prompt[:80], exact=False).first,
            f"Session dialog title should show the prompt '{prompt}'",
        ).to_be_visible(timeout=15000)
        return self

    @step
    def should_have_session_details(self):
        """Assert the session body rendered all its widgets, without errors."""
        for title in self.WIDGET_TITLES:
            expect(
                self.widget_heading(title),
                f"Session widget '{title}' should be visible",
            ).to_be_visible(timeout=15000)
        expect(
            self.load_error, "Session detail should load without errors"
        ).to_have_count(0)
        expect(
            self.no_data_message, "Session detail should not be empty"
        ).to_have_count(0)
        return self

    @step
    def should_be_closed(self):
        """Assert the session dialog is closed."""
        expect(self.root).to_be_hidden(timeout=15000)
        return self
