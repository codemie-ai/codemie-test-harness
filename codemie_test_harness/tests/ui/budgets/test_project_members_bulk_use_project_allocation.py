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

"""UI tests: 'Use project allocation' in the bulk 'Budget Override — N users' modal.

The bulk modal opens from the Members tab (select members, then Bulk Actions > Override budgets).
Each category card offers 'Use project allocation' when a selected member holds an override in
that category; the change takes effect on 'Save Override'.
"""

import pytest
from hamcrest import assert_that, equal_to, is_not

from codemie_test_harness.tests.test_data.budget_member_override_test_data import (
    MEMBER_OVERRIDE_MAX,
    MEMBER_OVERRIDE_SOFT,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_members_budget_section import (
    ProjectMembersBudgetSection,
)
from codemie_test_harness.tests.ui.test_data.budget_bulk_override_test_data import (
    BULK_CLI_MEMBER_MAX,
    BULK_CLI_MEMBER_SOFT,
    BULK_CLI_TYPED_HARD_LIMIT,
    BULK_PLATFORM_MEMBER_MAX,
    BULK_PLATFORM_MEMBER_SOFT,
    BULK_TWO_CATEGORY_DISTRIBUTION,
    PROJECT_PLATFORM_HARD_LIMIT,
    bulk_saved_toast,
)
from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)


# @case bulk-override-use-project-allocation_TC_001
@pytest.mark.budget
@pytest.mark.ui
def test_bulk_use_project_allocation_clears_override_of_every_selected_member(
    page,
    project_admin_setup,
    project_admin_setup_client,
    two_member_override_ui_ready,
    platform_budget_id,
):
    project_name, _, _, _ = project_admin_setup
    (first_email, _, first_id), (second_email, _, second_id) = (
        two_member_override_ui_ready
    )
    budget_utils = AdminProjectBudgetUtils(project_admin_setup_client)
    budget_utils.override_member(
        platform_budget_id, first_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
    )
    budget_utils.override_member(
        platform_budget_id, second_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
    )
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, first_id)[
            "allocation_mode"
        ],
        equal_to("fixed"),
        "Precondition: the first member must hold a fixed override",
    )
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, second_id)[
            "allocation_mode"
        ],
        equal_to("fixed"),
        "Precondition: the second member must hold a fixed override",
    )
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)

    details_page.navigate_to(project_name)
    details_page.open_members_tab()
    members.should_show_fixed_allocation_marker(first_email)
    members.should_show_fixed_allocation_marker(second_email)

    members.select_members(first_email, second_email)
    bulk_modal = members.open_bulk_override_modal(2)
    bulk_modal.should_offer_use_project_allocation_for("Platform")
    bulk_modal.use_project_allocation_for("Platform")
    bulk_modal.save_override()

    bulk_modal.should_show_saved_toast(bulk_saved_toast(2))
    bulk_modal.should_be_closed()
    members.should_not_show_fixed_allocation_marker(first_email)
    members.should_not_show_fixed_allocation_marker(second_email)
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, first_id)[
            "allocation_mode"
        ],
        is_not(equal_to("fixed")),
        "Saving 'Use project allocation' must clear the first member's fixed override",
    )
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, second_id)[
            "allocation_mode"
        ],
        is_not(equal_to("fixed")),
        "Saving 'Use project allocation' must clear the second member's fixed override",
    )


