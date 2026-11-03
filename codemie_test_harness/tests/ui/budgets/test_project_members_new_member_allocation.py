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

"""UI tests: Budget Allocations of a newly added member with "Enforce member spend limits" on.

The project has only the Platform budget category configured. The member's row on
the Members page must show the project-based allocation for the configured
category and nothing for the categories the project does not have.
"""

import pytest
from hamcrest import assert_that, not_none

from codemie_test_harness.tests.ui.pageobject.administration.project_add_user_modal_page import (
    ProjectAddUserModalPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_members_budget_section import (
    ProjectMembersBudgetSection,
)
from codemie_test_harness.tests.ui.test_data.project_member_allocation_ui_test_data import (
    UNCONFIGURED_CATEGORY_LABEL,
)
from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)


def _member_platform_allocation(budget_utils, budget_id: str, member_id: str):
    budget = budget_utils.get_budget(budget_id)
    return next(
        (
            alloc
            for alloc in budget["member_allocations"]
            if alloc["user_id"] == member_id
        ),
        None,
    )


# @case member-budget-allocations_TC_001
@pytest.mark.budget
@pytest.mark.ui
def test_new_member_shows_project_allocation_before_rebalance(
    page,
    project_admin_setup,
    unassigned_member_with_personal_budgets,
    admin_project_budget_utils,
):
    project_name, group_id, _, _ = project_admin_setup
    member_email, _, member_id = unassigned_member_with_personal_budgets
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)
    add_user_modal = ProjectAddUserModalPage(page)

    members.capture_user_list_responses()
    details_page.navigate_to(project_name)
    details_page.open_members_tab()
    members.should_show_allocation_column()
    add_user_modal.add_user(member_email)
    members.should_list_member(member_email)

    group = AdminProjectBudgetGroupUtils(admin_project_budget_utils.client).get_group(
        group_id
    )
    budget_id = AdminProjectBudgetUtils.budget_ids_by_category(group)["platform"]
    allocation = _member_platform_allocation(
        admin_project_budget_utils, budget_id, member_id
    )
    no_allocation = "new member has no project allocation"
    assert_that(allocation, not_none(), no_allocation)  # repro:precondition
    allocated = allocation["allocated_max_budget"]
    members.should_have_received_personal_budget(
        member_email, "platform"
    )  # repro:precondition

    members.should_show_allocation(member_email, 0.0, allocated)  # repro:symptom


# @case member-budget-allocations_TC_002
@pytest.mark.budget
@pytest.mark.ui
def test_new_member_has_no_allocation_for_unconfigured_category_after_rebalance(
    page,
    project_admin_setup,
    unassigned_member_with_personal_budgets,
    admin_project_budget_utils,
):
    project_name, group_id, _, _ = project_admin_setup
    member_email, _, member_id = unassigned_member_with_personal_budgets
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)
    add_user_modal = ProjectAddUserModalPage(page)

    members.capture_user_list_responses()
    details_page.navigate_to(project_name)
    details_page.open_members_tab()
    members.should_show_allocation_column()
    add_user_modal.add_user(member_email)
    members.should_list_member(member_email)

    group = AdminProjectBudgetGroupUtils(admin_project_budget_utils.client).get_group(
        group_id
    )
    budgets_by_category = AdminProjectBudgetUtils.budget_ids_by_category(group)
    admin_project_budget_utils.rebalance_budget(budgets_by_category["platform"])
    allocation = _member_platform_allocation(
        admin_project_budget_utils, budgets_by_category["platform"], member_id
    )
    no_allocation = "rebalance gave the new member no allocation"
    assert_that(allocation, not_none(), no_allocation)  # repro:precondition
    members.should_have_received_personal_budget(
        member_email, "cli"
    )  # repro:precondition
    category = UNCONFIGURED_CATEGORY_LABEL

    details_page.navigate_to(project_name)
    details_page.open_members_tab()
    members.should_list_member(member_email)
    members.should_not_show_category_allocation(member_email, category)  # repro:symptom
