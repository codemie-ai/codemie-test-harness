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

"""Scenario steps of the per-project rows on the personal spending page.

The tests in ``tests/budgets/test_budget_usage_project_rows.py`` read as lists of calls to the
functions here. Setup steps create projects and spend, ``assert_*`` steps hold the checks with
their failure messages. The building blocks they use (``BudgetUsageUtils``, spend generation,
waits, formulas) live in ``budget_usage_utils``.
"""

from dataclasses import dataclass

from hamcrest import (
    assert_that,
    close_to,
    empty,
    equal_to,
    greater_than,
    greater_than_or_equal_to,
    has_item,
    has_items,
    is_not,
    less_than,
    none,
    not_none,
    only_contains,
)

from codemie_test_harness.tests.test_data.budget_member_override_test_data import (
    MEMBER_OVERRIDE_MAX,
    MEMBER_OVERRIDE_SOFT,
)
from codemie_test_harness.tests.test_data.budget_test_data import (
    MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE,
)
from codemie_test_harness.tests.test_data.budget_usage_project_rows_test_data import (
    BUDGET_USAGE_COLUMN_IDS,
    BUDGET_USAGE_ROW_KEYS,
    CLI_ROW_SUFFIX,
    DISTINCT_SPEND_GAP,
    MIN_VISIBLE_SPEND,
    MONEY_TOLERANCE,
    PERCENT_TOLERANCE,
    PREMIUM_ROW_SUFFIX,
    ROUNDING_TOLERANCE,
    SCALED_OVERRIDE_EQUAL_TO_LIMIT_SOFT,
    SCALED_OVERRIDE_MAX,
    SCALED_OVERRIDE_SOFT,
    SCALED_PLATFORM_CATEGORIES,
    SCALED_PROJECT_LIMIT,
    SCALED_SHARE_OF_REST,
    SCALED_SHARE_OF_TWO,
    SPEND_PARITY_TOLERANCE,
    USER_PROJECT_SPENDING_COLUMN_IDS,
    USER_PROJECT_SPENDING_ROW_KEYS,
    VISIBLE_AT_TWO_DECIMALS,
)
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.budget_usage_utils import (
    BudgetUsageUtils,
    MemberProject,
    expected_override_limit,
    expected_total,
    generate_member_platform_spend,
    generate_member_spend,
    get_member_allocations,
    member_customer_spend,
    row_names,
    wait_for_member_allocation,
    wait_for_row_matching,
    wait_for_settled_key_spend,
)


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------


def _email(credentials) -> str:
    email, _ = credentials
    return email


def _personal_labels(credentials) -> list[str]:
    email = _email(credentials)
    return [email, f"{email}{CLI_ROW_SUFFIX}", f"{email}{PREMIUM_ROW_SUFFIX}"]


def _names_with_prefix(names: list[str], prefix: str) -> list[str]:
    return [name for name in names if name.startswith(prefix)]


def create_member_project(
    member_project_factory, member_client, member_credentials, enforce: bool = True
) -> MemberProject:
    """Project owned by user1 with a platform budget; the credentials' user is its member."""
    return member_project_factory(
        member_client, _email(member_credentials), enforce=enforce
    )


def read_project_hard_limit(
    admin_project_budget_utils, project: MemberProject
) -> float:
    """Hard limit (max budget) of the project's platform budget."""
    return admin_project_budget_utils.get_budget(project.platform_budget_id)[
        "max_budget"
    ]


def switch_enforcement(user1_project_utils, project: MemberProject, enabled: bool):
    """Switch member spend limit enforcement of the project and check the reply says so."""
    switched = user1_project_utils.set_enforce_member_spend_limits(
        project.name, enabled
    )
    assert_that(
        switched.enforce_member_spend_limits,
        equal_to(enabled),
        f"Precondition failed: enforcement was not switched {'on' if enabled else 'off'}",
    )


def set_project_as_default(user_utils, user_id: str, project: MemberProject):
    """The admin stores the project as the user's default project."""
    user_utils.set_default_project(user_id, project.name)


def wait_for_default_project_row_first(usage: BudgetUsageUtils, project: MemberProject):
    """Rows of the response once the project's row is the first one."""
    return usage.wait_for_rows_where(
        lambda rows: bool(rows) and rows[0]["project_name"] == project.name
    )


def override_member_budget(admin_project_budget_utils, project: MemberProject):
    """The admin overrides the member's budget with the standard override."""
    admin_project_budget_utils.override_member(
        project.platform_budget_id,
        project.member_id,
        MEMBER_OVERRIDE_MAX,
        MEMBER_OVERRIDE_SOFT,
    )


def clear_member_override(admin_project_budget_utils, project: MemberProject):
    """The admin clears the member's budget override."""
    admin_project_budget_utils.clear_member_override(
        project.platform_budget_id, project.member_id
    )


# ---------------------------------------------------------------------------
# Default project, order and is_default (TC-001, TC-010)
# ---------------------------------------------------------------------------


def wait_for_project_row_and_personal_row(
    user_usage: BudgetUsageUtils, project: MemberProject, user_credentials
):
    """Both the project row and the personal platform row are listed."""
    email = _email(user_credentials)
    assert_that(
        user_usage.wait_for_row(project.name),
        not_none(),
        f"Project row '{project.name}' missing on the personal spending page",
    )
    assert_that(
        user_usage.wait_for_row_names_among([email], count=1),
        equal_to([email]),
        "Precondition failed: the personal platform row is not listed yet",
    )


