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

"""API tests for project_management activity event audit records.

Covers:
    TC-019  project.created event stored when a project is created
    TC-020  project.updated event stored when a project is modified
    TC-021  project.deleted event stored when a project is deleted

Each project-lifecycle test creates and cleans up its own project so the tests
are fully isolated from the session-scoped activity_project fixture.
"""

import pytest
from hamcrest import assert_that, equal_to, greater_than_or_equal_to

from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.project_utils import ProjectUtils


# ---------------------------------------------------------------------------
# TC-019: project.created
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_project_created_audit_record_stored(activity_utils, maintainer_client):
    """TC-019: project.created audit record is stored when a project is created."""
    project_utils = ProjectUtils(maintainer_client)
    project_name = get_random_name()
    project_utils.create_project(name=project_name, description="Activity audit test")

    response = activity_utils.list_activity_events(
        entity_id=project_name,
        event_type=["project.created"],
        domain=["project_management"],
    )

    project_utils.delete_project(project_name)

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one project.created event should exist for the created project",
    )
    record = response.data[0]
    assert_that(
        record.event_type,
        equal_to("project.created"),
        "event_type should be project.created",
    )
    assert_that(
        record.domain,
        equal_to("project_management"),
        "domain should be project_management",
    )
    assert_that(
        record.entity_type,
        equal_to("project"),
        "entity_type should be project",
    )


# ---------------------------------------------------------------------------
# TC-020: project.updated
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_project_updated_audit_record_stored(activity_utils, maintainer_client):
    """TC-020: project.updated audit record is stored when a project is modified."""
    project_utils = ProjectUtils(maintainer_client)
    project_name = get_random_name()
    project_utils.create_project(name=project_name, description="Activity audit test")
    project_utils.update_project(project_name, description="Updated description")

    response = activity_utils.list_activity_events(
        entity_id=project_name,
        event_type=["project.updated"],
        domain=["project_management"],
    )

    project_utils.delete_project(project_name)

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one project.updated event should exist for the updated project",
    )
    record = response.data[0]
    assert_that(
        record.event_type,
        equal_to("project.updated"),
        "event_type should be project.updated",
    )
    assert_that(
        record.domain,
        equal_to("project_management"),
        "domain should be project_management",
    )
    assert_that(
        record.entity_type,
        equal_to("project"),
        "entity_type should be project",
    )


# ---------------------------------------------------------------------------
# TC-021: project.deleted
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_project_deleted_audit_record_stored(activity_utils, maintainer_client):
    """TC-021: project.deleted audit record is stored when a project is deleted."""
    project_utils = ProjectUtils(maintainer_client)
    project_name = get_random_name()
    project_utils.create_project(name=project_name, description="Activity audit test")
    project_utils.delete_project(project_name)

    response = activity_utils.list_activity_events(
        entity_id=project_name,
        event_type=["project.deleted"],
        domain=["project_management"],
    )

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one project.deleted event should exist for the deleted project",
    )
    record = response.data[0]
    assert_that(
        record.event_type,
        equal_to("project.deleted"),
        "event_type should be project.deleted",
    )
    assert_that(
        record.domain,
        equal_to("project_management"),
        "domain should be project_management",
    )
    assert_that(
        record.entity_type,
        equal_to("project"),
        "entity_type should be project",
    )
