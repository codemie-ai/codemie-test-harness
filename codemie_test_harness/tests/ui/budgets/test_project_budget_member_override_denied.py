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

"""UI test: a project member without the Project Admin role has no member override controls.

Overrides the directory ``login`` fixture so the browser authenticates as a
developer-only member of the project instead of the project admin.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_members_budget_section import (
    ProjectMembersBudgetSection,
)
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.fixture(autouse=True)
def login(page, project_admin_setup, member_override_ui_setup):
    member_email, member_password, member_id = member_override_ui_setup
    LoginPage(page).login_suppressing_popups(
        member_email,
        member_password,
        member_id,
        CredentialsManager.get_parameter("FRONTEND_URL", ""),
    )


@pytest.mark.budget
@pytest.mark.ui
def test_regular_member_does_not_see_member_override_controls(
    page, project_admin_setup, member_override_ui_setup
):
    project_name, _, pa_email, _ = project_admin_setup
    member_email, _, _ = member_override_ui_setup
    details_page = ProjectDetailsPage(page)
    members = ProjectMembersBudgetSection(page)

    details_page.navigate_to(project_name)

    details_page.should_be_on_project_details_page(project_name)
    details_page.open_members_tab()
    members.should_list_member(member_email)
    members.should_list_member(pa_email)
    members.should_not_show_allocation_column()
    members.should_not_show_override_controls()
    details_page.should_not_have_manage_budget_button()
    details_page.should_not_show_budgets_and_integrations_tabs()
