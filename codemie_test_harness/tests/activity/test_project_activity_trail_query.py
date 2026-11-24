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

"""API tests for reading a project's activity trail: ordering, paging, filters, metadata.

Covers:
    A project admin reads the trail newest first, paginated, with label and category
    Time range, domain and event type filters narrow the trail and the server-side total
    Paging by limit and offset repeats and skips no event
    The category and actor filters count only matching events
    Unknown filter values are rejected
    The metadata lists only the event types present in the project
"""

import math

import pytest
from hamcrest import (
    assert_that,
    contains_inanyorder,
    contains_string,
    equal_to,
    greater_than,
    has_item,
    has_length,
    instance_of,
    is_,
    is_not,
    only_contains,
)

from codemie_test_harness.tests.test_data.project_activity_test_data import (
    ADMIN_UPDATES,
    EVENT_TAXONOMY,
    PROJECT_ACTIVITY_CATEGORIES,
    UNKNOWN_FILTER_VALUES,
)
from codemie_test_harness.tests.utils.activity_utils import ActivityUtils

PAGE_SIZE = 2


# @case project-scoped-activity-trail_TC_006
@pytest.mark.activity
@pytest.mark.api
def test_project_admin_reads_own_trail_newest_first_paginated_and_labelled(
    populated_trail, trail_project_admin
):
    project_id = populated_trail.project.instance_id
    total = len(populated_trail.events)
    reader = ActivityUtils(trail_project_admin.client)

    first = reader.list_project_events(project_id, limit=PAGE_SIZE)
    second = reader.list_project_events(project_id, limit=PAGE_SIZE, offset=PAGE_SIZE)

    assert_that(first.recording_enabled, is_(True), "recording is enabled")
    assert_that(first.pagination.total, equal_to(total), "total counts the whole trail")
    assert_that(first.pagination.per_page, equal_to(PAGE_SIZE))
    assert_that(first.pagination.pages, equal_to(math.ceil(total / PAGE_SIZE)))
    assert_that(first.pagination.page, equal_to(0))
    assert_that(second.pagination.page, equal_to(1), "offset 2 with limit 2 is page 1")
    assert_that(first.data, has_length(PAGE_SIZE))
    paged = first.data + second.data
    assert_that(
        [event.created_at for event in paged],
        equal_to(sorted((event.created_at for event in paged), reverse=True)),
        "the newest event comes first",
    )
    assert_that(
        [event.id for event in paged],
        equal_to([event.id for event in populated_trail.events[: 2 * PAGE_SIZE]]),
        "the project admin sees the same newest events as the maintainer",
    )
    assert_that(
        [event.domain for event in paged],
        only_contains(instance_of(str)),
        "every event carries its domain",
    )
    assert_that(
        [event.label for event in paged],
        only_contains(instance_of(str)),
        "every event carries its label",
    )
    assert_that(
        [event.category for event in paged],
        only_contains(instance_of(str)),
        "every event carries its category",
    )
    known = [event for event in paged if event.event_type in EVENT_TAXONOMY]
    assert_that(
        [(event.label, event.category) for event in known],
        equal_to([EVENT_TAXONOMY[event.event_type] for event in known]),
        "label and category follow the taxonomy of the event type",
    )


# @case project-scoped-activity-trail_TC_011
@pytest.mark.activity
@pytest.mark.api
@pytest.mark.parametrize(
    "domain", ["project_management", "user_management"], ids=["project", "user"]
)
def test_trail_domain_filter_totals_all_matching_events(
    activity_utils, populated_trail, domain
):
    expected = [e for e in populated_trail.events if e.domain == domain]

    response = activity_utils.list_project_events(
        populated_trail.project.instance_id, domain=[domain], limit=1
    )

    assert_that(response.data, has_length(1), "limit 1 returns one event")
    assert_that(response.data[0].domain, equal_to(domain))
    assert_that(
        response.pagination.total,
        equal_to(len(expected)),
        "total counts the matching events of all pages",
    )


# @case project-scoped-activity-trail_TC_011
@pytest.mark.activity
@pytest.mark.api
def test_trail_event_type_filter_totals_all_matching_events(
    activity_utils, populated_trail
):
    expected = [e for e in populated_trail.events if e.event_type == "project.updated"]

    response = activity_utils.list_project_events(
        populated_trail.project.instance_id, event_type=["project.updated"], limit=1
    )

    assert_that(response.data, has_length(1))
    assert_that(response.data[0].event_type, equal_to("project.updated"))
    assert_that(response.pagination.total, greater_than(1), "several updates exist")
    assert_that(
        response.pagination.total,
        equal_to(len(expected)),
        "total counts the matching events of all pages",
    )


# @case project-scoped-activity-trail_TC_011
@pytest.mark.activity
@pytest.mark.api
def test_trail_time_range_filter_returns_events_inside_the_range(
    activity_utils, populated_trail
):
    updates = [e for e in populated_trail.events if e.event_type == "project.updated"]
    newest, oldest = updates[0], updates[-1]
    expected = [
        e
        for e in populated_trail.events
        if oldest.created_at <= e.created_at <= newest.created_at
    ]
    project_id = populated_trail.project.instance_id
    window = {
        "from_dt": oldest.created_at.isoformat(),
        "to_dt": newest.created_at.isoformat(),
    }

    page = activity_utils.list_project_events(project_id, limit=1, **window)
    inside = activity_utils.list_all_project_events(project_id, **window)

    assert_that(
        page.pagination.total,
        equal_to(len(expected)),
        "total counts the events of the whole range, not the page",
    )
    assert_that(
        [event.id for event in inside],
        equal_to([event.id for event in expected]),
        "only the events between the first and the last update are returned",
    )
    assert_that(
        [event.event_type for event in inside],
        is_not(has_item("project.created")),
        "the creation precedes the first update, so it is outside the range",
    )


