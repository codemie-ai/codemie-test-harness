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

"""API tests for who may read a project's activity trail and its metadata.

Covers:
    A non-admin of the project gets 404 on the trail and the metadata, as for an unknown project
    A platform admin and a maintainer read the trail of any project
    The trail of a personal project is never served
"""

import json

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    has_item,
    has_items,
    is_not,
)

from codemie_test_harness.tests.test_data.project_activity_test_data import (
    PROJECT_ACTIVITY_NOT_FOUND_MESSAGE,
    unknown_project_instance_id,
)
from codemie_test_harness.tests.utils.activity_utils import ActivityUtils


# @case project-scoped-activity-trail_TC_007
@pytest.mark.activity
@pytest.mark.api
@pytest.mark.parametrize(
    "request_name",
    ["project_events_denial", "project_event_metadata_denial"],
    ids=["trail", "metadata"],
)
@pytest.mark.parametrize(
    "project_is_known", [True, False], ids=["existing-project", "unknown-project"]
)
def test_non_admin_gets_not_found_for_trail_and_metadata(
    trail_project, trail_project_member, project_is_known, request_name
):
    project_instance_id = (
        trail_project.instance_id if project_is_known else unknown_project_instance_id()
    )
    caller = ActivityUtils(trail_project_member.client)

    denial = getattr(caller, request_name)(project_instance_id)

    assert_that(denial.status_code, equal_to(404), denial.body)
    assert_that(
        denial.message,
        equal_to(PROJECT_ACTIVITY_NOT_FOUND_MESSAGE),
        "an existing and an unknown project give the same message",
    )
    assert_that(
        list(json.loads(denial.body)),
        equal_to(["error"]),
        "the denial carries no events, counts, types or labels",
    )


# @case project-scoped-activity-trail_TC_008
@pytest.mark.activity
@pytest.mark.api
def test_platform_admin_reads_trail_of_a_project_they_do_not_belong_to(
    admin_client, trail_project
):
    events = ActivityUtils(admin_client).list_all_project_events(
        trail_project.instance_id
    )

    assert_that(
        [event.event_type for event in events],
        has_item("project.created"),
        "a platform admin gets the project's events",
    )


# @case project-scoped-activity-trail_TC_008
@pytest.mark.activity
@pytest.mark.api
def test_maintainer_reads_trail_of_a_project_they_do_not_belong_to(
    fresh_maintainer_client, trail_project
):
    events = ActivityUtils(fresh_maintainer_client).list_all_project_events(
        trail_project.instance_id
    )

    assert_that(
        [event.event_type for event in events],
        has_item("project.created"),
        "a maintainer gets the project's events",
    )


# @case project-scoped-activity-trail_TC_009
@pytest.mark.activity
@pytest.mark.api
def test_personal_project_trail_is_not_served_to_maintainer(
    activity_utils, project_utils, platform_user
):
    personal = project_utils.get_project_detail(platform_user.email)

    denial = activity_utils.project_events_denial(str(personal.project_instance_id))

    assert_that(denial.status_code, equal_to(404), denial.body)
    assert_that(denial.message, equal_to(PROJECT_ACTIVITY_NOT_FOUND_MESSAGE))


# @case project-scoped-activity-trail_TC_009
@pytest.mark.activity
@pytest.mark.api
def test_personal_project_trail_is_not_served_to_platform_admin(
    admin_client, project_utils, platform_user
):
    personal = project_utils.get_project_detail(platform_user.email)

    denial = ActivityUtils(admin_client).project_events_denial(
        str(personal.project_instance_id)
    )

    assert_that(denial.status_code, equal_to(404), denial.body)
    assert_that(denial.message, equal_to(PROJECT_ACTIVITY_NOT_FOUND_MESSAGE))


# @case project-scoped-activity-trail_TC_009
@pytest.mark.activity
@pytest.mark.api
def test_shared_project_trail_holds_no_event_of_a_personal_project(
    activity_utils, trail_project, trail_project_member, platform_user
):
    events = activity_utils.list_all_project_events(trail_project.instance_id)

    project_names = {event.project_name for event in events}
    assert_that(
        project_names,
        equal_to({trail_project.name}),
        "only events of the shared project appear",
    )
    assert_that(
        [event.event_type for event in events],
        has_items("project.created", "user.project.assigned"),
        "the shared project does have events, including the member's assignment",
    )
    assert_that(
        project_names,
        is_not(has_item(platform_user.email)),
        "no event of the member's personal project appears",
    )