def assert_personal_row_first_and_flagged_while_personal_is_default(
    rows: list[dict], project: MemberProject, user_credentials
):
    """With no stored default the personal row comes first and is the one flagged is_default."""
    email = _email(user_credentials)
    names = row_names(rows)
    flags = {row["project_name"]: row["is_default"] for row in rows}
    assert_that(names, has_items(email, project.name))
    assert_that(
        names[0],
        equal_to(email),
        "With no stored default the personal row must come first",
    )
    assert_that(
        names.index(email),
        less_than(names.index(project.name)),
        "Personal row must precede the per-project row while personal is the default",
    )
    assert_that(
        flags[email],
        equal_to(True),
        "The personal row of the default personal project must be flagged is_default",
    )
    assert_that(
        flags[project.name],
        equal_to(False),
        "A project that is not the default must not be flagged is_default",
    )


def assert_default_project_row_first_and_personal_row_unflagged(
    rows: list[dict], project: MemberProject, user_credentials
):
    """Once the project is the stored default its row is first and flagged, the personal one is not."""
    email = _email(user_credentials)
    names = row_names(rows)
    flags = {row["project_name"]: row["is_default"] for row in rows}
    assert_that(
        names[0],
        equal_to(project.name),
        "The default project's row must come first",
    )
    assert_that(names, has_item(email))
    assert_that(
        flags[project.name],
        equal_to(True),
        "The default project's row must be flagged is_default",
    )
    assert_that(
        flags[email],
        equal_to(False),
        "The personal row must lose is_default once another project is the default",
    )


def assert_every_row_carries_is_default_outside_the_columns(
    usage: BudgetUsageUtils,
    rows_without_default: list[dict],
    rows_with_default: list[dict],
):
    """Every row has the six column keys plus a boolean is_default, which is not a column."""
    all_rows = [*rows_without_default, *rows_with_default]
    assert_that(
        [set(row.keys()) for row in all_rows],
        only_contains(BUDGET_USAGE_ROW_KEYS),
        "Every row must carry the six column keys plus is_default",
    )
    assert_that(
        [type(row["is_default"]) for row in all_rows],
        only_contains(bool),
        "is_default must be a boolean on every row",
    )
    assert_that(usage.get_column_ids(), equal_to(BUDGET_USAGE_COLUMN_IDS))


def wait_for_personal_rows_and_project_row(
    user_usage: BudgetUsageUtils, project: MemberProject, user_credentials
):
    """The three personal rows (platform, cli, premium) and the project row are listed."""
    personal_labels = _personal_labels(user_credentials)
    assert_that(
        user_usage.wait_for_row_names_among(personal_labels, count=3),
        equal_to(personal_labels),
        "Precondition failed: the three personal rows are not listed yet",
    )
    assert_that(
        user_usage.wait_for_row(project.name),
        not_none(),
        "Precondition failed: the project row is not listed yet",
    )


def assert_personal_rows_are_the_first_three_rows_while_personal_is_default(
    rows: list[dict], project: MemberProject, user_credentials
):
    """The personal rows lead the whole response in category order, flagged, then the project row."""
    personal_labels = _personal_labels(user_credentials)
    names = row_names(rows)
    assert_that(
        names[:3],
        equal_to(personal_labels),
        "The personal rows must be the first three rows while personal is the default",
    )
    assert_that(
        [row["is_default"] for row in rows[:3]],
        equal_to([True, True, True]),
        "The personal rows of the default personal project must be flagged is_default",
    )
    assert_that(
        names[3:],
        equal_to([project.name]),
        "The project row must follow the personal rows",
    )
    assert_that(
        [row["is_default"] for row in rows[3:]],
        equal_to([False]),
    )


def assert_default_project_row_leads_and_personal_rows_follow_unflagged(
    rows: list[dict], project: MemberProject, user_credentials
):
    """The default project's row leads; the personal rows follow in category order, unflagged."""
    personal_labels = _personal_labels(user_credentials)
    names = row_names(rows)
    assert_that(
        names[0],
        equal_to(project.name),
        "The default project's row must come first",
    )
    assert_that(rows[0]["is_default"], equal_to(True))
    assert_that(
        names[1:],
        equal_to(personal_labels),
        "The personal rows must follow the default project's rows in category order",
    )
    assert_that(
        [row["is_default"] for row in rows[1:]],
        equal_to([False, False, False]),
        "The personal rows must not be flagged once another project is the default",
    )


# ---------------------------------------------------------------------------
# Parity with the admin Users list, enforcement on (TC-002)
# ---------------------------------------------------------------------------


def wait_for_member_project_row(usage: BudgetUsageUtils, project: MemberProject):
    """The member's row of the project, once listed."""
    row = usage.wait_for_row(project.name)
    assert_that(row, not_none())
    return row


def wait_for_admin_row_with_limit(
    admin_usage: BudgetUsageUtils, project: MemberProject
):
    """The admin table's row of the member and project, once it shows a platform limit."""
    return admin_usage.wait_for_user_project_limit(project.member_email, project.name)


