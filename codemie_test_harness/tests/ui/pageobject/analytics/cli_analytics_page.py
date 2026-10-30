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

"""Page object for the Analytics > CLI Analytics dashboard.

URL: /analytics?tab=cliAnalytics

CLI Analytics is a top-level Analytics tab with its own button-based navigation:
Overview | Users | Repositories | Tools & Models | Activity | Efficiency | Cost |
Sessions.

Locators verified against the live UI on 2026-10-12 and the
codemie-ui ``CliAnalyticsTab`` / ``AnalyticsWidget`` components: the top-level
tabpanel holds the section buttons and a nested ``role="tabpanel"`` that is
re-mounted on every section switch, which re-fetches that section's data.
"""

import re
from contextlib import ExitStack
from typing import NamedTuple
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.analytics.cli_analytics_session_modal import (
    CLIAnalyticsSessionModal,
)
from codemie_test_harness.tests.ui.pageobject.analytics.cli_analytics_user_modal import (
    CLIAnalyticsUserModal,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.analytics_test_data import (
    CLIAnalyticsSection,
)


class SectionSpec(NamedTuple):
    """What proves a CLI Analytics section has rendered."""

    marker_widget: str
    """Title of a widget that is always rendered by this section and no other."""
    endpoints: tuple[str, ...]
    """``/v1/analytics/cli-analytics/<endpoint>`` requests fired when the section mounts."""


class CLIAnalyticsPage(BasePage):
    """CLI Analytics dashboard and its section navigation."""

    PATH = "/analytics?tab=cliAnalytics"
    TAB_NAME = "CLI Analytics"
    API_PATH = "/v1/analytics/cli-analytics/"
    SECTIONS = {
        CLIAnalyticsSection.OVERVIEW: SectionSpec(
            "Net lines over time", ("overview", "repositories")
        ),
        CLIAnalyticsSection.USERS: SectionSpec(
            "Per-user detail", ("users", "user-charts")
        ),
        CLIAnalyticsSection.REPOSITORIES: SectionSpec(
            "Repositories", ("repositories",)
        ),
        CLIAnalyticsSection.TOOLS_AND_MODELS: SectionSpec(
            "Most Used Tools", ("tools",)
        ),
        CLIAnalyticsSection.ACTIVITY: SectionSpec("By weekday", ("activity",)),
        CLIAnalyticsSection.EFFICIENCY: SectionSpec(
            "Context Bloat", ("efficiency", "sessions")
        ),
        CLIAnalyticsSection.COST: SectionSpec("Cost by model", ("cost", "sessions")),
        CLIAnalyticsSection.SESSIONS: SectionSpec(
            "Sessions", ("sessions", "frameworks")
        ),
    }
    DEFAULT_SECTION = CLIAnalyticsSection.OVERVIEW
    # The section buttons expose no aria-pressed/aria-selected; the active one is
    # only distinguishable by this background class.
    ACTIVE_SECTION_CLASS = re.compile(r"\bbg-surface-interactive-active\b")
    SESSION_DETAIL_PATH = re.compile(re.escape(API_PATH) + r"sessions/[^/]+$")
    EMPTY_TABLE_TEXT = "No data available"
    # Em dash (U+2014): rendered when tool_calls = 0, meaning "no data".
    EM_DASH = "—"

    # ── Locators ────────────────────────────────────────────────────────────────

    @property
    def tab(self) -> Locator:
        """Top-level 'CLI Analytics' tab."""
        return self.page.get_by_role("tab", name=self.TAB_NAME, exact=True)

    @property
    def panel(self) -> Locator:
        """Top-level tabpanel of CLI Analytics (the one that nests a section tabpanel)."""
        return self.page.get_by_role("tabpanel").filter(
            has=self.page.get_by_role("tabpanel")
        )

    @property
    def section_panel(self) -> Locator:
        """Nested tabpanel with the content of the active section."""
        return self.panel.get_by_role("tabpanel")

    @property
    def section_nav(self) -> Locator:
        """Section button group rendered right before the section tabpanel."""
        return self.section_panel.locator("xpath=preceding-sibling::div[1]")

    def section_button(self, section: CLIAnalyticsSection) -> Locator:
        """Section navigation button by its exact visible name."""
        return self.section_nav.get_by_role("button", name=section, exact=True)

    def widget_heading(self, title: str) -> Locator:
        """Heading of a widget in the active section, by exact title."""
        return self.section_panel.get_by_role("heading", name=title, exact=True)

    @property
    def loading_indicators(self) -> Locator:
        """First-load overlays of widgets in the active section."""
        return self.section_panel.get_by_text("Loading data...", exact=True)

    @property
    def session_rows(self) -> Locator:
        """Data rows of the Sessions table (the 'No data available' row excluded)."""
        return (
            self.section_panel.get_by_role("row")
            .filter(has=self.page.get_by_role("cell"))
            .filter(has_not=self.page.get_by_text(self.EMPTY_TABLE_TEXT, exact=True))
        )

    def session_row(self, text: str) -> Locator:
        """Sessions table row containing the text (e.g. its repository or prompt)."""
        return self.session_rows.filter(has_text=text)

    @property
    def sessions_search_input(self) -> Locator:
        """'Search sessions...' input of the Sessions table (matches prompt, repository or branch)."""
        return self.section_panel.get_by_placeholder("Search sessions...", exact=True)

    @property
    def widget_errors(self) -> Locator:
        """Error messages that AnalyticsWidget renders in place of its content."""
        return self.section_panel.locator(".widget-content p.text-failed-secondary")

    @property
    def project_filter_section(self) -> Locator:
        """'PROJECT' expand/collapse button in the analytics sidebar."""
        return self.page.get_by_role("button", name="PROJECT")

    @property
    def project_filter_region(self) -> Locator:
        """'PROJECT' filter region in the analytics sidebar."""
        return self.page.get_by_role("region", name="PROJECT")

    @property
    def overview_tool_success_desc(self) -> Locator:
        """Tool Success description element in the Overview TOOL CALLS metric card.

        The live component does not render a data-testid on the description paragraph;
        the aria snapshot confirms exactly one paragraph with text — (U+2014) inside
        the section tabpanel when tool_calls == 0, so we locate it by exact text.
        """
        return self.section_panel.get_by_text(self.EM_DASH, exact=True)

    @property
    def users_data_rows(self) -> Locator:
        """Data rows of the Users table (empty-table message row excluded)."""
        return (
            self.section_panel.get_by_role("row")
            .filter(has=self.page.get_by_role("cell"))
            .filter(has_not=self.page.get_by_text(self.EMPTY_TABLE_TEXT, exact=True))
        )

    def _user_row_tool_success_cell(self, row: Locator) -> Locator:
        """Tool Success cell in a Users table row (5th column, index 4).

        Columns: USER(0) SESSIONS(1) TURNS(2) TOOL CALLS(3) TOOL SUCCESS(4) ...
        The live component renders no data-testid on table cells; positional lookup
        is used instead.
        """
        return row.get_by_role("cell").nth(4)

    # ── Actions ──────────────────────────────────────────────────────────────────

    def expect_section_data(self, section: CLIAnalyticsSection) -> ExitStack:
        """Context manager that waits for all data requests of a section.

        Wrap the action that mounts the section; on exit every endpoint of the
        section has answered and each response is asserted to be successful.
        """
        waiters = []

        def check_responses(exc_type, exc_value, traceback):
            if exc_type is not None:
                return
            for endpoint, waiter in waiters:
                response = waiter.value
                assert response.ok, (
                    f"CLI Analytics '{section}': {endpoint} request failed "
                    f"with HTTP {response.status}"
                )

        stack = ExitStack()
        # Exit callbacks run in reverse order: registered first, this one runs
        # after every response waiter below has resolved.
        stack.push(check_responses)
        for endpoint in self.SECTIONS[section].endpoints:
            waiter = stack.enter_context(
                self.page.expect_response(
                    lambda r, e=endpoint: r.request.method == "GET"
                    and urlparse(r.url).path.endswith(self.API_PATH + e),
                    timeout=30000,
                )
            )
            waiters.append((endpoint, waiter))
        return stack

    @step
    def navigate_to(self):
        """Open CLI Analytics by URL and wait for the default section data."""
        with self.expect_section_data(self.DEFAULT_SECTION):
            self.page.goto(self.PATH)
        return self.should_be_visible()

    @step
    def open_section(self, section: CLIAnalyticsSection):
        """Open a section that is not active yet and wait for its data."""
        button = self.section_button(section)
        expect(button).to_be_visible(timeout=15000)
        expect(
            button,
            f"'{section}' is already active; clicking it would not reload data",
        ).not_to_have_class(self.ACTIVE_SECTION_CLASS)
        with self.expect_section_data(section):
            button.click()
        return self

    @step
    def search_sessions(self, text: str):
        """Type into the Sessions search and wait for the filtered session list."""
        with self.page.expect_response(
            lambda r: r.request.method == "GET"
            and urlparse(r.url).path.endswith(self.API_PATH + "sessions")
            and parse_qs(urlparse(r.url).query).get("search") == [text],
            timeout=30000,
        ) as sessions:
            self.sessions_search_input.fill(text)
        response = sessions.value
        assert response.ok, f"Session search request failed with HTTP {response.status}"
        return self

    @step
    def open_session(self, text: str) -> CLIAnalyticsSessionModal:
        """Click the Sessions table row containing the text, wait for its detail and return the modal."""
        row = self.session_row(text)
        expect(row, f"Session row with '{text}' should be listed").to_be_visible(
            timeout=15000
        )
        with self.page.expect_response(
            lambda r: r.request.method == "GET"
            and bool(self.SESSION_DETAIL_PATH.search(urlparse(r.url).path)),
            timeout=30000,
        ) as detail:
            # The first (date) cell is plain text; clicks on links/buttons don't select the row.
            row.get_by_role("cell").first.click()
        response = detail.value
        assert response.ok, f"Session detail request failed with HTTP {response.status}"
        return CLIAnalyticsSessionModal(self.page).should_be_visible()

    @step
    def filter_by_project(self, project_name: str):
        """Select a project in the sidebar filter and wait for Overview data to reload."""
        region = self.project_filter_region
        try:
            region.wait_for(state="visible", timeout=3000)
        except Exception:
            self.project_filter_section.click()
        with self.expect_section_data(self.DEFAULT_SECTION):
            region.locator(".p-multiselect").click()
            self.page.get_by_role("searchbox").first.fill(project_name)
            self.page.get_by_role("option", name=project_name, exact=True).click()
        return self

    @step
    def open_first_user_modal(self) -> CLIAnalyticsUserModal:
        """Click the first Users table row and return the open user detail modal."""
        row = self.users_data_rows.first
        expect(row, "Users table should have at least one data row").to_be_visible(
            timeout=15000
        )
        row.get_by_role("cell").first.click()
        return CLIAnalyticsUserModal(self.page).should_be_visible()

    # ── Assertions ────────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self):
        """Assert that CLI Analytics is selected and its content is rendered."""
        expect(self.tab).to_have_attribute("aria-selected", "true", timeout=15000)
        expect(self.section_nav).to_be_visible(timeout=15000)
        expect(self.section_panel).to_be_visible(timeout=15000)
        return self

    @step
    def should_have_sections(self):
        """Assert that all CLI Analytics navigation sections are available."""
        for section in CLIAnalyticsSection:
            expect(
                self.section_button(section),
                f"CLI Analytics section '{section}' should be visible",
            ).to_be_visible(timeout=15000)
        return self

    @step
    def should_have_active_section(self, section: CLIAnalyticsSection):
        """Assert the section button is active and the section content is shown."""
        expect(
            self.section_button(section),
            f"CLI Analytics section '{section}' should be active",
        ).to_have_class(self.ACTIVE_SECTION_CLASS, timeout=15000)
        expect(
            self.widget_heading(self.SECTIONS[section].marker_widget),
            f"CLI Analytics section '{section}' content should be shown",
        ).to_be_visible(timeout=15000)
        return self

    @step
    def should_finish_loading(self):
        """Assert that no widget of the active section is still on its first load."""
        expect(
            self.loading_indicators,
            "CLI Analytics section should finish loading",
        ).to_have_count(0, timeout=15000)
        return self

    @step
    def should_not_have_widget_errors(self):
        """Assert that no widget of the active section shows an error state."""
        expect(
            self.widget_errors,
            "CLI Analytics widgets should not show errors",
        ).to_have_count(0)
        return self

    @step
    def should_have_loaded_section(self, section: CLIAnalyticsSection):
        """Assert the section is active, fully loaded and error-free."""
        self.should_have_active_section(section)
        self.should_finish_loading()
        self.should_not_have_widget_errors()
        return self

    @step
    def should_show_overview_tool_success_dash(self):
        """Assert the Overview TOOL CALLS card shows the em dash for Tool Success."""
        expect(
            self.overview_tool_success_desc,
            "metric-desc-total_tool_calls should display the em dash when tool_calls = 0",
        ).to_have_text(self.EM_DASH, timeout=15000)
        return self

    @step
    def should_show_first_user_row_tool_success_dash(self):
        """Assert the first Users table row shows the em dash for Tool Success."""
        row = self.users_data_rows.first
        expect(
            self._user_row_tool_success_cell(row),
            "cell-tool-success should display the em dash when tool_calls = 0",
        ).to_have_text(self.EM_DASH, timeout=15000)
        return self
