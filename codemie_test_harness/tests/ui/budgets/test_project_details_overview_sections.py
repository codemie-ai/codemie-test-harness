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

"""UI tests for the Project Details page's Overview tab layout and counts.

Covers:
    A1  Project Admin sees the tab bar (Overview, Members, Budgets, Integrations)
        and the Overview sections (Project information, Financial summary, Active budgets).
    A2  Users and Admins values in Project information match the project detail API.

The Chargeback / Routing impact checks (B1) live in
administration/test_project_budget_chargeback.py: the chargeback switch needs
the admin login, which this package does not use.

Runs as the project admin from `project_admin_setup` (budgets/conftest.py).
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_project_admin_sees_detail_tabs_and_overview_sections(
    page, project_admin_setup
):
    project_name, _, _, _ = project_admin_setup
    details_page = ProjectDetailsPage(page)

    details_page.navigate_to(project_name)

    details_page.should_show_detail_tabs()
    details_page.should_show_overview_sections()


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_overview_users_and_admins_match_project_api(
    page, project_admin_setup, admin_project_utils
):
    project_name, _, _, _ = project_admin_setup
    project_detail = admin_project_utils.get_project_detail(project_name)
    details_page = ProjectDetailsPage(page)

    details_page.navigate_to(project_name)

    details_page.should_have_users_count(project_detail.user_count)
    details_page.should_have_admins_count(project_detail.admin_count)
