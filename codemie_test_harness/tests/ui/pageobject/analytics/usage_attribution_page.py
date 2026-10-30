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

"""Page object for the Analytics > Usage Attribution tab.

URL: /analytics?tab=usageAttribution

The tab is shown to admins, maintainers and auditors when ``features:usageAttribution`` is on.
It has the sub-tabs Overview | People | How It Works (a PrimeReact ``SelectButton``: buttons with
``aria-pressed``). Locators follow the codemie-ui ``UsageAttributionTab``, ``OverviewView``,
``HowItWorksView``, ``SummaryTiles``, ``Tile`` and ``AnalyticsWidget`` components: a widget is a
box whose title is a level-3 heading, a tile label is a paragraph followed by its value.
"""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.analytics.usage_attribution_table import (
    UsageAttributionTable,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.usage_attribution_test_data import (
    HOW_IT_WORKS_SECTIONS,
    HOW_IT_WORKS_TILES,
    MONEY_WIDGETS,
    BREAKDOWN_WIDGETS,
    SUMMARY_TILES,
    SubTab,
    TableSpec,
)


class UsageAttributionPage(BasePage):
    """Usage Attribution tab: sub-tabs, Overview, People and How It Works views."""

    PATH = "/analytics?tab=usageAttribution"
    # Widgets read the shared analysis, which a cold cache computes in up to two minutes.
    ANALYSIS_TIMEOUT = 180_000
    # A money amount as the tab formats it: $1,234, or $0.45 under one dollar, with a leading minus.
    MONEY_AMOUNT = re.compile(r"^-?\$[\d,]+(\.\d{2})?$")
    COMPUTED_LINE = re.compile(r"^Computed .+ in .+")

    # ── Locators ─────────────────────────────────────────────────────────────────

    @property
    def sub_tab_bar(self) -> Locator:
        """The sub-tab group: a PrimeReact SelectButton, a nameless role=group around its buttons.

        Table headers and selects elsewhere on the tab are buttons too ('People' is also a column),
        so the sub-tab buttons are looked up inside the innermost group that holds all three.
        """
        bar = self.page.get_by_role("group")
        for sub_tab in SubTab:
            bar = bar.filter(
                has=self.page.get_by_role("button", name=sub_tab, exact=True)
            )
        return bar.filter(has_not=self.page.get_by_role("group"))

    def sub_tab_button(self, sub_tab: SubTab) -> Locator:
        """Sub-tab button (role=button, aria-label, aria-pressed) by its exact label."""
        return self.sub_tab_bar.get_by_role("button", name=sub_tab, exact=True)

    def widget(self, title: str) -> Locator:
        """The box of a widget: the third ancestor of its title (title block, header, box)."""
        return self.widget_heading(title).locator("xpath=ancestor::div[3]")

    def widget_heading(self, title: str) -> Locator:
        """Title of a widget by its exact text (a level-3 heading)."""
        return self.page.get_by_role("heading", name=title, exact=True, level=3)

    def tile_label(self, widget_title: str, label: str) -> Locator:
        """Label of a metric tile inside the widget with the given title (the label is a paragraph)."""
        return (
            self.widget(widget_title)
            .locator("p")
            .filter(has_text=re.compile(rf"^{re.escape(label)}$"))
        )

    def tile_value(self, widget_title: str, label: str) -> Locator:
        """Value of a metric tile: the paragraph right after its label.

        A tile that is pending or failed shows another element instead, so this finds nothing then.
        """
        return self.tile_label(widget_title, label).locator(
            "xpath=following-sibling::p"
        )

    @property
    def computed_line(self) -> Locator:
        """'Computed <time> in <duration>' pill of the 'This Analysis' widget."""
        return self.widget("This Analysis").get_by_text(self.COMPUTED_LINE)

    # ── Actions ──────────────────────────────────────────────────────────────────

    @step
    def open_sub_tab(self, sub_tab: SubTab):
        """Open a sub-tab and wait until it is the pressed one."""
        button = self.sub_tab_button(sub_tab)
        button.click()
        expect(button).to_have_attribute("aria-pressed", "true", timeout=15_000)
        return self

    @step
    def open_table(self, spec: TableSpec) -> UsageAttributionTable:
        """Open the sub-tab that holds a table and return the table's page object."""
        self.open_sub_tab(spec.sub_tab)
        return UsageAttributionTable(self.page, spec)

    # ── Assertions ───────────────────────────────────────────────────────────────

    @step
    def should_have_sub_tabs(self):
        """Assert the sub-tabs are shown and Overview is the one open by default."""
        for sub_tab in SubTab:
            expect(
                self.sub_tab_button(sub_tab),
                f"Sub-tab '{sub_tab}' should be visible",
            ).to_be_visible(timeout=15_000)
        expect(
            self.sub_tab_button(SubTab.OVERVIEW),
            "Overview should be the sub-tab open by default",
        ).to_have_attribute("aria-pressed", "true")
        return self

    @step
    def should_show_summary_tiles(self):
        """Assert the eight Summary tiles of the Overview are shown with their shipped labels."""
        for label in SUMMARY_TILES:
            expect(
                self.tile_label("Summary", label),
                f"Summary tile '{label}' should be visible",
            ).to_be_visible(timeout=self.ANALYSIS_TIMEOUT)
        return self

    @step
    def should_show_summary_amounts(self):
        """Assert every Summary tile resolved to a money amount (not pending, not an error)."""
        for label in SUMMARY_TILES:
            expect(
                self.tile_value("Summary", label),
                f"Summary tile '{label}' should show an amount",
            ).to_have_text(self.MONEY_AMOUNT, timeout=self.ANALYSIS_TIMEOUT)
        return self

    @step
    def should_show_money_widgets(self):
        """Assert the money widgets of the Overview are shown."""
        for title in MONEY_WIDGETS:
            expect(
                self.widget_heading(title), f"Widget '{title}' should be visible"
            ).to_be_visible(timeout=self.ANALYSIS_TIMEOUT)
        return self

    @step
    def should_show_breakdown_widgets(self):
        """Assert the personal-budget spend widgets by country and by job title group are shown."""
        for title in BREAKDOWN_WIDGETS:
            expect(
                self.widget_heading(title), f"Widget '{title}' should be visible"
            ).to_be_visible(timeout=self.ANALYSIS_TIMEOUT)
        return self

    @step
    def should_show_how_it_works(self):
        """Assert the How It Works tiles and sections, and the computed time and duration."""
        self.open_sub_tab(SubTab.HOW_IT_WORKS)
        for label in HOW_IT_WORKS_TILES:
            expect(
                self.tile_label("This Analysis", label),
                f"How It Works tile '{label}' should be visible",
            ).to_be_visible(timeout=self.ANALYSIS_TIMEOUT)
        for title in HOW_IT_WORKS_SECTIONS:
            expect(
                self.widget_heading(title),
                f"How It Works section '{title}' should be visible",
            ).to_be_visible(timeout=self.ANALYSIS_TIMEOUT)
        expect(
            self.computed_line,
            "The computed time and duration of the analysis should be shown",
        ).to_be_visible(timeout=self.ANALYSIS_TIMEOUT)
        return self
