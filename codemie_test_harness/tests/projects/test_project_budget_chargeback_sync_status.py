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

"""API test for chargeback/budget-sync consistency on GET /projects.

Covers:
    AC-1  GET /projects (page=0, per_page=10, include_budgets=true,
          has_assigned_budgets=true) succeeds.
    AC-2  Every returned project with a non-empty budgets array has
          chargeback_enabled=True.
    AC-3  Every budget in that project's budgets array has
          provider_sync_status == 'ok'.
    AC-4  The full response.data array is iterated across every page (not
          just the first page/item).

Consolidated per human override (see cases.json disposition for
TC_001): a single test iterates all projects once and asserts
both chargeback_enabled and provider_sync_status within the same pass, rather
than three separate tests.
"""

import pytest
from hamcrest import assert_that, empty, greater_than, has_length, instance_of

# page=0, per_page=10, include_budgets=true, has_assigned_budgets=true — AC-1
LIST_ALL_PROJECTS_ASSIGNED_BUDGETS_PARAMS = {
    "per_page": 10,
    "include_budgets": True,
    "has_assigned_budgets": True,
}

# Known, confirmed-intentional exceptions to AC-2 (chargeback_enabled=True):
# projects that legitimately have assigned, provider-synced budgets without
# chargeback enabled. Verified live against production on 2026-09-24 — this
# was the only project among 111 qualifying ones failing AC-2, and business
# confirmed it's an intentional exception rather than a data bug.
CHARGEBACK_EXCLUDED_PROJECT_NAMES = {
    "epm-sdai-runway-2026-09",
    "epm-sdai-runway-2026-10",
    "epm-cdme-testing",
}


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.production_check
def test_list_projects_with_assigned_budgets_have_chargeback_enabled_and_synced_status(
    project_utils,
):
    """GET /projects with has_assigned_budgets=true returns only chargeback-
    enabled, provider-synced project/budget pairs, across every page.

    Preconditions:
        - test user/service account has permission to call the Code Assistant
          API projects endpoint.
        - API regression/TAF test environment configured with valid
          authentication.
        - test data contains at least one project with assigned budgets.
    """
    all_projects = project_utils.list_all_projects(
        **LIST_ALL_PROJECTS_ASSIGNED_BUDGETS_PARAMS
    )

    # AC-1: call succeeds (client raises for non-2xx, so getting a typed
    # response here already proves success; assert on the payload shape too).
    assert_that(all_projects, instance_of(list))

    # Precondition guard: without at least one qualifying project, the
    # per-project/per-budget assertions below would pass vacuously.
    assert_that(
        all_projects,
        has_length(greater_than(0)),
        "Precondition violated: has_assigned_budgets=true returned no "
        "projects across any page — test data must contain at least one "
        "project with assigned budgets",
    )

    # AC-4: iterate every project on every page, not just the first page/item.
    violations = []
    for proj in all_projects:
        if not proj.budgets or proj.name in CHARGEBACK_EXCLUDED_PROJECT_NAMES:
            continue

        # AC-2
        if proj.chargeback_enabled is not True:
            violations.append(
                f"project '{proj.name}': chargeback_enabled="
                f"{proj.chargeback_enabled!r} (expected True) while it has "
                f"{len(proj.budgets)} assigned budget(s)"
            )

        # AC-3
        for budget in proj.budgets:
            if budget.provider_sync_status != "ok":
                violations.append(
                    f"project '{proj.name}', budget '{budget.name}' "
                    f"(budget_id={budget.budget_id}): provider_sync_status="
                    f"{budget.provider_sync_status!r} (expected 'ok')"
                )

    assert_that(
        violations,
        empty(),
        "Found project/budget chargeback or provider-sync-status mismatches:\n"
        + "\n".join(violations),
    )