def assert_personal_page_limit_equals_admin_limit(member_row: dict, admin_row: dict):
    assert_that(admin_row, not_none())
    assert_that(admin_row["platform_limit"], greater_than(0))
    assert_that(
        member_row["budget_limit"],
        close_to(admin_row["platform_limit"], ROUNDING_TOLERANCE),
        "budget_limit differs between the personal page and the admin table",
    )


def generate_member_spend_visible_at_two_decimals(
    proxy_utils, lite_llm_budget_utils, model: str, project: MemberProject
):
    """The member spends on the project's platform budget, enough to show at 2 decimals."""
    member_spend = generate_member_platform_spend(
        proxy_utils, lite_llm_budget_utils, model, project
    )
    assert_that(
        member_spend,
        greater_than_or_equal_to(MIN_VISIBLE_SPEND),
        "The stand did not record enough member spend to be visible at 2 decimals",
    )


def wait_for_admin_row_with_visible_spend(
    admin_usage: BudgetUsageUtils, project: MemberProject
):
    """The admin table's row, once it shows the member's spend at 2 decimals."""
    admin_ready_row = admin_usage.wait_for_user_project_spend(
        project.member_email, project.name
    )
    assert_that(admin_ready_row, not_none())
    assert_that(
        admin_ready_row["platform"],
        greater_than_or_equal_to(VISIBLE_AT_TWO_DECIMALS),
        "Admin table does not show the member's spend yet; the comparison would be 0 == 0",
    )


def wait_for_member_project_row_with_spend(
    member_usage: BudgetUsageUtils, project: MemberProject
):
    """The member's row of the project, once it shows non-zero spend."""
    member_row = member_usage.wait_for_current_spending(project.name)
    assert_that(member_row, not_none())
    assert_that(
        member_row["current_spending"],
        greater_than(0),
        "Personal page does not show the member's spend",
    )
    return member_row


def assert_personal_page_spend_and_total_equal_admin_table(
    member_row: dict, admin_usage: BudgetUsageUtils, project: MemberProject
):
    admin_row = admin_usage.get_user_project_spending_row(
        project.member_email, project.name
    )
    assert_that(admin_row["platform_limit"], greater_than(0))
    expected_total_value = round(
        admin_row["platform"] / admin_row["platform_limit"] * 100, 2
    )
    assert_that(expected_total_value, greater_than(0))
    assert_that(
        member_row["current_spending"],
        close_to(round(admin_row["platform"], 2), SPEND_PARITY_TOLERANCE),
        "current_spending differs between the personal page and the admin table",
    )
    assert_that(
        member_row["total"],
        close_to(expected_total_value, SPEND_PARITY_TOLERANCE),
        "total differs between the personal page and the admin table",
    )


# ---------------------------------------------------------------------------
# Who sees which rows (TC-003, TC-005, TC-006, TC-008, TC-009)
# ---------------------------------------------------------------------------


def assert_member_sees_project_row(
    member_usage: BudgetUsageUtils, project: MemberProject
):
    """Control: the member sees the project row."""
    assert_that(
        member_usage.wait_for_row(project.name),
        not_none(),
        "Control failed: the member does not see the project row either",
    )


def assert_non_member_sees_no_rows_of_project(
    user_usage: BudgetUsageUtils, project: MemberProject
):
    assert_that(
        user_usage.get_row_names_with_prefix(project.name),
        empty(),
        "A non-member must not see rows of a project they do not belong to",
    )


def assert_admin_user_project_spending_keeps_response_shape(
    client, project: MemberProject, admin_usage: BudgetUsageUtils
):
    response = client.analytics.get_user_project_spending(project.member_email)
    assert_that(
        [column.id for column in response.data.columns],
        equal_to(USER_PROJECT_SPENDING_COLUMN_IDS),
    )
    names = row_names(response.data.rows)
    assert_that(names, has_item(project.name))
    assert_that(
        len(set(names)),
        equal_to(len(names)),
        "Each project must appear in exactly one row",
    )
    row = admin_usage.get_user_project_spending_row(project.member_email, project.name)
    assert_that(set(row.keys()), equal_to(USER_PROJECT_SPENDING_ROW_KEYS))
    assert_that(row["platform_limit"], greater_than(0))
    assert_that(
        row["cli_limit"], none(), "No CLI budget exists, so no CLI limit is expected"
    )


def assert_control_member_sees_project_row_of_enforced_project(
    member_usage: BudgetUsageUtils, project: MemberProject
):
    assert_that(
        member_usage.wait_for_row(project.name),
        not_none(),
        "Control failed: the member of an enforced project sees no project row",
    )


def assert_user_without_memberships_gets_personal_rows_only(
    user_usage: BudgetUsageUtils,
    member_usage: BudgetUsageUtils,
    user_credentials,
    member_credentials,
    project: MemberProject,
):
    # A budget created through the API always has a positive max_budget, so no row with a
    # null budget_limit can be produced here; only the no-project-rows contract is checked.
    column_ids = user_usage.get_column_ids()
    project_row_names = user_usage.get_row_names_outside(
        _personal_labels(user_credentials)
    )
    member_project_row_names = member_usage.get_row_names_outside(
        _personal_labels(member_credentials)
    )

    assert_that(column_ids, equal_to(BUDGET_USAGE_COLUMN_IDS))
    assert_that(
        member_project_row_names,
        has_item(project.name),
        "Control failed: the project-row check does not detect a member's project row",
    )
    assert_that(
        project_row_names,
        empty(),
        "A user without project memberships must get no project rows",
    )


