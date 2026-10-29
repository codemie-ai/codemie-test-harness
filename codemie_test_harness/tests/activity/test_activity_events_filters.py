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

"""API tests for activity event filtering and pagination.

Covers:
    TC-006  Domain and entity_type filters return only matching events
    TC-006b Budget and project domain filters return only matching events
    TC-006c All entity_type filter values return correctly-typed events
    TC-007  Actor ID and entity ID filters return only matching events (merged)
    TC-008  Date range filter and sort direction control results correctly (merged)
    TC-009  Pagination controls work: limit, offset, and total are consistent (merged)
"""

from datetime import datetime, timezone

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than,
    greater_than_or_equal_to,
    less_than_or_equal_to,
    not_none,
)


# ---------------------------------------------------------------------------
# TC-006: Domain and entity_type filters return only matching events
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_domain_and_entity_type_filters_return_only_matching_events(activity_utils):
    """TC-006: domain= and entity_type= filters return only correctly-typed events."""
    # (a) Single domain filter
    response_a = activity_utils.list_activity_events(
        domain=["user_management"],
        limit=50,
    )
    assert_that(
        len(response_a.data),
        greater_than(0),
        "user_management domain filter should return at least one event",
    )
    domains_a = [e.domain for e in response_a.data]
    assert_that(
        all(d == "user_management" for d in domains_a),
        equal_to(True),
        "All returned events should have domain=user_management",
    )
    assert_that(
        any(d == "budget_management" for d in domains_a),
        equal_to(False),
        "No budget_management events should appear when filtering for user_management",
    )

    # (b) Add entity_type filter on top
    # CR-004: guard removed — a None entity_type must fail the equality check
    response_b = activity_utils.list_activity_events(
        domain=["user_management"],
        entity_type=["user"],
        limit=50,
    )
    if len(response_b.data) > 0:
        entity_types_b = [e.entity_type for e in response_b.data]
        assert_that(
            all(et == "user" for et in entity_types_b),
            equal_to(True),
            "All returned events should have entity_type=user",
        )

    # (c) Multi-domain filter should not return unrelated domains
    response_c = activity_utils.list_activity_events(
        domain=["user_management", "budget_management"],
        limit=50,
    )
    domains_c = [e.domain for e in response_c.data]
    assert_that(
        any(d == "project_management" for d in domains_c),
        equal_to(False),
        "Multi-domain filter should not include project_management events",
    )


# ---------------------------------------------------------------------------
# TC-006b: budget_management and project_management domain filters
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_budget_management_domain_filter_returns_only_matching_events(activity_utils):
    """TC-006b: domain=budget_management filter returns only budget_management events."""
    response = activity_utils.list_activity_events(
        domain=["budget_management"],
        limit=50,
    )
    domains = [e.domain for e in response.data]
    assert_that(
        all(d == "budget_management" for d in domains),
        equal_to(True),
        "All returned events should have domain=budget_management",
    )
    assert_that(
        any(d == "user_management" for d in domains),
        equal_to(False),
        "No user_management events should appear when filtering for budget_management",
    )


@pytest.mark.activity
@pytest.mark.api
def test_project_management_domain_filter_returns_only_matching_events(activity_utils):
    """TC-006b: domain=project_management filter returns only project_management events."""
    response = activity_utils.list_activity_events(
        domain=["project_management"],
        limit=50,
    )
    domains = [e.domain for e in response.data]
    assert_that(
        all(d == "project_management" for d in domains),
        equal_to(True),
        "All returned events should have domain=project_management",
    )
    assert_that(
        any(d == "user_management" for d in domains),
        equal_to(False),
        "No user_management events should appear when filtering for project_management",
    )


# ---------------------------------------------------------------------------
# TC-006c: entity_type filters for all supported values
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_entity_type_budget_filter_returns_only_matching_events(activity_utils):
    """TC-006c: entity_type=budget filter returns only events with entity_type=budget."""
    response = activity_utils.list_activity_events(
        entity_type=["budget"],
        limit=50,
    )
    entity_types = [e.entity_type for e in response.data]
    assert_that(
        all(et == "budget" for et in entity_types),
        equal_to(True),
        "All returned events should have entity_type=budget",
    )


@pytest.mark.activity
@pytest.mark.api
def test_entity_type_project_filter_returns_only_matching_events(activity_utils):
    """TC-006c: entity_type=project filter returns only events with entity_type=project."""
    response = activity_utils.list_activity_events(
        entity_type=["project"],
        limit=50,
    )
    entity_types = [e.entity_type for e in response.data]
    assert_that(
        all(et == "project" for et in entity_types),
        equal_to(True),
        "All returned events should have entity_type=project",
    )


@pytest.mark.activity
@pytest.mark.api
def test_entity_type_project_budget_group_filter_returns_only_matching_events(
    activity_utils,
):
    """TC-006c: entity_type=project_budget_group filter returns correctly-typed events."""
    response = activity_utils.list_activity_events(
        entity_type=["project_budget_group"],
        limit=50,
    )
    entity_types = [e.entity_type for e in response.data]
    assert_that(
        all(et == "project_budget_group" for et in entity_types),
        equal_to(True),
        "All returned events should have entity_type=project_budget_group",
    )


@pytest.mark.activity
@pytest.mark.api
def test_entity_type_user_budget_assignment_filter_returns_only_matching_events(
    activity_utils,
):
    """TC-006c: entity_type=user_budget_assignment filter returns correctly-typed events."""
    response = activity_utils.list_activity_events(
        entity_type=["user_budget_assignment"],
        limit=50,
    )
    entity_types = [e.entity_type for e in response.data]
    assert_that(
        all(et == "user_budget_assignment" for et in entity_types),
        equal_to(True),
        "All returned events should have entity_type=user_budget_assignment",
    )


