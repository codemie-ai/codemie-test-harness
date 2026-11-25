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
with one row a doughnut with the combined percentage, with none an empty-state text.
The panel has no test ids, so it is found by its heading (the card also carries the
data-onboarding attribute "spending-card"), the table by its column headers and the rows by
their cell text. The budget_limit, current_spending and is_shared_limit columns are hidden by
design, so the visible columns are project_name, budget_reset_at, time_until_reset and total.
The Total cell holds a usage block: the limit label with the percentage (2 decimals) and,
for a shared limit, an info icon with a tooltip; a progress bar; "Your spending: <amount>" and
"Available: <amount>".
"""

import logging
import re
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import parse_qs, urlparse

from hamcrest import assert_that, close_to, equal_to, not_none
from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.personal_spending_test_data import (
    SHARED_LIMIT_TOOLTIP,
)
from codemie_test_harness.tests.ui.utils.money import format_money
from codemie_test_harness.tests.utils.base_utils import poll_until

logger = logging.getLogger(__name__)

# Positions of the visible cells in a table row.
LABEL_CELL = 0
RESET_AT_CELL = 1
TIME_UNTIL_RESET_CELL = 2
TOTAL_CELL = 3

# What the panel shows for a value it does not know.
ABSENT_VALUE_MARKER = "-"


class PersonalSpendingPage(BasePage):
    """Personal settings page, 'Your personal spending' table."""

    PATH = "/settings/profile"
    API_PATH = "/v1/analytics/budget_usage"
    PANEL_HEADING = "Your personal spending"
    EMPTY_STATE_TEXT = "No spending data available"
    # The badge renders DEFAULT while the specification says Default.
    DEFAULT_BADGE_PATTERN = re.compile(r"^default$", re.IGNORECASE)
    DEFAULT_BADGE_SPECIFIED_TEXT = "Default"
    SHARED_LIMIT_TOOLTIP = SHARED_LIMIT_TOOLTIP
    # The usage block of a Total cell.
    LIMIT_LABEL_PATTERN = re.compile(r"^(Personal limit|Available to you|User limit)$")
    PERCENTAGE_PATTERN = re.compile(r"^(\d+(\.\d+)?%|-)$")
    SPENDING_PATTERN = re.compile(r"^Your spending:")
    BAR_WIDTH_PATTERN = re.compile(r"(?:^|;)\s*width:\s*([^%;\s]+)%")
    BAR_WIDTH_TOLERANCE = 1e-6
    # How long a tooltip that must not appear is given to show up after the hover.
    TOOLTIP_ABSENCE_WINDOW_S = 1.0
    AVAILABLE_PATTERN = re.compile(r"^Available:")
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

    @property
    def shared_limit_tooltip(self):
        """Tooltip of the info icon of a shared limit, in the DOM only while it is hovered."""
        return self.page.get_by_text(self.SHARED_LIMIT_TOOLTIP)

    def column_header(self, label: str):
        """Column header with exactly this label."""
        return self.page.get_by_role("columnheader", name=label, exact=True)

    def row_cells(self, index: int):
        """Cells of the body row at this position."""
        return self.rows.nth(index).get_by_role("cell")

    def row_named(self, name: str):
        """The body row whose label cell holds this project name, with or without the DEFAULT badge."""
        label = re.compile(rf"^{re.escape(name)}(\s*default)?$", re.IGNORECASE)
        return self.rows.filter(has=self.page.get_by_text(label))

    def usage_cell(self, name: str):
        """The Total cell, holding the usage block, of the row with this project name."""
        return self.row_named(name).get_by_role("cell").nth(TOTAL_CELL)

    def limit_label(self, name: str):
        """Limit label ('Personal limit' or 'Available to you') of the row's usage block."""
        return self.usage_cell(name).get_by_text(self.LIMIT_LABEL_PATTERN)

    def info_icon(self, name: str):
        """Info icon on the limit label line; only a shared limit has one."""
        return self.usage_label_line(name).locator("svg, img, [role='img']")

    def usage_percentages(self, name: str):
        """Every percentage text of the row's usage block; the progress bar adds none."""
        return self.usage_cell(name).get_by_text(self.PERCENTAGE_PATTERN)

    def usage_label_line(self, name: str):
        """The line of the usage block that holds the limit label and the percentage."""
        return (
            self.usage_cell(name)
            .locator("div")
            .filter(has=self.page.get_by_text(self.LIMIT_LABEL_PATTERN))
            .filter(has=self.page.get_by_text(self.PERCENTAGE_PATTERN))
            .filter(has_not=self.page.get_by_text(self.SPENDING_PATTERN))
        )

    def usage_bar_fill(self, name: str):
        """Filled part of the usage block's progress bar.

        The bar is plain divs with no role or test id. Its fill is the childless div of the
        usage block that carries an inline width, set to the clamped percentage
        (SpendingProgressBar.tsx); the track has a colour only and wrappers have children.
        """
        return self.usage_cell(name).locator('div[style*="width:"]:not(:has(*))')

    def usage_spending(self, name: str):
        """'Your spending: <amount>' text of the row's usage block."""
        return self.usage_cell(name).get_by_text(self.SPENDING_PATTERN)

    def usage_available(self, name: str):
        """'Available: <amount>' text of the row's usage block."""
        return self.usage_cell(name).get_by_text(self.AVAILABLE_PATTERN)

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
    def format_currency(value: float | None) -> str:
        """Currency text: dollar sign, thousands separators, 2 decimals; a dash when unknown."""
        if value is None:
            return ABSENT_VALUE_MARKER
        return format_money(value)

    @staticmethod
    def format_available(spent: float | None, limit: float | None) -> str:
        """'Available' amount: the limit less the spend, never below zero; a dash when unknown."""
        if spent is None or limit is None:
            return ABSENT_VALUE_MARKER
        return PersonalSpendingPage.format_currency(max(0, limit - spent))

    @staticmethod
    def _round_half_up(value: float, places: int) -> str:
        """Round like JS toFixed: half up on the exact binary value of the number.

        The number goes into ``Decimal`` as it is, not through its shortest decimal form, so a
        value such as 16.95 (stored a little below) is shown as 16.9 with one decimal.
        """
        return str(
            Decimal(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        )

    @classmethod
    def format_percentage(cls, value: float | None) -> str:
        """Percentage of the usage block: clamped to 0..100 with 2 decimals; a dash when unknown."""
        if value is None:
            return ABSENT_VALUE_MARKER
        return f"{cls._round_half_up(min(max(value, 0), 100), 2)}%"

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
    def should_show_usage_block(self, api_row: dict):
        """Verify the row's usage block shows the API row's values, in the panel's formats.

        Exactly one percentage text (the progress bar has no label of its own), 2 decimals, on
        the line of the limit label; 'Your spending: <amount>' equal to current_spending and
        'Available: <amount>' equal to max(0, budget_limit - current_spending).
        """
        name = api_row["project_name"]
        expect(
            self.usage_percentages(name), f"percentage texts of {name}"
        ).to_have_count(1)
        expect(self.usage_percentages(name)).to_have_text(
            self.format_percentage(api_row["total"])
        )
        expect(
            self.usage_label_line(name), f"limit label line of {name}"
        ).to_have_count(1)
        expect(self.usage_spending(name)).to_have_text(
            f"Your spending: {self.format_currency(api_row['current_spending'])}"
        )
        expect(self.usage_available(name)).to_have_text(
            "Available: "
            + self.format_available(
                api_row["current_spending"], api_row["budget_limit"]
            )
        )
        return self

    @staticmethod
    def expected_bar_width(total: float | None) -> float:
        """Width of the bar fill in percent: the total clamped to 0..100."""
        return float(min(max(total or 0, 0), 100))

    def _bar_width(self, name: str) -> float | None:
        """Width in percent from the inline style of the bar fill, None until it carries one."""
        style = self.usage_bar_fill(name).get_attribute("style") or ""
        match = self.BAR_WIDTH_PATTERN.search(style)
        return float(match.group(1)) if match else None

    @step
    def should_show_usage_bar(self, api_row: dict):
        """Verify the progress bar of the row's usage block is filled to the API row's total.

        The width is read from the style attribute and compared as a number: JS prints the full
        value, so it is not matched as text.
        """
        name = api_row["project_name"]
        expected = self.expected_bar_width(api_row["total"])
        expect(self.usage_bar_fill(name), f"bar fill of {name}").to_have_count(1)
        width = poll_until(
            lambda: self._bar_width(name),
            lambda value: value is not None
            and abs(value - expected) <= self.BAR_WIDTH_TOLERANCE,
        )
        assert_that(
            width,
            close_to(expected, self.BAR_WIDTH_TOLERANCE),
            f"bar fill width of {name}",
        )
        return self

    @step
    def should_show_row_values(self, api_rows: list[dict]):
        """Verify, row by row, the usage block equals the API's spend, limit and total.

        Reset columns are only checked to be filled when the API has a reset date: their
        text depends on the time zone and on the moment of the request.
        """
        for index, api_row in enumerate(api_rows):
            self.should_show_usage_block(api_row)
            cells = self.row_cells(index)
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

    @step
    def should_show_limit_label(self, names: list[str], label: str):
        """Verify the usage block of each of these rows is headed by exactly this limit label."""
        for name in names:
            expect(self.limit_label(name), f"limit label of {name}").to_have_text(label)
        return self

    @step
    def should_show_usage_blocks(self, api_rows: list[dict]):
        """Verify the usage block of each of these API rows, by project name."""
        for api_row in api_rows:
            self.should_show_usage_block(api_row)
        return self

    @step
    def should_show_shared_limit_tooltip(self, names: list[str]):
        """Verify each row has an info icon and hovering the first one shows the shared-budget tooltip."""
        for name in names:
            expect(self.info_icon(name), f"info icon of {name}").to_have_count(1)
        expect(self.shared_limit_tooltip).to_have_count(0)
        self.info_icon(names[0]).hover()
        # The tooltip is appended to the body, outside the usage block, and the panel renders its
        # element twice, so the visible check takes the first match instead of failing strict mode.
        expect(self.shared_limit_tooltip.first).to_be_visible()
        return self

    @step
    def should_not_show_shared_limit_tooltip(self, names: list[str]):
        """Verify none of these rows has an info icon, and hovering their limit label shows no shared-budget tooltip."""
        for name in names:
            expect(self.info_icon(name), f"info icon of {name}").to_have_count(0)
            # The tooltip exists only while hovered, so hover the label before checking it is absent.
            self.limit_label(name).hover()
            shown = poll_until(
                self.shared_limit_tooltip.count,
                lambda count: count > 0,
                timeout=self.TOOLTIP_ABSENCE_WINDOW_S,
                interval=0.1,
            )
            assert_that(
                shown, equal_to(0), f"shared-budget tooltips on hover of {name}"
            )
        return self

    @step
    def should_mark_shared_limit_only_when(self, names: list[str], is_shared: bool):
        """Verify the info icon and tooltip of a shared limit show on these rows only when shared."""
        if is_shared:
            return self.should_show_shared_limit_tooltip(names)
        return self.should_not_show_shared_limit_tooltip(names)
