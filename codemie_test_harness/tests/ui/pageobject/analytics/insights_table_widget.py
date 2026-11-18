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

from dataclasses import dataclass
from decimal import Decimal

from hamcrest import (
    assert_that,
    empty,
    equal_to,
    greater_than,
    has_item,
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


# What a cell shows when the row has no value, for example no cost.
NO_VALUE_TEXT = "-"


def parse_number(text: str) -> Decimal | None:
    """Parse the text of a number or currency cell: '2,712' -> 2712, '$1,234.50' -> 1234.50.

    A cell that shows no value ('-' or empty) gives None.
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
    def table(self) -> Locator:
        """The widget table, found by its count column header."""
        return self.page.get_by_role("table").filter(
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

    def _rows(self, value_column: str | None = None) -> list[InsightsRow]:
        """Read the name and the value of a column (the count by default) of every data row."""
        name_index = self._column_index(self.widget.name_column)
        count_index = self._column_index(value_column or self.widget.count_column)
        rows = []
        for row in self.body_rows.all():
            cells = row.get_by_role("cell").all_inner_texts()
            rows.append(
                InsightsRow(
                    name=cells[name_index].strip(),
                    value=parse_number(cells[count_index]),
                )
            )
        return rows

    @staticmethod
    def _expected_order(rows: list[InsightsRow]) -> list[InsightsRow]:
        """The rows by count descending, then name ascending in code point order."""
        return sorted(rows, key=lambda row: (-row.value, row.name))

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
        rows = self._rows()
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
        rows = self._rows()
        assert_that(
            [(row.name, row.value) for row in rows],
            equal_to([(row.name, row.value) for row in self._expected_order(rows)]),
            f"{self.widget.title} rows should be ordered by {self.widget.count_column} "
            f"descending, then {self.widget.name_column} ascending",
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
        costs = {row.value for row in self._costed_rows()}
        assert_that(
            len(self._costed_rows()),
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

    @step
    def should_align_footer_with_columns(self):
        """Verify every footer cell sits in the column position of its header and body cell."""
        headers = self.header_cells
        footer = self.footer_cells
        body = self.body_rows.first.get_by_role("cell")
        expect(
            footer,
            f"{self.widget.title} footer should have a cell for every column",
        ).to_have_count(headers.count())
        expect(body).to_have_count(headers.count())
        misplaced = []
        for index in range(footer.count()):
            footer_x = footer.nth(index).bounding_box()["x"]
            for source, cells in (("header", headers), ("body", body)):
                x = cells.nth(index).bounding_box()["x"]
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
            if not cell.is_visible():
                broken.append(f"'{text}' is not visible")
            elif cell.evaluate(LINE_COUNT_JS) != 1:
                broken.append(f"'{text}' wraps onto several lines")
            elif not cell.evaluate(FITS_BOX_JS):
                broken.append(f"'{text}' is clipped by its cell")
        assert_that(
            broken, empty(), f"{self.widget.title} footer totals should be fully shown"
        )
        return self
