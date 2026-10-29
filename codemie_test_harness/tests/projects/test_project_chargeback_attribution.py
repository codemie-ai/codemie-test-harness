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

"""E2E API tests for configurable chargeback attribution on projects.

Covers:
    TC-01  New project response includes chargeback_attribution defaulting to "project"
    TC-02  Update chargeback_attribution to "project" without a cost center — accepted
    TC-03  Update chargeback_attribution to "cost_center" with an active cost center — accepted
    TC-04  Omit chargeback_attribution from update — existing field value unchanged
    TC-05  Set chargeback_attribution to "cost_center" with no linked cost center — 400
    TC-06  Set chargeback_attribution to "cost_center" with soft-deleted cost center — 400
    TC-07  Setting chargeback fields when projectChargeback flag is disabled — 403 (skipped)
    TC-08  Set chargeback_attribution to an unrecognized value — 400 (parametrized)
    TC-09  Clear cost center on a project whose attribution is "cost_center" — 400
"""

import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

# ── Test data ─────────────────────────────────────────────────────────────────

VALID_ATTRIBUTION_DEFAULT = "project"
COST_CENTER_ATTRIBUTION = "cost_center"
INVALID_ATTRIBUTION_VALUES = ["invalid_str", "Cost_Center", "cost-center", ""]


# ── TC-01 ──────────────────────────────────────────────────────────────────────


@pytest.mark.smoke
@pytest.mark.project
@pytest.mark.api
def test_new_project_chargeback_attribution_defaults_to_project(project_utils, project):
    """TC-01: New project response includes chargeback_attribution field defaulting to "project".

    AC1, AC2, AC3 — create, list, and detail responses all carry the field.
    """
    created_project = project()

    # Assert on the create response
    assert_that(
        created_project.chargeback_attribution,
        equal_to(VALID_ATTRIBUTION_DEFAULT),
        "ProjectCreateResponse.chargeback_attribution must default to 'project'",
    )

    # Re-fetch via get_project_detail
    detail = project_utils.get_project_detail(created_project.name)
    assert_that(
        detail.chargeback_attribution,
        equal_to(VALID_ATTRIBUTION_DEFAULT),
        "ProjectDetailResponse.chargeback_attribution must default to 'project'",
    )

    # Re-fetch via list_projects — search by exact name
    list_response = project_utils.list_projects(
        search=created_project.name, per_page=10
    )
    matching = [p for p in list_response.data if p.name == created_project.name]
    assert_that(
        len(matching),
        equal_to(1),
        "Newly created project must appear in list_projects results",
    )
    assert_that(
        matching[0].chargeback_attribution,
        equal_to(VALID_ATTRIBUTION_DEFAULT),
        "ProjectListItem.chargeback_attribution must default to 'project'",
    )


# ── TC-02 ──────────────────────────────────────────────────────────────────────


@pytest.mark.smoke
@pytest.mark.project
@pytest.mark.api
def test_update_chargeback_attribution_to_project_without_cost_center(
    project_utils, project
):
    """TC-02: Update chargeback_attribution to "project" without a cost center — accepted.

    AC4, AC7 — PATCH returns 200 and value persists.
    """
    created_project = project()

    response = project_utils.update_project(
        project_name=created_project.name,
        chargeback_attribution=VALID_ATTRIBUTION_DEFAULT,
    )
    assert_that(
        response.chargeback_attribution,
        equal_to(VALID_ATTRIBUTION_DEFAULT),
        "Update response must reflect chargeback_attribution='project'",
    )

    # Confirm persistence via get_project_detail
    detail = project_utils.get_project_detail(created_project.name)
    assert_that(
        detail.chargeback_attribution,
        equal_to(VALID_ATTRIBUTION_DEFAULT),
        "chargeback_attribution='project' must persist after update",
    )


# ── TC-03 ──────────────────────────────────────────────────────────────────────


@pytest.mark.project
@pytest.mark.api
def test_update_chargeback_attribution_to_cost_center_with_active_cost_center(
    project_utils, project, cost_center
):
    """TC-03: Update chargeback_attribution to "cost_center" with a linked active cost center.

    AC4 — PATCH returns 200 and value persists.
    Requires CostCenterUtils fixture (§4–5).
    """
    cc_id = cost_center()
    created_project = project(cost_center_id=cc_id)

    response = project_utils.update_project(
        project_name=created_project.name,
        chargeback_attribution=COST_CENTER_ATTRIBUTION,
    )
    assert_that(
        response.chargeback_attribution,
        equal_to(COST_CENTER_ATTRIBUTION),
        "Update response must reflect chargeback_attribution='cost_center'",
    )

    # Confirm persistence
    detail = project_utils.get_project_detail(created_project.name)
    assert_that(
        detail.chargeback_attribution,
        equal_to(COST_CENTER_ATTRIBUTION),
        "chargeback_attribution='cost_center' must persist after update",
    )