@dataclass
class ThreeProjects:
    """Projects of one member: enforcement on with a budget, off with a budget, off without."""

    enforced: MemberProject
    not_enforced: MemberProject
    without_budget: MemberProject


def create_enforced_unenforced_and_unbudgeted_projects(
    member_project_factory, member_client, member_credentials
) -> ThreeProjects:
    email = _email(member_credentials)
    return ThreeProjects(
        enforced=member_project_factory(member_client, email, enforce=True),
        not_enforced=member_project_factory(member_client, email, enforce=False),
        without_budget=member_project_factory(
            member_client, email, enforce=False, with_budget=False
        ),
    )


@dataclass
class ListedRows:
    """What the member's page lists once the budgeted projects are there."""

    names: list[str]
    enforced_row: dict
    not_enforced_row: dict
    hard_limit: float


def read_rows_once_budgeted_projects_are_listed(
    member_usage: BudgetUsageUtils, projects: ThreeProjects, admin_project_budget_utils
) -> ListedRows:
    rows = member_usage.wait_for_rows_where(
        lambda current: {projects.enforced.name, projects.not_enforced.name}
        <= set(row_names(current))
    )
    return ListedRows(
        names=row_names(rows),
        enforced_row=next(
            (row for row in rows if row["project_name"] == projects.enforced.name),
            None,
        ),
        not_enforced_row=next(
            (row for row in rows if row["project_name"] == projects.not_enforced.name),
            None,
        ),
        hard_limit=read_project_hard_limit(
            admin_project_budget_utils, projects.not_enforced
        ),
    )


def assert_projects_with_a_budget_are_listed(
    listed: ListedRows, projects: ThreeProjects
):
    assert_that(
        listed.enforced_row,
        not_none(),
        f"Enforced project '{projects.enforced.name}' missing on the personal spending page",
    )
    assert_that(
        listed.not_enforced_row,
        not_none(),
        f"Project '{projects.not_enforced.name}' with a budget but no enforcement missing "
        "on the personal spending page",
    )


def assert_project_without_budget_is_not_listed(
    listed: ListedRows, projects: ThreeProjects
):
    assert_that(
        _names_with_prefix(listed.names, projects.without_budget.name),
        empty(),
        "A project without any project budget must not be listed",
    )


def assert_only_platform_category_is_listed_for_budgeted_projects(
    listed: ListedRows, projects: ThreeProjects
):
    assert_that(
        _names_with_prefix(listed.names, projects.enforced.name),
        equal_to([projects.enforced.name]),
        "Only the category with a budget (platform) may be listed for the enforced project",
    )
    assert_that(
        _names_with_prefix(listed.names, projects.not_enforced.name),
        equal_to([projects.not_enforced.name]),
        "Only the category with a budget (platform) may be listed for the project "
        "without enforcement",
    )


def assert_unenforced_row_at_rest_shows_hard_limit_without_spend(listed: ListedRows):
    assert_that(listed.hard_limit, greater_than(0))
    assert_that(
        listed.not_enforced_row["budget_limit"],
        close_to(listed.hard_limit, ROUNDING_TOLERANCE),
        "Without enforcement the limit is the project hard limit",
    )
    assert_that(listed.not_enforced_row["current_spending"], equal_to(0.0))
    assert_that(listed.not_enforced_row["total"], equal_to(0.0))


def assert_admin_list_still_contains_all_three_projects(
    admin_usage: BudgetUsageUtils, member_credentials, projects: ThreeProjects
):
    admin_names = row_names(
        admin_usage.get_user_project_spending_rows(_email(member_credentials))
    )
    assert_that(
        admin_names,
        has_items(
            projects.enforced.name,
            projects.not_enforced.name,
            projects.without_budget.name,
        ),
    )


def assert_project_row_carries_reset_date_and_time_until_reset(
    member_usage: BudgetUsageUtils, project: MemberProject
):
    project_row = member_usage.wait_for_row(project.name)
    assert_that(project_row, not_none())
    assert_that(
        project_row["budget_reset_at"],
        not_none(),
        "Project row must carry the budget reset date",
    )
    assert_that(
        project_row["time_until_reset"],
        not_none(),
        "Project row must carry the time until reset",
    )


# ---------------------------------------------------------------------------
# Member override (TC-014, TC-015)
# ---------------------------------------------------------------------------


def wait_for_default_share_row(member_usage: BudgetUsageUtils, project: MemberProject):
    """The member's row while it still shows the default share, not the override value."""
    default_row = member_usage.wait_for_row(project.name)
    assert_that(default_row, not_none())
    assert_that(
        default_row["budget_limit"],
        is_not(MEMBER_OVERRIDE_MAX),
        "The override value must differ from the default share to be observable",
    )
    return default_row


def assert_row_has_a_reset_date_to_compare(default_row: dict):
    assert_that(
        default_row["budget_reset_at"],
        not_none(),
        "Precondition failed: the row has no reset date to compare",
    )


def wait_for_overridden_row(member_usage: BudgetUsageUtils, project: MemberProject):
    """The member's row once it shows the override limit."""
    return member_usage.wait_for_budget_limit(project.name, MEMBER_OVERRIDE_MAX)


