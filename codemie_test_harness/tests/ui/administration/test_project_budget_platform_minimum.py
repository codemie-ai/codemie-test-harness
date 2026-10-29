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

"""UI tests for the Platform hard limit minimum in the Update Budget popup.

Covered cases:
    TC-003  Platform hard limit input refuses 0, negative and empty and keeps previous value
    TC-004  Dragging the allocation slider fully left stops at the minimum Platform share and saves
    TC-005  Reset to Default and lowering Total Budget keep Platform hard limit above 0
    TC-006  CLI Hard, Premium Hard and every Soft limit accept 0 and the budget saves
            (a typed value recalculates no other field, so the missing share is typed back in)
    TC_001  Typing 0 into CLI hard limit leaves Platform and Premium hard limits
            unchanged (the cli_hard case of TC-006)
    TC-008  Positive Platform amount below the minimum share is raised, not rejected

Navigation path:
    /settings/administration/projects/<project> → Manage Budget → Edit Budget → popup

Cleanup strategy: create via API → mutate via UI → clean up via API.
"""

import pytest
from hamcrest import assert_that, close_to, equal_to, greater_than, has_entries

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.test_data.project_budget_platform_test_data import (
    LOWERED_TOTAL_BUDGET,
    LOWERED_TOTAL_BUDGET_TEXT,
    PLATFORM_HARD_AFTER_LOWERED_TOTAL,
    PLATFORM_HARD_TEXT,
    PLATFORM_SLIDER_MIN_AMOUNT,
    PLATFORM_SLIDER_MIN_TEXT,
    REJECTED_PLATFORM_INPUTS,
    SUB_MINIMUM_CLI_HARD_AMOUNT,
    SUB_MINIMUM_CLI_HARD_TEXT,
    SUB_MINIMUM_PLATFORM_SOFT_TEXT,
    SUB_MINIMUM_PLATFORM_TEXT,
    ZERO_LIMIT_CASES,
)