# @case project-scoped-activity-trail_TC_012
@pytest.mark.activity
@pytest.mark.api
@pytest.mark.parametrize("sort_dir", ["desc", "asc"])
def test_paging_returns_every_event_once_in_the_unpaged_order(
    activity_utils, populated_trail, sort_dir
):
    project_id = populated_trail.project.instance_id
    unpaged = activity_utils.list_all_project_events(project_id, sort_dir=sort_dir)

    pages = activity_utils.page_project_events(
        project_id, page_size=PAGE_SIZE, sort_dir=sort_dir
    )

    paged_ids = [event.id for page in pages for event in page]
    assert_that(len(pages), greater_than(2), "the trail spans several pages")
    assert_that(len(set(paged_ids)), equal_to(len(paged_ids)), "no event repeats")
    assert_that(
        paged_ids,
        equal_to([event.id for event in unpaged]),
        "no event is skipped and the order matches the unpaged list",
    )


# @case project-scoped-activity-trail_TC_012
@pytest.mark.activity
@pytest.mark.api
def test_ascending_order_is_the_reverse_of_descending(activity_utils, populated_trail):
    project_id = populated_trail.project.instance_id

    ascending = activity_utils.list_all_project_events(project_id, sort_dir="asc")
    descending = activity_utils.list_all_project_events(project_id, sort_dir="desc")

    assert_that(
        [event.id for event in ascending],
        equal_to([event.id for event in reversed(descending)]),
        "equal timestamps are ordered by id in both directions",
    )


# @case project-scoped-activity-trail_TC_015
@pytest.mark.activity
@pytest.mark.api
@pytest.mark.parametrize("category", ["Budget", "Members", "Settings"])
def test_category_filter_totals_only_matching_events(
    activity_utils, populated_trail, category
):
    expected = [e for e in populated_trail.events if e.category == category]

    response = activity_utils.list_project_events(
        populated_trail.project.instance_id, category=[category], limit=1
    )

    assert_that(len(expected), greater_than(0), f"the trail has {category} events")
    assert_that(response.data, has_length(1))
    assert_that(response.data[0].category, equal_to(category))
    assert_that(
        response.pagination.total,
        equal_to(len(expected)),
        "total counts the matching events of all pages",
    )


# @case project-scoped-activity-trail_TC_019
@pytest.mark.activity
@pytest.mark.api
def test_metadata_lists_only_event_types_present_in_the_project(
    populated_trail, trail_project_admin
):
    reader = ActivityUtils(trail_project_admin.client)

    metadata = reader.get_project_event_metadata(populated_trail.project.instance_id)

    types_in_trail = {event.event_type for event in populated_trail.events}
    assert_that(
        {info.event_type for info in metadata.event_types},
        equal_to(types_in_trail),
        "exactly the event types present in the project are listed",
    )
    assert_that(
        {
            info.event_type: (info.label, info.category)
            for info in metadata.event_types
            if info.event_type in EVENT_TAXONOMY
        },
        equal_to(
            {
                event_type: EVENT_TAXONOMY[event_type]
                for event_type in types_in_trail
                if event_type in EVENT_TAXONOMY
            }
        ),
        "each listed type carries the label and category of the taxonomy",
    )
    assert_that(
        set(metadata.domains),
        equal_to({event.domain for event in populated_trail.events}),
        "domains are those of the project's events",
    )
    assert_that(
        metadata.categories,
        contains_inanyorder(*PROJECT_ACTIVITY_CATEGORIES),
        "all categories are listed",
    )
    assert_that(metadata.recording_enabled, is_(True))


# @case project-scoped-activity-trail_TC_021
@pytest.mark.activity
@pytest.mark.api
@pytest.mark.parametrize(
    "parameter,value,message",
    UNKNOWN_FILTER_VALUES,
    ids=[parameter for parameter, _, _ in UNKNOWN_FILTER_VALUES],
)
def test_unknown_filter_value_is_rejected(
    activity_utils, trail_project, parameter, value, message
):
    denial = activity_utils.project_events_denial(
        trail_project.instance_id, **{parameter: [value]}
    )

    assert_that(
        denial.status_code, equal_to(422), "a validation error, not an empty 200"
    )
    assert_that(denial.body, contains_string(message))


# @case project-scoped-activity-trail_TC_021
@pytest.mark.activity
@pytest.mark.api
def test_actor_filter_returns_only_events_of_that_actor(
    activity_utils, populated_trail
):
    actor_id = populated_trail.admin_user_id
    expected = [e for e in populated_trail.events if e.actor_id == actor_id]

    response = activity_utils.list_project_events(
        populated_trail.project.instance_id, actor_id=actor_id, limit=1000
    )

    assert_that(
        len(expected), equal_to(ADMIN_UPDATES), "the administrator made the updates"
    )
    assert_that(
        len(populated_trail.events),
        is_not(equal_to(len(expected))),
        "other actors have events in the trail",
    )
    assert_that(
        [event.id for event in response.data],
        equal_to([event.id for event in expected]),
    )
    assert_that(response.pagination.total, equal_to(len(expected)))
