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

"""UI tests: administration screens list users A to Z by name, the default of GET /v1/admin/users.

Users are created per test (admin API on local-auth stands, auth server plus first login
elsewhere); the assertions only look at users found by the per-run search token.
"""

import pytest

from codemie_test_harness.tests.test_data.admin_users_order_test_data import (
    MIXED_CASE_NAMES,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_members_section import (
    ProjectMembersSection,
)
from codemie_test_harness.tests.ui.pageobject.administration.user_management_page import (
    UserManagementPage,
)


@pytest.mark.project
@pytest.mark.ui
def test_project_members_tab_lists_members_a_to_z_without_sort_params(
    page, project_with_ordered_members
):
    # @case admin-users-default-name-order_TC_002
    project_name, members = project_with_ordered_members
    members_section = ProjectMembersSection(page).capture_user_list_requests()
    details_page = ProjectDetailsPage(page)

    details_page.navigate_to(project_name)
    details_page.open_members_tab()

    members_section.should_list_members_in_order(members.token, members.emails)
    members_section.should_have_loaded_members_without_sort_params()


@pytest.mark.user
@pytest.mark.ui
def test_users_management_lists_users_a_to_z(page, ordered_users):
    # @case admin-users-default-name-order_TC_005
    users = ordered_users(MIXED_CASE_NAMES)
    users_page = UserManagementPage(page).navigate_to()

    users_page.should_list_users_in_order(users.token, users.emails)
