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

"""Page object for the Marketplace management "Review queue" tab.

URL: /settings/administration/marketplace-management/marketplace-assistants

Locators use the data-testid attributes the page exposes.
"""

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

ROW_TIMEOUT_MS = 15000


def reason_counter_text(current_length: int, label: str = "Reason") -> str:
    """Live counter shown under a reason field (the range uses an en dash)."""
    return f"{label} must be 20–2000 characters (currently {current_length})."


class MarketplaceReviewQueuePage(BasePage):
    """Administration > Marketplace management > Review queue."""

    PATH = "/settings/administration/marketplace-management/marketplace-assistants"
    COLUMNS = ("Assistant", "Submitted by", "Submitted at", "Category", "Actions")

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def review_queue_tab(self):
        """'Review queue' tab of the Marketplace management layout."""
        return self.page.get_by_test_id("mm-tab-marketplace-assistants")

    @property
    def table(self):
        """Wrapper of the review queue table."""
        return self.page.get_by_test_id("marketplace-assistants-table")

    @property
    def table_rows(self):
        """Body rows of the table, including the empty-state row."""
        return self.table.locator("tbody tr")

    @property
    def search_input(self):
        """Search by assistant name or creator."""
        return self.page.get_by_test_id("assts-search-input")

    @property
    def category_filter(self):
        """Category select of the filter bar."""
        return self.page.get_by_test_id("asstsCategory-select")

    @property
    def clear_all_filters_button(self):
        """'Clear all' button, shown only while a filter is set."""
        return self.page.get_by_role("button", name="Clear all filters")

    @property
    def bulk_approve_button(self):
        """'Approve selected' bulk action."""
        return self.page.get_by_test_id("pending-bulk-approve")

    @property
    def bulk_reject_button(self):
        """'Reject selected' bulk action."""
        return self.page.get_by_test_id("pending-bulk-reject")

    @property
    def bulk_reason_input(self):
        """Shared reason textarea of the bulk reject popup."""
        return self.page.get_by_test_id("pending-bulk-reason-input")

    @property
    def bulk_submit_button(self):
        """Submit button of the bulk reject popup."""
        return self.page.get_by_test_id("pending-bulk-submit")

    @property
    def drawer_approve_button(self):
        """'Publish' (approve) button of the details drawer."""
        return self.page.get_by_test_id("drawer-approve-button")

    @property
    def drawer_approve_confirm_button(self):
        """Confirm button of the drawer approve confirmation."""
        return self.page.get_by_test_id("drawer-approve-confirm")

    @property
    def drawer_reject_button(self):
        """'Reject' button of the details drawer."""
        return self.page.get_by_test_id("drawer-reject-button")

    @property
    def drawer_reject_reason_input(self):
        """Reason textarea of the drawer reject popup."""
        return self.page.get_by_test_id("drawer-reject-reason")

    @property
    def drawer_reject_submit_button(self):
        """Submit button of the drawer reject popup."""
        return self.page.get_by_test_id("drawer-reject-submit")

    def row(self, assistant_id: str):
        """Table row of an assistant."""
        return self.page.get_by_test_id(f"marketplace-assistants-row-{assistant_id}")

    def row_checkbox(self, assistant_id: str):
        """Selection checkbox input of an assistant row."""
        return self.row(assistant_id).locator("[data-selection-checkbox] input")

    def row_name_button(self, assistant_id: str):
        """Assistant name button of a row; opens the details drawer."""
        return self.row(assistant_id).get_by_test_id(
            "marketplace-assistants-assistant-name"
        )

    def column_header(self, name: str):
        """Column header of the table by its label."""
        return self.table.get_by_role("columnheader", name=name)

    def toast(self, text: str):
        """Toast notification containing the text."""
        return self.page.locator(".codemie-toast").filter(has_text=text)

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def navigate_to(self):
        """Open the Review queue directly and wait for its table."""
        self.page.goto(self.PATH)
        expect(self.table).to_be_visible(timeout=30000)
        return self

    @step
    def search_for(self, text: str):
        """Type into the search box (applied after a short debounce)."""
        self.search_input.fill(text)
        return self

    @step
    def clear_all_filters(self):
        """Click 'Clear all'."""
        self.clear_all_filters_button.click()
        return self

    @step
    def select_rows(self, *assistant_ids: str):
        """Tick the selection checkbox of each given row."""
        for assistant_id in assistant_ids:
            self.row_checkbox(assistant_id).check()
        return self

    @step
    def open_drawer(self, assistant_id: str):
        """Open the details drawer of an assistant."""
        self.row_name_button(assistant_id).click()
        return self

    @step
    def approve_from_drawer(self):
        """Click Publish in the drawer and confirm."""
        self.drawer_approve_button.click()
        self.drawer_approve_confirm_button.click()
        return self

    @step
    def start_reject_from_drawer(self):
        """Click Reject in the drawer, opening the reason popup."""
        self.drawer_reject_button.click()
        return self

    @step
    def type_drawer_reject_reason(self, reason: str):
        """Replace the text of the drawer reject reason."""
        self.drawer_reject_reason_input.fill(reason)
        return self

    @step
    def submit_drawer_reject(self):
        """Submit the drawer reject popup."""
        self.drawer_reject_submit_button.click()
        return self

    @step
    def reject_selected_with_reason(self, reason: str):
        """Open the bulk reject popup, enter one shared reason and submit."""
        self.bulk_reject_button.click()
        self.bulk_reason_input.fill(reason)
        self.bulk_submit_button.click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_see_review_queue_tab(self):
        """The 'Review queue' tab is shown."""
        expect(self.review_queue_tab).to_contain_text("Review queue")
        return self

    @step
    def should_see_table_columns(self):
        """The table has the Assistant, Submitted by, Submitted at, Category and Actions columns."""
        expect(self.table).to_be_visible()
        for name in self.COLUMNS:
            expect(self.column_header(name)).to_be_visible()
        return self

    @step
    def should_see_row(self, assistant_id: str):
        """The assistant has a row in the table."""
        expect(self.row(assistant_id)).to_be_visible(timeout=ROW_TIMEOUT_MS)
        return self

    @step
    def should_not_see_row(self, assistant_id: str):
        """The assistant has no row in the table."""
        expect(self.row(assistant_id)).to_have_count(0, timeout=ROW_TIMEOUT_MS)
        return self

    @step
    def should_list_only_row(self, assistant_id: str):
        """The table shows the assistant's row and nothing else."""
        expect(self.row(assistant_id)).to_be_visible(timeout=ROW_TIMEOUT_MS)
        expect(self.table_rows).to_have_count(1, timeout=ROW_TIMEOUT_MS)
        return self

    @step
    def should_see_filter_bar(self):
        """The filter bar (search box) is shown."""
        expect(self.search_input).to_be_visible()
        return self

    @step
    def should_not_see_filter_bar(self):
        """The filter bar is replaced and absent from the page."""
        expect(self.search_input).to_have_count(0)
        return self

    @step
    def should_see_clear_all_button(self):
        """'Clear all' is shown."""
        expect(self.clear_all_filters_button).to_be_visible()
        return self

    @step
    def should_not_see_clear_all_button(self):
        """'Clear all' is gone."""
        expect(self.clear_all_filters_button).to_have_count(0)
        return self

    @step
    def should_see_bulk_actions(self):
        """'Approve selected' and 'Reject selected' are shown."""
        expect(self.bulk_approve_button).to_be_visible()
        expect(self.bulk_reject_button).to_be_visible()
        return self

    @step
    def should_see_drawer_actions(self):
        """The drawer loaded and offers Publish and Reject."""
        expect(self.drawer_approve_button).to_be_visible(timeout=ROW_TIMEOUT_MS)
        expect(self.drawer_reject_button).to_be_visible()
        return self

    @step
    def should_see_drawer_reject_counter(self, current_length: int):
        """The reject reason counter reports the typed length."""
        expect(
            self.page.get_by_text(reason_counter_text(current_length), exact=True)
        ).to_be_visible()
        return self

    @step
    def should_have_drawer_reject_submit_disabled(self):
        """The reject submit button is disabled."""
        expect(self.drawer_reject_submit_button).to_be_disabled()
        return self

    @step
    def should_have_drawer_reject_submit_enabled(self):
        """The reject submit button is enabled."""
        expect(self.drawer_reject_submit_button).to_be_enabled()
        return self

    @step
    def should_see_toast(self, text: str):
        """A toast with the text is shown."""
        expect(self.toast(text)).to_be_visible(timeout=ROW_TIMEOUT_MS)
        return self

    @step
    def should_show_row_details(
        self, assistant_id: str, assistant_name: str, submitted_by: str
    ):
        """The row shows the assistant's name and who submitted it."""
        expect(self.row_name_button(assistant_id)).to_have_text(
            assistant_name, timeout=ROW_TIMEOUT_MS
        )
        expect(
            self.row(assistant_id).get_by_test_id("assistants-creator")
        ).to_contain_text(submitted_by)
        return self