def assert_override_is_shown_and_reset_date_kept(
    overridden_row: dict, default_row: dict
):
    assert_that(overridden_row, not_none())
    assert_that(
        overridden_row["budget_limit"],
        equal_to(MEMBER_OVERRIDE_MAX),
        "Personal page must show the overridden limit",
    )
    assert_that(
        overridden_row["budget_reset_at"],
        equal_to(default_row["budget_reset_at"]),
        "Editing the member allocation must keep the budget reset date",
    )


def assert_admin_table_shows_same_overridden_limit(
    admin_usage: BudgetUsageUtils, project: MemberProject, overridden_row: dict
):
    admin_row = admin_usage.get_user_project_spending_row(
        project.member_email, project.name
    )
    assert_that(admin_row, not_none())
    assert_that(
        admin_row["platform_limit"],
        equal_to(overridden_row["budget_limit"]),
        "Admin table must show the same overridden limit as the personal page",
    )


def assert_owner_holds_the_share_left_by_the_override(
    owner_usage: BudgetUsageUtils, project: MemberProject, hard_limit: float
):
    """With enforcement on the owner, who has no override, holds what the override leaves.

    The override limit is the same in both modes when nothing is spent, so it cannot show
    which mode the page is in; the owner's limit can.
    """
    share_left_by_override = round(hard_limit - MEMBER_OVERRIDE_MAX, 2)
    owner_on_row = owner_usage.wait_for_budget_limit(
        project.name, share_left_by_override
    )
    assert_that(
        owner_on_row,
        not_none(),
        "Precondition failed: the owner's row is not listed",
    )
    assert_that(
        owner_on_row["budget_limit"],
        equal_to(share_left_by_override),
        "Precondition failed: with enforcement on the owner must hold the share "
        "left by the override, or the owner's row cannot signal the switch",
    )


def assert_owner_without_override_sees_hard_limit(
    owner_usage: BudgetUsageUtils, project: MemberProject, hard_limit: float
):
    owner_off_row = owner_usage.wait_for_budget_limit(
        project.name, round(hard_limit, 2)
    )
    assert_that(owner_off_row, not_none())
    assert_that(
        owner_off_row["budget_limit"],
        equal_to(round(hard_limit, 2)),
        "Without enforcement the owner without an override must see the project hard limit",
    )


def assert_override_is_still_shown_with_enforcement_off(
    member_usage: BudgetUsageUtils, project: MemberProject
):
    """With nothing spent the cap is far above the override, so the override is still the limit."""
    unenforced_row = member_usage.wait_for_budget_limit(
        project.name, MEMBER_OVERRIDE_MAX
    )
    assert_that(unenforced_row, not_none())
    assert_that(
        unenforced_row["budget_limit"],
        equal_to(MEMBER_OVERRIDE_MAX),
        "Personal page must show the overridden limit with enforcement off as well",
    )


def wait_for_override_shown_before_clearing(
    member_usage: BudgetUsageUtils, project: MemberProject
):
    overridden_row = wait_for_overridden_row(member_usage, project)
    assert_that(
        overridden_row["budget_limit"],
        equal_to(MEMBER_OVERRIDE_MAX),
        "Precondition failed: the override is not shown before it is cleared",
    )


def assert_default_share_is_restored_after_override_is_cleared(
    member_usage: BudgetUsageUtils, project: MemberProject, default_row: dict
) -> dict:
    default_limit = default_row["budget_limit"]
    restored_row = member_usage.wait_for_budget_limit(project.name, default_limit)
    assert_that(restored_row, not_none())
    assert_that(
        restored_row["budget_limit"],
        equal_to(default_limit),
        "Personal page must show the default share again after the override is cleared",
    )
    return restored_row


def assert_admin_table_shows_same_restored_limit(
    admin_usage: BudgetUsageUtils, project: MemberProject, restored_row: dict
):
    admin_row = admin_usage.get_user_project_spending_row(
        project.member_email, project.name
    )
    assert_that(admin_row, not_none())
    assert_that(
        admin_row["platform_limit"],
        equal_to(restored_row["budget_limit"]),
        "Admin table must show the same restored limit as the personal page",
    )


# ---------------------------------------------------------------------------
# Real spend: the scenario shared by TC-016, TC-017 and TC-018
# ---------------------------------------------------------------------------


@dataclass
class SpendScenario:
    """A project with a scaled-down platform budget, its members' usage and the spend they made."""

    project: MemberProject
    owner_id: str
    owner_usage: BudgetUsageUtils
    member_usage: BudgetUsageUtils
    lite_llm_budget_utils: object
    admin_project_budget_utils: object
    user1_project_utils: object
    hard_limit: float
    third_member_id: str | None = None
    owner_spend: float = 0.0
    member_spend: float = 0.0
    project_total: float = 0.0

    @property
    def budget_id(self) -> str:
        return self.project.platform_budget_id


def _wait_for_allocation_holders(admin_project_budget_utils, project, holders: set):
    return poll_until(
        lambda: get_member_allocations(
            admin_project_budget_utils, project.platform_budget_id
        ),
        lambda found: set(found) == holders,
        timeout=90.0,
        interval=3.0,
    )


