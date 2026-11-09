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

"""Per-project spending rows on the personal spending page (GET /v1/analytics/budget_usage).

The page lists one row per budget category that has a project budget, for each project the
caller belongs to, with enforcement of member spend limits on or off. Rows of the caller's
default project come first, then the personal rows, then the other projects, and every row
says whether it belongs to the default project (is_default).

With enforcement on, a project row shows the caller's own spend against the caller's
allocation, and its values match the admin Users-list table
(GET /v1/analytics/user-project-spending). With enforcement off, a row shows the caller's
own spend, and its total is the whole project's spend against the project hard limit; a member
override then caps the limit by what is left of the project budget.
"""

import datetime
import logging
import secrets

import pytest

from codemie_test_harness.tests.test_data.budget_test_data import project_key_alias
from codemie_test_harness.tests.utils.budget_usage_steps import (
    assert_admin_list_still_contains_all_three_projects,
    assert_admin_table_shows_same_overridden_limit,
    assert_admin_table_shows_same_restored_limit,
    assert_admin_user_project_spending_keeps_response_shape,
    assert_both_spent_and_the_member_spent_visibly_more,
    assert_both_spent_and_the_project_total_includes_both,
    assert_cap_is_visibly_below_the_override,
    assert_control_member_sees_project_row_of_enforced_project,
    assert_default_project_row_first_and_personal_row_unflagged,
    assert_default_project_row_leads_and_personal_rows_follow_unflagged,
    assert_default_share_is_restored_after_override_is_cleared,
    assert_enforcement_off_rows_show_own_spend_hard_limit_and_same_combined_total,
    assert_enforcement_on_rows_show_own_spend_against_equal_share,
    assert_enforcement_on_rows_show_own_spend_against_override_and_share,
    assert_every_row_carries_is_default_outside_the_columns,
    assert_member_sees_project_row,
    assert_member_with_override_is_capped_by_the_remaining_project_budget,
    assert_member_without_override_sees_hard_limit_and_combined_total,
    assert_non_member_sees_no_rows_of_project,
    assert_override_is_shown_and_reset_date_kept,
    assert_override_is_still_shown_with_enforcement_off,
    assert_owner_and_member_hold_the_only_allocations,
    assert_owner_holds_the_share_left_by_the_override,
    assert_owner_spent_and_the_project_total_is_visible,
    assert_owner_with_override_stays_capped_at_the_override,
    assert_owner_without_override_sees_hard_limit,
    assert_owner_without_override_sees_hard_limit_and_combined_total,
    assert_personal_page_limit_equals_admin_limit,
    assert_personal_page_spend_and_total_equal_admin_table,
    assert_personal_row_first_and_flagged_while_personal_is_default,
    assert_personal_rows_are_the_first_three_rows_while_personal_is_default,
    assert_only_platform_category_is_listed_for_budgeted_projects,
    assert_project_row_carries_reset_date_and_time_until_reset,
    assert_project_without_budget_is_not_listed,
    assert_projects_with_a_budget_are_listed,
    assert_row_has_a_reset_date_to_compare,
    assert_unenforced_row_at_rest_shows_hard_limit_without_spend,
    assert_user_without_memberships_gets_personal_rows_only,
    clear_member_override,
    create_enforced_unenforced_and_unbudgeted_projects,
    create_member_project,
    create_three_member_scenario,
    create_two_member_scenario,
    generate_distinct_spend_for_owner_and_member,
    generate_member_spend_visible_at_two_decimals,
    generate_spend_for_owner,
    generate_spend_for_owner_and_member,
    override_member_budget,
    override_member_with_the_whole_project_limit,
    override_owner_with_forty_percent_of_the_limit,
    read_project_hard_limit,
    read_rows_once_budgeted_projects_are_listed,
    set_project_as_default,
    switch_enforcement,
    wait_for_admin_row_with_limit,
    wait_for_admin_row_with_visible_spend,
    wait_for_default_project_row_first,
    wait_for_default_share_row,
    wait_for_member_project_row,
    wait_for_member_project_row_with_spend,
    wait_for_override_shown_before_clearing,
    wait_for_overridden_row,
    wait_for_personal_rows_and_project_row,
    wait_for_project_row_and_personal_row,
)
from codemie_test_harness.tests.utils.budget_usage_utils import (
    BudgetUsageUtils,
    MemberProject,
)
from codemie_test_harness.tests.utils.proxy_utils import ProxyUtils

