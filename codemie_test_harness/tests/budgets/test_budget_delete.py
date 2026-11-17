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

"""API tests for DELETE /v1/admin/budgets/{budgetId}.

Only a maintainer creates, updates and deletes budgets; a platform admin can only view
them, so every delete that is expected to go through acts as the maintainer.

Covers:
    TC-001 (AC-1)  a manual budget with no users is hard-deleted, in CodeMie and in LiteLLM,
        whether LiteLLM still has it or already lost it
    TC-002 (AC-1, AC-4)  a maintainer deletes it, a platform admin is rejected
    TC-003 (AC-2)  assigned users block the delete (409), nothing changes
    TC-004 (AC-3)  a preconfigured budget is rejected like an edit of it
    TC-005 (AC-4)  a user without a platform role is rejected
    TC-006 (AC-5)  an unknown id is 404
    TC-008 (AC-7)  sync does not bring a deleted budget back
    TC-011 (gap from the change)  a project budget cannot be deleted here
    TC-012 (gap from the change)  a deactivated user still blocks the delete
"""

import pytest
from hamcrest import (
    all_of,
    assert_that,
    contains_string,
    empty,
    equal_to,
    greater_than_or_equal_to,
    has_item,
    has_length,
    is_not,
    less_than,
    none,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.budget_delete_test_data import (
    DELETE_REASON_MANUAL,
    LITELLM_ALREADY_ABSENT,
    LITELLM_PRESENT,
    budget_in_use_message,
    budget_not_found_message,
    budget_preconfigured_delete_message,
    unknown_budget_id,
)
from codemie_test_harness.tests.utils.admin_budget_utils import AdminBudgetUtils
from codemie_test_harness.tests.utils.base_utils import poll_until

EVENT_TIMEOUT = 15
LITELLM_TIMEOUT = 15


def _rejection_status(exc_info) -> int:
    return exc_info.value.response.status_code


def _assert_client_error(status: int, who: str):
    """The delete is rejected with a 4xx; the exact code is set by the access gate, so the
    observed one is reported in the message."""
    assert_that(
        status,
        all_of(greater_than_or_equal_to(400), less_than(500)),
        f"DELETE as {who} should be rejected with a 4xx status; observed {status}",
    )


def _assert_budget_gone(budget_utils, budget_id: str):
    with pytest.raises(HTTPError) as exc_info:
        budget_utils.get_budget(budget_id)
    assert_that(
        _rejection_status(exc_info),
        equal_to(404),
        f"GET /v1/admin/budgets/{budget_id} should be 404 after the delete",
    )


def _category_budgets(group: dict) -> dict:
    """{budget_id: (category, max_budget)} of a project budget group response."""
    return {
        c["budget_id"]: (c["category"], c["max_budget"]) for c in group["categories"]
    }


# ---------------------------------------------------------------------------
# TC-001
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.parametrize(
    "budget_in_litellm_state",
    [LITELLM_PRESENT, LITELLM_ALREADY_ABSENT],
    indirect=True,
    ids=["litellm_present", "litellm_already_absent"],
)
@pytest.mark.api
def test_delete_manual_budget_removes_it_in_codemie_and_litellm(
    budget_in_litellm_state,
    maintainer_budget_utils,
    maintainer_activity_utils,
    lite_llm_budget_utils,
):
    """@case delete-budget_TC_001

    AC-1: DELETE answers 204 with no body, the budget row is gone (GET 404, absent from the
    list), one budget.deleted event with reason manual_delete is recorded, and LiteLLM no
    longer has the budget. A LiteLLM 404 is tolerated, so the budget that LiteLLM already
    lost is deleted all the same (budget_service.py:476-498, budget_provider_adapter.py:737-739).
    """
    budget_id = budget_in_litellm_state["budget_id"]

    response = maintainer_budget_utils.delete_budget(budget_id)

    assert_that(response.status_code, equal_to(204), "DELETE should answer 204")
    assert_that(response.content, equal_to(b""), "DELETE 204 should carry no body")
    _assert_budget_gone(maintainer_budget_utils, budget_id)
    assert_that(
        maintainer_budget_utils.find_budget_in_list(budget_id),
        none(),
        f"{budget_id} should be absent from GET /v1/admin/budgets",
    )

    # Activity events are written asynchronously, so poll until the event shows up.
    events = poll_until(
        lambda: maintainer_activity_utils.list_budget_deleted_events(budget_id),
        bool,
        timeout=EVENT_TIMEOUT,
        interval=1.0,
    )
    assert_that(events, has_length(1), "exactly one budget.deleted event is recorded")
    assert_that(events[0].event_type, equal_to("budget.deleted"))
    assert_that(
        events[0].attributes["reason"],
        equal_to(DELETE_REASON_MANUAL),
        "the budget.deleted event should carry reason manual_delete",
    )
    in_litellm = poll_until(
        lambda: lite_llm_budget_utils.get_budget_info(budget_id),
        lambda info: info is None,
        timeout=LITELLM_TIMEOUT,
        interval=2.0,
    )
    assert_that(in_litellm, none(), f"{budget_id} should be absent in LiteLLM")


# ---------------------------------------------------------------------------
# TC-002
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
def test_maintainer_deletes_budget_and_admin_is_rejected(
    manual_budget, admin_client, maintainer_budget_utils
):
    """@case delete-budget_TC_002

    AC-1/AC-4: a platform admin is view-only, so the delete is rejected by
    maintainer_access_only (budget_router.py:177) and the budget stays; the maintainer's
    delete then answers 204 and the budget is gone.
    """
    budget_id = manual_budget["budget_id"]
    admin_utils = AdminBudgetUtils(admin_client)

    with pytest.raises(HTTPError) as exc_info:
        admin_utils.delete_budget(budget_id)

    _assert_client_error(_rejection_status(exc_info), "a platform admin")
    assert_that(
        admin_utils.get_budget(budget_id)["budget_id"],
        equal_to(budget_id),
        "the budget should still be present after the admin's rejected delete",
    )

    response = maintainer_budget_utils.delete_budget(budget_id)

    assert_that(response.status_code, equal_to(204), "maintainer DELETE should be 204")
    assert_that(response.content, equal_to(b""), "DELETE 204 should carry no body")
    _assert_budget_gone(admin_utils, budget_id)


# ---------------------------------------------------------------------------
# TC-003
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.parametrize(
    "assigned_users", [1, 2], indirect=True, ids=["one_user", "two_users"]
)
@pytest.mark.api
def test_delete_budget_with_assigned_users_is_refused_and_changes_nothing(
    assigned_users, manual_budget, maintainer_budget_utils, maintainer_activity_utils
):
    """@case delete-budget_TC_003

    AC-2: a budget with assigned users answers 409 "Budget '<id>' is in use: N user(s)
    assigned" ("user" for exactly one), and neither the budget, its assignments nor the
    activity log change (budget_service.py:471-476).
    """
    budget_id = manual_budget["budget_id"]
    user_count = len(assigned_users)
    budget_before = maintainer_budget_utils.get_budget(budget_id)

    with pytest.raises(HTTPError) as exc_info:
        maintainer_budget_utils.delete_budget(budget_id)

    assert_that(_rejection_status(exc_info), equal_to(409), "DELETE should be 409")
    assert_that(
        exc_info.value.response.text,
        contains_string(budget_in_use_message(budget_id, user_count)),
    )
    assert_that(
        maintainer_budget_utils.get_budget(budget_id),
        equal_to(budget_before),
        "the budget should be unchanged after the refused delete",
    )
    listed = maintainer_budget_utils.find_budget_in_list(budget_id)
    assert_that(
        listed["user_count"],
        equal_to(user_count),
        "the assignments should be intact after the refused delete",
    )
    assert_that(
        maintainer_activity_utils.list_budget_deleted_events(budget_id),
        empty(),
        "a refused delete should record no budget.deleted event",
    )


# ---------------------------------------------------------------------------
# TC-004
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
def test_delete_preconfigured_budget_is_rejected_like_an_update(
    admin_budget_utils, maintainer_budget_utils
):
    """@case delete-budget_TC_004

    AC-3: a preconfigured budget answers 403 "Budget '<id>' is preconfigured and cannot be
    deleted via API" before any lookup, the same status update_budget answers; the budget is
    still there (budget_service.py:442-449, :372).
    """
    preconfigured = admin_budget_utils.find_preconfigured_budget()
    budget_id = preconfigured["budget_id"]

    with pytest.raises(HTTPError) as delete_exc:
        maintainer_budget_utils.delete_budget(budget_id)
    with pytest.raises(HTTPError) as update_exc:
        # Same name as now, so nothing changes should the update ever be accepted.
        maintainer_budget_utils.update_budget(budget_id, name=preconfigured["name"])

    delete_status = _rejection_status(delete_exc)
    assert_that(delete_status, equal_to(403), "DELETE should be 403")
    assert_that(
        delete_exc.value.response.text,
        contains_string(budget_preconfigured_delete_message(budget_id)),
    )
    assert_that(
        delete_status,
        equal_to(_rejection_status(update_exc)),
        "DELETE should be rejected with the same status as PATCH",
    )
    assert_that(
        maintainer_budget_utils.get_budget(budget_id)["budget_id"],
        equal_to(budget_id),
        "the preconfigured budget should still be present",
    )


# ---------------------------------------------------------------------------
# TC-005
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
def test_user_without_platform_role_cannot_delete_budget(
    manual_budget, platform_user, admin_budget_utils
):
    """@case delete-budget_TC_005

    AC-4: a user with no platform role is rejected by maintainer_access_only
    (budget_router.py:177) and the budget is still there.
    """
    budget_id = manual_budget["budget_id"]

    with pytest.raises(HTTPError) as exc_info:
        AdminBudgetUtils(platform_user.client).delete_budget(budget_id)

    _assert_client_error(_rejection_status(exc_info), "a user without a platform role")
    assert_that(
        admin_budget_utils.get_budget(budget_id)["budget_id"],
        equal_to(budget_id),
        "the budget should still be present after the rejected delete",
    )


# ---------------------------------------------------------------------------
# TC-006
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
def test_delete_unknown_budget_returns_not_found(maintainer_budget_utils):
    """@case delete-budget_TC_006

    AC-5: an id no budget has answers 404 "Budget '<id>' not found" (budget_service.py:459).
    """
    budget_id = unknown_budget_id()

    with pytest.raises(HTTPError) as exc_info:
        maintainer_budget_utils.delete_budget(budget_id)

    assert_that(_rejection_status(exc_info), equal_to(404), "DELETE should be 404")
    assert_that(
        exc_info.value.response.text,
        contains_string(budget_not_found_message(budget_id)),
    )


# ---------------------------------------------------------------------------
# TC-008
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_sync_does_not_recreate_a_deleted_budget(
    manual_budget, maintainer_budget_utils
):
    """@case delete-budget_TC_008

    AC-7: the delete removes the budget in LiteLLM too, so POST /v1/admin/budgets/sync (it
    upserts only what the provider returns, budget_service.py:837) neither lists it nor
    brings it back. Sync is global, hence not_for_parallel_run; the shared counters are not
    asserted, only the deleted id.
    """
    budget_id = manual_budget["budget_id"]
    response = maintainer_budget_utils.delete_budget(budget_id)
    assert_that(response.status_code, equal_to(204), "DELETE should be 204")

    sync_result = maintainer_budget_utils.sync_budgets()

    assert_that(
        [b["budget_id"] for b in sync_result["budgets"]],
        is_not(has_item(budget_id)),
        "the sync result should not list the deleted budget",
    )
    assert_that(
        maintainer_budget_utils.find_budget_in_list(budget_id),
        none(),
        f"{budget_id} should still be absent from GET /v1/admin/budgets after the sync",
    )
    _assert_budget_gone(maintainer_budget_utils, budget_id)


# ---------------------------------------------------------------------------
# TC-011
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
def test_project_budget_cannot_be_deleted_through_the_global_budget_endpoint(
    budget_project,
    project_budget_groups,
    maintainer_budget_utils,
    admin_project_budget_utils,
):
    """@case delete-budget_TC_011

    Gap from the change: a budget that is not global (a project budget) is answered 404
    like an unknown id (budget_service.py:458), and the project budget group keeps its budget.
    """
    project_budget = project_budget_groups.create(budget_project)
    budget_id = project_budget.budget_ids["platform"]
    group_before = admin_project_budget_utils.get_group(project_budget.group_id)

    with pytest.raises(HTTPError) as exc_info:
        maintainer_budget_utils.delete_budget(budget_id)

    assert_that(_rejection_status(exc_info), equal_to(404), "DELETE should be 404")
    assert_that(
        exc_info.value.response.text,
        contains_string(budget_not_found_message(budget_id)),
    )
    group_after = admin_project_budget_utils.get_group(project_budget.group_id)
    assert_that(
        _category_budgets(group_after),
        equal_to(_category_budgets(group_before)),
        "the project budget group should be unchanged",
    )
    assert_that(
        _category_budgets(group_after).keys(),
        has_item(budget_id),
        "the project budget should still belong to its group",
    )


# ---------------------------------------------------------------------------
# TC-012
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.api
def test_deactivated_user_still_blocks_budget_deletion(
    platform_user,
    manual_budget,
    assign_budget_user,
    user_utils,
    maintainer_budget_utils,
):
    """@case delete-budget_TC_012

    Gap from the change: only soft-deleted users are ignored by the in-use count, a
    deactivated user is still counted, so the delete answers 409 "1 user assigned"
    (budget_repository.py:211-219) and the budget stays.
    """
    budget_id = manual_budget["budget_id"]
    assign_budget_user(platform_user.user_id)
    user_utils.deactivate_user(platform_user.user_id)

    with pytest.raises(HTTPError) as exc_info:
        maintainer_budget_utils.delete_budget(budget_id)

    assert_that(_rejection_status(exc_info), equal_to(409), "DELETE should be 409")
    assert_that(
        exc_info.value.response.text,
        contains_string(budget_in_use_message(budget_id, 1)),
    )
    assert_that(
        maintainer_budget_utils.get_budget(budget_id)["budget_id"],
        equal_to(budget_id),
        "the budget should still be present",
    )
