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

The tests in ``test_personal_spending_project_rows.py`` and ``test_personal_spending_categories.py``
read as lists of calls to the page object
and to the functions here. These read and check the same user's API response and set up the
spend; what the page shows is checked by ``PersonalSpendingPage``.
"""

from dataclasses import dataclass
from decimal import Decimal

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
    SPEND_PARITY_TOLERANCE,
)
from codemie_test_harness.tests.ui.pageobject.budgets.personal_spending_page import (
    PersonalSpendingPage,
)
from codemie_test_harness.tests.ui.test_data.personal_spending_test_data import (
    HIDDEN_COLUMN_ID,
    HIDDEN_COLUMN_IDS,
    PERSONAL_BUDGETS,
    PLATFORM_ASSISTANT_SPEND_MAX_BATCHES,
    PERSONAL_ROW_POLL_INTERVAL,
    PERSONAL_ROW_WAIT_TIMEOUT,
    SPENT_CATEGORY,
    LimitLabelRow,
)
from codemie_test_harness.tests.utils.budget_usage_utils import (
    BudgetUsageUtils,
    expected_total,
    generate_member_spend,
    generate_personal_assistant_spend,
    generate_personal_spend,
    row_names,
    settle_customer_spend,
    wait_for_settled_key_spend,
)
from codemie_test_harness.tests.utils.assistant_utils import AssistantUtils
from codemie_test_harness.tests.utils.base_utils import poll_until
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
            if column.id not in HIDDEN_COLUMN_IDS
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


def switch_enforcement(admin_project_utils, budget, enabled: bool):
    """Switch enforcement of member spend limits of the project and check the reply says so."""
    switched = admin_project_utils.set_enforce_member_spend_limits(
        _project_name(budget), enabled
    )
    assert_that(
        switched.enforce_member_spend_limits,
        equal_to(enabled),
        f"Precondition failed: enforcement was not switched {'on' if enabled else 'off'}",
    )


def switch_enforcement_off(admin_project_utils, budget):
    """member_override_ui_setup switches enforcement on; this case is about enforcement off."""
    switch_enforcement(admin_project_utils, budget, False)


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


def find_cli_row(api_rows: list[dict], budget) -> dict:
    """The spent (cli) category row of the project."""
    return next(row for row in api_rows if row["project_name"] == _cli_label(budget))


def read_listed_cli_row(client, budget) -> dict:
    """The spent category row of the project, once the API lists it."""
    row = BudgetUsageUtils(client).wait_for_row(_cli_label(budget))
    assert_that(
        row,
        not_none(),
        "Precondition failed: the cli category row is not listed by the API yet",
    )
    return row


def assert_other_member_spend_moved_only_the_project_percentage(
    row_before: dict, row_after: dict
):
    """Another member's spend raises the project percentage; the viewer's own spend and limit stay.

    'Your spending' is current_spending and 'Available' is derived from it and budget_limit only,
    so neither moves when the percentage does.
    """
    assert_that(
        row_after["current_spending"],
        equal_to(row_before["current_spending"]),
        "The viewer's own spending must not move with another member's spend",
    )
    assert_that(
        row_after["budget_limit"],
        equal_to(row_before["budget_limit"]),
        "The limit Available is derived from must not move with another member's spend",
    )
    assert_that(
        row_after["total"],
        greater_than(row_before["total"]),
        "The project percentage must rise with another member's spend",
    )


# ---------------------------------------------------------------------------
# A user with no project: own spend on every personal default budget
# ---------------------------------------------------------------------------


@dataclass
class PersonalSpend:
    """The user's settled LiteLLM customer spend on one personal budget, and the row showing it."""

    category: str
    row_name: str
    customer_id: str
    spend: float


def generate_personal_spend_on_every_category(
    user, assistant, default_llm, lite_llm_budget_utils
) -> list[PersonalSpend]:
    """The user spends on its personal platform, cli and premium budgets.

    Platform: chat with ``assistant``, the user's assistant in its personal project. Cli and
    premium: /v1/messages with the CLI client header and no project header. Every category is
    spent on first and each customer is settled afterwards, so the returned spend of each
    category is a value LiteLLM no longer changes.
    """
    proxy_utils = ProxyUtils(user.client)
    assistant_utils = AssistantUtils(user.client)
    spends = []
    for budget in PERSONAL_BUDGETS:
        customer_id = f"{user.email}{budget.customer_suffix}"
        if budget.client_header is None:
            generate_personal_assistant_spend(
                assistant_utils,
                assistant,
                lite_llm_budget_utils,
                customer_id,
                max_batches=PLATFORM_ASSISTANT_SPEND_MAX_BATCHES,
            )
        else:
            generate_personal_spend(
                proxy_utils,
                lite_llm_budget_utils,
                budget.model or default_llm.base_name,
                customer_id,
                budget.client_header,
            )
        spends.append(
            PersonalSpend(
                category=budget.category,
                row_name=f"{user.email}{budget.row_suffix}",
                customer_id=customer_id,
                spend=0.0,
            )
        )
    for spend in spends:
        spend.spend = settle_customer_spend(lite_llm_budget_utils, spend.customer_id)
    return spends


def assert_personal_spend_is_recorded_on_every_category(spends: list[PersonalSpend]):
    for spend in spends:
        assert_that(
            spend.spend,
            greater_than_or_equal_to(MIN_VISIBLE_SPEND),
            f"Precondition failed: the stand did not record enough {spend.category} spend "
            "for the user",
        )


