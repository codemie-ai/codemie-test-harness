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

"""Page object for the Analytics page.

URL: /analytics

Locators derived from live UI inspection on 2026-08-18.
Tab structure observed: Insights | CLI Insights | CLI Analytics | Leaderboard
Sidebar filters: TIME PERIOD | START DATE | END DATE | PROJECT | USERS
"""

import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.analytics.cli_analytics_page import (
    CLIAnalyticsPage,
)
from codemie_test_harness.tests.ui.pageobject.analytics.usage_attribution_page import (
    UsageAttributionPage,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.usage_attribution_test_data import (
    FILTER_NOTE,
    FILTER_SECTIONS_HIDDEN,
    FILTER_SECTIONS_SHOWN,
    TAB_NAME as USAGE_ATTRIBUTION_TAB_NAME,
    TABS_BEFORE_USAGE_ATTRIBUTION,
)

ALWAYS_PRESENT_TABS = ("Insights", "CLI Insights")
ALWAYS_PRESENT_TABS_PATTERN = re.compile(
    "^(" + "|".join(re.escape(name) for name in ALWAYS_PRESENT_TABS) + ")$"
)
STANDARD_TABS_PATTERN = re.compile(
    "^(" + "|".join(re.escape(name) for name in TABS_BEFORE_USAGE_ATTRIBUTION) + ")$"
)


class AnalyticsPage(BasePage):
    """Analytics Dashboard page object."""

    PATH = "/analytics"

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def page_heading(self):
        """'Analytics Dashboard' main heading."""
        return self.page.get_by_role("heading", name="Analytics Dashboard")

    @property
    def tab_leaderboard(self):
        """'Leaderboard' analytics tab."""
        return self.page.get_by_role("tab", name="Leaderboard")

    @property
    def manage_dashboards_button(self):
        """'Manage Dashboards' button (custom dashboards entry point)."""
        return self.page.get_by_role("button", name="Manage Dashboards")

    @property
    def users_filter_section(self):
        """'USERS' filter section (expandable) in the sidebar."""
        return self.page.get_by_role("button", name="USERS")

    @property
    def users_filter_dropdown(self):
        """Users multi-select combobox inside the USERS filter region."""
        return self.page.get_by_role("region", name="USERS").get_by_role(
            "combobox", name="Users"
        )

    @property
    def users_filter_region(self):
        """The USERS filter region that contains the combobox."""
        return self.page.get_by_role("region", name="USERS")

    @property
    def tab_usage_attribution(self) -> Locator:
        """'Usage Attribution' analytics tab (admins, maintainers and auditors, flag on)."""
        return self.page.get_by_role("tab", name=USAGE_ATTRIBUTION_TAB_NAME, exact=True)

    @property
    def standard_tabs_before_usage_attribution(self) -> Locator:
        """The standard analytics tabs that come before the Usage Attribution tab."""
        return self.tab_usage_attribution.locator(
            "xpath=preceding::*[@role='tab']"
        ).filter(has_text=ALWAYS_PRESENT_TABS_PATTERN)

    @property
    def standard_tabs_after_usage_attribution(self) -> Locator:
        """The standard analytics tabs that come after the Usage Attribution tab (there should be none)."""
        return self.tab_usage_attribution.locator(
            "xpath=following::*[@role='tab']"
        ).filter(has_text=STANDARD_TABS_PATTERN)

    @property
    def filter_sidebar(self) -> Locator:
        """The filter sidebar: the page's complementary region, titled 'Analytics'."""
        return self.page.get_by_role("complementary").filter(
            has=self.page.get_by_role("heading", name="Analytics", exact=True, level=2)
        )

    def filter_section(self, label: str) -> Locator:
        """Collapsible filter section of the sidebar by its label (shown in upper case)."""
        return self.filter_sidebar.get_by_role(
            "button", name=re.compile(rf"^{re.escape(label)}$", re.IGNORECASE)
        )

    @property
    def usage_attribution_filter_note(self) -> Locator:
        """Note under the filters that tells Project and Users filters do not apply to the tab."""
        return self.filter_sidebar.get_by_text(FILTER_NOTE)

    @property
    def date_range_from_url(self) -> tuple[datetime, datetime]:
        """Parse the current URL's 'start_date'/'end_date' query params.

        Both params are ISO-8601 UTC timestamps (e.g.
        ``2026-10-02T00:00:00.000Z``) set by the "View analytics" link on the
        Project Details page's Financial summary card.
        """
        query = parse_qs(urlparse(self.page.url).query)
        start = datetime.fromisoformat(query["start_date"][0].replace("Z", "+00:00"))
        end = datetime.fromisoformat(query["end_date"][0].replace("Z", "+00:00"))
        return start, end

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def navigate_to(self):
        """Navigate to the Analytics page and wait for the dashboard to render."""
        self.page.goto(self.PATH)
        self.page.wait_for_load_state("networkidle", timeout=30000)
        expect(self.page_heading).to_be_visible(timeout=15000)
        return self

    @step
    def should_be_on_analytics_page(self):
        """Verify the URL is the Analytics page and its dashboard heading is shown."""
        expect(self.page).to_have_url(re.compile(r".*/analytics.*"), timeout=15000)
        expect(self.page_heading).to_be_visible(timeout=15000)
        return self

    @step
    def open_user_filter(self):
        """Expand the USERS filter section if not already expanded."""
        region = self.page.get_by_role("region", name="USERS")
        try:
            region.wait_for(state="visible", timeout=3000)
        except Exception:
            self.users_filter_section.click()
            self.page.wait_for_timeout(500)
        return self

    @step
    def click_tab(self, tab_name: str):
        """Click a named analytics tab (Insights, CLI Insights, CLI Analytics, Leaderboard)."""
        tab = self.page.get_by_role("tab", name=tab_name, exact=True)
        expect(tab).to_be_visible(timeout=15000)
        tab.click()
        expect(tab).to_have_attribute("aria-selected", "true", timeout=15000)
        return self

    @step
    def open_cli_analytics(self) -> CLIAnalyticsPage:
        """Open the CLI Analytics tab, wait for its default section data and return its page object."""
        cli_analytics = CLIAnalyticsPage(self.page)
        with cli_analytics.expect_section_data(CLIAnalyticsPage.DEFAULT_SECTION):
            self.click_tab(CLIAnalyticsPage.TAB_NAME)
        return cli_analytics.should_be_visible()

    @step
    def should_offer_usage_attribution_tab(self):
        """Assert the Usage Attribution tab is offered to the current user.

        The tab shows once the app configuration has loaded, for an admin, maintainer or auditor
        when the feature is on, so callers use this where the backend already reports it on.
        """
        expect(
            self.tab_usage_attribution,
            f"The '{USAGE_ATTRIBUTION_TAB_NAME}' tab should be offered while the feature is on",
        ).to_be_visible(timeout=30000)
        return self

    @step
    def open_usage_attribution(self) -> UsageAttributionPage:
        """Open the Usage Attribution tab and return its page object."""
        self.click_tab(USAGE_ATTRIBUTION_TAB_NAME)
        usage_attribution = UsageAttributionPage(self.page)
        usage_attribution.should_have_sub_tabs()
        return usage_attribution

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_show_date_range_matching_budget_period(
        self,
        expected_start: datetime,
        end_tolerance_seconds: float = 30 * 60 + 60,
    ):
        """Verify the URL's start_date equals `expected_start` and end_date is
        within `end_tolerance_seconds` of "now" (i.e. "to date").

        The default is the Analytics date pickers' 30-minute step plus a minute,
        because the app floors end_date to that step.
        """
        # The date params are written into the URL after the page heading renders,
        # so wait for them instead of reading the URL once.
        expect(self.page).to_have_url(re.compile(r"[?&]start_date=.*[?&]end_date="))
        start, end = self.date_range_from_url
        assert start == expected_start, (
            f"Analytics start_date {start.isoformat()} does not match the "
            f"project's budget period start {expected_start.isoformat()}"
        )
        now = datetime.now(timezone.utc)
        age = abs((now - end).total_seconds())
        assert age <= end_tolerance_seconds, (
            f"Analytics end_date {end.isoformat()} is not close to now "
            f"({now.isoformat()}, {age:.0f}s away)"
        )
        return self

    @step
    def should_see_analytics_sections(self, sections: list[str]):
        """Assert each named analytics section tab is visible on the page.

        Uses ``exact=True`` on every lookup so that 'Insights' does not accidentally
        match 'CLI Insights'.

        Args:
            sections: List of tab names, e.g. ['Insights', 'Leaderboard', 'CLI Insights']
        """
        for section in sections:
            tab = self.page.get_by_role("tab", name=section, exact=True)
            expect(tab).to_be_visible(timeout=10000)
        return self

    @step
    def should_see_manage_dashboards(self):
        """Assert 'Manage Dashboards' button is visible (custom dashboards access)."""
        expect(self.manage_dashboards_button).to_be_visible(timeout=10000)
        return self

    @step
    def should_not_see_restricted_analytics_sections(self):
        """Assert that the Leaderboard tab is absent for a regular user."""
        expect(self.tab_leaderboard).not_to_be_visible(timeout=5000)
        return self

    @step
    def should_see_all_users_in_filter(self, expected_other_user: str):
        """Open the USERS filter, search for a known user, and assert they appear.

        Args:
            expected_other_user: Display name of a known non-self user to search for.
        """
        self.open_user_filter()
        multiselect = self.users_filter_region.locator(".p-multiselect")
        try:
            multiselect.wait_for(state="visible", timeout=5000)
            multiselect.click()
        except Exception:
            self.users_filter_dropdown.click(force=True)
        self.page.wait_for_timeout(500)
        # The dropdown has a search box — type the user name to filter the list.
        search = self.page.get_by_role("searchbox", name="Search users")
        search.fill(expected_other_user)
        self.page.wait_for_timeout(500)
        user_option = self.page.get_by_role("option", name=expected_other_user)
        expect(user_option).to_be_visible(timeout=10000)
        return self

    @step
    def should_list_usage_attribution_tab_after_existing_tabs(self):
        """Assert the Usage Attribution tab comes after the standard tabs the user has."""
        expect(self.tab_usage_attribution).to_be_visible(timeout=15000)
        expect(
            self.standard_tabs_before_usage_attribution,
            "Insights and CLI Insights should come before the Usage Attribution tab",
        ).to_have_count(len(ALWAYS_PRESENT_TABS))
        expect(
            self.standard_tabs_after_usage_attribution,
            "No standard tab should come after the Usage Attribution tab",
        ).to_have_count(0)
        return self

    @step
    def should_show_only_period_filters_with_note(self):
        """Assert period and date filters are shown, Project and Users are hidden, and the note says so."""
        for label in FILTER_SECTIONS_SHOWN:
            expect(
                self.filter_section(label), f"Filter '{label}' should be visible"
            ).to_be_visible(timeout=15000)
        for label in FILTER_SECTIONS_HIDDEN:
            expect(
                self.filter_section(label), f"Filter '{label}' should be hidden"
            ).to_have_count(0)
        expect(
            self.usage_attribution_filter_note,
            "The note about the missing project and user filter should be shown",
        ).to_be_visible(timeout=15000)
        return self
