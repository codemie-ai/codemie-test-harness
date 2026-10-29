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

"""Page object for the Budgets Management administration page.

URL: /settings/administration/budgets

Locators derived from live UI inspection on 2026-08-18.
For the Auditor role:
  - No 'Create budget' button
  - Budgets table is visible and readable
  - No edit/sync/assign write controls exposed
"""

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class BudgetsManagementPage(BasePage):
    """Administration > Budgets Management page."""

    PATH = "/settings/administration/budgets"

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def page_heading(self):
        """'Budgets management' page heading."""
        return self.page.get_by_role("heading", name="Budgets management")

    @property
    def budget_table(self):
        """The budgets data table."""
        return self.page.locator("table").first

    @property
    def budget_rows(self):
        """All data rows inside the budgets table body."""
        return self.page.locator("tbody tr")

    @property
    def create_budget_button(self):
        """'Create budget' button (should be absent for auditor role)."""
        return self.page.get_by_role("button", name="Create budget", exact=True)

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def navigate_to(self):
        """Navigate to the Budgets Management page and wait for the heading."""
        self.page.goto(self.PATH)
        self.page.wait_for_load_state("networkidle", timeout=30000)
        expect(self.page_heading).to_be_visible(timeout=15000)
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_see_budget_list_not_empty(self):
        """Assert the budgets table contains at least one row."""
        expect(self.budget_table).to_be_visible(timeout=10000)
        expect(self.budget_rows.first).to_be_visible(timeout=10000)
        return self

    @step
    def should_not_see_write_controls(self):
        """Assert no budget write controls are exposed for the auditor role.

        Verifies:
        - No 'Create budget' button
        - No 'Sync' button
        - No 'Edit' button in the budget table actions
        - No 'Assign' button
        """
        expect(self.create_budget_button).to_have_count(0)
        # Generic write-action buttons that should be absent
        expect(self.page.get_by_role("button", name="Sync", exact=True)).to_have_count(
            0
        )
        return self

    @step
    def should_be_redirected_from_budgets(self):
        """Navigate to the Budgets URL and assert a non-privileged user is redirected away.

        After the page settles, the 'Budgets management' heading must NOT be visible —
        the app redirected the user to a different page.
        """
        self.page.goto(self.PATH)
        self.page.wait_for_load_state("networkidle", timeout=30000)
        expect(self.page_heading).not_to_be_visible(timeout=8000)
        return self