def _wait_for_row_with_customer_spend(
    usage: BudgetUsageUtils, spend: PersonalSpend, lite_llm_budget_utils
) -> tuple[dict | None, float]:
    """Poll until the row shows the customer spend read right after it; both re-read each time.

    Returns ``(row, customer_spend)`` of the last attempt, matched or not.
    """
    return poll_until(
        lambda: (
            usage.get_row(spend.row_name),
            lite_llm_budget_utils.get_customer_spend(spend.customer_id),
        ),
        lambda result: result[0] is not None
        and abs(result[0]["current_spending"] - result[1]) <= SPEND_PARITY_TOLERANCE,
        timeout=PERSONAL_ROW_WAIT_TIMEOUT,
        interval=PERSONAL_ROW_POLL_INTERVAL,
    )


def wait_for_personal_rows_with_own_spend(
    client, spends: list[PersonalSpend], lite_llm_budget_utils
) -> list[dict]:
    """The row of every personal budget, once the API shows the user's customer spend on it."""
    usage = BudgetUsageUtils(client)
    rows = []
    for spend in spends:
        row, customer_spend = _wait_for_row_with_customer_spend(
            usage, spend, lite_llm_budget_utils
        )
        assert_that(
            row, not_none(), f"Precondition failed: {spend.row_name} is not listed"
        )
        assert_that(
            row["current_spending"],
            close_to(customer_spend, SPEND_PARITY_TOLERANCE),
            f"Precondition failed: the API does not show the user's settled {spend.category} "
            "spend",
        )
        spend.spend = customer_spend
        rows.append(row)
    return rows


def _has_more_than_two_decimals(value: float) -> bool:
    exact = Decimal(str(value))
    return exact != exact.quantize(Decimal("0.01"))


def find_personal_platform_row(rows: list[dict], email: str) -> dict:
    """The personal platform row: its label is the user's e-mail alone."""
    platform_row = next((row for row in rows if row["project_name"] == email), None)
    assert_that(
        platform_row, not_none(), f"The personal platform row {email} is not listed"
    )
    return platform_row


def assert_platform_spend_has_more_than_two_decimals(platform_row: dict):
    """The rounding to cents is only exercised by a platform spend that is not a whole cent."""
    assert_that(
        _has_more_than_two_decimals(platform_row["current_spending"]),
        equal_to(True),
        "Precondition failed: the user's platform spend "
        f"{platform_row['current_spending']} has no more than 2 decimals",
    )


def assert_api_lists_only_the_personal_rows(
    api_rows: list[dict], personal_rows: list[dict]
):
    """The API, read after the page opened, lists only the personal rows, with their settled spend.

    Compared regardless of order; the order of the table is checked against the API response.
    """
    assert_that(
        sorted((row["project_name"], row["current_spending"]) for row in api_rows),
        equal_to(
            sorted(
                (row["project_name"], row["current_spending"]) for row in personal_rows
            )
        ),
        "The user's personal rows or their spend changed while the page was opened",
    )


# ---------------------------------------------------------------------------
# Usage block of the project rows: shared limit, label and tooltip
# ---------------------------------------------------------------------------


def project_row_names(budget) -> list[str]:
    """Labels of the project's platform and cli rows, in the order the API lists them."""
    return [_project_name(budget), _cli_label(budget)]


def _project_rows(rows: list[dict], budget) -> list[dict]:
    names = project_row_names(budget)
    return [row for row in rows if row["project_name"] in names]


def _is_set_up_as(rows: list[dict], budget, shared: bool, default: bool | None) -> bool:
    project_rows = _project_rows(rows, budget)
    return len(project_rows) == len(project_row_names(budget)) and all(
        row["is_shared_limit"] is shared
        and (default is None or row["is_default"] is default)
        for row in project_rows
    )


def wait_for_project_rows_set_up_as(
    client, budget, shared: bool, default: bool | None = None
) -> list[dict]:
    """The project's rows once both are listed with this is_shared_limit (and is_default)."""
    rows = BudgetUsageUtils(client).wait_for_rows_where(
        lambda listed: _is_set_up_as(listed, budget, shared, default)
    )
    return _project_rows(rows, budget)


def assert_project_rows_are_set_up_as(
    project_rows: list[dict], budget, shared: bool, default: bool | None = None
):
    assert_that(
        row_names(project_rows),
        equal_to(project_row_names(budget)),
        "Precondition failed: the API does not list the platform and cli rows of the project",
    )
    assert_that(
        [row["is_shared_limit"] for row in project_rows],
        equal_to([shared] * len(project_rows)),
        "Precondition failed: the rows do not carry the expected is_shared_limit",
    )
    if default is not None:
        assert_that(
            [row["is_default"] for row in project_rows],
            equal_to([default] * len(project_rows)),
            "Precondition failed: the rows do not carry the expected is_default",
        )


def wait_for_shared_project_rows(client, budget) -> list[dict]:
    """The project's rows, listed with a shared limit (enforcement off)."""
    wait_for_cli_row_to_be_listed(client, budget)
    project_rows = wait_for_project_rows_set_up_as(client, budget, shared=True)
    assert_project_rows_are_set_up_as(project_rows, budget, shared=True)
    return project_rows


def set_up_project_rows(
    admin_project_utils, user_utils, client, budget, row_kind: LimitLabelRow
) -> list[dict]:
    """Set the project up as this kind of row and return its rows once the API reflects it."""
    wait_for_cli_row_to_be_listed(client, budget)
    switch_enforcement(
        admin_project_utils, budget, row_kind.enforce_member_spend_limits
    )
    if row_kind.is_default_project:
        make_project_the_default(user_utils, client, budget)
    project_rows = wait_for_project_rows_set_up_as(
        client,
        budget,
        shared=row_kind.is_shared_limit,
        default=row_kind.is_default_project,
    )
    assert_project_rows_are_set_up_as(
        project_rows,
        budget,
        shared=row_kind.is_shared_limit,
        default=row_kind.is_default_project,
    )
    return project_rows