def create_two_member_scenario(
    member_project_factory,
    user1_id,
    member_client,
    member_credentials,
    user1_project_utils,
    lite_llm_budget_utils,
    admin_project_budget_utils,
    owner_usage,
    member_usage,
    enforce: bool,
) -> SpendScenario:
    """The owner and the member share a scaled-down platform budget."""
    project = member_project_factory(
        member_client,
        _email(member_credentials),
        enforce=enforce,
        categories=SCALED_PLATFORM_CATEGORIES,
    )
    _wait_for_allocation_holders(
        admin_project_budget_utils, project, {user1_id, project.member_id}
    )
    return SpendScenario(
        project=project,
        owner_id=user1_id,
        owner_usage=owner_usage,
        member_usage=member_usage,
        lite_llm_budget_utils=lite_llm_budget_utils,
        admin_project_budget_utils=admin_project_budget_utils,
        user1_project_utils=user1_project_utils,
        hard_limit=read_project_hard_limit(admin_project_budget_utils, project),
    )


def create_three_member_scenario(
    member_project_factory,
    user1_id,
    third_member_id,
    member_client,
    member_credentials,
    user1_project_utils,
    lite_llm_budget_utils,
    admin_project_budget_utils,
    owner_usage,
    member_usage,
) -> SpendScenario:
    """The owner, the member and a third member share a scaled-down budget, enforcement on."""
    project = member_project_factory(
        member_client,
        _email(member_credentials),
        enforce=True,
        extra_member_ids=(third_member_id,),
        categories=SCALED_PLATFORM_CATEGORIES,
    )
    _wait_for_allocation_holders(
        admin_project_budget_utils,
        project,
        {user1_id, project.member_id, third_member_id},
    )
    return SpendScenario(
        project=project,
        owner_id=user1_id,
        owner_usage=owner_usage,
        member_usage=member_usage,
        lite_llm_budget_utils=lite_llm_budget_utils,
        admin_project_budget_utils=admin_project_budget_utils,
        user1_project_utils=user1_project_utils,
        hard_limit=read_project_hard_limit(admin_project_budget_utils, project),
        third_member_id=third_member_id,
    )


def assert_owner_and_member_hold_the_only_allocations(scenario: SpendScenario):
    allocations = get_member_allocations(
        scenario.admin_project_budget_utils, scenario.budget_id
    )
    assert_that(
        set(allocations),
        equal_to({scenario.owner_id, scenario.project.member_id}),
        "Precondition failed: the owner and the member must be the only allocation holders",
    )
    assert_that(
        scenario.hard_limit,
        close_to(SCALED_PROJECT_LIMIT, ROUNDING_TOLERANCE),
        "Precondition failed: the project budget is not the scaled-down limit",
    )


def _override_customer_exists(scenario: SpendScenario, user_id: str):
    customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=scenario.project.name, category="platform", user_id=user_id
    )
    assert_that(
        scenario.lite_llm_budget_utils.wait_for_customer(customer_id),
        not_none(),
        "Precondition failed: the override customer does not exist at the provider",
    )


def override_owner_with_forty_percent_of_the_limit(scenario: SpendScenario):
    """The owner gets 40 percent of the limit; the other two members split the rest."""
    scenario.admin_project_budget_utils.override_member(
        scenario.budget_id,
        scenario.owner_id,
        SCALED_OVERRIDE_MAX,
        SCALED_OVERRIDE_SOFT,
    )
    for member_id in (scenario.project.member_id, scenario.third_member_id):
        wait_for_member_allocation(
            scenario.admin_project_budget_utils,
            scenario.budget_id,
            member_id,
            SCALED_SHARE_OF_REST,
        )
    allocations = wait_for_member_allocation(
        scenario.admin_project_budget_utils,
        scenario.budget_id,
        scenario.owner_id,
        SCALED_OVERRIDE_MAX,
    )
    assert_that(
        {
            member: allocation["allocated_max_budget"]
            for member, allocation in allocations.items()
        },
        equal_to(
            {
                scenario.owner_id: SCALED_OVERRIDE_MAX,
                scenario.project.member_id: SCALED_SHARE_OF_REST,
                scenario.third_member_id: SCALED_SHARE_OF_REST,
            }
        ),
        "Precondition failed: the override is not split as 40 / 30 / 30 percent",
    )
    assert_that(
        scenario.hard_limit,
        close_to(SCALED_PROJECT_LIMIT, ROUNDING_TOLERANCE),
        "Precondition failed: the project budget is not the scaled-down limit",
    )
    _override_customer_exists(scenario, scenario.owner_id)


def override_member_with_the_whole_project_limit(scenario: SpendScenario):
    """The member gets an override equal to the project limit, so any spend of others caps it."""
    scenario.admin_project_budget_utils.override_member(
        scenario.budget_id,
        scenario.project.member_id,
        SCALED_PROJECT_LIMIT,
        SCALED_OVERRIDE_EQUAL_TO_LIMIT_SOFT,
    )
    _override_customer_exists(scenario, scenario.project.member_id)


def _spend_as(scenario, proxy_utils, default_llm, user_id, target_spend=None):
    kwargs = {} if target_spend is None else {"target_spend": target_spend}
    return generate_member_spend(
        proxy_utils,
        scenario.lite_llm_budget_utils,
        default_llm.base_name,
        scenario.project.name,
        user_id,
        **kwargs,
    )


def _settle_project_total(scenario: SpendScenario):
    scenario.project_total = wait_for_settled_key_spend(
        scenario.lite_llm_budget_utils, scenario.project.budget.alias("platform")
    )


