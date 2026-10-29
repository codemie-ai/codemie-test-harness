"""API tests for the cost center budget rollup.

GET /v1/admin/cost-centers/{costCenterId}/budget-rollup sums the budgets of every project
linked to a cost center, per category and overall. It needs ENABLE_USER_MANAGEMENT on the
target environment and a build that includes the rollup endpoint.

Covered cases:
    TC-001  Per-category and overall sums across linked projects (AC-1, AC-2, AC-5)
    TC-003  A project budget change shows on the next request (AC-3)
    TC-004  A cost center without projects returns zero totals (AC-4)
    TC-008  Rows with a different reset window are excluded, mixed periods null the limit
    TC-009  A member in two linked projects is counted once, both spends are in the total
    TC-011  Cost center spend equals the sum of its projects' spend after real spend
"""

import datetime
import logging

import pytest
from hamcrest import (
    all_of,
    assert_that,
    close_to,
    contains_inanyorder,
    empty,
    equal_to,
    greater_than,
    greater_than_or_equal_to,
    is_,
    less_than_or_equal_to,
    none,
    not_none,
)

from codemie_test_harness.tests.test_data.budget_test_data import budget_chat_prompt
from codemie_test_harness.tests.test_data.cost_center_rollup_test_data import (
    AMOUNT_TOLERANCE,
    DEFAULT_RESET_WINDOW,
    PROJECT_A_ALL_CATEGORIES,
    PROJECT_A_PLATFORM_ONLY,
    PROJECT_B_PLATFORM_AND_CLI,
    PROJECT_B_PLATFORM_ONLY,
    SHORT_RESET_WINDOW,
    SINGLE_PROJECT_PLATFORM,
    SINGLE_PROJECT_PLATFORM_AFTER_UPDATE,
    SPEND_ROUNDING_TOLERANCE,
    SPENDING_PLATFORM_ONLY,
)
from codemie_test_harness.tests.utils.project_utils import ProjectUtils

logger = logging.getLogger(__name__)

_SPENDING_PROPAGATION_WAIT = 600


