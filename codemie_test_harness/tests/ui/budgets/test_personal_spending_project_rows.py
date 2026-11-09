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

"""UI tests for the per-project rows of the 'Your personal spending' panel.

Each test opens the personal settings page as the project's user, waits for the
GET /v1/analytics/budget_usage response the page itself makes, and compares what the table
shows with the same user's API response read through the SDK.

`project_admin_setup` (budgets/conftest.py) creates a project without enforcement of member
spend limits and a budget group; `two_category_budget` spreads that group over the platform and
cli categories, because the panel draws a table only for two or more rows. The budget_limit
column is hidden in the table by design, so limit values are asserted in the API tests.
"""

import datetime

import pytest

from codemie_test_harness.tests.ui.budgets.personal_spending_steps import (
    assert_api_lists_platform_and_cli_rows_of_the_project,
    assert_default_project_rows_come_first_and_only_they_are_flagged,
    assert_other_member_spend_is_recorded,
    assert_project_is_not_the_default_before_the_admin_sets_it,
    assert_setting_the_default_changed_which_rows_are_flagged,
    assert_spent_category_row_keeps_its_combined_total,
    assert_viewer_has_not_spent_and_sees_the_combined_project_total,
    generate_spend_as_other_member,
    make_project_the_default,
    read_budget_usage,
    read_rows,
    switch_enforcement_off,
    wait_for_cli_row_to_be_listed,
    wait_for_default_project_rows_first,
    wait_for_viewer_row_with_combined_total,
)
from codemie_test_harness.tests.ui.test_data.personal_spending_test_data import (
    SPENT_CATEGORY,
)
from codemie_test_harness.tests.ui.pageobject.budgets.personal_spending_page import (
    PersonalSpendingPage,
)


# @case per-project-spending-personal-page_TC_019
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.ui
def test_personal_spending_table_lists_project_rows_for_user_without_enforcement(
    page, two_category_budget, project_admin_setup_client
):
    wait_for_cli_row_to_be_listed(project_admin_setup_client, two_category_budget)

    spending = PersonalSpendingPage(page).open()
    api = read_budget_usage(project_admin_setup_client)

    assert_api_lists_platform_and_cli_rows_of_the_project(api, two_category_budget)
    spending.should_have_requested_own_usage_only()
    spending.should_have_received_rows(api.names)
    spending.should_show_table()
    spending.should_show_columns(api.shown_labels)
    spending.should_not_show_column(api.hidden_label)
    spending.should_match_budget_usage(api.rows)


# @case per-project-spending-personal-page_TC_020
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.ui
def test_personal_spending_default_badge_follows_is_default_flag_of_rows(
    page, two_category_budget, project_admin_setup_client, user_utils
):
    wait_for_cli_row_to_be_listed(project_admin_setup_client, two_category_budget)

    # No stored default: the badge goes exactly where the API flags is_default.
    spending = PersonalSpendingPage(page).open()
    rows_without_default = read_rows(project_admin_setup_client)
    assert_project_is_not_the_default_before_the_admin_sets_it(
        rows_without_default, two_category_budget
    )
    spending.should_show_table()
    spending.should_match_budget_usage(rows_without_default)
    spending.should_show_default_badge_on_flagged_rows(rows_without_default)

    # The project becomes the default: its rows come first and carry the badge.
    make_project_the_default(
        user_utils, project_admin_setup_client, two_category_budget
    )
    rows_with_default = wait_for_default_project_rows_first(project_admin_setup_client)
    assert_default_project_rows_come_first_and_only_they_are_flagged(
        rows_with_default, two_category_budget
    )
    assert_setting_the_default_changed_which_rows_are_flagged(
        rows_with_default, rows_without_default
    )
    spending.reload()
    spending.should_show_table()
    spending.should_match_budget_usage(rows_with_default)
    spending.should_show_default_badge_on_flagged_rows(rows_with_default)


# @case per-project-spending-personal-page_TC_021
@pytest.mark.enterprise
@pytest.mark.budget
@pytest.mark.timeout(1800)
@pytest.mark.ui
def test_personal_spending_shows_combined_project_total_for_user_who_has_not_spent(
    page,
    scaled_spent_category_budget,
    spent_member_cleanup,
    project_admin_setup_client,
    member_override_ui_setup,
    admin_project_utils,
    lite_llm_budget_utils,
    default_llm,
    admin_spend_tracking_utils,
):
    switch_enforcement_off(admin_project_utils, scaled_spent_category_budget)

    # The other member spends and the spend is collected before the page is opened.
    spend = generate_spend_as_other_member(
        scaled_spent_category_budget,
        member_override_ui_setup,
        default_llm,
        lite_llm_budget_utils,
    )
    project_name, _ = scaled_spent_category_budget
    admin_spend_tracking_utils.collect_spends()
    today = datetime.date.today()
    admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, SPENT_CATEGORY
    )
    assert_other_member_spend_is_recorded(spend)
    viewer_row = wait_for_viewer_row_with_combined_total(
        project_admin_setup_client, scaled_spent_category_budget
    )
    assert_viewer_has_not_spent_and_sees_the_combined_project_total(viewer_row, spend)

    spending = PersonalSpendingPage(page).open()
    api_rows = read_rows(project_admin_setup_client)

    assert_spent_category_row_keeps_its_combined_total(
        api_rows, scaled_spent_category_budget
    )
    spending.should_show_table()
    spending.should_match_budget_usage(api_rows)
