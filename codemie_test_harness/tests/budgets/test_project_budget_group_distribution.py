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

"""API tests for project budget group spend bucket distribution.

Covers:
    TC-01  Project admin reads and updates spend bucket distribution
    TC-03  System rejects invalid distribution values
    TC-05  Unauthorized actors cannot update spend bucket distribution
    TC-06  Project admin cannot update non-distribution fields
    TC-07  Audit event recorded after distribution update
"""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    greater_than_or_equal_to,
)
from requests.exceptions import HTTPError

from codemie_test_harness.tests.test_data.budget_spend_bucket_distribution_test_data import (
    spend_bucket_distribution_test_data,
)
from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _extract_category_pcts(response: dict) -> dict:
    """Extract {category: max_budget} mapping from budget group GET response.

    The API returns a ``categories`` list where each item has a ``category``
    (string name) and ``max_budget`` (dollar hard limit) field.
    """
    result = {}
    for item in response.get("categories", []):
        cat = item.get("category")
        max_budget = item.get("max_budget")
        if cat is not None and max_budget is not None:
            try:
                result[cat] = float(max_budget)
            except (TypeError, ValueError):
                continue
    return result


# ---------------------------------------------------------------------------
# TC-01 — Project admin reads and updates spend bucket distribution
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
def test_project_admin_reads_and_updates_spend_bucket_distribution(
    project_budget_group,
    project_admin_budget_group_utils,
):
    """TC-01: GET returns current categories; PUT with valid payload succeeds; GET confirms update."""
    td = spend_bucket_distribution_test_data()
    _, group_id = project_budget_group

    # GET — verify the group is accessible
    get_response = project_admin_budget_group_utils.get_group(group_id)
    assert_that(
        isinstance(get_response, dict),
        equal_to(True),
        "GET /v1/admin/project-budget-groups/{group_id} should return a dict",
    )

    # PUT — update distribution to valid categories
    put_response = project_admin_budget_group_utils.update_group(
        group_id, td.valid_categories
    )
    assert_that(
        isinstance(put_response, dict),
        equal_to(True),
        "PUT with valid categories should return 200 with a dict body",
    )

    # GET again — assert updated categories match
    updated_response = project_admin_budget_group_utils.get_group(group_id)
    updated_pcts = _extract_category_pcts(updated_response)
    for category, expected_pct in td.valid_categories.items():
        assert_that(
            updated_pcts.get(category),
            equal_to(expected_pct),
            f"Category '{category}' should have pct={expected_pct} after update",
        )


# ---------------------------------------------------------------------------
# TC-03 — System rejects invalid distribution values
# ---------------------------------------------------------------------------


_INVALID_DISTRIBUTION_PARAMS = [
    pytest.param(
        "sum_off",
        lambda td: td.invalid_sum_categories,
        id="sum_off",
    ),
    pytest.param(
        "no_platform",
        lambda td: td.missing_platform_categories,
        id="no_platform",
    ),
    pytest.param(
        "negative",
        lambda td: td.negative_pct_categories,
        id="negative",
    ),
]


@pytest.mark.budget
@pytest.mark.parametrize("label,get_categories", _INVALID_DISTRIBUTION_PARAMS)
@pytest.mark.api
def test_system_rejects_invalid_distribution_values(
    project_budget_group,
    project_admin_budget_group_utils,
    label,
    get_categories,
):
    """TC-03: PUT with invalid categories returns 400 or 422; original categories unchanged."""
    td = spend_bucket_distribution_test_data()
    _, group_id = project_budget_group

    # Capture original categories before the invalid PUT
    original_response = project_admin_budget_group_utils.get_group(group_id)
    original_pcts = _extract_category_pcts(original_response)
    assert_that(
        len(original_pcts),
        greater_than_or_equal_to(1),
        "original_pcts must be non-empty — _extract_category_pcts must succeed before comparing state",
    )

    invalid_cats = get_categories(td)

    with pytest.raises(HTTPError) as exc_info:
        project_admin_budget_group_utils.update_group(group_id, invalid_cats)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        f"PUT with invalid distribution ({label}) should return 400",
    )

    # Verify original categories are unchanged
    after_response = project_admin_budget_group_utils.get_group(group_id)
    after_pcts = _extract_category_pcts(after_response)
    assert_that(
        after_pcts,
        equal_to(original_pcts),
        f"Categories should be unchanged after rejected PUT ({label})",
    )