def generate_distinct_spend_for_owner_and_member(
    scenario: SpendScenario, user1_proxy_utils, user2_proxy_utils, default_llm
):
    """Both spend; the member spends visibly more than the owner. Settled before any page read."""
    scenario.owner_spend = _spend_as(
        scenario, user1_proxy_utils, default_llm, scenario.owner_id
    )
    scenario.member_spend = _spend_as(
        scenario,
        user2_proxy_utils,
        default_llm,
        scenario.project.member_id,
        target_spend=scenario.owner_spend + DISTINCT_SPEND_GAP,
    )
    _settle_project_total(scenario)


def generate_spend_for_owner_and_member(
    scenario: SpendScenario, user1_proxy_utils, user2_proxy_utils, default_llm
):
    """Both spend; the third member never does. Settled before any page read."""
    scenario.owner_spend = _spend_as(
        scenario, user1_proxy_utils, default_llm, scenario.owner_id
    )
    scenario.member_spend = _spend_as(
        scenario, user2_proxy_utils, default_llm, scenario.project.member_id
    )
    _settle_project_total(scenario)


def generate_spend_for_owner(scenario: SpendScenario, user1_proxy_utils, default_llm):
    """Only the owner spends. Settled before any page read."""
    scenario.owner_spend = _spend_as(
        scenario, user1_proxy_utils, default_llm, scenario.owner_id
    )
    _settle_project_total(scenario)


def assert_both_spent_and_the_member_spent_visibly_more(scenario: SpendScenario):
    assert_that(
        scenario.owner_spend,
        greater_than_or_equal_to(MIN_VISIBLE_SPEND),
        "The stand did not record enough spend for the owner",
    )
    assert_that(
        scenario.member_spend,
        greater_than_or_equal_to(scenario.owner_spend + DISTINCT_SPEND_GAP),
        "The second member must spend visibly more than the first, "
        "otherwise own spend cannot be told apart",
    )
    assert_that(
        scenario.project_total,
        greater_than(max(scenario.owner_spend, scenario.member_spend)),
        "The project key spend must include both members' spend, "
        "otherwise the combined total cannot be told from the own one",
    )


def assert_both_spent_and_the_project_total_includes_both(scenario: SpendScenario):
    assert_that(
        scenario.owner_spend,
        greater_than_or_equal_to(MIN_VISIBLE_SPEND),
        "The stand did not record enough spend for the owner",
    )
    assert_that(
        scenario.member_spend,
        greater_than_or_equal_to(MIN_VISIBLE_SPEND),
        "The stand did not record enough spend for the member",
    )
    assert_that(
        scenario.project_total,
        greater_than(max(scenario.owner_spend, scenario.member_spend)),
        "The project key spend must include both members' spend",
    )


def assert_owner_spent_and_the_project_total_is_visible(scenario: SpendScenario):
    assert_that(
        scenario.owner_spend,
        greater_than_or_equal_to(MIN_VISIBLE_SPEND),
        "The stand did not record enough spend for the owner",
    )
    assert_that(
        scenario.project_total,
        greater_than_or_equal_to(MIN_VISIBLE_SPEND),
        "The project key shows no spend, so the remaining budget would not shrink",
    )


def assert_cap_is_visibly_below_the_override(scenario: SpendScenario):
    capped_limit = expected_override_limit(
        SCALED_PROJECT_LIMIT, 0.0, scenario.hard_limit, scenario.project_total
    )
    assert_that(
        SCALED_PROJECT_LIMIT - capped_limit,
        greater_than_or_equal_to(VISIBLE_AT_TWO_DECIMALS),
        "Precondition failed: the cap must be visibly below the override at 2 decimals",
    )


# ---------------------------------------------------------------------------
# Rows that must match the spend measured at the provider
# ---------------------------------------------------------------------------


def _assert_row_values(row, spend: float, limit: float, total: float, who: str):
    """Assert a project row shows the member's own spend, the limit and the total percentage."""
    assert_that(row, not_none(), f"{who}: project row missing")
    assert_that(
        row["current_spending"],
        close_to(round(spend, 2), MONEY_TOLERANCE),
        f"{who}: current_spending must be the member's own spend",
    )
    assert_that(
        row["budget_limit"],
        close_to(round(limit, 2), MONEY_TOLERANCE),
        f"{who}: budget_limit differs from the expected limit",
    )
    assert_that(
        row["total"],
        close_to(total, PERCENT_TOLERANCE),
        f"{who}: total differs from the expected percentage",
    )


def _measure(scenario: SpendScenario):
    """Provider spend now: each member's customer spend and the project key spend."""
    return {
        **{
            user_id: member_customer_spend(
                scenario.lite_llm_budget_utils, scenario.project.name, user_id
            )
            for user_id in (scenario.owner_id, scenario.project.member_id)
        },
        "project": scenario.lite_llm_budget_utils.get_key_spend_by_alias(
            scenario.project.budget.alias("platform")
        ),
    }


def _read_row_matching_spend(scenario, usage, expected, who):
    """Wait for the member's project row to match freshly measured spend, then assert it.

    ``expected(measured)`` returns the ``(spend, limit, total)`` the row must show for the
    measurement. Returns the row and the measurement it matched (or, on timeout, the last row
    and measurement, which the assertions then fail on).
    """
    row, measured = wait_for_row_matching(
        usage, scenario.project.name, lambda: _measure(scenario), expected
    )
    _assert_row_values(row, *expected(measured), who)
    return row, measured


