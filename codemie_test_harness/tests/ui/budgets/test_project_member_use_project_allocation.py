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

"""UI test: 'Use project allocation' in the member Budget Override modal restores the project allocation."""

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
from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)


# @case remove-reset-budget-usage_TC_003
@pytest.mark.xfail(
    reason=(
        "Confirmed pre-existing product defect, not a test bug, and unrelated to "
        "the budget-usage reset removal this file was written for: clearing a "
        "member's LAST fixed budget override hides the whole per-category action row (including the 'Undo' button), because "
        "MemberAllocationOverrideModal computes hasAnyOverride across all categories "
        "(codemie-ui src/pages/settings/administration/projectsManagement/components/"
        "MemberAllocationOverrideModal.tsx:153) and passes that single flag as "
        "hasActionRow to every category card (:325, :351). Once the only override is "
        "cleared, 'Undo' disappears, so should_mark_category_as_using_project_allocation "
        "fails. strict=True: when this is fixed upstream the test XPASSes and the "
        "suite flags it so this mark gets removed. See "
        "remove-reset-budget-usage_TC_008 for the case where Undo works."
    ),
    raises=AssertionError,
    strict=True,
)
@pytest.mark.budget
@pytest.mark.ui
def test_use_project_allocation_clears_member_override(
    page,
    project_admin_setup,
    project_admin_setup_client,
    member_override_ui_ready,
    platform_budget_id,
):
    project_name, _, _, _ = project_admin_setup
    member_email, _, member_id = member_override_ui_ready
    budget_utils = AdminProjectBudgetUtils(project_admin_setup_client)
    budget_utils.override_member(
        platform_budget_id, member_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
    )
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, member_id)[
            "allocation_mode"
        ],
        equal_to("fixed"),
        "Precondition: the member must hold a fixed override",
    )
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)

    details_page.navigate_to(project_name)
    details_page.open_members_tab()
    members.should_show_fixed_allocation_marker(member_email)

    modal = members.open_override_modal(member_email)
    modal.use_project_allocation()
    modal.should_mark_category_as_using_project_allocation()
    modal.save_override()

    modal.should_be_closed()
    members.should_not_show_error_notification()
    members.should_not_show_fixed_allocation_marker(member_email)
    assert_that(
        budget_utils.get_member_allocation(platform_budget_id, member_id)[
            "allocation_mode"
        ],
        is_not(equal_to("fixed")),
        "Saving 'Use project allocation' must clear the fixed override",
    )


# @case remove-reset-budget-usage_TC_008
@pytest.mark.budget
@pytest.mark.ui
def test_use_project_allocation_shows_undo_when_another_category_stays_overridden(
    page,
    project_admin_setup,
    project_admin_setup_client,
    member_override_ui_ready,
):
    project_name, group_id, _, _ = project_admin_setup
    member_email, _, member_id = member_override_ui_ready
    group_utils = AdminProjectBudgetGroupUtils(project_admin_setup_client)
    budget_utils = AdminProjectBudgetUtils(project_admin_setup_client)

    group_utils.update_group(group_id, {"platform": 60.0, "cli": 40.0})
    budget_ids = AdminProjectBudgetUtils.budget_ids_by_category(
        group_utils.get_group(group_id)
    )
    for category in ("platform", "cli"):
        budget_utils.override_member(
            budget_ids[category], member_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
        )
        assert_that(
            budget_utils.get_member_allocation(budget_ids[category], member_id)[
                "allocation_mode"
            ],
            equal_to("fixed"),
            f"Precondition: the member must hold a fixed {category} override",
        )
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)

    details_page.navigate_to(project_name)
    details_page.open_members_tab()
    members.should_show_fixed_allocation_marker_for(member_email, "CLI")

    modal = members.open_override_modal_from_category(member_email, "CLI")
    modal.use_project_allocation_for("Platform")

    modal.should_show_undo_for("Platform")
    modal.should_still_offer_use_project_allocation_for("CLI")
    # Nothing is saved: the pre-save UI state is the whole contract under test.
    modal.cancel()
    modal.should_be_closed()
