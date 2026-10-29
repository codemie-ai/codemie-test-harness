"""UI tests for the cost center budget rollup card.

The 'Budget rollup' section of the cost center details page needs the budget management
feature flag (useBudgetManagementEnabled) on the target environment.

Covered cases:
    TC-002  Combined total and per-category breakdown for a linked project (AC-2, AC-5)
    TC-005  Empty state for a cost center without linked projects (AC-4)

Navigation path:
    /settings/administration/cost-centers/{cost_center_id}

Cleanup strategy: create via API → verify via UI → clean up via API.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.cost_center_details_page import (
    CostCenterDetailsPage,
    NOT_ASSIGNED_TEXT,
)
from codemie_test_harness.tests.ui.test_data.cost_center_rollup_test_data import (
    CLI_BUDGET,
    CLI_LABEL,
    PLATFORM_AND_CLI_CATEGORIES,
    PLATFORM_BUDGET,
    PLATFORM_LABEL,
    PREMIUM_MODELS_LABEL,
    TOTAL_BUDGET,
)


@pytest.mark.budget
@pytest.mark.ui
def test_rollup_card_shows_total_and_category_breakdown_for_linked_project(
    page, cost_center, cost_center_budget_projects
):
    cc_id = cost_center()
    cost_center_budget_projects.create(cc_id, PLATFORM_AND_CLI_CATEGORIES)

    details_page = CostCenterDetailsPage(page)
    details_page.navigate_to(cc_id)

    details_page.should_show_budget_rollup()
    details_page.should_have_summary(
        total_budget=TOTAL_BUDGET, spend=0.0, percent_used="0.0%"
    )
    details_page.should_have_category_budget(
        PLATFORM_LABEL,
        spend=0.0,
        hard_limit=PLATFORM_BUDGET.max_budget,
        remaining=PLATFORM_BUDGET.max_budget,
        soft_limit=PLATFORM_BUDGET.soft_budget,
    )
    details_page.should_have_category_budget(
        CLI_LABEL,
        spend=0.0,
        hard_limit=CLI_BUDGET.max_budget,
        remaining=CLI_BUDGET.max_budget,
        soft_limit=CLI_BUDGET.soft_budget,
    )
    details_page.should_show_category_not_assigned(PREMIUM_MODELS_LABEL)


@pytest.mark.budget
@pytest.mark.ui
def test_rollup_card_shows_no_projects_linked_for_each_category_of_empty_cost_center(
    page, cost_center
):
    cc_id = cost_center()

    details_page = CostCenterDetailsPage(page)
    details_page.navigate_to(cc_id)

    details_page.should_show_budget_rollup()
    details_page.should_show_no_projects_linked(PLATFORM_LABEL)
    details_page.should_show_no_projects_linked(CLI_LABEL)
    details_page.should_show_no_projects_linked(PREMIUM_MODELS_LABEL)
    details_page.should_have_summary(
        total_budget=NOT_ASSIGNED_TEXT, spend=0.0, percent_used="—"
    )
