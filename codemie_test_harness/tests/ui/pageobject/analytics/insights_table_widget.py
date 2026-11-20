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

"""Page object for a table widget of Analytics > Insights (the default tab).

Each widget is a card with a heading and a table: a header row, a body of data rows and a footer row
of totals. The widgets load lazily, when they are scrolled into view. The Expand widget dialog shows
a second copy of the table, so the dialog stays closed: a table locator would match both copies.
"""

import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from hamcrest import (
    assert_that,
    empty,
    equal_to,
    greater_than,
    has_item,
    is_in,
    not_,
    not_none,
)
from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.analytics_test_data import (
    INSIGHTS_FOOTER_LABEL,
    InsightsTable,
)

# Distinct vertical positions of the text lines inside an element: 1 for text on a single line.
LINE_COUNT_JS = """el => {
    const range = document.createRange();
    range.selectNodeContents(el);
    const tops = Array.from(range.getClientRects())
        .filter(rect => rect.width > 0)
        .map(rect => Math.round(rect.top));
    return new Set(tops).size;
}"""
# True when the content of the element fits its box without being clipped.
FITS_BOX_JS = "el => el.scrollWidth <= el.clientWidth"
# Columns of the same table may differ by sub-pixel rounding only.
POSITION_TOLERANCE_PX = 1
# The table body is read again until two reads in a row agree.
SETTLE_INTERVAL_MS = 500
# Names of rows with an equal count are ordered by the code point or ignoring the case; the page
# is correct with either, so the order check accepts both.
NAME_ORDER_KEYS = (str, str.casefold)


# What a cell shows when the row has no value, for example no cost.
NO_VALUE_TEXT = "-"


def parse_number(text: str) -> Decimal | None:
    """Parse the text of a number or currency cell: '2,712' -> 2712, '$1,234.50' -> 1234.50.

    A cell that shows no value ('-' or empty) gives None. Text that is not a number raises
    ``InvalidOperation``.
    """
    cleaned = text.strip().replace("$", "").replace(",", "")
    if cleaned in ("", NO_VALUE_TEXT):
        return None
    return Decimal(cleaned)


@dataclass(frozen=True)
class InsightsRow:
    """A data row of an Insights table: the name and the number the rows are ordered by.

    ``value`` is None when the cell shows no value.
    """

    name: str
    value: Decimal | None


