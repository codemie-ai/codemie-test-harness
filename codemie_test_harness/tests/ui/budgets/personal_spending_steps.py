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

"""Scenario steps of the 'Your personal spending' UI tests.

The tests in ``test_personal_spending_project_rows.py`` read as lists of calls to the page object
and to the functions here. These read and check the same user's API response and set up the
spend; what the page shows is checked by ``PersonalSpendingPage``.
"""

from dataclasses import dataclass

from hamcrest import (
    assert_that,
    close_to,
    equal_to,
    greater_than,
    greater_than_or_equal_to,
    is_not,
    not_none,
)

from codemie_test_harness.tests.test_data.budget_test_data import project_key_alias
from codemie_test_harness.tests.test_data.budget_usage_project_rows_test_data import (
    CLI_ROW_SUFFIX,
    MIN_VISIBLE_SPEND,
    PERCENT_TOLERANCE,
    SCALED_PROJECT_LIMIT,
)
from codemie_test_harness.tests.ui.pageobject.budgets.personal_spending_page import (
    PersonalSpendingPage,
)
from codemie_test_harness.tests.ui.test_data.personal_spending_test_data import (
    HIDDEN_COLUMN_ID,
    SPENT_CATEGORY,
)
from codemie_test_harness.tests.utils.budget_usage_utils import (
    BudgetUsageUtils,
    expected_total,
    generate_member_spend,
    row_names,
    wait_for_settled_key_spend,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.proxy_utils import ProxyUtils


def _project_name(budget) -> str:
    project_name, _ = budget
    return project_name


def _cli_label(budget) -> str:
    return f"{_project_name(budget)}{CLI_ROW_SUFFIX}"


# ---------------------------------------------------------------------------
# The user's own budget_usage response
# ---------------------------------------------------------------------------


@dataclass
class BudgetUsageResponse:
    """The user's budget_usage response, read through the SDK."""

    rows: list[dict]
    names: list[str]
    shown_labels: list[str]
    hidden_label: str


def read_budget_usage(client) -> BudgetUsageResponse:
    response = client.analytics.get_budget_usage()
    return BudgetUsageResponse(
        rows=response.data.rows,
        names=row_names(response.data.rows),
        shown_labels=[
            column.label
            for column in response.data.columns
            if column.id != HIDDEN_COLUMN_ID
        ],
        hidden_label=next(
            column.label
            for column in response.data.columns
            if column.id == HIDDEN_COLUMN_ID
        ),
    )


def wait_for_cli_row_to_be_listed(client, budget):
    """The API lists the cli category row of the project."""
    assert_that(
        BudgetUsageUtils(client).wait_for_row(_cli_label(budget)),
        not_none(),
        "Precondition failed: the cli category row is not listed by the API yet",
    )


def read_rows(client) -> list[dict]:
    return BudgetUsageUtils(client).get_rows()


def assert_api_lists_platform_and_cli_rows_of_the_project(
    api: BudgetUsageResponse, budget
):
    project_name = _project_name(budget)
    assert_that(
        [name for name in api.names if name.startswith(project_name)],
        equal_to([project_name, _cli_label(budget)]),
        "The API must list the platform and cli rows of the project, in this order",
    )


# ---------------------------------------------------------------------------
# Default project (TC-020)
# ---------------------------------------------------------------------------


def assert_project_is_not_the_default_before_the_admin_sets_it(
    rows: list[dict], budget
):
    flagged = [row["project_name"] for row in rows if row["is_default"]]
    assert_that(
        flagged,
        is_not(equal_to([_project_name(budget), _cli_label(budget)])),
        "Precondition failed: the project is already the default before the admin sets it, "
        "so the second state would prove the same state twice",
    )


def make_project_the_default(user_utils, client, budget):
    """The admin stores the project as the user's default project."""
    user_utils.set_default_project(
        client.users.about_me().user_id, _project_name(budget)
    )


def wait_for_default_project_rows_first(client) -> list[dict]:
    return BudgetUsageUtils(client).wait_for_rows_where(
        lambda rows: bool(rows) and rows[0]["is_default"] is True
    )


def assert_default_project_rows_come_first_and_only_they_are_flagged(
    rows: list[dict], budget
):
    expected_names = [_project_name(budget), _cli_label(budget)]
    assert_that(
        row_names(rows[:2]),
        equal_to(expected_names),
        "The default project's rows must come first in the API response",
    )
    assert_that(
        [row["project_name"] for row in rows if row["is_default"]],
        equal_to(expected_names),
        "Exactly the default project's rows must be flagged is_default",
    )


def assert_setting_the_default_changed_which_rows_are_flagged(
    rows_with_default: list[dict], rows_without_default: list[dict]
):
    assert_that(
        [row["is_default"] for row in rows_with_default],
        is_not(equal_to([row["is_default"] for row in rows_without_default])),
        "Setting the default project must change which rows the API flags",
    )


# ---------------------------------------------------------------------------
# Combined project total for a user who has not spent (TC-021)
# ---------------------------------------------------------------------------


@dataclass
class OtherMemberSpend:
    """Spend of the other project member on the spent category, settled at the provider."""

    member_spend: float
    project_total: float


def switch_enforcement_off(admin_project_utils, budget):
    """member_override_ui_setup switches enforcement on; this case is about enforcement off."""
    switched = admin_project_utils.set_enforce_member_spend_limits(
        _project_name(budget), False
    )
    assert_that(
        switched.enforce_member_spend_limits,
        equal_to(False),
        "Precondition failed: enforcement was not switched off",
    )


def generate_spend_as_other_member(
    budget, other_member, default_llm, lite_llm_budget_utils
) -> OtherMemberSpend:
    """The other member spends on the cli category; the viewer does not.

    Settled before anything reads budget_usage: the first read stores its values for the
    staleness window.
    """
    member_email, member_password, member_id = other_member
    project_name = _project_name(budget)
    member_spend = generate_member_spend(
        ProxyUtils(get_client(username=member_email, password=member_password)),
        lite_llm_budget_utils,
        default_llm.base_name,
        project_name,
        member_id,
        category=SPENT_CATEGORY,
    )
    return OtherMemberSpend(
        member_spend=member_spend,
        project_total=wait_for_settled_key_spend(
            lite_llm_budget_utils, project_key_alias(project_name, SPENT_CATEGORY)
        ),
    )


def assert_other_member_spend_is_recorded(spend: OtherMemberSpend):
    assert_that(
        spend.member_spend,
        greater_than_or_equal_to(MIN_VISIBLE_SPEND),
        "The stand did not record enough spend for the other member",
    )
    assert_that(
        spend.project_total,
        greater_than(0),
        "The project key shows no spend, so there is no combined total to display",
    )


def wait_for_viewer_row_with_combined_total(client, budget) -> dict:
    viewer_row = BudgetUsageUtils(client).wait_for_row_where(
        _cli_label(budget), lambda row: row["total"] > 0
    )
    assert_that(viewer_row, not_none())
    return viewer_row


def assert_viewer_has_not_spent_and_sees_the_combined_project_total(
    viewer_row: dict, spend: OtherMemberSpend
):
    assert_that(
        viewer_row["budget_limit"],
        equal_to(SCALED_PROJECT_LIMIT),
        "Precondition failed: the spent category does not have the scaled-down limit, "
        "so it is not the denominator the combined total was computed with",
    )
    assert_that(
        viewer_row["current_spending"],
        equal_to(0.0),
        "Precondition failed: the viewer must not have spent",
    )
    assert_that(
        viewer_row["total"],
        close_to(
            expected_total(spend.project_total, viewer_row["budget_limit"]),
            PERCENT_TOLERANCE,
        ),
        "Precondition failed: the API total is not the combined project spend over the limit",
    )
    assert_that(
        PersonalSpendingPage.format_percentage(viewer_row["total"]),
        is_not(PersonalSpendingPage.format_percentage(0)),
        "Precondition failed: the combined total is not visible at the table's precision",
    )


def assert_spent_category_row_keeps_its_combined_total(api_rows: list[dict], budget):
    spent_row = next(
        row for row in api_rows if row["project_name"] == _cli_label(budget)
    )
    assert_that(
        spent_row["total"],
        greater_than(0),
        "The spent category row lost its combined total while the page was opened",
    )
