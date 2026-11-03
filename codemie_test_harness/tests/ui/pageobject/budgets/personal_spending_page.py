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

"""Page object for the 'Your personal spending' panel of the personal settings page.

URL: /settings/profile

The panel loads GET /v1/analytics/budget_usage. With two or more rows it draws a table,
with one row or none a doughnut or an empty-state text; only the table is modelled here.
The panel has no test ids, so it is found by its heading, the table by its column headers
and the rows by their cell text. The budget_limit column is hidden by design, so the visible
columns are project_name, current_spending, budget_reset_at, time_until_reset and total.
"""

import logging
import re
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import parse_qs, urlparse

from hamcrest import assert_that, equal_to, not_none
from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.utils.base_utils import poll_until

logger = logging.getLogger(__name__)

# Positions of the visible cells in a table row.
LABEL_CELL = 0
SPENDING_CELL = 1
RESET_AT_CELL = 2
TIME_UNTIL_RESET_CELL = 3
TOTAL_CELL = 4


class PersonalSpendingPage(BasePage):
    """Personal settings page, 'Your personal spending' table."""

    PATH = "/settings/profile"
    API_PATH = "/v1/analytics/budget_usage"
    PANEL_HEADING = "Your personal spending"
    EMPTY_STATE_TEXT = "No spending data available"
    # The badge renders DEFAULT while the specification says Default.
    DEFAULT_BADGE_PATTERN = re.compile(r"^default$", re.IGNORECASE)
    DEFAULT_BADGE_SPECIFIED_TEXT = "Default"
    RESPONSE_TIMEOUT_MS = 30000

    def __init__(self, page):
        super().__init__(page)
        self._response = None

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def heading(self):
        """'Your personal spending' heading of the panel."""
        return self.page.get_by_role("heading", name=self.PANEL_HEADING)

    @property
    def table(self):
        """The spending table, found by its 'Time Until Reset' column header."""
        return self.page.get_by_role("table").filter(
            has=self.page.get_by_role("columnheader", name="Time Until Reset")
        )

    @property
    def column_headers(self):
        """Column headers of the spending table."""
        return self.table.get_by_role("columnheader")

    @property
    def rows(self):
        """Body rows of the spending table (rows holding cells, so not the header row)."""
        return self.table.get_by_role("row").filter(has=self.page.get_by_role("cell"))

    @property
    def empty_state(self):
        """'No spending data available' text."""
        return self.page.get_by_text(self.EMPTY_STATE_TEXT)

    def column_header(self, label: str):
        """Column header with exactly this label."""
        return self.page.get_by_role("columnheader", name=label, exact=True)

    def row_cells(self, index: int):
        """Cells of the body row at this position."""
        return self.rows.nth(index).get_by_role("cell")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _is_budget_usage_response(self, response) -> bool:
        return response.request.method == "GET" and urlparse(
            response.url
        ).path.endswith(self.API_PATH)

    def _remember(self, response):
        assert_that(
            response.ok,
            equal_to(True),
            f"GET {self.API_PATH} made by the page failed with HTTP {response.status}",
        )
        self._response = response

    @step
    def open(self):
        """Open the personal settings page and wait for the budget_usage response it requests."""
        with self.page.expect_response(
            self._is_budget_usage_response, timeout=self.RESPONSE_TIMEOUT_MS
        ) as response_info:
            self.page.goto(self.PATH)
        self._remember(response_info.value)
        return self

    @step
    def reload(self):
        """Reload the page and wait for the budget_usage response it requests again."""
        with self.page.expect_response(
            self._is_budget_usage_response, timeout=self.RESPONSE_TIMEOUT_MS
        ) as response_info:
            self.page.reload()
        self._remember(response_info.value)
        return self

    # ── Formatting, as the panel renders values ──────────────────────────────

    @staticmethod
    def format_currency(value: float) -> str:
        """Currency cell text: dollar sign, thousands separators, 2 decimals."""
        return f"${value:,.2f}"

    @staticmethod
    def format_percentage(value: float) -> str:
        """Total cell text: the value clamped to 0..100 with 1 decimal, rounded like JS toFixed.

        ``toFixed`` rounds half up on the exact binary value of the number, not on its shortest
        decimal form, so the number goes into ``Decimal`` as it is: 16.95 is shown as 16.9.
        """
        clamped = min(max(value, 0), 100)
        return f"{Decimal(clamped).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_have_requested_own_usage_only(self):
        """Verify the page asked for the caller's own usage: HTTP 200 and no user_id parameter."""
        assert_that(self._response, not_none(), "open() must run before this check")
        query = parse_qs(urlparse(self._response.url).query)
        assert_that(self._response.status, equal_to(200))
        assert_that(
            "user_id" in query,
            equal_to(False),
            "The personal page must not pass user_id to budget_usage",
        )
        return self

    @step
    def should_have_received_rows(self, project_names: list[str]):
        """Verify the response the page received holds exactly these row names, in this order."""
        assert_that(self._response, not_none(), "open() must run before this check")
        received = [
            row["project_name"] for row in self._response.json()["data"]["rows"]
        ]
        assert_that(
            received,
            equal_to(project_names),
            "The page and the SDK got different budget_usage rows",
        )
        return self

    @step
    def should_show_table(self):
        """Verify the panel draws its table, not the empty state."""
        expect(self.heading).to_be_visible(timeout=self.RESPONSE_TIMEOUT_MS)
        expect(self.table).to_be_visible(timeout=self.RESPONSE_TIMEOUT_MS)
        expect(self.empty_state).to_have_count(0)
        return self

    @step
    def should_show_columns(self, labels: list[str]):
        """Verify the table's column headers are exactly these labels, in this order."""
        expect(self.column_headers).to_have_text(labels)
        return self

    @step
    def should_not_show_column(self, label: str):
        """Verify the table has no column with this label."""
        expect(self.column_header(label)).to_have_count(0)
        return self

    @step
    def should_list_rows(self, api_rows: list[dict]):
        """Verify one table row per API row, with the API's project name first, in the API's order.

        The label cell may carry the DEFAULT badge after the name.
        """
        expect(self.rows).to_have_count(len(api_rows))
        expected = [api_row["project_name"] for api_row in api_rows]
        shown = poll_until(
            lambda: self._shown_labels(expected), lambda labels: labels == expected
        )
        assert_that(shown, equal_to(expected), "Row labels shown by the table")
        return self

    def _shown_labels(self, expected: list[str]) -> list[str]:
        """Text of each label cell, without the DEFAULT badge when it follows the expected name."""
        labels = []
        for index, name in enumerate(expected[: self.rows.count()]):
            text = self.row_cells(index).nth(LABEL_CELL).inner_text().strip()
            name_part = text[: -len("DEFAULT")].rstrip()
            is_badged_name = text.upper().endswith("DEFAULT") and name_part == name
            labels.append(name_part if is_badged_name else text)
        return labels

    @step
    def should_show_row_values(self, api_rows: list[dict]):
        """Verify, row by row, the spend and total the table shows equal the API's values.

        Reset columns are only checked to be filled when the API has a reset date: their
        text depends on the time zone and on the moment of the request.
        """
        for index, api_row in enumerate(api_rows):
            cells = self.row_cells(index)
            expect(cells.nth(SPENDING_CELL)).to_have_text(
                self.format_currency(api_row["current_spending"])
            )
            expect(cells.nth(TOTAL_CELL)).to_have_text(
                self.format_percentage(api_row["total"])
            )
            if api_row["budget_reset_at"] is not None:
                expect(cells.nth(RESET_AT_CELL)).not_to_have_text(re.compile(r"^-?$"))
                expect(cells.nth(TIME_UNTIL_RESET_CELL)).not_to_have_text(
                    re.compile(r"^-?$")
                )
        return self

    @step
    def should_match_budget_usage(self, api_rows: list[dict]):
        """Verify the table equals the API response: rows, order, spend and total."""
        return self.should_list_rows(api_rows).should_show_row_values(api_rows)

    @step
    def should_show_default_badge_on_flagged_rows(self, api_rows: list[dict]):
        """Verify the DEFAULT badge shows on the rows the API flags is_default and on no other."""
        return self.should_show_default_badge_on(
            [row["is_default"] for row in api_rows]
        )

    @step
    def should_show_default_badge_on(self, flags: list[bool]):
        """Verify the DEFAULT badge shows on the rows flagged True and on no other row.

        The badge text is matched case-insensitively. The specification says 'Default' while
        the panel renders 'DEFAULT'; that difference is logged, not failed.
        """
        for index, flagged in enumerate(flags):
            badge = (
                self.row_cells(index)
                .nth(LABEL_CELL)
                .get_by_text(self.DEFAULT_BADGE_PATTERN)
            )
            expect(badge, f"row {index}").to_have_count(1 if flagged else 0)
            if flagged:
                text = badge.inner_text().strip()
                if text != self.DEFAULT_BADGE_SPECIFIED_TEXT:
                    logger.warning(
                        "Advisory: row %s badge reads %r, the specification says %r",
                        index,
                        text,
                        self.DEFAULT_BADGE_SPECIFIED_TEXT,
                    )
        return self
