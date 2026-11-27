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

"""UI tests for the Users column of Budgets management and its link to User Management.

Each budget row carries a Users badge (user icon, the number of assigned users) that links to
User Management filtered by that budget (`?budgets=<budget_id>`); the column is shown to admin
and maintainer, not to an auditor (BudgetsManagementPage.tsx:105, :181-193, :206).

Budgets are created and assigned through the API by the maintainer (`manual_budget`,
`assign_budget_user`, `manual_budget_factory`) and removed by those fixtures. Counts are
asserted only on these budgets: shared budgets on a stand carry any number of users.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.budgets_management_page import (
    BudgetsManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.user_management_page import (
    UserManagementPage,
)

# Tests that open User Management as the shared admin account run on one worker, one after
# another, so a filter one of them saves is never seen by another (filters.ts:114).
ADMIN_USER_MANAGEMENT_GROUP = pytest.mark.xdist_group(name="budget_users_admin_filters")


def _open_budget_row(page, budget_name: str) -> BudgetsManagementPage:
    budgets_page = BudgetsManagementPage(page).navigate_to()
    budgets_page.show_up_to_100_items_per_page()
    budgets_page.find_budget_row(budget_name)
    return budgets_page


# @case budget-user-count-redirect_TC_001
@pytest.mark.budget
@ADMIN_USER_MANAGEMENT_GROUP
@pytest.mark.ui
def test_users_badge_shows_assigned_user_count_and_zero_badge_opens_empty_list(
    page,
    manual_budget,
    assign_budget_user,
    manual_budget_factory,
    platform_user,
    second_platform_user,
):
    """AC-1/AC-4: every row carries a Users badge with a user icon; the budget with two
    assigned users shows 2 and the budget with none shows 0. The 0 badge is still a link and
    opens User Management filtered to that budget, with an empty list and no error."""
    empty_budget = manual_budget_factory()
    assign_budget_user(platform_user.user_id)
    assign_budget_user(second_platform_user.user_id)

    budgets_page = _open_budget_row(page, manual_budget["name"])
    budgets_page.should_see_users_badge_on_every_row()
    budgets_page.should_see_users_badge(manual_budget["name"], 2)

    budgets_page = _open_budget_row(page, empty_budget["name"])
    budgets_page.should_see_users_badge(empty_budget["name"], 0)
    budgets_page.should_link_users_badge_to_user_management(
        empty_budget["name"], empty_budget["budget_id"]
    )

    budgets_page.click_users_badge(empty_budget["name"])

    users_page = UserManagementPage(page)
    users_page.should_be_filtered_by_budget_only_in_url(empty_budget["budget_id"])
    users_page.should_show_empty_list_without_error()


# @case budget-user-count-redirect_TC_004
@pytest.mark.budget
@pytest.mark.parametrize(
    "acting_credentials",
    [
        pytest.param("admin", id="admin", marks=ADMIN_USER_MANAGEMENT_GROUP),
        pytest.param("maintainer", id="maintainer"),
    ],
    indirect=True,
)
@pytest.mark.ui
def test_users_badge_opens_user_management_filtered_by_budget_and_filter_stays_editable(
    page,
    manual_budget,
    assign_budget_user,
    manual_budget_factory,
    platform_user,
    second_platform_user,
):
    """AC-3: the badge opens User Management with ?budgets=<budget_id> and the list holds only
    the budget's assigned user (the other user is not listed). AC-5: the Budget filter shows
    the budget as selected. AC-6: adding a second budget, then removing the first, and
    finally 'Clear All' change the URL and the list exactly as a hand-set filter does."""
    assigned, other = platform_user, second_platform_user
    assign_budget_user(assigned.user_id)
    other_budget = manual_budget_factory(other.user_id)

    budgets_page = _open_budget_row(page, manual_budget["name"])
    budgets_page.click_users_badge(manual_budget["name"])

    users_page = UserManagementPage(page)
    users_page.should_be_filtered_by_budget_only_in_url(manual_budget["budget_id"])
    users_page.should_list_only_users([assigned.email])
    users_page.should_show_budget_selected_in_filter(manual_budget["name"])

    users_page.toggle_budget_in_filter(other_budget["name"])

    users_page.should_show_budget_selected_in_filter(other_budget["name"])
    users_page.should_list_only_users([assigned.email, other.email])

    users_page.toggle_budget_in_filter(manual_budget["name"])

    users_page.should_be_filtered_by_budget_only_in_url(other_budget["budget_id"])
    users_page.should_not_show_budget_selected_in_filter(manual_budget["name"])
    users_page.should_list_only_users([other.email])

    users_page.clear_all_filters()

    users_page.should_not_be_filtered_by_budget_in_url()
    users_page.should_not_show_budget_selected_in_filter(other_budget["name"])
    users_page.should_list_user(assigned.email)
    users_page.should_list_user(other.email)


# @case budget-user-count-redirect_TC_006
@pytest.mark.xfail(
    raises=AssertionError,
    strict=True,
    reason="A Project filter saved on an earlier User Management visit is merged into "
    "the users query on arrival via the budget Users badge, so the budget's assigned "
    "user is filtered out; the list should be filtered by that budget only",
)
@pytest.mark.budget
@ADMIN_USER_MANAGEMENT_GROUP
@pytest.mark.ui
def test_users_badge_arrival_is_not_narrowed_by_a_saved_project_filter(
    page,
    manual_budget,
    assign_budget_user,
    platform_user,
    project,
    reset_user_management_filters,
):
    """AC-3: a Project filter chosen on an earlier visit to User Management (kept per user,
    filters.ts:114) must not narrow the arrival through the badge: the URL carries only
    ?budgets=<budget_id>, the budget's assigned user (not a member of that project) is listed
    and the Project filter is not applied."""
    saved_project = project().name
    assign_budget_user(platform_user.user_id)
    earlier_visit = UserManagementPage(page).navigate_to()
    earlier_visit.select_project_in_filter(saved_project)
    earlier_visit.should_be_filtered_by_project_in_url(saved_project)

    budgets_page = _open_budget_row(page, manual_budget["name"])
    budgets_page.click_users_badge(manual_budget["name"])

    users_page = UserManagementPage(page)
    users_page.should_be_filtered_by_budget_only_in_url(manual_budget["budget_id"])
    users_page.should_list_only_users([platform_user.email])
    users_page.should_not_show_project_selected_in_filter(saved_project)


# @case budget-user-count-redirect_TC_008
@pytest.mark.budget
@pytest.mark.parametrize(
    "acting_credentials, users_column_shown",
    [
        pytest.param("cli_auditor", False, id="auditor - hidden"),
        pytest.param("admin", True, id="admin - shown"),
    ],
    indirect=["acting_credentials"],
)
@pytest.mark.ui
def test_users_column_is_hidden_for_auditor_and_shown_for_admin(
    page, users_column_shown
):
    """Gap from the change: the Users column and its badges are shown only to admin and
    maintainer; an auditor sees the budgets list without them (BudgetsManagementPage.tsx:206)."""
    budgets_page = BudgetsManagementPage(page).navigate_to()

    budgets_page.should_see_budget_list_not_empty()
    budgets_page.should_show_users_column(users_column_shown)