# @case bulk-override-use-project-allocation_TC_002
@pytest.mark.budget
@pytest.mark.ui
def test_bulk_use_project_allocation_leaves_unselected_members_unchanged(
    page,
    project_admin_setup,
    project_admin_setup_client,
    two_member_override_ui_ready,
    platform_budget_id,
):
    project_name, _, _, _ = project_admin_setup
    (first_email, _, first_id), (second_email, _, second_id) = (
        two_member_override_ui_ready
    )
    admin_id = project_admin_setup_client.users.about_me().user_id
    budget_utils = AdminProjectBudgetUtils(project_admin_setup_client)
    budget_utils.override_member(
        platform_budget_id, first_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
    )
    budget_utils.override_member(
        platform_budget_id, admin_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
    )
    second_before = budget_utils.get_member_allocation(platform_budget_id, second_id)
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, first_id)[
            "allocation_mode"
        ],
        equal_to("fixed"),
        "Precondition: the first member must hold a fixed override",
    )
    assert_that(
        second_before["allocation_mode"],
        is_not(equal_to("fixed")),
        "Precondition: the second member must hold no override",
    )
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)

    details_page.navigate_to(project_name)
    details_page.open_members_tab()
    members.select_members(first_email, second_email)
    bulk_modal = members.open_bulk_override_modal(2)
    bulk_modal.should_offer_use_project_allocation_for("Platform")
    bulk_modal.use_project_allocation_for("Platform")
    bulk_modal.save_override()

    bulk_modal.should_show_saved_toast(bulk_saved_toast(2))
    bulk_modal.should_be_closed()
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, first_id)[
            "allocation_mode"
        ],
        is_not(equal_to("fixed")),
        "The selected member's fixed override must be cleared",
    )
    second_after = budget_utils.get_member_allocation(platform_budget_id, second_id)
    assert_that(
        second_after["allocation_mode"],
        equal_to(second_before["allocation_mode"]),
        "The second member, who held no override, must keep its allocation mode",
    )
    # Finding: clearing the first member's override makes the backend recompute the hard limit
    # of every equal-share member, including the selected second member, so its limit is not
    # asserted here. Only its override state is checked.
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, admin_id)[
            "allocation_mode"
        ],
        equal_to("fixed"),
        "The project admin, who is not selected, must keep the fixed override",
    )


# @case bulk-override-use-project-allocation_TC_004
@pytest.mark.budget
@pytest.mark.ui
def test_bulk_modal_offers_no_use_project_allocation_without_overrides(
    page,
    project_admin_setup,
    project_admin_setup_client,
    two_member_override_ui_ready,
    platform_budget_id,
):
    project_name, _, _, _ = project_admin_setup
    (first_email, _, first_id), (second_email, _, second_id) = (
        two_member_override_ui_ready
    )
    budget_utils = AdminProjectBudgetUtils(project_admin_setup_client)
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, first_id)[
            "allocation_mode"
        ],
        is_not(equal_to("fixed")),
        "Precondition: the first member must hold no override",
    )
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, second_id)[
            "allocation_mode"
        ],
        is_not(equal_to("fixed")),
        "Precondition: the second member must hold no override",
    )
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)

    details_page.navigate_to(project_name)
    details_page.open_members_tab()
    members.select_members(first_email, second_email)
    bulk_modal = members.open_bulk_override_modal(2)

    bulk_modal.should_not_offer_use_project_allocation()
    bulk_modal.should_offer_cancel_and_save()


