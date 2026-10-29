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

"""UI test for the Project Admin member budget override on the project details page.

Login is performed by the ``login`` fixture override in conftest.py — the test
authenticates as a dynamically created project-admin user.
"""

import pytest
from hamcrest import assert_that, close_to, equal_to

from codemie_test_harness.tests.test_data.budget_member_override_test_data import (
    MEMBER_OVERRIDE_MAX,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_members_budget_section import (
    ProjectMembersBudgetSection,
)
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.ui.test_data.budget_member_override_ui_test_data import (
    make_member_override_data,
)
from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.mark.budget
@pytest.mark.ui
def test_project_admin_overrides_member_allocation_via_ui(
    page,
    new_context,
    project_admin_setup,
    project_admin_setup_client,
    member_override_ui_ready,
):
    project_name, group_id, pa_email, pa_password = project_admin_setup
    member_email, _, member_id = member_override_ui_ready
    override = make_member_override_data()
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)

    details_page.navigate_to(project_name)
    details_page.should_be_on_project_details_page(project_name)
    details_page.open_members_tab()
    members.should_show_allocation_column()
    members.should_show_override_control(member_email)

    modal = members.open_override_modal(member_email)
    modal.set_hard_limit(override.hard_limit)
    modal.set_soft_limit(override.soft_limit)
    modal.save_override()

    modal.should_be_closed()
    members.should_not_show_error_notification()
    members.should_show_allocation(member_email, 0.0, override.hard_limit)
    members.should_show_fixed_allocation_marker(member_email)

    group = AdminProjectBudgetGroupUtils(project_admin_setup_client).get_group(group_id)
    budget_id = AdminProjectBudgetUtils.budget_ids_by_category(group)["platform"]
    budget = AdminProjectBudgetUtils(project_admin_setup_client).get_budget(budget_id)
    allocations = {m["user_id"]: m for m in budget["member_allocations"]}
    assert_that(allocations[member_id]["allocation_mode"], equal_to("fixed"))
    assert_that(
        allocations[member_id]["allocated_max_budget"],
        close_to(MEMBER_OVERRIDE_MAX, 0.01),
    )

    page.reload()
    details_page.open_members_tab()
    members.should_show_allocation_column()
    members.should_show_override_control(member_email)
    members.should_show_allocation(member_email, 0.0, override.hard_limit)

    fresh_page = new_context().new_page()
    fresh_user_id = project_admin_setup_client.users.about_me().user_id
    LoginPage(fresh_page).login_suppressing_popups(
        pa_email,
        pa_password,
        fresh_user_id,
        CredentialsManager.get_parameter("FRONTEND_URL", ""),
    )
    fresh_details_page = ProjectDetailsPage(fresh_page)
    fresh_details_page.navigate_to(project_name)
    fresh_details_page.open_members_tab()
    fresh_members = ProjectMembersBudgetSection(fresh_page)
    fresh_members.should_show_allocation_column()
    fresh_members.should_show_override_control(member_email)
    fresh_members.should_show_allocation(member_email, 0.0, override.hard_limit)
