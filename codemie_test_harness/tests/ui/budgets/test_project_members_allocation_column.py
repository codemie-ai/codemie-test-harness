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

"""UI test: the Budget Allocations column is shown regardless of the enforce flag (D2).

The column must render for a project admin whether "Enforce member spend limits"
is enabled or disabled on the project, and the per-member override control must
be present in both states.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_members_budget_section import (
    ProjectMembersBudgetSection,
)


@pytest.mark.budget
@pytest.mark.ui
@pytest.mark.parametrize("enforce_member_spend_limits", [True, False])
def test_allocation_column_visible_regardless_of_enforce_flag(
    page,
    project_admin_setup,
    member_override_ui_setup,
    admin_project_utils,
    enforce_member_spend_limits,
):
    project_name, _, _, _ = project_admin_setup
    member_email, _, _ = member_override_ui_setup
    admin_project_utils.set_enforce_member_spend_limits(
        project_name, enforce_member_spend_limits
    )

    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)

    details_page.navigate_to(project_name)
    details_page.open_members_tab()
    members.should_list_member(member_email)
    members.should_show_allocation_column()
    members.should_show_override_control(member_email)