class InsightsTableWidget(BasePage):
    """One table widget of the Insights tab, found by its heading and its count column."""

    ROWS_TIMEOUT = 30_000

    def __init__(self, page, widget: InsightsTable):
        super().__init__(page)
        self.widget = widget

    # ── Locators ─────────────────────────────────────────────────────────────────

    @property
    def heading(self) -> Locator:
        """The widget heading (the side navigation holds a span with the same text)."""
        return self.page.get_by_role(
            "heading", name=self.widget.title, exact=True, level=3
        )

    @property
    def card(self) -> Locator:
        """The widget card: the nearest ancestor of the heading that holds a table."""
        return self.heading.locator("xpath=ancestor::*[.//table][1]")

    @property
    def table(self) -> Locator:
        """The widget table, found in its card by its count column header.

        The card scope tells apart widgets that share a count column: Invocations heads both
        Top Assistants Usage and Top Workflow Usage.
        """
        return self.card.get_by_role("table").filter(
            has=self.page.get_by_role(
                "columnheader", name=self.widget.count_column, exact=True
            )
        )

    @property
    def header_cells(self) -> Locator:
        """Column headers of the table."""
        return self.table.get_by_role("columnheader")

    @property
    def body_rows(self) -> Locator:
        """Data rows of the table, without the totals footer."""
        return self.table.locator("tbody").get_by_role("row")

    @property
    def footer_row(self) -> Locator:
        """The totals footer row of the table."""
        return self.table.locator("tfoot").get_by_role("row")

    @property
    def footer_cells(self) -> Locator:
        """Cells of the totals footer row."""
        return self.footer_row.get_by_role("cell")

    # ── Reading ──────────────────────────────────────────────────────────────────

    def _column_index(self, column: str) -> int:
        """Position of a column in the header row."""
        columns = [text.strip() for text in self.header_cells.all_inner_texts()]
        assert_that(
            columns,
            has_item(column),
            f"{self.widget.title} should have a {column} column",
        )
        return columns.index(column)

    def _body_cells(self) -> list[list[str]]:
        """The text of the cells of every data row, as shown now."""
        return [
            [text.strip() for text in row.get_by_role("cell").all_inner_texts()]
            for row in self.body_rows.all()
        ]

    def _settled_body_cells(self, needed_cells: int) -> list[list[str]]:
        """The cells of the data rows once the table stops changing.

        Reads the body until two reads in a row agree and every row has ``needed_cells`` cells
        (a placeholder row, such as 'No data', has fewer), or until the timeout. The last read is
        returned either way, so the caller's assertions report what the table showed.
        """
        deadline = time.monotonic() + self.ROWS_TIMEOUT / 1000
        previous = None
        while True:
            current = self._body_cells()
            if (
                current
                and current == previous
                and all(len(cells) >= needed_cells for cells in current)
            ):
                return current
            if time.monotonic() >= deadline:
                return current
            previous = current
            self.page.wait_for_timeout(SETTLE_INTERVAL_MS)

    def _rows(self, value_column: str | None = None) -> list[InsightsRow]:
        """Read the name and the value of a column (the count by default) of every data row."""
        value_column = value_column or self.widget.count_column
        name_index = self._column_index(self.widget.name_column)
        value_index = self._column_index(value_column)
        needed_cells = max(name_index, value_index) + 1
        body = self._settled_body_cells(needed_cells)
        assert_that(body, not_(empty()), f"{self.widget.title} should list rows")
        short = [cells for cells in body if len(cells) < needed_cells]
        assert_that(
            short,
            empty(),
            f"{self.widget.title} rows should have a {self.widget.name_column} and a "
            f"{value_column} cell",
        )
        rows = []
        for cells in body:
            name, text = cells[name_index], cells[value_index]
            try:
                value = parse_number(text)
            except InvalidOperation:
                raise AssertionError(
                    f"{self.widget.title}: the {value_column} cell of row '{name}' "
                    f"is not a number: '{text}'"
                ) from None
            rows.append(InsightsRow(name=name, value=value))
        return rows

    def _counted_rows(self) -> list[InsightsRow]:
        """Rows with a count: a count cell showing no value fails with the names of those rows."""
        rows = self._rows()
        blank = [row.name for row in rows if row.value is None]
        assert_that(
            blank,
            empty(),
            f"{self.widget.title} rows should show a {self.widget.count_column}",
        )
        return rows

    @staticmethod
    def _expected_order(rows: list[InsightsRow], name_key) -> list[InsightsRow]:
        """The rows by count descending, then name ascending, compared with ``name_key``."""
        return sorted(rows, key=lambda row: (-row.value, name_key(row.name)))

    # ── Actions ──────────────────────────────────────────────────────────────────

    @step
    def open(self):
        """Scroll to the widget and wait for its rows and its totals footer to load."""
        self.heading.scroll_into_view_if_needed()
        expect(
            self.body_rows.first,
            f"{self.widget.title} should load its rows",
        ).to_be_visible(timeout=self.ROWS_TIMEOUT)
        self.footer_row.scroll_into_view_if_needed()
        expect(
            self.footer_row, f"{self.widget.title} should show its totals footer"
        ).to_be_visible()
        return self

    # ── Verifications ────────────────────────────────────────────────────────────

    @step
    def should_list_rows_with_different_counts(self):
        """Verify the widget lists several rows whose counts differ.

        Without that any row order is a correct one and the order check proves nothing.
        """
        rows = self._counted_rows()
        assert_that(
            len(rows), greater_than(1), f"{self.widget.title} should list several rows"
        )
        assert_that(
            len({row.value for row in rows}),
            greater_than(1),
            f"{self.widget.title} rows should not all have the same {self.widget.count_column}",
        )
        return self

    @step
    def should_order_rows_by_count_then_name(self):
        """Verify the rows are ordered by the count descending, then by the name ascending."""
        rows = self._counted_rows()
        shown = [(row.name, row.value) for row in rows]
        expected_orders = [
            [(row.name, row.value) for row in self._expected_order(rows, name_key)]
            for name_key in NAME_ORDER_KEYS
        ]
        assert_that(
            shown,
            is_in(expected_orders),
            f"{self.widget.title} rows should be ordered by {self.widget.count_column} "
            f"descending, then {self.widget.name_column} ascending "
            "(by code point or ignoring the case)",
        )
        return self

    def _costed_rows(self) -> list[InsightsRow]:
        """Rows that show a cost, in the order shown; the rows showing '-' are left out.

        A row without a cost has no place in a cost order, so where it sits among the costed rows
        is not asserted.
        """
        assert_that(
            self.widget.cost_column,
            not_none(),
            f"{self.widget.title} has no cost column",
        )
        return [
            row for row in self._rows(self.widget.cost_column) if row.value is not None
        ]

    @step
    def should_list_rows_with_different_costs(self):
        """Verify at least two rows show a cost and the costs differ.

        Without that any row order is a correct one and the cost order check proves nothing.
        """
        rows = self._costed_rows()
        costs = {row.value for row in rows}
        assert_that(
            len(rows),
            greater_than(1),
            f"{self.widget.title} should list several rows with a {self.widget.cost_column}",
        )
        assert_that(
            len(costs),
            greater_than(1),
            f"{self.widget.title} rows should not all have the same {self.widget.cost_column}",
        )
        return self

    @step
    def should_order_rows_by_cost_descending(self):
        """Verify the rows that show a cost are ordered by that cost descending.

        Rows with an equal cost are not ordered against each other: the expected order is a stable
        sort by cost, which keeps the shown order of equal-cost rows. Rows showing '-' are left out.
        """
        rows = self._costed_rows()
        expected = sorted(rows, key=lambda row: -row.value)
        assert_that(
            [(row.name, row.value) for row in rows],
            equal_to([(row.name, row.value) for row in expected]),
            f"{self.widget.title} rows should be ordered by {self.widget.cost_column} "
            "descending (rows with an equal cost in any order)",
        )
        return self

    @step
    def should_label_footer_total(self):
        """Verify the first cell of the totals footer reads Total."""
        expect(
            self.footer_cells.first,
            f"{self.widget.title} footer should start with its label",
        ).to_have_text(INSIGHTS_FOOTER_LABEL)
        return self

    def _left_edge(self, cell: Locator, description: str) -> float:
        """The x position of a rendered cell; a cell that is not rendered fails the test."""
        box = cell.bounding_box()
        assert_that(
            box,
            not_none(),
            f"{self.widget.title} {description} should be rendered",
        )
        return box["x"]

    @step
    def should_align_footer_with_columns(self):
        """Verify every footer cell sits in the column position of its header and body cell."""
        headers = self.header_cells
        footer = self.footer_cells
        body = self.body_rows.first.get_by_role("cell")
        expect(
            headers.first, f"{self.widget.title} should show its column headers"
        ).to_be_visible()
        column_count = headers.count()
        expect(
            footer,
            f"{self.widget.title} footer should have a cell for every column",
        ).to_have_count(column_count)
        expect(
            body,
            f"{self.widget.title} first row should have a cell for every column",
        ).to_have_count(column_count)
        misplaced = []
        for index in range(column_count):
            footer_x = self._left_edge(footer.nth(index), f"footer cell {index}")
            for source, cells in (("header", headers), ("body", body)):
                x = self._left_edge(cells.nth(index), f"{source} cell {index}")
                if abs(footer_x - x) > POSITION_TOLERANCE_PX:
                    misplaced.append(
                        f"column {index}: footer at x={footer_x}, {source} at x={x}"
                    )
        assert_that(
            misplaced,
            empty(),
            f"{self.widget.title} footer cells should sit in the column of the table body",
        )
        return self

    @staticmethod
    def _is_number(text: str) -> bool:
        """True when the text of a cell is a number or an amount."""
        try:
            return parse_number(text) is not None
        except InvalidOperation:
            return False

    @step
    def should_show_numeric_totals_on_one_line(self):
        """Verify every total in the footer is on one line and fully visible."""
        totals = [
            cell
            for cell in self.footer_cells.all()[1:]
            if cell.inner_text().strip() != ""
        ]
        assert_that(
            len(totals),
            greater_than(0),
            f"{self.widget.title} footer should show numeric totals",
        )
        broken = []
        for cell in totals:
            text = cell.inner_text().strip()
            if not self._is_number(text):
                broken.append(f"'{text}' is not a number")
            elif not cell.is_visible():
                broken.append(f"'{text}' is not visible")
            elif cell.evaluate(LINE_COUNT_JS) != 1:
                broken.append(f"'{text}' wraps onto several lines")
            elif not cell.evaluate(FITS_BOX_JS):
                broken.append(f"'{text}' is clipped by its cell")
        assert_that(
            broken, empty(), f"{self.widget.title} footer totals should be fully shown"
        )
        return self
