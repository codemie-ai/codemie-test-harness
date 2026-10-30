# Copyright 2026 EPAM Systems, Inc. ("EPAM")
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

"""Page object for the CLI Analytics user detail modal.

Opened by clicking a row in the Users table. The modal shows a Summary card
with per-user metrics including Tool Success.
"""

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

# Em dash (U+2014): rendered when tool_calls = 0, meaning "no data".
EM_DASH = "—"


class CLIAnalyticsUserModal(BasePage):
    """User detail dialog in the CLI Analytics Users section."""

    # ── Locators ─────────────────────────────────────────────────────────────────

    @property
    def root(self) -> Locator:
        """The user detail dialog."""
        return self.page.get_by_role("dialog")

    @property
    def close_button(self) -> Locator:
        """Dialog close button."""
        return self.root.get_by_role("button", name="Close", exact=True)

    @property
    def modal_tool_success(self) -> Locator:
        """Tool Success metric in the user modal Summary card.

        The live component renders no data-testid on the metric element; we locate
        by exact em-dash text (U+2014), which is the only exact-dash element in the
        dialog when tool_calls == 0.
        """
        return self.root.get_by_text(EM_DASH, exact=True)

    # ── Actions ──────────────────────────────────────────────────────────────────

    @step
    def close(self):
        """Close the dialog with its close button."""
        self.close_button.click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self):
        """Assert the user detail dialog is open."""
        expect(self.root).to_be_visible(timeout=15000)
        expect(self.close_button).to_be_visible(timeout=15000)
        return self

    @step
    def should_show_tool_success_dash(self):
        """Assert Tool Success shows the em dash, indicating no tool calls were made."""
        expect(
            self.modal_tool_success,
            "modal-tool-success should display '—' when tool_calls = 0",
        ).to_have_text(EM_DASH, timeout=15000)
        return self

    @step
    def should_be_closed(self):
        """Assert the user detail dialog is closed."""
        expect(self.root).to_be_hidden(timeout=15000)
        return self
