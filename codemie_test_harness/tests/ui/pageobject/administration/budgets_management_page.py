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

Locators derived from live UI inspection on 2026-08-18 (base table/role controls) and
2026-11-11 (Created By column, row actions menu, items-per-page dropdown).
For the Auditor role:
  - No 'Create budget' button
  - Budgets table is visible and readable
  - No edit/sync/assign write controls exposed
"""

from typing import List

from hamcrest import assert_that, empty
from playwright.sync_api import expect, TimeoutError as PlaywrightTimeoutError
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class BudgetsManagementPage(BasePage):
    """Administration > Budgets Management page."""

    PATH = "/settings/administration/budgets"

    def __init__(self, page):
        super().__init__(page)
        self._requested_urls: List[str] = []

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

    def budget_row(self, budget_name: str):
        """A specific budget row identified by its Name column text."""
        return self.budget_rows.filter(has_text=budget_name)

    def created_by_cell(self, budget_name: str):
        """'Created By' cell (7th column, index 6) of a budget row."""
        return self.budget_row(budget_name).get_by_role("cell").nth(6)

    @property
    def items_per_page_dropdown(self):
        """PrimeReact items-per-page dropdown (not a native <select>)."""
        return self.page.locator('span[role="combobox"]')

    def _row_actions_button(self, budget_name: str):
        """'More options <budget name>' button in the last column of a budget row."""
        return self.page.get_by_role("button", name=f"More options {budget_name}")

    @property
    def _row_actions_menu(self):
        """The currently open row-actions dropdown menu."""
        return self.page.get_by_role("menu", name="Options")

    @property
    def _view_details_menu_item(self):
        """'View details' item of the currently open row-actions menu."""
        return self.page.get_by_role("menuitem", name="View details")

    @property
    def _edit_menu_item(self):
        """'Edit' item of the currently open row-actions menu."""
        return self.page.get_by_role("menuitem", name="Edit")

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def navigate_to(self):
        """Navigate to the Budgets Management page and wait for the heading."""
        self.page.goto(self.PATH)
        self.page.wait_for_load_state("networkidle", timeout=30000)
        expect(self.page_heading).to_be_visible(timeout=15000)
        return self

    def _record_request(self, request):
        self._requested_urls.append(request.url)

    @step
    def capture_requests(self):
        """Record every request from now on; call before navigate_to so the first
        mount's calls are captured too."""
        self.page.on("request", self._record_request)
        return self

    @step
    def show_up_to_100_items_per_page(self):
        """Switch the items-per-page dropdown to 100, so a row search covers the whole
        list in a single page (seeded/system budgets are not guaranteed to be on page 1)."""
        self.items_per_page_dropdown.click()
        self.page.get_by_role("option", name="100 items").click()
        self.page.wait_for_load_state("networkidle", timeout=15000)
        return self

    @step
    def open_row_actions(self, budget_name: str):
        """Open the row-actions menu of a budget row.

        The first click sometimes does not register (observed live on the preview stand);
        a second click is tried once before letting the timeout propagate.
        """
        button = self._row_actions_button(budget_name)
        expect(button).to_be_visible(timeout=15000)
        button.click()
        try:
            self._row_actions_menu.wait_for(state="visible", timeout=2000)
        except PlaywrightTimeoutError:
            button.click()
            self._row_actions_menu.wait_for(state="visible", timeout=5000)
        return self

    @step
    def click_view_details(self, budget_name: str):
        """Open a budget row's actions menu and click 'View details'."""
        self.open_row_actions(budget_name)
        self._view_details_menu_item.click()
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

    @step
    def should_have_created_by(self, budget_name: str, expected_text: str):
        """Assert the 'Created By' cell of a budget row shows exactly `expected_text`."""
        expect(self.created_by_cell(budget_name)).to_have_text(
            expected_text, timeout=15000
        )
        return self

    @step
    def should_offer_view_details_but_not_edit(self, budget_name: str):
        """Open a row's actions menu and assert it offers 'View details' but not 'Edit'
        (e.g. a preconfigured budget, which has no Edit control), then dismiss it."""
        self.open_row_actions(budget_name)
        expect(self._view_details_menu_item).to_be_visible(timeout=5000)
        expect(self._edit_menu_item).to_have_count(0)
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(300)
        return self

    @step
    def should_not_have_requested(self, path_fragment: str):
        """Assert no request recorded since `capture_requests()` contains `path_fragment`.

        Covers both the list mount and, when the popup was opened meanwhile, its mount too —
        `_requested_urls` accumulates every request made on this page since capture started.
        """
        matches = [url for url in self._requested_urls if path_fragment in url]
        assert_that(
            matches,
            empty(),
            f"No request should contain '{path_fragment}'; got {matches}",
        )
        return self