logger = logging.getLogger(__name__)

ENFORCEMENT_MODES = pytest.mark.parametrize(
    "enforce",
    [True, False],
    ids=["enforcement_on", "enforcement_off"],
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def member_project_factory(
    user1_client,
    user1_project_utils,
    project_budget_groups,
    lite_llm_budget_utils,
):
    """Creates projects owned by user1 with one assigned member and, by default, a platform budget.

    ``create(member_client, member_email, enforce, with_budget, extra_member_ids, categories)``
    returns a ``MemberProject`` once the budget group exists; ``with_budget=False`` creates the
    project without a budget group, ``extra_member_ids`` assigns more members before the group is
    created so they get an allocation too, and ``categories`` is the budget group definition.
    Teardown deletes the budget, LiteLLM objects and the project.
    """
    created: list[MemberProject] = []

    def create(
        member_client,
        member_email: str,
        enforce: bool = True,
        with_budget: bool = True,
        extra_member_ids: tuple = (),
        categories: dict | None = None,
    ):
        project_name = f"autotest-project-{secrets.token_hex(4)}"
        member_id = member_client.users.about_me().user_id
        user1_project_utils.create_project(
            name=project_name, description="Autotest personal spending page project"
        )
        project = MemberProject(
            name=project_name,
            member_id=member_id,
            member_email=member_email,
            owner_id=user1_client.users.about_me().user_id,
            extra_member_ids=list(extra_member_ids),
        )
        created.append(project)
        if enforce:
            user1_project_utils.set_enforce_member_spend_limits(project_name, True)
        for user_id in (member_id, *extra_member_ids):
            user1_project_utils.assign_user_to_project(
                project_name, user_id, is_project_admin=False
            )
            user1_project_utils.wait_for_project_member(project_name, user_id)
        if with_budget:
            project.budget = project_budget_groups.create(
                project_name, categories, name_prefix="autotest"
            )
        return project

    yield create

    for project in reversed(created):
        if project.budget is not None:
            member_objects_deleted = False
            try:
                project_budget_groups.delete(project.budget, project.member_id)
                member_objects_deleted = True
            except Exception as e:
                logger.warning(f"Failed to delete budget of {project.name}: {e}")
            for budget_id in project.budget.budget_ids.values():
                for user_id in project.user_ids:
                    if member_objects_deleted and user_id == project.member_id:
                        continue
                    try:
                        lite_llm_budget_utils.delete_project_budget_objects(
                            budget_id, user_id
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to delete LiteLLM budget objects of {budget_id}: {e}"
                        )
        for category in ("platform", "cli", "premium_models"):
            alias = project_key_alias(project.name, category)
            try:
                lite_llm_budget_utils.delete_key_by_alias(alias)
            except Exception as e:
                logger.warning(f"Failed to delete LiteLLM key for alias {alias}: {e}")
        for user_id in project.user_ids:
            try:
                lite_llm_budget_utils.delete_override_customers_for_project(
                    project.name, user_id
                )
            except Exception as e:
                logger.warning(
                    f"Failed to delete override customers for project {project.name}: {e}"
                )
        try:
            user1_project_utils.delete_project_cascade(project.name)
        except Exception as e:
            logger.warning(f"Failed to delete project {project.name}: {e}")


@pytest.fixture(scope="function")
def enforced_project(member_project_factory, user2_client, keycloak_user_2):
    """Project with enforce_member_spend_limits on and a platform budget; user2 is the member."""
    email, _ = keycloak_user_2
    return member_project_factory(user2_client, email, enforce=True)


@pytest.fixture(scope="function")
def member_usage(user2_client):
    return BudgetUsageUtils(user2_client)


@pytest.fixture(scope="function")
def owner_usage(user1_client):
    """Budget usage of user1, the owner of every project the factory creates."""
    return BudgetUsageUtils(user1_client)


@pytest.fixture(scope="function")
def user_usage(user_client):
    return BudgetUsageUtils(user_client)


@pytest.fixture(scope="function")
def admin_usage(client):
    return BudgetUsageUtils(client)


@pytest.fixture(scope="function")
def user1_proxy_utils(user1_client):
    return ProxyUtils(user1_client)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# @case per-project-spending-personal-page_TC_001
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_get_budget_usage_lists_default_project_first_and_flags_is_default(
    user_client,
    user_id,
    keycloak_user,
    assigned_platform_budget,
    member_project_factory,
    user_usage,
    user_utils,
):
    project = create_member_project(
        member_project_factory, user_client, keycloak_user, enforce=True
    )
    wait_for_project_row_and_personal_row(user_usage, project, keycloak_user)

    rows_without_default = user_usage.get_rows()
    assert_personal_row_first_and_flagged_while_personal_is_default(
        rows_without_default, project, keycloak_user
    )

    set_project_as_default(user_utils, user_id, project)
    rows_with_default = wait_for_default_project_row_first(user_usage, project)
    assert_default_project_row_first_and_personal_row_unflagged(
        rows_with_default, project, keycloak_user
    )
    assert_every_row_carries_is_default_outside_the_columns(
        user_usage, rows_without_default, rows_with_default
    )


# @case per-project-spending-personal-page_TC_002
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_get_budget_usage_project_limit_equals_admin_user_project_spending_limit_enforcement_on(
    enforced_project, member_usage, admin_usage
):
    """Enforcement-on rows share the limit with the admin Users-list table."""
    member_row = wait_for_member_project_row(member_usage, enforced_project)
    admin_row = wait_for_admin_row_with_limit(admin_usage, enforced_project)

    assert_personal_page_limit_equals_admin_limit(member_row, admin_row)


# @case per-project-spending-personal-page_TC_002
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_get_budget_usage_project_spend_equals_admin_user_project_spending_enforcement_on(
    enforced_project,
    user2_proxy_utils,
    default_llm,
    lite_llm_budget_utils,
    member_usage,
    admin_usage,
    admin_spend_tracking_utils,
):
    """Enforcement-on rows share spend and total with the admin Users-list table."""
    generate_member_spend_visible_at_two_decimals(
        user2_proxy_utils,
        lite_llm_budget_utils,
        default_llm.base_name,
        enforced_project,
    )
    admin_spend_tracking_utils.collect_spends()
    today = datetime.date.today()
    admin_spend_tracking_utils.wait_for_project_spends(
        enforced_project.name, today, today, "platform"
    )
    wait_for_admin_row_with_visible_spend(admin_usage, enforced_project)
    member_row = wait_for_member_project_row_with_spend(member_usage, enforced_project)

    assert_personal_page_spend_and_total_equal_admin_table(
        member_row, admin_usage, enforced_project
    )


# @case per-project-spending-personal-page_TC_003
@ENFORCEMENT_MODES
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_get_budget_usage_hides_project_rows_from_non_member(
    enforce,
    member_project_factory,
    user2_client,
    keycloak_user_2,
    member_usage,
    user_usage,
):
    project = create_member_project(
        member_project_factory, user2_client, keycloak_user_2, enforce=enforce
    )

    assert_member_sees_project_row(member_usage, project)
    assert_non_member_sees_no_rows_of_project(user_usage, project)


# @case per-project-spending-personal-page_TC_005
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_get_user_project_spending_keeps_response_shape_for_admin(
    client, enforced_project, admin_usage
):
    assert_admin_user_project_spending_keeps_response_shape(
        client, enforced_project, admin_usage
    )


# @case per-project-spending-personal-page_TC_006
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_get_budget_usage_returns_personal_rows_only_without_memberships(
    keycloak_user,
    keycloak_user_2,
    enforced_project,
    user_usage,
    member_usage,
):
    assert_control_member_sees_project_row_of_enforced_project(
        member_usage, enforced_project
    )

    assert_user_without_memberships_gets_personal_rows_only(
        user_usage, member_usage, keycloak_user, keycloak_user_2, enforced_project
    )


# @case per-project-spending-personal-page_TC_008
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_get_budget_usage_lists_projects_with_a_budget_whatever_the_enforcement(
    member_project_factory,
    user2_client,
    keycloak_user_2,
    member_usage,
    admin_usage,
    admin_project_budget_utils,
):
    projects = create_enforced_unenforced_and_unbudgeted_projects(
        member_project_factory, user2_client, keycloak_user_2
    )
    listed = read_rows_once_budgeted_projects_are_listed(
        member_usage, projects, admin_project_budget_utils
    )

    assert_projects_with_a_budget_are_listed(listed, projects)
    assert_project_without_budget_is_not_listed(listed, projects)
    assert_only_platform_category_is_listed_for_budgeted_projects(listed, projects)
    assert_unenforced_row_at_rest_shows_hard_limit_without_spend(listed)
    assert_admin_list_still_contains_all_three_projects(
        admin_usage, keycloak_user_2, projects
    )


# @case per-project-spending-personal-page_TC_009
@ENFORCEMENT_MODES
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_get_budget_usage_project_row_carries_reset_date_and_time_until_reset(
    enforce, member_project_factory, user2_client, keycloak_user_2, member_usage
):
    project = create_member_project(
        member_project_factory, user2_client, keycloak_user_2, enforce=enforce
    )

    assert_project_row_carries_reset_date_and_time_until_reset(member_usage, project)


# @case per-project-spending-personal-page_TC_010
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_get_budget_usage_orders_rows_by_default_project_then_personal_platform_cli_premium(
    user_client,
    user_id,
    keycloak_user,
    assigned_premium_budget,
    assigned_cli_budget,
    assigned_platform_budget,
    member_project_factory,
    user_usage,
    user_utils,
):
    # Budgets are assigned premium, cli, platform: the reverse of the expected row order.
    project = create_member_project(
        member_project_factory, user_client, keycloak_user, enforce=True
    )
    wait_for_personal_rows_and_project_row(user_usage, project, keycloak_user)

    rows_without_default = user_usage.get_rows()
    assert_personal_rows_are_the_first_three_rows_while_personal_is_default(
        rows_without_default, project, keycloak_user
    )

    set_project_as_default(user_utils, user_id, project)
    rows_with_default = wait_for_default_project_row_first(user_usage, project)
    assert_default_project_row_leads_and_personal_rows_follow_unflagged(
        rows_with_default, project, keycloak_user
    )


# @case per-project-spending-personal-page_TC_014
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_get_budget_usage_project_row_reflects_member_budget_override_in_both_modes(
    enforced_project,
    member_usage,
    owner_usage,
    admin_usage,
    admin_project_budget_utils,
    user1_project_utils,
):
    default_row = wait_for_default_share_row(member_usage, enforced_project)
    assert_row_has_a_reset_date_to_compare(default_row)
    override_member_budget(admin_project_budget_utils, enforced_project)

    # Enforcement on.
    overridden_row = wait_for_overridden_row(member_usage, enforced_project)
    assert_override_is_shown_and_reset_date_kept(overridden_row, default_row)
    assert_admin_table_shows_same_overridden_limit(
        admin_usage, enforced_project, overridden_row
    )

    # Enforcement off, signalled by the owner's row, which has no override.
    hard_limit = read_project_hard_limit(admin_project_budget_utils, enforced_project)
    assert_owner_holds_the_share_left_by_the_override(
        owner_usage, enforced_project, hard_limit
    )
    switch_enforcement(user1_project_utils, enforced_project, enabled=False)
    assert_owner_without_override_sees_hard_limit(
        owner_usage, enforced_project, hard_limit
    )
    assert_override_is_still_shown_with_enforcement_off(member_usage, enforced_project)


# @case per-project-spending-personal-page_TC_015
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_get_budget_usage_project_row_returns_to_default_share_after_override_cleared_enforcement_on(
    enforced_project, member_usage, admin_usage, admin_project_budget_utils
):
    """Enforcement on: clearing the override restores the share, which the admin table shows too."""
    default_row = wait_for_default_share_row(member_usage, enforced_project)
    override_member_budget(admin_project_budget_utils, enforced_project)
    wait_for_override_shown_before_clearing(member_usage, enforced_project)

    clear_member_override(admin_project_budget_utils, enforced_project)

    restored_row = assert_default_share_is_restored_after_override_is_cleared(
        member_usage, enforced_project, default_row
    )
    assert_admin_table_shows_same_restored_limit(
        admin_usage, enforced_project, restored_row
    )


# @case per-project-spending-personal-page_TC_016
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(3600)
@pytest.mark.api
def test_get_budget_usage_two_members_real_spend_total_follows_enforcement_mode(
    user1_id,
    user2_client,
    keycloak_user_2,
    member_project_factory,
    user1_proxy_utils,
    user2_proxy_utils,
    user1_project_utils,
    default_llm,
    lite_llm_budget_utils,
    admin_project_budget_utils,
    owner_usage,
    member_usage,
    admin_spend_tracking_utils,
):
    scenario = create_two_member_scenario(
        member_project_factory,
        user1_id,
        user2_client,
        keycloak_user_2,
        user1_project_utils,
        lite_llm_budget_utils,
        admin_project_budget_utils,
        owner_usage,
        member_usage,
        enforce=False,
    )
    assert_owner_and_member_hold_the_only_allocations(scenario)

    # No personal-page or admin read happens before the spend is settled and collected.
    generate_distinct_spend_for_owner_and_member(
        scenario, user1_proxy_utils, user2_proxy_utils, default_llm
    )
    admin_spend_tracking_utils.collect_spends()
    today = datetime.date.today()
    admin_spend_tracking_utils.wait_for_project_spends(
        scenario.project.name, today, today, "platform"
    )
    assert_both_spent_and_the_member_spent_visibly_more(scenario)

    assert_enforcement_off_rows_show_own_spend_hard_limit_and_same_combined_total(
        scenario
    )
    switch_enforcement(user1_project_utils, scenario.project, enabled=True)
    assert_enforcement_on_rows_show_own_spend_against_equal_share(scenario)


# @case per-project-spending-personal-page_TC_017
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(3600)
@pytest.mark.api
def test_get_budget_usage_three_members_override_and_real_spend_total_by_mode(
    user1_id,
    user_id,
    user2_client,
    keycloak_user_2,
    member_project_factory,
    user1_proxy_utils,
    user2_proxy_utils,
    user1_project_utils,
    default_llm,
    lite_llm_budget_utils,
    admin_project_budget_utils,
    owner_usage,
    member_usage,
    admin_spend_tracking_utils,
):
    scenario = create_three_member_scenario(
        member_project_factory,
        user1_id,
        user_id,
        user2_client,
        keycloak_user_2,
        user1_project_utils,
        lite_llm_budget_utils,
        admin_project_budget_utils,
        owner_usage,
        member_usage,
    )
    override_owner_with_forty_percent_of_the_limit(scenario)

    # No personal-page or admin read happens before the spend is settled and collected.
    generate_spend_for_owner_and_member(
        scenario, user1_proxy_utils, user2_proxy_utils, default_llm
    )
    admin_spend_tracking_utils.collect_spends()
    today = datetime.date.today()
    admin_spend_tracking_utils.wait_for_project_spends(
        scenario.project.name, today, today, "platform"
    )
    assert_both_spent_and_the_project_total_includes_both(scenario)

    assert_enforcement_on_rows_show_own_spend_against_override_and_share(scenario)
    switch_enforcement(user1_project_utils, scenario.project, enabled=False)
    assert_member_without_override_sees_hard_limit_and_combined_total(scenario)
    assert_owner_with_override_stays_capped_at_the_override(scenario)


# @case per-project-spending-personal-page_TC_018
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(3600)
@pytest.mark.api
def test_get_budget_usage_override_is_capped_by_remaining_project_budget_when_not_enforced(
    user1_id,
    user2_client,
    keycloak_user_2,
    member_project_factory,
    user1_proxy_utils,
    default_llm,
    lite_llm_budget_utils,
    admin_project_budget_utils,
    owner_usage,
    member_usage,
    user1_project_utils,
    admin_spend_tracking_utils,
):
    scenario = create_two_member_scenario(
        member_project_factory,
        user1_id,
        user2_client,
        keycloak_user_2,
        user1_project_utils,
        lite_llm_budget_utils,
        admin_project_budget_utils,
        owner_usage,
        member_usage,
        enforce=False,
    )
    override_member_with_the_whole_project_limit(scenario)

    # Only the owner spends; nothing is read from the page before it is settled and collected.
    generate_spend_for_owner(scenario, user1_proxy_utils, default_llm)
    admin_spend_tracking_utils.collect_spends()
    today = datetime.date.today()
    admin_spend_tracking_utils.wait_for_project_spends(
        scenario.project.name, today, today, "platform"
    )
    assert_owner_spent_and_the_project_total_is_visible(scenario)
    assert_cap_is_visibly_below_the_override(scenario)

    assert_member_with_override_is_capped_by_the_remaining_project_budget(scenario)
    assert_owner_without_override_sees_hard_limit_and_combined_total(scenario)
