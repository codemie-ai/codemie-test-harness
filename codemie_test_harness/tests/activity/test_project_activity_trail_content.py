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

"""API tests for what the project activity trail records.

Covers:
    Every event of a project carries its project name, in every domain
    Events with no project context have a null project name
    Events of a deleted project stay readable with their project name
    The Budget category spans budget and spend-enforcement events
    The spend-enforcement event is emitted only when the flag changes
    The entity label is captured when the event is written and survives a delete

Each test creates its own project (`trail_project`), so the trail it reads holds only
what the test did.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_inanyorder,
    empty,
    equal_to,
    greater_than_or_equal_to,
    has_item,
    has_items,
    has_length,
    is_,
    none,
    only_contains,
)

from codemie_test_harness.tests.test_data.project_activity_test_data import (
    ENFORCEMENT_EVENT,
)


# @case project-scoped-activity-trail_TC_001
@pytest.mark.activity
@pytest.mark.api
def test_project_events_of_every_domain_carry_the_project_name(
    activity_utils, trail_project, trail_project_member, project_budget_groups
):
    project_budget_groups.create(trail_project.name)

    events = activity_utils.list_all_project_events(trail_project.instance_id)

    assert_that(
        {event.domain for event in events},
        has_items("project_management", "budget_management", "user_management"),
        "the trail should hold events of the project, budget and user domains",
    )
    other_project = [
        f"{event.domain}/{event.event_type}: {event.project_name!r}"
        for event in events
        if event.project_name != trail_project.name
    ]
    assert_that(
        other_project,
        empty(),
        f"every event should carry project_name={trail_project.name!r}",
    )


# @case project-scoped-activity-trail_TC_002
@pytest.mark.activity
@pytest.mark.api
def test_budget_event_without_project_has_null_project_name(
    activity_utils, manual_budget
):
    events = activity_utils.list_activity_events(
        entity_id=manual_budget["budget_id"],
        event_type=["budget.created"],
        domain=["budget_management"],
    ).data

    assert_that(events, has_length(1), "one budget.created event for the new budget")
    assert_that(
        events[0].project_name,
        is_(none()),
        "a platform budget belongs to no project: project_name is null, not an empty string",
    )


# @case project-scoped-activity-trail_TC_002
@pytest.mark.activity
@pytest.mark.api
def test_account_events_of_new_user_have_null_project_name(
    activity_utils, platform_user
):
    events = activity_utils.list_activity_events(
        entity_id=platform_user.user_id,
        event_type=["user.created", "user.login"],
        domain=["user_management"],
    ).data

    assert_that(
        len(events),
        greater_than_or_equal_to(1),
        "a fresh user has an account event (user.created, plus user.login on a local-IdP stand)",
    )
    assert_that(
        [event.project_name for event in events],
        only_contains(none()),
        "account events belong to no project: project_name is null, not an empty string",
    )


# @case project-scoped-activity-trail_TC_005
@pytest.mark.activity
@pytest.mark.api
def test_events_of_deleted_project_remain_with_project_name(
    activity_utils, project_utils, trail_project
):
    project_utils.update_project(
        trail_project.name, description="Changed before delete"
    )
    project_utils.delete_project(trail_project.name)

    response = activity_utils.list_project_events(trail_project.instance_id, limit=1000)

    assert_that(
        [event.event_type for event in response.data],
        has_items("project.created", "project.updated", "project.deleted"),
        "the events written before the delete and the delete itself should remain",
    )
    assert_that(
        {event.project_name for event in response.data},
        equal_to({trail_project.name}),
        "every retained event keeps the name of the deleted project",
    )


# @case project-scoped-activity-trail_TC_016
@pytest.mark.activity
@pytest.mark.api
def test_budget_category_spans_budget_and_enforcement_events(
    activity_utils, project_utils, project_budget_groups, trail_project
):
    project_budget_groups.create(trail_project.name)
    project_utils.set_enforce_member_spend_limits(trail_project.name, True)

    response = activity_utils.list_project_events(
        trail_project.instance_id, category=["Budget"], limit=1000
    )

    assert_that(
        {event.category for event in response.data},
        equal_to({"Budget"}),
        "the Budget filter should return Budget events only",
    )
    assert_that(
        {event.domain for event in response.data},
        equal_to({"budget_management", "project_management"}),
        "the Budget category spans the budget and the project domain",
    )
    assert_that(
        [
            event.event_type
            for event in response.data
            if event.domain == "project_management"
        ],
        contains_inanyorder(ENFORCEMENT_EVENT),
        "the only project_management event in the Budget category is the enforcement change",
    )
    assert_that(
        [event.event_type for event in response.data],
        has_item("budget.project_budget_group.created"),
        "the budget group creation is a Budget event",
    )
    assert_that(
        response.pagination.total,
        equal_to(len(response.data)),
        "total counts the matching events",
    )


# @case project-scoped-activity-trail_TC_017
@pytest.mark.activity
@pytest.mark.api
def test_enforcement_event_is_emitted_only_when_the_flag_changes(
    activity_utils, project_utils, trail_project
):
    project_utils.set_enforce_member_spend_limits(trail_project.name, True)
    enforcement_after_flag = activity_utils.list_all_project_events(
        trail_project.instance_id, event_type=[ENFORCEMENT_EVENT]
    )
    updates_after_flag = activity_utils.list_all_project_events(
        trail_project.instance_id, event_type=["project.updated"]
    )

    project_utils.update_project(trail_project.name, description="Only the description")
    enforcement_after_description = activity_utils.list_all_project_events(
        trail_project.instance_id, event_type=[ENFORCEMENT_EVENT]
    )
    updates_after_description = activity_utils.list_all_project_events(
        trail_project.instance_id, event_type=["project.updated"]
    )

    assert_that(
        enforcement_after_flag, has_length(1), "changing the flag records one event"
    )
    assert_that(
        enforcement_after_flag[0].attributes,
        equal_to(
            {
                "previous_enforce_member_spend_limits": False,
                "new_enforce_member_spend_limits": True,
            }
        ),
        "the event records the previous and the new flag value",
    )
    assert_that(
        len(updates_after_description),
        equal_to(len(updates_after_flag) + 1),
        "the description change itself is recorded as project.updated",
    )
    assert_that(
        [event.id for event in enforcement_after_description],
        equal_to([event.id for event in enforcement_after_flag]),
        "a description-only update records no new enforcement event",
    )


# @case project-scoped-activity-trail_TC_018
@pytest.mark.activity
@pytest.mark.api
def test_entity_label_is_captured_at_event_time_and_survives_delete(
    activity_utils, admin_project_budget_utils, project_budget_groups, trail_project
):
    budget = project_budget_groups.create(
        trail_project.name, name_prefix="autotest-label"
    )
    group_name = admin_project_budget_utils.get_group(budget.group_id)["name"]

    created_before = activity_utils.list_all_project_events(
        trail_project.instance_id, event_type=["budget.project_budget_group.created"]
    )
    project_budget_groups.delete(budget)
    created_after = activity_utils.list_all_project_events(
        trail_project.instance_id, event_type=["budget.project_budget_group.created"]
    )
    deleted = activity_utils.list_all_project_events(
        trail_project.instance_id, event_type=["budget.project_budget_group.deleted"]
    )

    assert_that(created_before, has_length(1), "one group creation event")
    assert_that(
        created_before[0].entity_label,
        equal_to(group_name),
        "the event is labelled with the budget group name",
    )
    assert_that(
        [event.entity_label for event in created_after],
        equal_to([group_name]),
        "the original event keeps its label after the group is deleted",
    )
    assert_that(
        [event.entity_label for event in deleted],
        equal_to([group_name]),
        "the delete event carries the same label",
    )
