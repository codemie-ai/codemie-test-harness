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

"""Page object for the 'Budget details' popup opened from a budget row's row-actions menu
(BudgetsManagementPage.click_view_details).

FE: src/pages/settings/administration/components/BudgetDetailsPopup.tsx

Locators derived from live UI inspection on 2026-11-11. The dialog has no data-testid
attributes; its detail rows are generic label/value div pairs with no role, so a row's
value is selected by its label text.
"""

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class BudgetDetailsPopupPage(BasePage):
    """'Budget details' popup."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def dialog(self):
        """The 'Budget details' dialog."""
        return self.page.get_by_role("dialog")

    @property
    def heading(self):
        """'Budget details' dialog heading."""
        return self.dialog.get_by_role("heading", name="Budget details")

    @property
    def close_button(self):
        """Dialog close button."""
        return self.dialog.get_by_role("button", name="Close")

    def _detail_value(self, label: str):
        """Value of a label/value detail row, selected by the label's own text."""
        return self.dialog.get_by_text(label, exact=True).locator(
            "xpath=following-sibling::div[1]"
        )

    @property
    def created_by_value(self):
        """'Created by' row value (BudgetDetailsPopup.tsx:54, getBudgetCreatorDisplay)."""
        return self._detail_value("Created by")

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def close(self):
        """Close the dialog."""
        self.close_button.click()
        expect(self.dialog).to_have_count(0)
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self):
        """Assert the dialog has opened."""
        expect(self.heading).to_be_visible(timeout=15000)
        return self

    @step
    def should_have_created_by(self, expected_text: str):
        """Assert the 'Created by' row shows exactly `expected_text`."""
        self.should_be_visible()
        expect(self.created_by_value).to_have_text(expected_text, timeout=15000)
        return self
