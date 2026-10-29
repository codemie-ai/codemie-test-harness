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

"""Page object for the Project Details administration page.

URL: /settings/administration/projects/{project_name}

This page shows the project detail view including the Budgets section that
exposes the "Manage Budget" context menu → "Edit Budget" link to open the
UnifiedProjectBudgetModal.

The "Project sections" tablist additionally exposes "Budgets" and
"Integrations" tabs (and the "Overview" tab's Financial summary /
Integrations cards) — these only render when the signed-in user is an admin
of the specific project being viewed (confirmed via live inspection on
2026-10-09, project "codemie"). A project created via
the API by the test user automatically satisfies this (the caller becomes
the project's admin).
"""

import re
from urllib.parse import quote

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.administration.unified_project_budget_modal_page import (
    UnifiedProjectBudgetModalPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_models_section import (
    ProjectModelsSection,
)
from codemie_test_harness.tests.ui.pageobject.analytics.analytics_page import (
    AnalyticsPage,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ProjectDetailsPage(BasePage):
    """Administration > Project Detail page."""

    BASE_PATH = "/settings/administration/projects"

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def manage_budget_button(self):
        """'Manage Budget' button in the project Budgets section."""
        return self.page.get_by_role("button", name="Manage Budget")

    @property
    def edit_budget_link(self):
        """'Edit Budget' link inside the Manage Budget context menu."""
        return self.page.get_by_role("link", name="Edit Budget")

    @property
    def budget_dialog(self):
        """The 'Update Budget' dialog element."""
        return self.page.get_by_role("dialog")

    @property
    def members_tab(self):
        """'Members' tab in the 'Project sections' tablist."""
        return self.page.get_by_role("tab", name="Members")

    @property
    def budgets_tab(self):
        """'Budgets' tab in the 'Project sections' tablist."""
        return self.page.get_by_role("tab", name="Budgets")

    @property
    def integrations_tab(self):
        """'Integrations' tab in the 'Project sections' tablist."""
        return self.page.get_by_role("tab", name="Integrations")

    @property
    def models_tab(self):
        """'Models' tab in the 'Project sections' tablist."""
        return self.page.get_by_role("tab", name="Models")

    @property
    def overview_tab(self):
        """'Overview' tab in the 'Project sections' tablist."""
        return self.page.get_by_role("tab", name="Overview", exact=True)

    @property
    def users_value(self):
        """Users count rendered in the Project information card."""
        return self.page.get_by_text("Users", exact=True).locator(
            "xpath=following-sibling::div[1]"
        )

    @property
    def admins_value(self):
        """Admins count rendered in the Project information card."""
        return self.page.get_by_text("Admins", exact=True).locator(
            "xpath=following-sibling::div[1]"
        )

    @property
    def financial_summary_card(self):
        """Smallest container holding both the 'Financial summary' heading and the Routing impact row."""
        return (
            self.page.locator("div")
            .filter(has=self.page.get_by_text("Financial summary", exact=True))
            .filter(has=self.routing_impact_label)
            .last
        )

    @property
    def integrations_table_rows(self):
        """Body rows of the integrations table on the Integrations tab."""
        return self.page.get_by_role("table").locator("tbody tr")

    @property
    def view_analytics_button(self):
        """'View analytics' button in the Overview tab's Financial summary card."""
        return self.page.get_by_role("button", name="View analytics")

    @property
    def active_budgets_grid(self):
        """Grid holding the Platform / CLI / Premium models cards, located as the
        sibling after the 'Active budgets' heading row.
        """
        header_row = self.page.get_by_text("Active budgets", exact=True).locator(
            "xpath=../.."
        )
        return header_row.locator("xpath=following-sibling::*[1]")

    def active_budget_card(self, category_label: str):
        """One category card: a direct child of the Active budgets grid whose text
        starts with the category label. Matching by the grid's direct children
        keeps the lookup to a single card — a text-based ancestor search would
        also match the whole grid, whose other cards carry the same markers.
        Prefix matching is needed because an unassigned card's heading also
        holds a nested 'Disabled' badge ("CLI" + "Disabled" in one text run).
        """
        return self.active_budgets_grid.locator(":scope > div").filter(
            has_text=re.compile(rf"^\s*{re.escape(category_label)}")
        )

    def active_budget_hard_limit_value(self, category_label: str):
        """The '<spend> / <hard limit>' text in a category's Active budgets card."""
        return (
            self.active_budget_card(category_label)
            .get_by_text("Spend / hard limit", exact=True)
            .locator("xpath=following-sibling::div[1]")
        )

    def active_budget_soft_limit_value(self, category_label: str):
        """The soft-limit value text in a category's Active budgets card."""
        return (
            self.active_budget_card(category_label)
            .get_by_text("Soft limit", exact=True)
            .locator("xpath=following-sibling::div[1]")
        )

    def active_budget_disabled_status(self, category_label: str):
        """The 'Disabled' status badge on a category's Active budgets card."""
        return self.active_budget_card(category_label).get_by_role(
            "status", name="Disabled"
        )

    def active_budget_not_assigned_placeholder(self, category_label: str):
        """The '— not assigned —' placeholder text on an unassigned category card."""
        return self.active_budget_card(category_label).get_by_text(
            "not assigned", exact=False
        )

    @property
    def model_availability_heading(self):
        """'Model availability' heading in the Overview tab's Models card."""
        return self.page.get_by_text("Model availability", exact=True)

    @property
    def model_availability_configure_button(self):
        """'Configure' button in the Overview tab's Model availability card."""
        return self.page.get_by_role("button", name="Configure")

    @property
    def model_availability_count_value(self):
        """The '<N> of <M> models' text shown in the Model availability card."""
        return self.model_availability_heading.locator(
            "xpath=../following-sibling::div[1]"
        )

    @property
    def integrations_count_label(self):
        """'Project-level integrations' label under the Overview tab's Integrations card."""
        return self.page.get_by_text("Project-level integrations", exact=True)

    @property
    def integrations_count_value(self):
        """The integrations count shown in the Overview tab's Integrations card.

        DOM order places the count/"View" button row *before* the label
        ("Project-level integrations"), so the value is reached from the label
        by walking up to the card and back down to its first child, rather than
        via the following-sibling pattern used by the other summary fields.
        """
        return self.integrations_count_label.locator("xpath=../div[1]/div[1]")

    @property
    def view_integrations_button(self):
        """'View' button in the Overview tab's Integrations card.

        Must be matched with exact=True — a fuzzy match also picks up the
        unrelated "View analytics" button in the Financial summary card.
        """
        return self.page.get_by_role("button", name="View", exact=True)

    @property
    def chargeback_label(self):
        """'Chargeback' field label in the Financial summary card."""
        return self.page.get_by_text("Chargeback", exact=True)

    @property
    def chargeback_value(self):
        """'Enabled'/'Disabled' value rendered next to the Chargeback label."""
        return self.chargeback_label.locator("xpath=following-sibling::div[1]")

    @property
    def reset_period_value(self):
        """Value rendered next to the 'Reset period' label; '—' until the project's budgets load."""
        return self.page.get_by_text("Reset period", exact=True).locator(
            "xpath=following-sibling::div[1]"
        )

    @property
    def routing_impact_label(self):
        """'Routing impact' field label in the Financial summary card.

        Always rendered regardless of budget/chargeback configuration
        (confirmed live on both a project with no budget and one with an
        active budget) — no feature-flag skip is needed around it.
        """
        return self.page.get_by_text("Routing impact", exact=True)

    @property
    def routing_impact_value(self):
        """Value rendered next to the Routing impact label."""
        return self.routing_impact_label.locator("xpath=following-sibling::div[1]")

    @property
    def description_label(self):
        """The 'Description' field label on the details page (exact text, not a substring)."""
        return self.page.get_by_text("Description", exact=True)

    @property
    def description_value(self):
        """The value block rendered under the Description label — the same `displayValue()`
        mechanism used for every other empty field on this page (renders '-' when null).
        """
        return self.description_label.locator("xpath=following-sibling::div[1]")

    @property
    def owned_by_label(self):
        """The 'Owned by' field label on the details page (exact text)."""
        return self.page.get_by_text("Owned by", exact=True)

    @property
    def owned_by_value(self):
        """The value block rendered under the 'Owned by' label (the owner's display name)."""
        return self.owned_by_label.locator("xpath=following-sibling::div[1]")

    @property
    def create_budget_control(self):
        """The 'Create Budget' control of the Active budgets section (button or link)."""
        return self.page.get_by_text("Create Budget", exact=True)

    # ── CLI Analytics status / Edit Project ───────────────────
    # FE source of truth (codemie-ui, branch for this feature):
    #   src/pages/settings/administration/projectsManagement/ProjectOverviewSection.tsx:72-77
    #     InfoItem = <div><div class="mb-1 text-xs text-text-quaternary">{label}</div>
    #                     <div class="break-words text-sm ...">{value}</div></div>
    #   ProjectOverviewSection.tsx:410-415: rendered only when project.cli_analytics_enabled
    #     !== undefined (the backend sends the key to viewers only):
    #     <InfoItem label="CLI Analytics" value={enabled ? 'Enabled' : 'Disabled'} />
    #   src/pages/settings/administration/ProjectDetailsPage.tsx:108,253-258: the 'Edit Project'
    #     button is shown when canManageProject = !personal && (isAdmin || isProjectAdmin).
    # There is no data-testid on these nodes in the branch; the label div is located by its
    # class triple plus exact text.

    @property
    def edit_project_button(self):
        """'Edit Project' button in the page header (ProjectDetailsPage.tsx:253-258)."""
        return self.page.get_by_role("button", name="Edit Project", exact=True)

    @property
    def cli_analytics_label(self):
        """The 'CLI Analytics' item label in Overview > Project information."""
        return self.page.locator("div.mb-1.text-xs.text-text-quaternary").filter(
            has_text=re.compile(r"^CLI Analytics$")
        )

    @property
    def cli_analytics_value(self):
        """The value block under the 'CLI Analytics' label ('Enabled' or 'Disabled')."""
        return self.cli_analytics_label.locator("xpath=following-sibling::div[1]")

    @property
    def project_not_found_message(self):
        """'Project not found' placeholder (ProjectDetailsPage.tsx, project === null)."""
        # scoped to the main content: an error toast titled the same appears at the same time
        return self.page.locator("#main-content").get_by_text(
            "Project not found", exact=True
        )

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def open_edit_project(self):
        """Click 'Edit Project' and return the opened modal page object."""
        from codemie_test_harness.tests.ui.pageobject.administration.project_modal_page import (
            ProjectModal,
        )

        expect(self.edit_project_button).to_be_visible(timeout=15000)
        self.edit_project_button.click()
        modal = ProjectModal(self.page)
        modal.should_be_visible()
        return modal

    @step
    def navigate_to(self, project_name: str):
        """Navigate directly to a project's detail page."""
        self.page.goto(f"{self.BASE_PATH}/{project_name}")
        self.page.wait_for_load_state("networkidle", timeout=30000)
        return self

    @step
    def open_members_tab(self):
        """Switch to the Members tab, which holds the members table."""
        expect(self.members_tab).to_be_visible(timeout=15000)
        self.members_tab.click()
        expect(self.members_tab).to_have_attribute("aria-selected", "true")
        return self

    @step
    def open_budgets_tab(self):
        """Switch to the Budgets tab (routes to .../budgets)."""
        expect(self.budgets_tab).to_be_visible(timeout=15000)
        self.budgets_tab.click()
        expect(self.budgets_tab).to_have_attribute("aria-selected", "true")
        return self

    @step
    def open_integrations_tab(self):
        """Switch to the Integrations tab (routes to .../integrations)."""
        expect(self.integrations_tab).to_be_visible(timeout=15000)
        self.integrations_tab.click()
        expect(self.integrations_tab).to_have_attribute("aria-selected", "true")
        return self

    @step
    def open_models_tab(self) -> "ProjectModelsSection":
        """Switch to the Models tab (routes to .../models)."""
        expect(self.models_tab).to_be_visible(timeout=15000)
        self.models_tab.click()
        expect(self.models_tab).to_have_attribute("aria-selected", "true")
        return ProjectModelsSection(self.page)

    @step
    def click_configure_models(self) -> "ProjectModelsSection":
        """Click the Model availability card's 'Configure' button; navigates to
        the project's Models tab.
        """
        expect(self.model_availability_configure_button).to_be_visible(timeout=15000)
        self.model_availability_configure_button.click()
        models = ProjectModelsSection(self.page)
        models.should_be_visible()
        return models

    @step
    def click_view_integrations(self):
        """Click the Integrations card's 'View' button; navigates to the Integrations tab."""
        expect(self.view_integrations_button).to_be_visible(timeout=15000)
        self.view_integrations_button.click()
        return self

    @step
    def click_view_analytics(self) -> "AnalyticsPage":
        """Click 'View analytics'; navigates to the separate /analytics page."""
        expect(self.view_analytics_button).to_be_visible(timeout=15000)
        self.view_analytics_button.click()
        analytics_page = AnalyticsPage(self.page)
        expect(analytics_page.page_heading).to_be_visible(timeout=15000)
        return analytics_page

    @step
    def open_budget_config_modal(self) -> "UnifiedProjectBudgetModalPage":
        """Click Manage Budget → Edit Budget to open the UnifiedProjectBudgetModal."""
        expect(self.manage_budget_button).to_be_visible(timeout=15000)
        self.manage_budget_button.click()
        expect(self.edit_budget_link).to_be_visible(timeout=5000)
        self.edit_budget_link.click()
        modal = UnifiedProjectBudgetModalPage(self.page)
        modal.should_be_visible()
        return modal

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_be_on_project_details_page(self, project_name: str):
        """Verify the browser is on the correct project detail URL.

        Uses a compiled regex (matched against the full absolute URL) rather than a
        glob string: a glob string is resolved relative to `base_url` first, which
        double-counts the leading '/' already present in `BASE_PATH` and never matches.
        The project name is percent-encoded the way the app does it (a personal project
        is named after an email, so '@' appears in the URL as '%40').
        """
        encoded_name = quote(project_name, safe="")
        expect(self.page).to_have_url(
            re.compile(re.escape(f"{self.BASE_PATH}/{encoded_name}") + r"/?$"),
            timeout=10000,
        )
        return self

    @step
    def should_not_have_manage_budget_button(self):
        """Verify the Manage Budget button is absent (non-editor view).

        Probes for the button first so the assertion is not a false PASS when
        the button is JS-suppressed and has not yet rendered (or will never
        render due to canManageBudgets=false).  The probe waits up to 5 s for
        the element to be attached; if it never appears we assert not_to_be_visible
        immediately.  If it does appear (unexpected), the assertion fails cleanly.
        """
        try:
            self.page.wait_for_selector(
                '[role="button"][name="Manage Budget"]',
                state="attached",
                timeout=5000,
            )
        except Exception:
            pass
        expect(self.manage_budget_button).not_to_be_visible(timeout=3000)
        return self

    @step
    def should_not_show_budgets_and_integrations_tabs(self):
        """Verify the Budgets and Integrations tabs are absent (non-editor view)."""
        expect(self.budgets_tab).to_have_count(0)
        expect(self.integrations_tab).to_have_count(0)
        return self

    @step
    def should_show_no_description_placeholder(self):
        """Verify the Description block renders the 'No description' placeholder."""
        expect(self.description_value).to_have_text("No description")
        return self

    @step
    def should_be_on_integrations_tab(self, project_name: str):
        """Verify the browser navigated to the project's Integrations tab."""
        expect(self.page).to_have_url(
            re.compile(
                re.escape(f"{self.BASE_PATH}/{project_name}/integrations") + r"/?$"
            ),
            timeout=10000,
        )
        expect(self.integrations_tab).to_have_attribute(
            "aria-selected", "true", timeout=10000
        )
        return self

    @step
    def should_be_on_models_tab(self, project_name: str):
        """Verify the browser navigated to the project's Models tab."""
        expect(self.page).to_have_url(
            re.compile(re.escape(f"{self.BASE_PATH}/{project_name}/models") + r"/?$"),
            timeout=10000,
        )
        expect(self.models_tab).to_have_attribute(
            "aria-selected", "true", timeout=10000
        )
        return self

    @step
    def should_have_selected_models_count(self, selected: int, total: int):
        """Verify the Model availability card shows '<selected> of <total> models'."""
        expect(self.model_availability_count_value).to_have_text(
            re.compile(rf"^{selected} of {total} models$"), timeout=15000
        )
        return self

    @step
    def should_have_active_budget_hard_limit(self, category_label: str, value: float):
        """Verify an assigned category's card shows '<spend> / $<value>' hard limit."""
        expect(self.active_budget_hard_limit_value(category_label)).to_have_text(
            re.compile(rf"/\s*\${value:.2f}$"), timeout=15000
        )
        return self

    @step
    def should_have_active_budget_soft_limit(self, category_label: str, value: float):
        """Verify an assigned category's card shows '$<value>' soft limit."""
        expect(self.active_budget_soft_limit_value(category_label)).to_have_text(
            f"${value:.2f}", timeout=15000
        )
        return self

    @step
    def should_show_active_budget_disabled(self, category_label: str):
        """Verify an unassigned category's card shows the 'Disabled' badge and
        the '— not assigned —' placeholder (no Spend/hard limit section).
        """
        expect(self.active_budget_disabled_status(category_label)).to_be_visible(
            timeout=15000
        )
        expect(
            self.active_budget_not_assigned_placeholder(category_label)
        ).to_be_visible(timeout=15000)
        return self

    @step
    def should_not_show_active_budget_disabled(self, category_label: str):
        """Verify a category's card no longer shows the 'Disabled' badge /
        '— not assigned —' placeholder — it has been assigned a real budget.
        """
        expect(self.active_budget_card(category_label)).to_be_visible(timeout=15000)
        expect(self.active_budget_disabled_status(category_label)).to_have_count(0)
        return self

    @step
    def should_have_integrations_count(self, count: int):
        """Verify the Overview tab's Integrations card shows the given count."""
        expect(self.integrations_count_value).to_have_text(str(count), timeout=15000)
        return self

    @step
    def should_have_integrations_table_row_count(self, count: int):
        """Verify the Integrations tab's table lists exactly `count` rows."""
        expect(self.integrations_table_rows).to_have_count(count, timeout=15000)
        return self

    @step
    def should_have_chargeback_value(self, value: str):
        """Verify the Overview tab's Chargeback field shows 'Enabled' or 'Disabled'."""
        expect(self.chargeback_value).to_have_text(value, timeout=15000)
        return self

    @step
    def should_show_routing_impact(self):
        """Verify the Routing impact field is rendered — always visible, no flag/skip."""
        expect(self.routing_impact_label).to_be_visible(timeout=15000)
        expect(self.routing_impact_value).to_be_visible(timeout=5000)
        return self

    @step
    def should_show_detail_tabs(self):
        """Verify the Project sections tablist shows Overview, Members, Budgets and Integrations."""
        expect(self.overview_tab).to_be_visible(timeout=15000)
        expect(self.members_tab).to_be_visible(timeout=15000)
        expect(self.budgets_tab).to_be_visible(timeout=15000)
        expect(self.integrations_tab).to_be_visible(timeout=15000)
        return self

    @step
    def should_show_overview_sections(self):
        """Verify the Overview tab renders its Project information, Financial summary and Active budgets sections."""
        expect(self.overview_tab).to_have_attribute(
            "aria-selected", "true", timeout=15000
        )
        expect(self.page.get_by_text("Project information", exact=True)).to_be_visible(
            timeout=15000
        )
        expect(self.page.get_by_text("Financial summary", exact=True)).to_be_visible(
            timeout=15000
        )
        expect(self.page.get_by_text("Active budgets", exact=True)).to_be_visible(
            timeout=15000
        )
        return self

    @step
    def should_have_users_count(self, count: int):
        """Verify the Project information card's Users value equals the given count."""
        expect(self.users_value).to_have_text(str(count), timeout=15000)
        return self

    @step
    def should_have_admins_count(self, count: int):
        """Verify the Project information card's Admins value equals the given count."""
        expect(self.admins_value).to_have_text(str(count), timeout=15000)
        return self

    @step
    def should_show_reset_period(self, period: str):
        """Wait until the Financial summary shows `period` (e.g. '30d').

        The field reads the same budgets the 'View analytics' button builds its
        dates from, so once it shows the period the button no longer falls back
        to `time_period=last_30_days`.
        """
        expect(self.reset_period_value).to_have_text(period, timeout=30000)
        return self

    @step
    def should_have_chargeback_and_routing_inside_financial_summary(self):
        """Verify Chargeback and Routing impact are rows of the Financial summary card, not separate blocks."""
        card = self.financial_summary_card
        expect(card).to_be_visible(timeout=15000)
        expect(card.get_by_text("Chargeback", exact=True)).to_be_visible(timeout=5000)
        expect(card.get_by_text("Routing impact", exact=True)).to_be_visible(
            timeout=5000
        )
        expect(card.get_by_text("Total budget", exact=True)).to_be_visible(timeout=5000)
        return self

    @step
    def should_show_owner(self, owner_name: str):
        """Verify the 'Owned by' field shows the owner's display name."""
        expect(self.owned_by_value).to_have_text(owner_name, timeout=15000)
        return self

    @step
    def should_not_offer_create_budget(self):
        """Verify the loaded project details page renders no 'Create Budget' control.

        The page is first proven loaded (the 'Owned by' field is visible), so the absence
        check cannot pass merely because the page has not rendered yet.
        """
        expect(self.owned_by_label).to_be_visible(timeout=15000)
        expect(self.create_budget_control).to_have_count(0)
        return self

    @step
    def should_show_cli_analytics_status(self, enabled: bool):
        """Verify Overview shows 'CLI Analytics: Enabled|Disabled'."""
        expect(self.cli_analytics_label).to_be_visible(timeout=15000)
        expect(self.cli_analytics_value).to_have_text(
            "Enabled" if enabled else "Disabled"
        )
        return self

    @step
    def should_not_show_cli_analytics_status(self):
        """Verify the page rendered (Overview fields or 'Project not found') and the
        'CLI Analytics' item is absent. Waiting for the render first keeps the absence
        from passing vacuously on a page that has not loaded yet."""
        expect(self.owned_by_label.or_(self.project_not_found_message)).to_be_visible(
            timeout=15000
        )
        expect(self.cli_analytics_label).to_have_count(0)
        return self

    @step
    def should_show_project_without_cli_analytics_status(self):
        """STRICT: the project details are shown ('Owned by' is visible) and the
        'CLI Analytics' item is absent. For users who must see the project."""
        expect(self.owned_by_label).to_be_visible(timeout=15000)
        expect(self.cli_analytics_label).to_have_count(0)
        return self

    @step
    def should_show_project_without_edit_project_button(self):
        """STRICT: the project details are shown ('Owned by' is visible) and there is no
        'Edit Project' button. For users who must see the project."""
        expect(self.owned_by_label).to_be_visible(timeout=15000)
        expect(self.edit_project_button).to_have_count(0)
        return self

    @step
    def should_have_edit_project_button(self):
        """Verify the 'Edit Project' button is available."""
        expect(self.edit_project_button).to_be_visible(timeout=15000)
        return self

    @step
    def should_not_have_edit_project_button(self):
        """Verify the page rendered and there is no 'Edit Project' button."""
        expect(self.owned_by_label.or_(self.project_not_found_message)).to_be_visible(
            timeout=15000
        )
        expect(self.edit_project_button).to_have_count(0)
        return self