def _collect_platform_budget_items(
    admin_project_utils, lite_llm_budget_utils, admin_spend_tracking_utils, *budgets
):
    """Wait for each project's platform key spend, collect it, and return the projects' own
    platform budget items (in the order of ``budgets``) as the projects API reports them."""
    for budget in budgets:
        logger.info(
            "Waiting for platform key spend (alias=%s)", budget.alias("platform")
        )
        key_info = lite_llm_budget_utils.wait_for_key_alias_spending(
            budget.alias("platform")
        )
        assert_that(
            key_info,
            not_none(),
            f"LiteLLM platform key spend not recorded for {budget.project_name}.",
        )
        assert_that(float(key_info["spend"]), greater_than(0))

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends()

    today = datetime.date.today()
    items = []
    for budget in budgets:
        admin_spend_tracking_utils.wait_for_project_spends(
            budget.project_name, today, today
        )
        item = admin_project_utils.wait_for_project_budget_spending(
            budget.project_name, "platform", timeout=_SPENDING_PROPAGATION_WAIT
        )
        assert_that(
            item,
            not_none(),
            f"Platform spend of {budget.project_name} did not reach the projects API.",
        )
        assert_that(float(item.current_spending), greater_than(0))
        items.append(item)
    return items


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_rollup_sums_budgets_per_category_and_overall_across_linked_projects(
    cost_center, cost_center_budget_projects, cost_center_utils
):
    cc_id = cost_center()
    cost_center_budget_projects.create(cc_id, PROJECT_A_ALL_CATEGORIES)
    cost_center_budget_projects.create(cc_id, PROJECT_B_PLATFORM_ONLY)

    summary = cost_center_utils.get_budget_rollup(cc_id)

    assert_that(
        [b.budget_category for b in summary.budgets],
        contains_inanyorder("platform", "cli", "premium_models"),
        "The rollup must list exactly the categories that have budgets.",
    )
    platform = cost_center_utils.rollup_category(summary, "platform")
    cli = cost_center_utils.rollup_category(summary, "cli")
    premium = cost_center_utils.rollup_category(summary, "premium_models")

    a, b = PROJECT_A_ALL_CATEGORIES, PROJECT_B_PLATFORM_ONLY
    assert_that(
        platform.max_budget,
        close_to(
            a["platform"]["max_budget"] + b["platform"]["max_budget"], AMOUNT_TOLERANCE
        ),
        "Platform max_budget must be project A plus project B.",
    )
    assert_that(
        platform.soft_budget,
        close_to(
            a["platform"]["soft_budget"] + b["platform"]["soft_budget"],
            AMOUNT_TOLERANCE,
        ),
        "Platform soft_budget must be project A plus project B.",
    )
    assert_that(
        cli.max_budget,
        close_to(a["cli"]["max_budget"], AMOUNT_TOLERANCE),
        "CLI max_budget must be project A alone: project B has no CLI budget.",
    )
    assert_that(
        cli.soft_budget,
        close_to(a["cli"]["soft_budget"], AMOUNT_TOLERANCE),
        "CLI soft_budget must be project A alone: project B has no CLI budget.",
    )
    assert_that(
        premium.max_budget,
        close_to(a["premium_models"]["max_budget"], AMOUNT_TOLERANCE),
        "Premium models max_budget must be project A alone.",
    )
    assert_that(
        premium.soft_budget,
        close_to(a["premium_models"]["soft_budget"], AMOUNT_TOLERANCE),
        "Premium models soft_budget must be project A alone.",
    )
    assert_that(
        summary.budget_limit,
        close_to(sum(entry.max_budget for entry in summary.budgets), AMOUNT_TOLERANCE),
        "budget_limit must equal the sum of the category max_budget.",
    )
    assert_that(summary.current_spending, greater_than_or_equal_to(0.0))
    assert_that(
        summary.total_percent,
        all_of(greater_than_or_equal_to(0.0), less_than_or_equal_to(100.0)),
        "total_percent must stay within 0..100.",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_rollup_reflects_project_budget_change_on_next_request(
    cost_center,
    cost_center_budget_projects,
    cost_center_utils,
    admin_project_budget_utils,
):
    cc_id = cost_center()
    budget = cost_center_budget_projects.create(cc_id, SINGLE_PROJECT_PLATFORM)
    before = SINGLE_PROJECT_PLATFORM["platform"]
    after = SINGLE_PROJECT_PLATFORM_AFTER_UPDATE["platform"]

    summary_before = cost_center_utils.get_budget_rollup(cc_id)
    platform_before = cost_center_utils.rollup_category(summary_before, "platform")
    assert_that(platform_before, not_none())
    assert_that(
        platform_before.max_budget,
        close_to(before["max_budget"], AMOUNT_TOLERANCE),
        "The first read must show the initial platform budget.",
    )

    admin_project_budget_utils.update_budget_group_category(
        budget.group_id,
        "platform",
        max_budget=after["max_budget"],
        soft_budget=after["soft_budget"],
    )

    summary_after = cost_center_utils.get_budget_rollup(cc_id)
    platform_after = cost_center_utils.rollup_category(summary_after, "platform")
    assert_that(platform_after, not_none())
    assert_that(
        platform_after.max_budget,
        close_to(after["max_budget"], AMOUNT_TOLERANCE),
        "The next read must show the updated platform max_budget, not the old one.",
    )
    assert_that(
        platform_after.soft_budget,
        close_to(after["soft_budget"], AMOUNT_TOLERANCE),
        "The next read must show the updated platform soft_budget.",
    )
    assert_that(
        summary_after.budget_limit,
        close_to(after["max_budget"], AMOUNT_TOLERANCE),
        "budget_limit must follow the updated budget.",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_rollup_of_cost_center_without_linked_projects_returns_zero_totals(
    cost_center, cost_center_utils
):
    cc_id = cost_center()

    summary = cost_center_utils.get_budget_rollup(cc_id)

    assert_that(summary.current_spending, equal_to(0.0))
    assert_that(summary.budget_limit, is_(none()))
    assert_that(summary.total_percent, equal_to(0.0))
    assert_that(summary.budgets, is_(empty()))


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_rollup_excludes_rows_with_other_reset_window_and_nulls_limit_for_mixed_periods(
    cost_center, cost_center_budget_projects, cost_center_utils
):
    cc_id = cost_center()
    cost_center_budget_projects.create(
        cc_id, PROJECT_A_PLATFORM_ONLY, budget_duration=DEFAULT_RESET_WINDOW
    )
    cost_center_budget_projects.create(
        cc_id, PROJECT_B_PLATFORM_AND_CLI, budget_duration=SHORT_RESET_WINDOW
    )

    summary = cost_center_utils.get_budget_rollup(cc_id)

    platform = cost_center_utils.rollup_category(summary, "platform")
    cli = cost_center_utils.rollup_category(summary, "cli")
    assert_that(platform, not_none())
    assert_that(cli, not_none())
    assert_that(platform.budget_duration, equal_to(DEFAULT_RESET_WINDOW))
    assert_that(
        platform.excluded_count,
        equal_to(1),
        "Project B's platform row has another reset window and must be excluded.",
    )
    assert_that(
        platform.max_budget,
        close_to(PROJECT_A_PLATFORM_ONLY["platform"]["max_budget"], AMOUNT_TOLERANCE),
        "Platform max_budget must be project A alone.",
    )
    assert_that(
        platform.soft_budget,
        close_to(PROJECT_A_PLATFORM_ONLY["platform"]["soft_budget"], AMOUNT_TOLERANCE),
        "Platform soft_budget must be project A alone.",
    )
    assert_that(cli.budget_duration, equal_to(SHORT_RESET_WINDOW))
    assert_that(
        summary.budget_limit,
        is_(none()),
        "budget_limit must be null when the categories use different reset windows.",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.timeout(1500)
@pytest.mark.api
def test_rollup_counts_member_of_two_projects_once_and_sums_both_projects_spend(
    keycloak_user,
    user_client,
    user_assistant,
    user_assistant_utils,
    cost_center,
    cost_center_budget_projects,
    cost_center_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    # The user creates both projects, so each has this user as its only member. A project
    # delete removes the assistants in it, so only the last assistant needs fixture cleanup.
    cc_id = cost_center()
    user_projects = ProjectUtils(user_client)
    budget_a = cost_center_budget_projects.create(
        cc_id,
        SPENDING_PLATFORM_ONLY,
        creator_utils=user_projects,
        track_members=True,
    )
    budget_b = cost_center_budget_projects.create(
        cc_id,
        SPENDING_PLATFORM_ONLY,
        creator_utils=user_projects,
        track_members=True,
    )
    cost_center_budget_projects.wait_until_budgets_usable(budget_a, budget_b)

    user_assistant_utils.ask_assistant(
        user_assistant(project_name=budget_a.project_name), budget_chat_prompt()
    )
    user_assistant_utils.ask_assistant(
        user_assistant(project_name=budget_b.project_name), budget_chat_prompt()
    )

    item_a, item_b = _collect_platform_budget_items(
        admin_project_utils,
        lite_llm_budget_utils,
        admin_spend_tracking_utils,
        budget_a,
        budget_b,
    )
    assert_that(item_a.member_count, equal_to(1), "Project A must have one member.")
    assert_that(item_b.member_count, equal_to(1), "Project B must have one member.")

    summary = cost_center_utils.get_budget_rollup(cc_id)

    platform = cost_center_utils.rollup_category(summary, "platform")
    assert_that(platform, not_none())
    assert_that(
        platform.member_count,
        equal_to(1),
        "The user in both projects must be counted once, not once per project.",
    )
    assert_that(
        platform.current_spending,
        close_to(
            float(item_a.current_spending) + float(item_b.current_spending),
            SPEND_ROUNDING_TOLERANCE,
        ),
        "Platform spend must include the user's spend in both projects.",
    )
    assert_that(
        summary.current_spending,
        close_to(
            float(item_a.current_spending) + float(item_b.current_spending),
            SPEND_ROUNDING_TOLERANCE,
        ),
        "Overall spend must include the user's spend in both projects.",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.timeout(1500)
@pytest.mark.api
def test_rollup_spend_equals_sum_of_project_spend_after_real_spend_and_collection(
    keycloak_user_1,
    keycloak_user_2,
    user1_client,
    user2_client,
    user1_assistant,
    user2_assistant,
    user1_assistant_utils,
    user2_assistant_utils,
    cost_center,
    cost_center_budget_projects,
    cost_center_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    # The test uses no API keys, so the rollup's key spend share is zero and its overall
    # spend is the sum of the category spend.
    cc_id = cost_center()
    budget_a = cost_center_budget_projects.create(
        cc_id,
        SPENDING_PLATFORM_ONLY,
        creator_utils=ProjectUtils(user1_client),
        track_members=True,
    )
    budget_b = cost_center_budget_projects.create(
        cc_id,
        SPENDING_PLATFORM_ONLY,
        creator_utils=ProjectUtils(user2_client),
        track_members=True,
    )
    cost_center_budget_projects.wait_until_budgets_usable(budget_a, budget_b)

    user1_assistant_utils.ask_assistant(
        user1_assistant(project_name=budget_a.project_name), budget_chat_prompt()
    )
    user2_assistant_utils.ask_assistant(
        user2_assistant(project_name=budget_b.project_name), budget_chat_prompt()
    )

    item_a, item_b = _collect_platform_budget_items(
        admin_project_utils,
        lite_llm_budget_utils,
        admin_spend_tracking_utils,
        budget_a,
        budget_b,
    )

    summary = cost_center_utils.get_budget_rollup(cc_id)

    assert_that(
        summary.current_spending,
        close_to(
            float(item_a.current_spending) + float(item_b.current_spending),
            SPEND_ROUNDING_TOLERANCE,
        ),
        "Cost center spend must equal the sum of both projects' own spend.",
    )
    platform = cost_center_utils.rollup_category(summary, "platform")
    assert_that(platform, not_none())
    assert_that(
        platform.current_spending,
        close_to(
            float(item_a.current_spending) + float(item_b.current_spending),
            SPEND_ROUNDING_TOLERANCE,
        ),
        "Platform spend must equal the sum of both projects' own platform spend.",
    )
