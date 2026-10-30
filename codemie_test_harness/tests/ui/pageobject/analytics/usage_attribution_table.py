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

"""Page object for the tables of Analytics > Usage Attribution.

Shared projects, repository groups and people are the same ``UaTable`` of codemie-ui: a table
named by an aria-label, a search box and a select above it, a name button in the first cell of
every row (a click anywhere in the row opens its popup) and a 'No data available' row when the
list is empty. The table spec carries what differs: labels, placeholder, select and endpoint.
"""

import re

from playwright.sync_api import Locator
from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.analytics.usage_attribution_popup import (
    UsageAttributionPopup,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.usage_attribution_test_data import (
    TableSpec,
)


class UsageAttributionTable(BasePage):
    """One table of the Usage Attribution tab, with its search box and scope or filter select."""

    API_PATH = "/v1/analytics/usage-attribution/"
    LOADING_TEXT = "Loading data..."
    # The tables read the shared analysis, which a cold cache computes in up to two minutes.
    ANALYSIS_TIMEOUT = 180_000
    ROW_TIMEOUT = 5_000

    def __init__(self, page, spec: TableSpec):
        super().__init__(page)
        self.spec = spec

    # ── Locators ─────────────────────────────────────────────────────────────────

    @property
    def table(self) -> Locator:
        """The table, found by its aria-label."""
        return self.page.get_by_role("table", name=self.spec.aria_label, exact=True)

    def column_header(self, label: str) -> Locator:
        """Column header by its exact label (matched on the header text, which holds a sort button)."""
        return self.table.get_by_role("columnheader").filter(
            has_text=re.compile(rf"^{re.escape(label)}$")
        )

    @property
    def search_box(self) -> Locator:
        """Search field above the table."""
        return self.page.get_by_placeholder(self.spec.search_placeholder, exact=True)

    @property
    def options_select(self) -> Locator:
        """Select that switches the scope (shared projects, repository groups) or the filter (people).

        A PrimeReact Dropdown exposes its aria-label on the trigger, a role=button element.
        """
        return self.page.get_by_role(
            "button", name=self.spec.options_select, exact=True
        )

    @property
    def options_panel(self) -> Locator:
        """The open dropdown's list of options (the closed dropdown renders none).

        Scoping to it leaves out the hidden native select, whose options repeat the selected label.
        """
        return self.page.get_by_role("listbox")

    def option(self, pattern: str) -> Locator:
        """Option of the open dropdown whose label matches the regular expression."""
        return self.options_panel.get_by_role("option", name=re.compile(pattern))

    @property
    def loading_overlays(self) -> Locator:
        """First-load overlays of the widgets on the page."""
        return self.page.get_by_text(self.LOADING_TEXT, exact=True)

    @property
    def row_name_buttons(self) -> Locator:
        """Name button in the first cell of each data row (the 'No data available' row has none)."""
        return self.table.locator("tbody tr td:first-child").get_by_role("button")

    # ── Actions ──────────────────────────────────────────────────────────────────

    @step
    def wait_until_loaded(self):
        """Wait until the table is rendered and no widget on the page is still loading."""
        expect(
            self.table, f"Table '{self.spec.aria_label}' should be rendered"
        ).to_be_visible(timeout=self.ANALYSIS_TIMEOUT)
        expect(self.loading_overlays).to_have_count(0, timeout=self.ANALYSIS_TIMEOUT)
        return self

    @step
    def show_all_rows(self):
        """Pick the select option that lists every row and wait for the list the page asks for."""
        self.wait_until_loaded()
        with self.page.expect_response(
            lambda response: self.API_PATH + self.spec.endpoint in response.url
            and self.spec.all_rows_query in response.url,
            timeout=self.ANALYSIS_TIMEOUT,
        ):
            self.options_select.click()
            self.option(self.spec.all_rows_option).click()
        return self

    @step
    def open_first_row(self, header_prefix: str) -> UsageAttributionPopup:
        """Open the popup of the first row by its name button.

        Args:
            header_prefix: Text the popup shows before the row name in its header.
        """
        name_button = self.row_name_buttons.first
        row_name = name_button.inner_text().strip()
        name_button.click()
        return UsageAttributionPopup(self.page, header_prefix + row_name)

    # ── Assertions ───────────────────────────────────────────────────────────────

    @step
    def should_have_rows(self):
        """Assert the loaded table lists at least one row."""
        self.wait_until_loaded()
        expect(
            self.row_name_buttons.first,
            f"The '{self.spec.aria_label}' table has no rows on this environment: "
            "seed data is required for this test",
        ).to_be_visible(timeout=self.ROW_TIMEOUT)
        return self

    @step
    def should_have_columns(self):
        """Assert the table shows the shipped column labels."""
        self.wait_until_loaded()
        for label in self.spec.columns:
            expect(
                self.column_header(label),
                f"Column '{label}' of '{self.spec.aria_label}' should be visible",
            ).to_be_visible()
        return self

    @step
    def should_have_search_box(self):
        """Assert the search field above the table shows its shipped placeholder."""
        expect(
            self.search_box,
            f"Search field '{self.spec.search_placeholder}' should be visible",
        ).to_be_visible(timeout=self.ANALYSIS_TIMEOUT)
        return self

    @step
    def should_offer_options(self):
        """Open the scope or filter select and assert it offers the shipped options, then close it."""
        self.wait_until_loaded()
        self.options_select.click()
        for pattern in self.spec.option_patterns:
            expect(
                self.option(pattern),
                f"Select '{self.spec.options_select}' should offer an option like {pattern}",
            ).to_be_visible(timeout=self.ANALYSIS_TIMEOUT)
        self.page.keyboard.press("Escape")
        return self