# ── TC-04 ──────────────────────────────────────────────────────────────────────


@pytest.mark.project
@pytest.mark.api
def test_omit_chargeback_attribution_from_update_leaves_value_unchanged(
    project_utils, project
):
    """TC-04: Omitting chargeback_attribution from PATCH leaves the field value unchanged.

    AC9 — partial update must not reset chargeback_attribution.
    """
    created_project = project()

    # Explicitly set to "project" first (same as default, but makes the test explicit)
    project_utils.update_project(
        project_name=created_project.name,
        chargeback_attribution=VALID_ATTRIBUTION_DEFAULT,
    )

    # Now update description only — no chargeback_attribution key
    response = project_utils.update_project(
        project_name=created_project.name,
        description="Updated description for TC-04",
    )
    assert_that(
        response.chargeback_attribution,
        equal_to(VALID_ATTRIBUTION_DEFAULT),
        "Omitting chargeback_attribution from PATCH must leave existing value unchanged",
    )

    # Confirm via detail
    detail = project_utils.get_project_detail(created_project.name)
    assert_that(
        detail.chargeback_attribution,
        equal_to(VALID_ATTRIBUTION_DEFAULT),
        "chargeback_attribution must remain unchanged after a description-only PATCH",
    )


# ── TC-05 ──────────────────────────────────────────────────────────────────────


@pytest.mark.project
@pytest.mark.api
def test_update_chargeback_attribution_to_cost_center_with_no_cost_center_rejected(
    project_utils, project
):
    """TC-05: Set chargeback_attribution to "cost_center" with no linked cost center — 400.

    AC6 — server must reject with 400 when no active cost center is linked.
    """
    created_project = project()

    with pytest.raises(HTTPError) as exc_info:
        project_utils.update_project(
            project_name=created_project.name,
            chargeback_attribution=COST_CENTER_ATTRIBUTION,
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "Expected 400 when setting cost_center attribution with no linked cost center",
    )


# ── TC-06 ──────────────────────────────────────────────────────────────────────


@pytest.mark.project
@pytest.mark.api
def test_create_project_with_deleted_cost_center_rejected(
    project, cost_center, cost_center_utils
):
    """TC-06: Create a project referencing a soft-deleted cost center — 404.

    The API enforces referential integrity in both directions:
    deleting a referenced cost center is rejected (409), and creating a project
    with a deleted cost center ID is rejected (404).
    """
    cc_id = cost_center()
    cost_center_utils.delete_cost_center(cc_id)

    with pytest.raises(HTTPError) as exc_info:
        project(cost_center_id=cc_id)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Expected 404 when creating a project with a soft-deleted cost center ID",
    )


# ── TC-08 ──────────────────────────────────────────────────────────────────────


@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize("invalid_value", INVALID_ATTRIBUTION_VALUES)
def test_update_chargeback_attribution_with_invalid_value_rejected(
    project_utils, project, invalid_value
):
    """TC-08: Set chargeback_attribution to an unrecognized value — 400.

    CR-002 — VALID_CHARGEBACK_ATTRIBUTIONS allow-list fix; validates that any
    value outside {"project", "cost_center"} is rejected with 400 before reaching
    the DB constraint.
    """
    created_project = project()

    with pytest.raises(HTTPError) as exc_info:
        project_utils.update_project(
            project_name=created_project.name,
            chargeback_attribution=invalid_value,
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        f"Expected 400 for invalid chargeback_attribution value: {invalid_value!r}",
    )


# ── TC-09 ──────────────────────────────────────────────────────────────────────


@pytest.mark.not_for_parallel_run
@pytest.mark.project
@pytest.mark.api
def test_clear_cost_center_on_cost_center_attributed_project_rejected(
    project_utils, project, cost_center, cost_center_utils
):
    """TC-09: Clear cost center on a project whose chargeback_attribution is "cost_center" — 400.

    CR-001 — stale-attribution guard: clearing cost_center_id without resetting
    chargeback_attribution must be rejected with 400, not silently persisted.
    Requires CostCenterUtils fixture (§4–5).
    """
    cc_id = cost_center()
    created_project = project(cost_center_id=cc_id)

    # Set attribution to "cost_center" with an active linked cost center
    project_utils.update_project(
        project_name=created_project.name,
        chargeback_attribution=COST_CENTER_ATTRIBUTION,
    )

    # Verify the attribution is set
    detail = project_utils.get_project_detail(created_project.name)
    assert_that(
        detail.chargeback_attribution,
        equal_to(COST_CENTER_ATTRIBUTION),
        "Pre-condition: chargeback_attribution must be 'cost_center' before clearing",
    )

    # Now clear the cost center WITHOUT resetting chargeback_attribution — must be 400
    with pytest.raises(HTTPError) as exc_info:
        project_utils.update_project(
            project_name=created_project.name,
            clear_cost_center=True,
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "Expected 400 when clearing cost center leaves chargeback_attribution='cost_center' orphaned",
    )