# Saved amounts are derived from percentages, so allow a float epsilon.
AMOUNT_TOLERANCE = 0.001


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.parametrize("rejected_input", REJECTED_PLATFORM_INPUTS)
@pytest.mark.ui
def test_platform_hard_limit_input_rejects_invalid_value_and_keeps_previous(
    page, project_with_distributed_budget, rejected_input
):
    project_name, _ = project_with_distributed_budget

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    modal = details_page.open_budget_config_modal()
    modal.should_have_platform_hard_limit(PLATFORM_HARD_TEXT)

    modal.enter_platform_hard_limit(rejected_input)

    modal.should_have_platform_hard_limit(PLATFORM_HARD_TEXT)


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_allocation_slider_dragged_fully_left_stops_at_minimum_platform_share(
    page, project_with_distributed_budget, budget_group_utils
):
    project_name, group_id = project_with_distributed_budget

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    modal = details_page.open_budget_config_modal()
    modal.should_have_platform_hard_limit(PLATFORM_HARD_TEXT)

    modal.drag_platform_handle_fully_left()

    modal.should_have_platform_hard_limit(PLATFORM_SLIDER_MIN_TEXT)
    modal.save_budget_config()
    platform_budget = budget_group_utils.get_category_budgets(group_id)["platform"]
    assert_that(
        platform_budget,
        close_to(PLATFORM_SLIDER_MIN_AMOUNT, AMOUNT_TOLERANCE),
        "Saved Platform hard limit should be the minimum share (pct 0.01 of 1000)",
    )


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_reset_to_default_and_lowered_total_budget_keep_platform_hard_limit_above_zero(
    page, project_with_distributed_budget, budget_group_utils
):
    project_name, group_id = project_with_distributed_budget

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    modal = details_page.open_budget_config_modal()
    modal.should_have_platform_hard_limit(PLATFORM_HARD_TEXT)
    modal.drag_platform_handle_fully_left()
    modal.should_have_platform_hard_limit(PLATFORM_SLIDER_MIN_TEXT)

    modal.reset_to_default_distribution()
    modal.should_have_platform_hard_limit(PLATFORM_HARD_TEXT)

    modal.enter_total_budget(LOWERED_TOTAL_BUDGET_TEXT)
    modal.should_have_platform_hard_limit_above_zero()
    modal.save_budget_config()

    group = budget_group_utils.get_group(group_id)
    assert_that(
        float(group["total_amount"]),
        equal_to(LOWERED_TOTAL_BUDGET),
        "Saved total_amount should be the lowered Total Budget",
    )
    assert_that(
        budget_group_utils.get_category_budgets(group_id)["platform"],
        close_to(PLATFORM_HARD_AFTER_LOWERED_TOTAL, AMOUNT_TOLERANCE),
        "Saved Platform hard limit should keep the 30% default share of the lowered total",
    )


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.parametrize(
    "zero_case", ZERO_LIMIT_CASES, ids=[c.id for c in ZERO_LIMIT_CASES]
)
@pytest.mark.ui
def test_zero_non_platform_limit_is_accepted_and_saved(
    page, project_with_distributed_budget, budget_group_utils, zero_case
):
    project_name, group_id = project_with_distributed_budget

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    modal = details_page.open_budget_config_modal()
    modal.should_have_platform_hard_limit(PLATFORM_HARD_TEXT)

    modal.set_limits_to_zero(*zero_case.limits)

    modal.should_have_zero_limits(*zero_case.limits)
    modal.should_have_hard_limits(*zero_case.hard_limit_texts)
    modal.should_have_platform_hard_limit_above_zero()
    modal.enter_limits(*zero_case.compensations)
    modal.save_budget_config()

    hard_limits = budget_group_utils.get_category_budgets(group_id)
    soft_limits = budget_group_utils.get_category_soft_budgets(group_id)
    assert_that(
        hard_limits["platform"],
        greater_than(0.0),
        "Platform hard limit should stay above 0",
    )
    assert_that(
        {c: hard_limits.get(c, 0.0) for c in zero_case.saved_hard_amounts},
        has_entries(
            {
                c: close_to(amount, AMOUNT_TOLERANCE)
                for c, amount in zero_case.saved_hard_amounts.items()
            }
        ),
        "Saved hard limits should be exactly the typed values, nothing recalculated",
    )
    assert_that(
        {c: hard_limits.get(c, 0.0) for c in zero_case.zero_hard_categories},
        equal_to({c: 0.0 for c in zero_case.zero_hard_categories}),
        "Hard limits set to 0 should be saved as 0",
    )
    assert_that(
        {c: soft_limits.get(c, 0.0) for c in zero_case.zero_soft_categories},
        equal_to({c: 0.0 for c in zero_case.zero_soft_categories}),
        "Soft limits set to 0 should be saved as 0",
    )


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_sub_minimum_platform_amount_is_raised_to_minimum_share_not_rejected(
    page, project_with_distributed_budget, budget_group_utils
):
    project_name, group_id = project_with_distributed_budget

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    modal = details_page.open_budget_config_modal()
    modal.should_have_platform_hard_limit(PLATFORM_HARD_TEXT)

    modal.enter_platform_hard_limit(SUB_MINIMUM_PLATFORM_TEXT)

    modal.should_not_have_platform_hard_limit(PLATFORM_HARD_TEXT)
    modal.enter_limits(
        ("platform_soft", SUB_MINIMUM_PLATFORM_SOFT_TEXT),
        ("cli_hard", SUB_MINIMUM_CLI_HARD_TEXT),
    )
    modal.save_budget_config()
    hard_limits = budget_group_utils.get_category_budgets(group_id)
    platform_budget = hard_limits["platform"]
    assert_that(
        hard_limits["cli"],
        close_to(SUB_MINIMUM_CLI_HARD_AMOUNT, AMOUNT_TOLERANCE),
        "Saved CLI hard limit should be the typed compensating amount",
    )
    assert_that(
        platform_budget,
        close_to(PLATFORM_SLIDER_MIN_AMOUNT, AMOUNT_TOLERANCE),
        "Saved Platform hard limit should be raised to the minimum share (pct 0.01 of 1000)",
    )