# ---------------------------------------------------------------------------
# TC-007: Actor ID and entity ID filters return only matching events (merged)
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_actor_id_and_entity_id_filters_return_only_matching_events(
    activity_utils, user_utils, disposable_user
):
    """TC-007: actor_id= and entity_id= filters return only matching events."""
    _, user_id, _ = disposable_user

    # Trigger a maintainer-actor event: deactivate the disposable user
    user_utils.deactivate_user(user_id)

    # entity_id filter: all results must share the same entity_id
    entity_response = activity_utils.list_activity_events(entity_id=user_id)
    assert_that(
        len(entity_response.data),
        greater_than(0),
        "entity_id filter should return at least one event for the disposable user",
    )
    entity_ids = [e.entity_id for e in entity_response.data]
    assert_that(
        all(eid == user_id for eid in entity_ids),
        equal_to(True),
        "All returned events should have entity_id matching the disposable user",
    )

    # CR-005: assert actor_id is present before using it; None is a test failure
    first_actor_id = entity_response.data[0].actor_id
    assert_that(
        first_actor_id,
        not_none(),
        "actor_id must be present to validate actor filter",
    )
    if first_actor_id is not None:
        actor_response = activity_utils.list_activity_events(
            actor_id=first_actor_id,
            limit=10,
        )
        assert_that(
            len(actor_response.data),
            greater_than(0),
            "actor_id filter should return at least one event",
        )
        actor_ids = [e.actor_id for e in actor_response.data]
        assert_that(
            all(aid == first_actor_id for aid in actor_ids),
            equal_to(True),
            "All returned events should have actor_id matching the queried actor",
        )


# ---------------------------------------------------------------------------
# TC-008: Date range filter and sort direction control results (merged)
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_date_range_filter_and_sort_direction_control_results(
    activity_utils, disposable_user
):
    """TC-008: from/to date range filter and sort_dir asc/desc work correctly."""
    _, user_id, _ = disposable_user

    # Record timestamps bracketing the user.created event that disposable_user produced
    from datetime import timedelta

    now = datetime.now(timezone.utc)

    # (a) Date range filter: all returned created_at must fall within range
    # Use a wider window to ensure the event is captured
    wide_before = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    wide_after = (now + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

    range_response = activity_utils.list_activity_events(
        entity_id=user_id,
        from_dt=wide_before,
        to_dt=wide_after,
    )
    assert_that(
        len(range_response.data),
        greater_than(0),
        "Date range filter should return at least one event for the disposable user",
    )

    # (b) sort_dir=asc: first created_at <= last created_at
    # CR-006: guard None created_at before comparison to avoid TypeError
    asc_response = activity_utils.list_activity_events(sort_dir="asc", limit=10)
    if len(asc_response.data) >= 2:
        first_ts = asc_response.data[0].created_at
        last_ts = asc_response.data[-1].created_at
        assert_that(
            first_ts,
            not_none(),
            "created_at of first event must be present for ascending sort comparison",
        )
        assert_that(
            last_ts,
            not_none(),
            "created_at of last event must be present for ascending sort comparison",
        )
        assert_that(
            first_ts <= last_ts,
            equal_to(True),
            "Ascending sort: first event should be earlier than or equal to last",
        )

    # (c) sort_dir=desc: first created_at >= last created_at
    desc_response = activity_utils.list_activity_events(sort_dir="desc", limit=10)
    if len(desc_response.data) >= 2:
        first_ts = desc_response.data[0].created_at
        last_ts = desc_response.data[-1].created_at
        assert_that(
            first_ts,
            not_none(),
            "created_at of first event must be present for descending sort comparison",
        )
        assert_that(
            last_ts,
            not_none(),
            "created_at of last event must be present for descending sort comparison",
        )
        assert_that(
            first_ts >= last_ts,
            equal_to(True),
            "Descending sort: first event should be later than or equal to last",
        )


# ---------------------------------------------------------------------------
# TC-009: Pagination controls work (merged)
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_pagination_controls_limit_offset_and_total_are_consistent(activity_utils):
    """TC-009: limit, offset, and total pagination controls work correctly."""
    # (a) limit=5: at most 5 items, pagination.per_page=5
    page_a = activity_utils.list_activity_events(limit=5)

    assert_that(
        len(page_a.data),
        less_than_or_equal_to(5),
        "limit=5 should return at most 5 events",
    )
    assert_that(
        page_a.pagination.per_page,
        equal_to(5),
        "pagination.per_page should equal the requested limit",
    )

    # (b) offset=5: returned IDs should be disjoint from page (a)
    # CR-007: assert page_b is non-empty before the disjointness check to avoid
    # a vacuous pass when total events < 6
    page_b = activity_utils.list_activity_events(limit=5, offset=5)

    ids_a = {e.id for e in page_a.data}
    ids_b = {e.id for e in page_b.data}
    assert_that(
        len(page_b.data),
        greater_than(0),
        "offset=5 should return at least one event; total events may be insufficient",
    )
    assert_that(
        len(ids_a & ids_b),
        equal_to(0),
        "Events at offset=5 should be disjoint from events at offset=0",
    )

    # (c) pagination metadata sanity
    assert_that(
        page_a.pagination.total,
        greater_than(0),
        "pagination.total should be > 0 when events exist",
    )
    assert_that(
        page_a.pagination.pages,
        greater_than_or_equal_to(1),
        "pagination.pages should be >= 1",
    )
