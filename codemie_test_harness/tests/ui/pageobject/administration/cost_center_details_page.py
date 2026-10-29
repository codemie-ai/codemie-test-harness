"""Page object for the Cost Center Details administration page.

URL: /settings/administration/cost-centers/{cost_center_id}

The 'Budget rollup' section is shown only when the budget management feature flag
(useBudgetManagementEnabled) is on. The rollup card has no data-testid, so its elements are
located by text inside the section.
"""

import re

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

NOT_ASSIGNED_TEXT = "— not assigned —"
NO_PROJECTS_LINKED_TEXT = "No projects linked"


def format_money(value: float) -> str:
    """Format an amount the way the rollup card does: '$1,234.50'."""
    return f"${value:,.2f}"


class CostCenterDetailsPage(BasePage):
    """Administration > Cost Center Detail page."""

    BASE_PATH = "/settings/administration/cost-centers"

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def budget_rollup_heading(self):
        """'Budget rollup' section heading."""
        return self.page.get_by_text("Budget rollup", exact=True)

    @property
    def budget_rollup_section(self):
        """The <section> holding the 'Budget rollup' heading and the rollup card."""
        return self.page.locator("section").filter(has=self.budget_rollup_heading)

    @property
    def budget_rollup_error(self):
        """Error text the rollup card shows when the summary cannot be loaded."""
        return self.budget_rollup_section.get_by_text(
            "Failed to load cost center budget summary", exact=False
        )

    def summary_value(self, label: str):
        """Value shown under a summary label ('Total budget', 'Spend', '% used').

        'Total budget' may carry a reset period suffix ('Total budget · Monthly · 30d'),
        so the label is matched by its start.
        """
        label_element = self.budget_rollup_section.get_by_text(
            re.compile(rf"^{re.escape(label)}(\s·.*)?$")
        )
        return label_element.locator("xpath=following-sibling::div[1]")

    def category_card(self, category_label: str):
        """The card of one category: the parent of its label inside the rollup section."""
        return self.budget_rollup_section.get_by_text(
            category_label, exact=True
        ).locator("xpath=..")

    def category_metric(self, category_label: str, metric_label: str):
        """Value under a metric label ('Spend / hard limit', 'Remaining', 'Soft limit')
        in a category's card."""
        return (
            self.category_card(category_label)
            .get_by_text(metric_label, exact=True)
            .locator("xpath=following-sibling::div[1]")
        )

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def navigate_to(self, cost_center_id):
        """Open a cost center's detail page directly."""
        self.page.goto(f"{self.BASE_PATH}/{cost_center_id}")
        self.page.wait_for_load_state("networkidle", timeout=30000)
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_show_budget_rollup(self):
        """Verify the 'Budget rollup' section is shown and its card did not fail to load."""
        expect(self.budget_rollup_heading).to_be_visible(timeout=15000)
        expect(self.budget_rollup_error).to_have_count(0)
        return self

    @step
    def should_have_summary(
        self, total_budget: float | str, spend: float, percent_used: str
    ):
        """Verify the summary row: 'Total budget', 'Spend' and '% used'.

        ``total_budget`` is an amount, or the exact text shown instead of one.
        """
        expected_total = (
            total_budget
            if isinstance(total_budget, str)
            else format_money(total_budget)
        )
        expect(self.summary_value("Total budget")).to_have_text(
            expected_total, timeout=15000
        )
        expect(self.summary_value("Spend")).to_have_text(
            format_money(spend), timeout=15000
        )
        expect(self.summary_value("% used")).to_have_text(percent_used, timeout=15000)
        return self

    @step
    def should_have_category_budget(
        self,
        category_label: str,
        spend: float,
        hard_limit: float,
        remaining: float,
        soft_limit: float,
    ):
        """Verify a category card shows spend / hard limit, Remaining and Soft limit."""
        expect(self.category_metric(category_label, "Spend / hard limit")).to_have_text(
            f"{format_money(spend)} / {format_money(hard_limit)}", timeout=15000
        )
        expect(self.category_metric(category_label, "Remaining")).to_have_text(
            format_money(remaining), timeout=15000
        )
        expect(self.category_metric(category_label, "Soft limit")).to_have_text(
            format_money(soft_limit), timeout=15000
        )
        return self

    @step
    def should_show_category_not_assigned(self, category_label: str):
        """Verify a category card shows '— not assigned —' and no spend metrics."""
        expect(self.category_card(category_label)).to_contain_text(
            NOT_ASSIGNED_TEXT, timeout=15000
        )
        expect(
            self.category_card(category_label).get_by_text(
                "Spend / hard limit", exact=True
            )
        ).to_have_count(0)
        return self

    @step
    def should_show_no_projects_linked(self, category_label: str):
        """Verify a category card shows 'No projects linked'."""
        expect(self.category_card(category_label)).to_contain_text(
            NO_PROJECTS_LINKED_TEXT, timeout=15000
        )
        return self