def _own_spend_against(user_id: str, limit: float):
    return lambda m: (m[user_id], limit, expected_total(m[user_id], limit))


def _own_spend_against_combined_total(user_id: str, hard_limit: float):
    return lambda m: (
        m[user_id],
        hard_limit,
        expected_total(m["project"], hard_limit),
    )


def assert_enforcement_off_rows_show_own_spend_hard_limit_and_same_combined_total(
    scenario: SpendScenario,
):
    owner_off, _ = _read_row_matching_spend(
        scenario,
        scenario.owner_usage,
        _own_spend_against_combined_total(scenario.owner_id, scenario.hard_limit),
        "owner, off",
    )
    member_off, _ = _read_row_matching_spend(
        scenario,
        scenario.member_usage,
        _own_spend_against_combined_total(
            scenario.project.member_id, scenario.hard_limit
        ),
        "member, off",
    )
    assert_that(
        member_off["total"],
        close_to(owner_off["total"], PERCENT_TOLERANCE),
        "Without enforcement every member sees the same combined total",
    )


def assert_enforcement_on_rows_show_own_spend_against_equal_share(
    scenario: SpendScenario,
):
    owner_on, _ = _read_row_matching_spend(
        scenario,
        scenario.owner_usage,
        _own_spend_against(scenario.owner_id, SCALED_SHARE_OF_TWO),
        "owner, on",
    )
    member_on, _ = _read_row_matching_spend(
        scenario,
        scenario.member_usage,
        _own_spend_against(scenario.project.member_id, SCALED_SHARE_OF_TWO),
        "member, on",
    )
    assert_that(
        abs(member_on["total"] - owner_on["total"]),
        greater_than(PERCENT_TOLERANCE),
        "With enforcement the members' totals must differ, as their spends do",
    )


def assert_enforcement_on_rows_show_own_spend_against_override_and_share(
    scenario: SpendScenario,
):
    _read_row_matching_spend(
        scenario,
        scenario.owner_usage,
        _own_spend_against(scenario.owner_id, SCALED_OVERRIDE_MAX),
        "owner with override, on",
    )
    _read_row_matching_spend(
        scenario,
        scenario.member_usage,
        _own_spend_against(scenario.project.member_id, SCALED_SHARE_OF_REST),
        "member without override, on",
    )


def assert_member_without_override_sees_hard_limit_and_combined_total(
    scenario: SpendScenario,
):
    _read_row_matching_spend(
        scenario,
        scenario.member_usage,
        _own_spend_against_combined_total(
            scenario.project.member_id, scenario.hard_limit
        ),
        "member without override, off",
    )


def assert_owner_with_override_stays_capped_at_the_override(scenario: SpendScenario):
    """The cap (own spend plus what is left of the project budget) is far above the override."""
    owner_limit_off = expected_override_limit(
        SCALED_OVERRIDE_MAX,
        scenario.owner_spend,
        scenario.hard_limit,
        scenario.project_total,
    )
    assert_that(
        owner_limit_off,
        close_to(SCALED_OVERRIDE_MAX, ROUNDING_TOLERANCE),
        "Precondition failed: the cap must not bind in this example",
    )

    def expected(m):
        limit = expected_override_limit(
            SCALED_OVERRIDE_MAX, m[scenario.owner_id], scenario.hard_limit, m["project"]
        )
        return m[scenario.owner_id], limit, expected_total(m[scenario.owner_id], limit)

    _read_row_matching_spend(
        scenario, scenario.owner_usage, expected, "owner with override, off"
    )


def assert_member_with_override_is_capped_by_the_remaining_project_budget(
    scenario: SpendScenario,
):
    member_id = scenario.project.member_id

    def expected(m):
        limit = expected_override_limit(
            SCALED_PROJECT_LIMIT, m[member_id], scenario.hard_limit, m["project"]
        )
        return m[member_id], limit, expected_total(m[member_id], limit)

    capped_row, measured = _read_row_matching_spend(
        scenario, scenario.member_usage, expected, "member with override"
    )
    assert_that(
        measured[member_id],
        equal_to(0.0),
        "Precondition failed: the member with the override must not have spent",
    )
    assert_that(
        measured["project"],
        greater_than(0),
        "Precondition failed: the project must have spend for the cap to shrink",
    )
    assert_that(
        capped_row["budget_limit"],
        less_than(SCALED_PROJECT_LIMIT),
        "The override must shrink once the rest of the project budget is smaller",
    )
    assert_that(
        capped_row["current_spending"],
        equal_to(0.0),
        "Precondition failed: the member with the override must not have spent",
    )
    # An override row is measured on the member's own spend; the combined project total, which
    # is above zero, must not leak into it.
    assert_that(
        capped_row["total"],
        equal_to(0.0),
        "A member with an override who has not spent must show 0 percent, "
        "not the combined project total",
    )


def assert_owner_without_override_sees_hard_limit_and_combined_total(
    scenario: SpendScenario,
):
    uncapped_row, _ = _read_row_matching_spend(
        scenario,
        scenario.owner_usage,
        _own_spend_against_combined_total(scenario.owner_id, scenario.hard_limit),
        "owner without override",
    )
    assert_that(
        uncapped_row["total"],
        greater_than(0),
        "Control failed: the member without an override shows no combined total",
    )
