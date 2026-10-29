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

"""Page object for the Activity Events admin page.

Locators derived from playwright-cli inspection of the
/settings/administration/activity-events page.
"""

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ActivityEventsPage(BasePage):
    """Activity Events administration page object.

    URL: /settings/administration/activity-events
    """

    page_url = "/settings/administration/activity-events"

    # ------------------------------------------------------------------
    # Element locators (always @property — never accessed from test code)
    # ------------------------------------------------------------------

    @property
    def heading(self):
        """'Activity events' page heading."""
        return self.page.get_by_role("heading", name="Activity events")

    @property
    def table(self):
        """Events table."""
        return self.page.locator("table")

    @property
    def table_rows(self):
        """Table body rows."""
        return self.table.locator("tbody tr")

    @property
    def domain_filter(self):
        """Domain multi-select combobox (labeled 'Domain')."""
        return self.page.get_by_label("Domain").first

    @property
    def domain_listbox(self):
        """Domain filter dropdown listbox opened after clicking the combobox."""
        return self.page.get_by_role("listbox")

    def domain_option(self, domain: str):
        """A specific option inside the Domain filter listbox.

        Args:
            domain: Option text to select, e.g. 'user_management'.
        """
        return self.page.get_by_role("option", name=domain)

    @property
    def event_detail_popup(self):
        """Event detail dialog opened when a row Details button is clicked."""
        return self.page.get_by_role("dialog")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    @step
    def navigate_to(self):
        """Navigate to the Activity Events admin page and wait for the table."""
        self.page.goto(self.page_url)
        self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        expect(self.heading).to_be_visible(timeout=15000)
        return self

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    @step
    def apply_domain_filter(self, domain: str):
        """Open the Domain filter and select the given domain value.

        Presses Escape afterwards to close the dropdown and trigger the filter.

        Args:
            domain: Domain value to select, e.g. 'user_management'.
        """
        self.domain_filter.click()
        expect(self.domain_listbox).to_be_visible(timeout=5000)
        self.domain_option(domain).click()
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(500)
        return self

    @step
    def click_event_row(self, index: int = 0):
        """Click the Details button in the row at the given zero-based index.

        Args:
            index: Zero-based row index.  Defaults to first row.
        """
        row = self.table_rows.nth(index)
        row.get_by_role("button").click()
        return self

    def get_first_row_identifier(self) -> str:
        """Return the 'When' timestamp text of the first visible table row.

        Used as a stable identifier to compare pages before/after pagination.
        """
        return self.table_rows.first.locator("td").first.inner_text()

    # ------------------------------------------------------------------
    # Assertions  (all in should_* methods; never in test functions)
    # ------------------------------------------------------------------

    @step
    def should_show_events_table_with_rows(self, min_count: int = 1):
        """Assert the events table is visible and has at least min_count rows.

        Args:
            min_count: Minimum expected row count.  Defaults to 1.
        """
        expect(self.table).to_be_visible(timeout=15000)
        expect(self.table_rows.nth(min_count - 1)).to_be_visible(timeout=15000)
        return self

    @step
    def should_show_only_domain_events(self, domain: str):
        """Assert every currently visible table row contains the given domain text.

        Args:
            domain: Expected domain value in every row, e.g. 'user_management'.
        """
        self.page.wait_for_timeout(500)
        rows = self.table_rows.all()
        for row in rows:
            expect(row.get_by_text(domain, exact=True)).to_be_visible(timeout=5000)
        return self

    @step
    def should_show_event_detail_popup(self):
        """Assert the event detail dialog is visible."""
        expect(self.event_detail_popup).to_be_visible(timeout=10000)
        return self

    @step
    def should_popup_contain_fields(self, fields: list[str]):
        """Assert each field label is visible inside the event detail dialog.

        Args:
            fields: List of label texts expected in the popup.
        """
        for field in fields:
            expect(
                self.event_detail_popup.get_by_text(field, exact=False)
            ).to_be_visible(timeout=5000)
        return self

    @step
    def should_show_different_first_row(self, previous_first_id: str):
        """Assert the first visible row identifier differs from a previous page.

        Call get_first_row_identifier() before clicking next-page, then pass
        the returned string here to verify pagination actually moved.

        Args:
            previous_first_id: Row identifier captured before page navigation.
        """
        self.page.wait_for_timeout(500)
        current_first_id = self.get_first_row_identifier()
        assert current_first_id != previous_first_id, (
            f"Expected first row to change after pagination, but both pages "
            f"show the same first row: {current_first_id!r}"
        )
        return self
