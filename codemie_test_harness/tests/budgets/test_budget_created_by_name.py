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

"""API tests for the created_by_name field on the admin budgets endpoints.

Covers:
    TC-005 (AC-4, AC-5, AC-9)  created_by_name resolves to the creator's display name across
        GET list / GET by id / POST create / PATCH update / POST sync, and created_by keeps
        its original value and type on every call.
    TC-006 (AC-5, AC-6, AC-7)  GET /v1/admin/budgets sets created_by_name by creator state:
        display name, username fallback, null for a system/predefined budget, and null with a
        200 response when the creator no longer resolves.
"""

import secrets

import pytest
from hamcrest import assert_that, equal_to, is_not, none

from codemie_test_harness.tests.utils.admin_budget_utils import AdminBudgetUtils
from codemie_test_harness.tests.utils.base_utils import get_random_name

# ---------------------------------------------------------------------------
# TC-005
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
def test_created_by_name_resolves_across_admin_endpoints(budget_creator):
    """@case budget-created-by-column_TC_005

    AC-4/AC-5/AC-9: created_by_name resolves to the creator's display name on every admin
    budgets endpoint that returns a budget (budget_router.py:76,97,113,145,164 — create,
    list, get by id, sync, update), and created_by keeps its original value and type
    throughout (BudgetResponse.created_by stays typed str; test_budget_router.py:605).
    """
    user_client, creator_name = budget_creator(get_random_name())
    creator_id = user_client.users.about_me().user_id
    utils = AdminBudgetUtils(user_client)
    budget_id = f"autotest-cbn-{secrets.token_hex(4)}"

    created = utils.create_budget(budget_id, "platform")
    assert_that(
        created["created_by_name"],
        equal_to(creator_name),
        "POST /v1/admin/budgets: created_by_name should be the creator's display name",
    )
    assert_that(
        created["created_by"],
        equal_to(creator_id),
        "POST /v1/admin/budgets: created_by should identify the creator",
    )
    assert_that(
        type(created["created_by"]),
        equal_to(str),
        "POST /v1/admin/budgets: created_by should be a string (AC-9)",
    )

    fetched = utils.get_budget(budget_id)
    assert_that(
        fetched["created_by_name"],
        equal_to(creator_name),
        "GET /v1/admin/budgets/{budgetId}: created_by_name should be the creator's display name",
    )
    assert_that(
        fetched["created_by"],
        equal_to(created["created_by"]),
        "GET /v1/admin/budgets/{budgetId}: created_by should stay unchanged",
    )

    listed = utils.find_budget_in_list(budget_id)
    assert_that(
        listed,
        is_not(none()),
        f"{budget_id} should be present in GET /v1/admin/budgets",
    )
    assert_that(
        listed["created_by_name"],
        equal_to(creator_name),
        "GET /v1/admin/budgets: created_by_name should be the creator's display name",
    )
    assert_that(
        listed["created_by"],
        equal_to(created["created_by"]),
        "GET /v1/admin/budgets: created_by should stay unchanged",
    )

    patched = utils.update_budget(
        budget_id, description="autotest created_by_name check"
    )
    assert_that(
        patched["created_by_name"],
        equal_to(creator_name),
        "PATCH /v1/admin/budgets/{budgetId}: created_by_name should be the creator's display name",
    )
    assert_that(
        patched["created_by"],
        equal_to(created["created_by"]),
        "PATCH /v1/admin/budgets/{budgetId}: created_by should stay unchanged",
    )

    sync_result = utils.sync_budgets()
    synced = next(
        (b for b in sync_result["budgets"] if b["budget_id"] == budget_id), None
    )
    assert_that(
        synced,
        is_not(none()),
        f"{budget_id} should be present in POST /v1/admin/budgets/sync",
    )
    assert_that(
        synced["created_by_name"],
        equal_to(creator_name),
        "POST /v1/admin/budgets/sync: created_by_name should be the creator's display name",
    )
    assert_that(
        synced["created_by"],
        equal_to(created["created_by"]),
        "POST /v1/admin/budgets/sync: created_by should stay unchanged",
    )


# ---------------------------------------------------------------------------
# TC-006
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.parametrize(
    "budget_for_creator_state",
    ["named", "unnamed", "system", "unresolved"],
    indirect=True,
    ids=[
        "user_with_display_name",
        "user_with_no_display_name",
        "system_or_predefined_budget",
        "creator_no_longer_resolves",
    ],
)
def test_list_budgets_sets_created_by_name_by_creator_state(
    admin_budget_utils, budget_for_creator_state
):
    """@case budget-created-by-column_TC_006

    AC-5/AC-6/AC-7: GET /v1/admin/budgets sets created_by_name by creator state —
    the creator's display name (budget_service.py:342), the username when no display name
    is set (same fallback), null while created_by stays unresolved for a system/predefined
    budget (budget_router.py:57, budget_service.py:338), and null with a 200 response — no
    exception — when the creator no longer resolves (user_repository.py:595).
    """
    budget_id, expected_created_by_name = budget_for_creator_state

    match = admin_budget_utils.find_budget_in_list(budget_id)

    assert_that(
        match,
        is_not(none()),
        f"{budget_id} should be present in a successful (200) GET /v1/admin/budgets response",
    )
    assert_that(
        match["created_by_name"],
        equal_to(expected_created_by_name),
        "created_by_name for this creator state",
    )