# ---------------------------------------------------------------------------
# TC-05 — Unauthorized actors cannot update spend bucket distribution
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
def test_unauthorized_actors_cannot_update_spend_bucket_distribution(
    project_budget_group,
    cross_project_admin_client,
    keycloak_regular_user,
):
    """TC-05: Cross-project admin and regular user receive 403 on PUT."""
    td = spend_bucket_distribution_test_data()
    _, group_id = project_budget_group

    # Regular user — no project admin role at all
    from codemie_test_harness.tests.utils.client_factory import get_client

    email, password = keycloak_regular_user
    regular_client = get_client(username=email, password=password)
    regular_utils = AdminProjectBudgetGroupUtils(regular_client)
    with pytest.raises(HTTPError) as exc_info:
        regular_utils.update_group(group_id, td.valid_categories)
    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        "Regular user should receive 403",
    )

    # Cross-project admin — admin of a different project
    cross_utils = AdminProjectBudgetGroupUtils(cross_project_admin_client)
    with pytest.raises(HTTPError) as exc_info:
        cross_utils.update_group(group_id, td.valid_categories)
    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        "Cross-project admin should receive 403",
    )


# ---------------------------------------------------------------------------
# TC-06 — Project admin cannot update non-distribution fields
# ---------------------------------------------------------------------------


_RESTRICTED_FIELDS = [
    pytest.param({"name": "restricted-update"}, id="name"),
    pytest.param({"total_amount": 999.0}, id="total_amount"),
    pytest.param({"budget_duration": "60d"}, id="budget_duration"),
    pytest.param({"description": "attempted restricted update"}, id="description"),
]

_EXPECTED_RESTRICTION_DETAIL = "Project administrators may only update the categories and soft_limit_notification_enabled fields."


@pytest.mark.budget
@pytest.mark.parametrize("restricted_body", _RESTRICTED_FIELDS)
@pytest.mark.api
def test_project_admin_cannot_update_non_distribution_fields(
    project_budget_group,
    project_admin_budget_group_utils,
    restricted_body,
):
    """TC-06: PUT with restricted field as project admin returns 403 with correct message."""
    _, group_id = project_budget_group
    # project_admin_budget_group_utils.get_group()
    with pytest.raises(HTTPError) as exc_info:
        project_admin_budget_group_utils.update_raw(group_id, restricted_body)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        f"PUT with restricted field {list(restricted_body.keys())} should return 403",
    )
    try:
        error_body = exc_info.value.response.json()
    except ValueError:
        pytest.fail(f"403 body was not JSON: {exc_info.value.response.text[:200]}")
    err = error_body.get("error", {})
    details = err.get("details", "") if isinstance(err, dict) else ""
    assert_that(
        details,
        contains_string(_EXPECTED_RESTRICTION_DETAIL),
        "403 body should contain the field-restriction detail message",
    )


# ---------------------------------------------------------------------------
# TC-07 — Audit event recorded after distribution update
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
def test_audit_event_recorded_after_distribution_update(
    project_budget_group,
    project_admin_budget_group_utils,
    budget_group_activity_utils,
):
    """TC-07: PUT valid categories → audit event budget.project_budget_group.updated recorded."""
    td = spend_bucket_distribution_test_data()
    _, group_id = project_budget_group

    import time  # noqa: PLC0415

    project_admin_budget_group_utils.update_group(group_id, td.valid_categories)

    # Audit events are written asynchronously — poll until the event appears.
    deadline = time.monotonic() + 15
    response = None
    while True:
        try:
            response = budget_group_activity_utils.list_activity_events(
                entity_id=group_id,
                event_type=["budget.project_budget_group.updated"],
                domain=["budget_management"],
            )
            if bool(response.data) or time.monotonic() >= deadline:
                break
        except Exception:
            if time.monotonic() >= deadline:
                break
        time.sleep(1)

    assert_that(
        response is not None and response.data is not None,
        equal_to(True),
        "list_activity_events must return a non-None response with non-None data",
    )
    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one budget.project_budget_group.updated event should be recorded",
    )
    record = response.data[0]
    assert_that(
        record.event_type,
        equal_to("budget.project_budget_group.updated"),
        "event_type should be budget.project_budget_group.updated",
    )
    assert_that(
        record.domain,
        equal_to("budget_management"),
        "domain should be budget_management",
    )
    assert_that(
        record.entity_type,
        equal_to("project_budget_group"),
        "entity_type should be project_budget_group",
    )