# @case bulk-override-use-project-allocation_TC_005
@pytest.mark.budget
@pytest.mark.ui
def test_bulk_use_project_allocation_and_override_save_in_one_action(
    page,
    project_admin_setup,
    project_admin_setup_client,
    two_member_override_ui_ready,
):
    project_name, group_id, _, _ = project_admin_setup
    (first_email, _, first_id), (second_email, _, second_id) = (
        two_member_override_ui_ready
    )
    group_utils = AdminProjectBudgetGroupUtils(project_admin_setup_client)
    budget_utils = AdminProjectBudgetUtils(project_admin_setup_client)
    group_utils.update_group(group_id, BULK_TWO_CATEGORY_DISTRIBUTION)
    budget_ids = AdminProjectBudgetUtils.budget_ids_by_category(
        group_utils.get_group(group_id)
    )
    budget_utils.override_member(
        budget_ids["platform"],
        first_id,
        BULK_PLATFORM_MEMBER_MAX,
        BULK_PLATFORM_MEMBER_SOFT,
    )
    budget_utils.override_member(
        budget_ids["cli"], first_id, BULK_CLI_MEMBER_MAX, BULK_CLI_MEMBER_SOFT
    )
    budget_utils.override_member(
        budget_ids["platform"],
        second_id,
        BULK_PLATFORM_MEMBER_MAX,
        BULK_PLATFORM_MEMBER_SOFT,
    )
    budget_utils.override_member(
        budget_ids["cli"], second_id, BULK_CLI_MEMBER_MAX, BULK_CLI_MEMBER_SOFT
    )
    assert_that(
        budget_utils.get_member_allocation(budget_ids["platform"], first_id)[
            "allocation_mode"
        ],
        equal_to("fixed"),
        "Precondition: the first member must hold a fixed platform override",
    )
    assert_that(
        budget_utils.get_member_allocation(budget_ids["cli"], second_id)[
            "allocation_mode"
        ],
        equal_to("fixed"),
        "Precondition: the second member must hold a fixed cli override",
    )
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)

    details_page.navigate_to(project_name)
    details_page.open_members_tab()
    members.select_members(first_email, second_email)
    bulk_modal = members.open_bulk_override_modal(2)
    bulk_modal.should_offer_use_project_allocation_for("Platform")
    bulk_modal.should_offer_use_project_allocation_for("CLI")
    bulk_modal.use_project_allocation_for("Platform")
    bulk_modal.set_hard_limit_for("CLI", BULK_CLI_TYPED_HARD_LIMIT)
    bulk_modal.save_override()

    bulk_modal.should_show_saved_toast(bulk_saved_toast(2))
    bulk_modal.should_be_closed()
    first_platform = budget_utils.get_member_allocation(
        budget_ids["platform"], first_id
    )
    first_cli = budget_utils.get_member_allocation(budget_ids["cli"], first_id)
    second_platform = budget_utils.get_member_allocation(
        budget_ids["platform"], second_id
    )
    second_cli = budget_utils.get_member_allocation(budget_ids["cli"], second_id)
    assert_that(
        first_platform["allocation_mode"],
        is_not(equal_to("fixed")),
        "The platform override must be cleared for the first selected member",
    )
    assert_that(
        second_platform["allocation_mode"],
        is_not(equal_to("fixed")),
        "The platform override must be cleared for the second selected member",
    )
    assert_that(
        first_cli["allocation_mode"],
        equal_to("fixed"),
        "The cli override must stay for the first selected member",
    )
    assert_that(
        second_cli["allocation_mode"],
        equal_to("fixed"),
        "The cli override must stay for the second selected member",
    )
    assert_that(
        first_cli["allocated_max_budget"],
        equal_to(BULK_CLI_TYPED_HARD_LIMIT),
        "The typed cli hard limit must be saved for the first selected member",
    )
    assert_that(
        second_cli["allocated_max_budget"],
        equal_to(BULK_CLI_TYPED_HARD_LIMIT),
        "The typed cli hard limit must be saved for the second selected member",
    )


# @case bulk-override-use-project-allocation_TC_006
@pytest.mark.budget
@pytest.mark.ui
def test_bulk_undo_cancels_pending_use_project_allocation(
    page,
    project_admin_setup,
    project_admin_setup_client,
    two_member_override_ui_ready,
    platform_budget_id,
):
    project_name, _, _, _ = project_admin_setup
    (first_email, _, first_id), (second_email, _, second_id) = (
        two_member_override_ui_ready
    )
    budget_utils = AdminProjectBudgetUtils(project_admin_setup_client)
    budget_utils.override_member(
        platform_budget_id, first_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
    )
    budget_utils.override_member(
        platform_budget_id, second_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
    )
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, first_id)[
            "allocation_mode"
        ],
        equal_to("fixed"),
        "Precondition: the first member must hold a fixed override",
    )
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, second_id)[
            "allocation_mode"
        ],
        equal_to("fixed"),
        "Precondition: the second member must hold a fixed override",
    )
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)

    details_page.navigate_to(project_name)
    details_page.open_members_tab()
    members.select_members(first_email, second_email)
    bulk_modal = members.open_bulk_override_modal(2)
    bulk_modal.use_project_allocation_for("Platform")

    bulk_modal.should_show_undo_for("Platform")
    bulk_modal.should_show_hard_limit_for("Platform", PROJECT_PLATFORM_HARD_LIMIT)
    bulk_modal.undo_for("Platform")
    bulk_modal.should_disable_save_override()

    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, first_id)[
            "allocation_mode"
        ],
        equal_to("fixed"),
        "Undo must keep the first member's fixed override",
    )
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, second_id)[
            "allocation_mode"
        ],
        equal_to("fixed"),
        "Undo must keep the second member's fixed override",
    )
