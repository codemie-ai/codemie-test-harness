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

"""UI tests for the Project Details Overview tab's 'Active budgets' section.

Covers:
    TC-01  An assigned category (Platform, from `project_admin_setup`) shows
           its real hard limit / soft limit, matching the budget group's API
           data, and no 'Disabled' badge.
    TC-02  Unassigned categories (CLI, Premium models) show the 'Disabled'
           badge and the '— not assigned —' placeholder.
    TC-03  Distributing budget to a previously-unassigned category (CLI) via
           the API makes its card show real limits and drop the 'Disabled'
           badge — round-trip.

Navigation path:
    /settings/administration/projects/{name} → Overview tab (default)
    → Active budgets section

`project_admin_setup` (budgets/conftest.py) creates a budget group with only
the "platform" category assigned (100%), so CLI and Premium models start
unassigned — exactly the state TC-02 and TC-03 need.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_assigned_category_card_shows_real_limits(
    page, project_admin_setup, project_admin_setup_client
):
    project_name, group_id, _, _ = project_admin_setup
    group_utils = AdminProjectBudgetGroupUtils(project_admin_setup_client)
    categories = group_utils.get_group(group_id)["categories"]
    platform = next(c for c in categories if c["category"] == "platform")

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)

    details_page.should_not_show_active_budget_disabled("Platform")
    details_page.should_have_active_budget_hard_limit(
        "Platform", float(platform["max_budget"])
    )
    details_page.should_have_active_budget_soft_limit(
        "Platform", float(platform["soft_budget"])
    )


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_unassigned_categories_show_disabled_placeholder(page, project_admin_setup):
    project_name, _, _, _ = project_admin_setup

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)

    details_page.should_show_active_budget_disabled("CLI")
    details_page.should_show_active_budget_disabled("Premium models")


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_distributing_category_budget_updates_its_card(
    page, project_admin_setup, project_admin_setup_client
):
    project_name, group_id, _, _ = project_admin_setup
    group_utils = AdminProjectBudgetGroupUtils(project_admin_setup_client)

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    details_page.should_show_active_budget_disabled("CLI")

    group_utils.update_group(group_id, {"platform": 60.0, "cli": 40.0})
    cli_category = next(
        c
        for c in group_utils.get_group(group_id)["categories"]
        if c["category"] == "cli"
    )

    page.reload()
    details_page.should_not_show_active_budget_disabled("CLI")
    details_page.should_have_active_budget_hard_limit(
        "CLI", float(cli_category["max_budget"])
    )
    details_page.should_have_active_budget_soft_limit(
        "CLI", float(cli_category["soft_budget"])
    )
