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

"""API tests for the Platform hard limit > 0 rule of project budget groups.

Covers:
    TC-001  Backend rejects Platform hard limit 0 on create and on update, nothing saved
    TC-002  Backend accepts Platform above 0 with CLI, Premium and all Soft limits at 0

The legacy "saved Platform 0" group of AC-5 cannot be built any more (the backend refuses
to create it), so the update tests send a Platform-0 payload to a valid group and go
through the same validator.
"""

import secrets

import pytest
from hamcrest import (
    all_of,
    assert_that,
    close_to,
    contains_string,
    empty,
    equal_to,
    has_entries,
)
from requests.exceptions import HTTPError

from codemie_test_harness.tests.test_data.budget_platform_hard_limit_test_data import (
    ACCEPTED_DISTRIBUTIONS,
    GROUP_TOTAL_AMOUNT,
    PLATFORM_ZERO_MESSAGE_PARTS,
    platform_zero_data,
)

# Persisted dollar amounts are derived from percentages, so allow a float epsilon.
AMOUNT_TOLERANCE = 0.001


# ---------------------------------------------------------------------------
# TC-001 — Backend rejects Platform hard limit 0
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
def test_create_budget_group_rejects_platform_hard_limit_zero(
    budget_project, admin_budget_group_utils
):
    td = platform_zero_data()

    with pytest.raises(HTTPError) as exc_info:
        admin_budget_group_utils.create_budget_group(
            project_name=budget_project,
            total_amount=GROUP_TOTAL_AMOUNT,
            categories=td.platform_zero_pcts,
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "Create with Platform pct 0 should return 400",
    )
    assert_that(
        exc_info.value.response.text,
        all_of(*[contains_string(part) for part in PLATFORM_ZERO_MESSAGE_PARTS]),
        "400 body should name the platform category and the hard limit rule",
    )
    assert_that(
        admin_budget_group_utils.list_by_project(budget_project),
        empty(),
        "No budget group should be created by the rejected request",
    )


@pytest.mark.budget
@pytest.mark.api
def test_update_budget_group_rejects_platform_hard_limit_zero(
    project_budget_group, admin_budget_group_utils
):
    td = platform_zero_data()
    _, group_id = project_budget_group
    original_budgets = admin_budget_group_utils.get_category_budgets(group_id)
    assert_that(
        original_budgets,
        has_entries({"platform": close_to(GROUP_TOTAL_AMOUNT, AMOUNT_TOLERANCE)}),
        "The group should start with the whole budget on Platform",
    )

    with pytest.raises(HTTPError) as exc_info:
        admin_budget_group_utils.update_group(group_id, td.platform_zero_pcts)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "Update with Platform pct 0 should return 400",
    )
    assert_that(
        exc_info.value.response.text,
        all_of(*[contains_string(part) for part in PLATFORM_ZERO_MESSAGE_PARTS]),
        "400 body should name the platform category and the hard limit rule",
    )
    assert_that(
        admin_budget_group_utils.get_category_budgets(group_id),
        equal_to(original_budgets),
        "Categories should be unchanged after the rejected update",
    )


# ---------------------------------------------------------------------------
# TC-002 — Backend accepts Platform above 0, other limits may be 0
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.parametrize(
    "distribution", ACCEPTED_DISTRIBUTIONS, ids=[d.id for d in ACCEPTED_DISTRIBUTIONS]
)
@pytest.mark.api
def test_create_budget_group_accepts_platform_above_zero_and_zero_soft_limits(
    budget_project, admin_project_budget_utils, admin_budget_group_utils, distribution
):
    group = admin_project_budget_utils.create_budget_group(
        project_name=budget_project,
        name=f"autotest-phl-{secrets.token_hex(4)}",
        categories=distribution.create_categories(),
    )

    hard_limits = admin_budget_group_utils.get_category_budgets(group["group_id"])
    soft_limits = admin_budget_group_utils.get_category_soft_budgets(group["group_id"])
    expected = distribution.expected_hard_limits()
    assert_that(
        hard_limits,
        has_entries({c: close_to(v, AMOUNT_TOLERANCE) for c, v in expected.items()}),
        "Persisted hard limits should match the created distribution",
    )
    assert_that(
        sum(hard_limits.values()),
        close_to(GROUP_TOTAL_AMOUNT, AMOUNT_TOLERANCE),
        "Categories with a 0 share should not hold any hard limit",
    )
    assert_that(
        soft_limits,
        has_entries({c: close_to(0.0, AMOUNT_TOLERANCE) for c in expected}),
        "Soft limits sent as 0 should be persisted as 0",
    )


@pytest.mark.budget
@pytest.mark.parametrize(
    "distribution", ACCEPTED_DISTRIBUTIONS, ids=[d.id for d in ACCEPTED_DISTRIBUTIONS]
)
@pytest.mark.api
def test_update_budget_group_accepts_platform_above_zero_and_zero_soft_limits(
    project_budget_group, admin_budget_group_utils, distribution
):
    _, group_id = project_budget_group

    admin_budget_group_utils.update_raw(group_id, distribution.update_body())

    hard_limits = admin_budget_group_utils.get_category_budgets(group_id)
    soft_limits = admin_budget_group_utils.get_category_soft_budgets(group_id)
    expected = distribution.expected_hard_limits()
    assert_that(
        hard_limits,
        has_entries({c: close_to(v, AMOUNT_TOLERANCE) for c, v in expected.items()}),
        "Persisted hard limits should match the updated distribution",
    )
    assert_that(
        sum(hard_limits.values()),
        close_to(GROUP_TOTAL_AMOUNT, AMOUNT_TOLERANCE),
        "Categories with a 0 share should not hold any hard limit",
    )
    assert_that(
        soft_limits,
        has_entries({c: close_to(0.0, AMOUNT_TOLERANCE) for c in expected}),
        "Soft limits sent as 0 should be persisted as 0",
    )
