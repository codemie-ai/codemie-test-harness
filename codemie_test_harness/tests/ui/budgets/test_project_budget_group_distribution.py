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

"""UI tests for project budget group spend bucket distribution.

Covers:
    TC-02  Project Admin views and updates distribution via UI
    TC-04  UI shows validation error for invalid distribution input

Login is performed by the ``login`` fixture override in conftest.py — each test
authenticates as a dynamically created project-admin user.

NOTE: These tests require the frontend change (MR 1738) to be
deployed.  When the feature is not yet deployed, the "Manage Budget" button
opens a dropdown (maintainer mode) rather than the distribution-only modal
directly.  The tests are written for the expected post-deployment behaviour.
"""

from __future__ import annotations

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.ui.pageobject.budgets.project_budget_group_page import (
    ProjectBudgetGroupPage,
)
from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)


# ---------------------------------------------------------------------------
# TC-02 — Project Admin views and updates distribution via UI
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.ui
def test_project_admin_updates_distribution_via_ui(
    page, project_admin_setup, project_admin_setup_client
):
    """TC-02: PA navigates to project, opens Manage Budget modal, sets valid
    distribution, saves, asserts no error toast, and verifies persistence via API."""
    project_name, group_id, _, _ = project_admin_setup
    budget_page = ProjectBudgetGroupPage(page)

    budget_page.navigate_to(project_name)
    budget_page.should_show_distribution()
    budget_page.open_manage_budget_modal()
    budget_page.should_have_total_budget_disabled()

    budget_page.set_platform_hard_limit(60.0)
    budget_page.set_platform_soft_limit(48.0)
    budget_page.set_cli_hard_limit(40.0)
    budget_page.submit_distribution()

    budget_page.should_not_show_validation_error()

    group_utils = AdminProjectBudgetGroupUtils(project_admin_setup_client)
    categories = group_utils.get_category_budgets(group_id)
    assert_that(
        categories.get("platform"),
        equal_to(60.0),
        "Platform max_budget should be 60.0 after UI update",
    )
    assert_that(
        categories.get("cli"),
        equal_to(40.0),
        "CLI max_budget should be 40.0 after UI update",
    )


# ---------------------------------------------------------------------------
# TC-009 — Platform hard limit minimum in the distribution-only modal
# ---------------------------------------------------------------------------

PLATFORM_ONLY_HARD_LIMIT = 100.0


@pytest.mark.budget
@pytest.mark.ui
def test_project_admin_cannot_set_platform_hard_limit_to_zero_via_ui(
    page, project_admin_setup, project_admin_setup_client
):
    project_name, group_id, _, _ = project_admin_setup
    budget_page = ProjectBudgetGroupPage(page)

    budget_page.navigate_to(project_name)
    budget_page.should_show_distribution()
    budget_page.open_manage_budget_modal()
    budget_page.should_have_platform_hard_limit("100")

    budget_page.enter_platform_hard_limit("0")

    budget_page.should_have_platform_hard_limit("100")
    budget_page.submit_distribution()
    budget_page.should_not_show_validation_error()

    group_utils = AdminProjectBudgetGroupUtils(project_admin_setup_client)
    assert_that(
        group_utils.get_category_budgets(group_id).get("platform"),
        equal_to(PLATFORM_ONLY_HARD_LIMIT),
        "Platform max_budget should stay 100.0: the 0 entry is refused, not saved",
    )
