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

"""API tests for activity event audit records.

Covers:
    TC-001  user.created event stored when user is added
    TC-002  user.updated event stored when user profile is changed
    TC-003  user.deactivated event stored when user is deactivated
    TC-005  user.project.assigned and user.project.removed events stored in sequence
    TC-012  user.project.role_updated event stored when user role is changed

Parallelism strategy: each test creates its own disposable_user (function-scoped)
and filters audit queries by entity_id=<user_id>, so tests are fully isolated
regardless of parallel execution.
"""

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than_or_equal_to,
    has_key,
    is_not,
    none,
    not_none,
)

from codemie_test_harness.tests.utils.base_utils import get_random_name


# ---------------------------------------------------------------------------
# TC-001: user.created
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_user_created_audit_record_stored(activity_utils, disposable_user):
    """TC-001: user.created audit record is stored when a user is added."""
    _, user_id, _ = disposable_user

    response = activity_utils.list_activity_events(
        entity_id=user_id,
        event_type=["user.created"],
        domain=["user_management"],
    )

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one user.created event should exist for the disposable user",
    )
    record = response.data[0]
    assert_that(
        record.domain,
        equal_to("user_management"),
        "Event domain should be user_management",
    )
    assert_that(
        record.entity_type,
        equal_to("user"),
        "Entity type should be user",
    )
    assert_that(
        record.entity_id,
        equal_to(user_id),
        "entity_id should match the created user's ID",
    )
    assert_that(
        record.event_type,
        equal_to("user.created"),
        "event_type should be user.created",
    )
    assert_that(
        record.created_at,
        is_not(none()),
        "created_at should be set",
    )


# ---------------------------------------------------------------------------
# TC-002: user.updated
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_user_updated_audit_record_stored(activity_utils, user_utils, disposable_user):
    """TC-002: user.updated audit record is stored when user profile is changed."""
    _, user_id, _ = disposable_user

    new_name = get_random_name()
    user_utils.update_admin_user(user_id, name=new_name)

    response = activity_utils.list_activity_events(
        entity_id=user_id,
        event_type=["user.updated"],
    )

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one user.updated event should exist for the user",
    )
    record = response.data[0]
    assert_that(
        record.entity_id,
        equal_to(user_id),
        "entity_id should match the updated user's ID",
    )
    assert_that(
        record.event_type,
        equal_to("user.updated"),
        "event_type should be user.updated",
    )
    assert_that(
        record.domain,
        equal_to("user_management"),
        "domain should be user_management",
    )


# ---------------------------------------------------------------------------
# TC-003: user.deactivated
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_user_deactivated_audit_record_stored(
    activity_utils, user_utils, disposable_user
):
    """TC-003: user.deactivated audit record is stored when user is deactivated."""
    _, user_id, _ = disposable_user

    user_utils.deactivate_user(user_id)

    response = activity_utils.list_activity_events(
        entity_id=user_id,
        event_type=["user.deactivated"],
    )

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one user.deactivated event should exist",
    )
    record = response.data[0]
    assert_that(
        record.entity_id,
        equal_to(user_id),
        "entity_id should match the deactivated user's ID",
    )
    assert_that(
        record.event_type,
        equal_to("user.deactivated"),
        "event_type should be user.deactivated",
    )
    assert_that(
        record.domain,
        equal_to("user_management"),
        "domain should be user_management",
    )
    assert_that(
        record.entity_type,
        equal_to("user"),
        "entity_type should be user",
    )


# ---------------------------------------------------------------------------
# TC-005: user.project.assigned + user.project.removed (merged)
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_user_project_assigned_and_removed_audit_records_stored(
    activity_utils, project_utils, disposable_user, activity_project
):
    """TC-005: user.project.assigned and user.project.removed audit records
    are stored in sequence for project assignment and removal."""
    _, user_id, _ = disposable_user
    project_name = activity_project

    # Assign user to project and assert audit record
    project_utils.assign_user_to_project(project_name, user_id, is_project_admin=False)

    assigned_response = activity_utils.list_activity_events(
        entity_id=user_id,
        event_type=["user.project.assigned"],
    )

    assert_that(
        len(assigned_response.data),
        greater_than_or_equal_to(1),
        "At least one user.project.assigned event should exist",
    )
    assigned_record = assigned_response.data[0]
    assert_that(
        assigned_record.entity_id,
        equal_to(user_id),
        "entity_id should match the assigned user's ID",
    )
    assert_that(
        assigned_record.event_type,
        equal_to("user.project.assigned"),
        "event_type should be user.project.assigned",
    )
    assert_that(
        assigned_record.attributes,
        not_none(),
        "attributes should be set for project assignment",
    )
    assert_that(
        assigned_record.attributes,
        has_key("project_name"),
        "attributes should contain project_name",
    )

    # Remove user from project and assert audit record
    project_utils.remove_user_from_project(project_name, user_id)

    removed_response = activity_utils.list_activity_events(
        entity_id=user_id,
        event_type=["user.project.removed"],
    )

    assert_that(
        len(removed_response.data),
        greater_than_or_equal_to(1),
        "At least one user.project.removed event should exist",
    )
    removed_record = removed_response.data[0]
    assert_that(
        removed_record.entity_id,
        equal_to(user_id),
        "entity_id should match the removed user's ID",
    )
    assert_that(
        removed_record.event_type,
        equal_to("user.project.removed"),
        "event_type should be user.project.removed",
    )
    assert_that(
        removed_record.attributes,
        not_none(),
        "attributes should be set for project removal",
    )
    assert_that(
        removed_record.attributes,
        has_key("project_name"),
        "attributes should contain project_name",
    )


# ---------------------------------------------------------------------------
# TC-012: user.project.role_updated
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_user_project_role_updated_audit_record_stored(
    activity_utils, project_utils, disposable_user, activity_project
):
    """TC-012: user.project.role_updated audit record is stored when role changes."""
    _, user_id, _ = disposable_user
    project_name = activity_project

    project_utils.assign_user_to_project(project_name, user_id, is_project_admin=False)
    project_utils.update_user_project_assignment(
        project_name, user_id, is_project_admin=True
    )

    response = activity_utils.list_activity_events(
        entity_id=user_id,
        event_type=["user.project.role_updated"],
    )

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one user.project.role_updated event should exist",
    )
    record = response.data[0]
    assert_that(
        record.entity_id,
        equal_to(user_id),
        "entity_id should match the user whose role was updated",
    )
    assert_that(
        record.event_type,
        equal_to("user.project.role_updated"),
        "event_type should be user.project.role_updated",
    )
    assert_that(
        record.domain,
        equal_to("user_management"),
        "domain should be user_management",
    )

    project_utils.remove_user_from_project(project_name, user_id)
