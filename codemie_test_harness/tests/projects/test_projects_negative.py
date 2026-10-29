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

"""Negative flow tests for project management API endpoints."""

from uuid import uuid4

import pytest
from hamcrest import assert_that, contains_string, equal_to, greater_than, not_none
from pydantic import ValidationError
from requests import HTTPError

from codemie_test_harness.tests.utils.base_utils import get_random_name


# CRUD Operations - Negative Flows


@pytest.mark.project
@pytest.mark.api
def test_create_project_with_duplicate_name(project_utils, project):
    """Test that creating a project with duplicate name fails with 409."""
    created_project = project()

    with pytest.raises(HTTPError) as exc_info:
        project_utils.create_project(
            name=created_project.name,  # Use existing project name
            description="Duplicate project",
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(409),
        "Expected 409 Conflict for duplicate project name",
    )


@pytest.mark.project
@pytest.mark.api
def test_create_project_with_empty_name(project_utils):
    """Test that creating a project with empty name fails with 400."""
    with pytest.raises(HTTPError) as exc_info:
        project_utils.create_project(
            name="",
            description="Project with empty name",
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "Expected 400 Bad Request for empty project name",
    )


@pytest.mark.project
@pytest.mark.api
def test_update_project_description_and_clear_description_together_returns_422(
    project_utils, project
):
    """Sending description and clear_description=True together
    in the same PATCH is rejected with 422, never silently resolved to one side; verified via
    an independent get_project_detail read that the original description survives untouched.
    """
    description = (
        f"Description that must survive the rejected PATCH {get_random_name()}"
    )
    created_project = project(description=description)

    with pytest.raises(HTTPError) as exc_info:
        project_utils.update_project(
            project_name=created_project.name,
            description=f"New description {get_random_name()}",
            clear_description=True,
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(422),
        "Expected 422 when description and clear_description are both provided together",
    )
    # The mutual-exclusion guard's own text (projects.py's model_validator,
    # ValueError("Provide either description or clear_description")) must be present in
    # the error body verbatim, not just a generic validation failure. Verified live: the
    # 422 body is {"error": {"message": "request: Value error, Provide either description
    # or clear_description", ...}} — "request: Value error, " is FastAPI/pydantic's fixed
    # wrapper for a body-level model_validator ValueError, not part of the guard's own text.
    assert_that(
        exc_info.value.response.json()["error"]["message"],
        contains_string("Provide either description or clear_description"),
        "Expected the mutual-exclusion guard's exact error text in the 422 body",
    )

    # Independent-channel check: a separate get_project_detail round trip, not the failing
    # call's own response, proves the guard rejected the request outright rather than
    # silently resolving to either side.
    after = project_utils.get_project_detail(created_project.name)
    assert_that(
        after.description,
        equal_to(description),
        "The original description must be unchanged after a rejected combined PATCH",
    )


@pytest.mark.project
@pytest.mark.api
def test_get_nonexistent_project_detail(project_utils):
    """Test getting details of non-existent project returns 404."""
    fake_project_name = get_random_name()

    with pytest.raises(HTTPError) as exc_info:
        project_utils.get_project_detail(fake_project_name)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Expected 404 Not Found for non-existent project",
    )


@pytest.mark.project
@pytest.mark.api
def test_update_nonexistent_project(project_utils):
    """Test updating a non-existent project returns 404."""
    fake_project_name = get_random_name()

    with pytest.raises(HTTPError) as exc_info:
        project_utils.update_project(
            project_name=fake_project_name,
            description="Updated description",
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Expected 404 Not Found when updating non-existent project",
    )


@pytest.mark.project
@pytest.mark.api
def test_update_project_name_fails_with_assigned_users(project_utils, project):
    """Test that renaming a project fails when users are assigned.

    API returns 409 Conflict when trying to rename a project that has
    assigned members (including the auto-assigned creator).
    """
    created_project = project()

    # Verify project has assigned members (creator is auto-assigned)
    project_detail = project_utils.get_project_detail(created_project.name)
    assert_that(
        len(project_detail.members),
        greater_than(0),
        "Project should have at least the creator assigned",
    )

    # Try to rename - should fail with 409
    new_name = get_random_name()
    with pytest.raises(HTTPError) as exc_info:
        project_utils.update_project(
            project_name=created_project.name,
            name=new_name,
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(409),
        "Expected 409 Conflict when renaming project with assigned users",
    )


@pytest.mark.project
@pytest.mark.api
def test_delete_nonexistent_project(project_utils):
    """Test deleting a non-existent project returns 404."""
    fake_project_name = get_random_name()

    with pytest.raises(HTTPError) as exc_info:
        project_utils.delete_project(fake_project_name)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Expected 404 for non-existent project",
    )


# User Assignment - Negative Flows


@pytest.mark.project
@pytest.mark.api
def test_assign_nonexistent_user_to_project(project_utils, project):
    """Test assigning a non-existent user returns 404."""
    created_project = project()
    fake_user_id = "00000000-0000-0000-0000-000000000000"

    with pytest.raises(HTTPError) as exc_info:
        project_utils.assign_user_to_project(
            project_name=created_project.name,
            user_id=fake_user_id,
            is_project_admin=False,
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Expected 404 Not Found for non-existent user",
    )


@pytest.mark.project
@pytest.mark.api
def test_update_assignment_for_non_assigned_user(project_utils, project):
    """Test updating assignment for a user not assigned to project fails."""
    created_project = project()

    # Use a valid but different user ID (not assigned to this project)
    fake_user_id = str(uuid4())

    with pytest.raises(HTTPError) as exc_info:
        project_utils.update_user_project_assignment(
            project_name=created_project.name,
            user_id=fake_user_id,
            is_project_admin=True,
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Expected 404 when updating assignment for non-assigned user",
    )


@pytest.mark.project
@pytest.mark.api
@pytest.mark.smoke
def test_remove_project_creator_fails(project_utils, project, user_utils):
    """Test that project creator cannot be removed.

    API returns 400 Bad Request when trying to remove the project creator.
    """
    created_project = project()
    # Get current user ID (who is the project creator)
    user_data = user_utils.get_about_me()
    user_id = user_data.user_id

    # Verify user is the creator
    project_detail = project_utils.get_project_detail(created_project.name)
    assert_that(project_detail.created_by, not_none(), "Project should have a creator")

    # Try to remove creator - should fail with 400
    with pytest.raises(HTTPError) as exc_info:
        project_utils.remove_user_from_project(created_project.name, user_id)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "Expected 400 Bad Request when removing project creator",
    )


@pytest.mark.project
@pytest.mark.api
def test_bulk_assign_empty_list(project_utils, project):
    """Test bulk assigning with empty user list is rejected by the SDK before hitting the API.

    This is a client-side guard: the SDK's BulkAssignmentRequest model enforces
    min_length=1 on the users list, so no HTTP request is made.
    """
    created_project = project()
    with pytest.raises(ValidationError, match="at least 1 item"):
        project_utils.bulk_assign_users_to_project(
            project_name=created_project.name,
            users=[],
        )


@pytest.mark.project
@pytest.mark.api
def test_bulk_remove_project_creator_fails(project_utils, project, user_utils):
    """Test that project creator cannot be removed via bulk operations.

    API returns 400 Bad Request when trying to bulk remove the project creator.
    """
    created_project = project()
    # Get current user ID (who is the project creator)
    user_data = user_utils.get_about_me()
    user_id = user_data.user_id

    # Verify user is assigned to the project
    project_detail = project_utils.get_project_detail(created_project.name)
    is_assigned = any(member.user_id == user_id for member in project_detail.members)
    assert_that(
        is_assigned, equal_to(True), "Creator should be assigned to the project"
    )

    # Try to bulk remove creator - should fail with 400
    with pytest.raises(HTTPError) as exc_info:
        project_utils.bulk_remove_users_from_project(
            project_name=created_project.name,
            user_ids=[user_id],
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "Expected 400 Bad Request when bulk removing project creator",
    )


@pytest.mark.project
@pytest.mark.api
def test_bulk_remove_empty_list(project_utils, project):
    """Test bulk removing with empty user list fails with 422."""
    created_project = project()

    with pytest.raises(HTTPError) as exc_info:
        project_utils.bulk_remove_users_from_project(
            project_name=created_project.name,
            user_ids=[],  # Empty list
        )

    # API rejects empty list
    assert_that(
        exc_info.value.response.status_code,
        equal_to(422),
        "Expected 422 Unprocessable Entity for empty user list",
    )


# CSV Import - Negative Flows


@pytest.mark.project
@pytest.mark.api
def test_validate_csv_with_malformed_format(project_utils, project):
    """Test CSV validation fails with 422 for malformed CSV (no header row)."""
    created_project = project()
    # CSV without header — structural error → API must reject with 422
    malformed_csv = b"""test@example.com,user
another@example.com,project_admin
"""

    with pytest.raises(HTTPError) as exc_info:
        project_utils.validate_users_from_csv(
            project_name=created_project.name,
            file_content=malformed_csv,
            filename="malformed.csv",
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(422),
        "Expected 422 for malformed CSV without header",
    )


@pytest.mark.project
@pytest.mark.api
def test_validate_csv_with_missing_email_column(project_utils, project):
    """Test CSV validation fails with 422 when required 'email' column is absent."""
    created_project = project()
    # CSV without 'email' column — missing required column → 422
    invalid_csv = b"""role
user
"""

    with pytest.raises(HTTPError) as exc_info:
        project_utils.validate_users_from_csv(
            project_name=created_project.name,
            file_content=invalid_csv,
            filename="invalid.csv",
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(422),
        "Expected 422 for CSV missing required 'email' column",
    )


@pytest.mark.project
@pytest.mark.api
def test_import_csv_for_nonexistent_project(project_utils):
    """Test importing CSV for non-existent project returns 404."""
    fake_project_name = get_random_name()
    csv_content = b"""email,role
test@example.com,user
"""

    with pytest.raises(HTTPError) as exc_info:
        project_utils.import_users_from_csv(
            project_name=fake_project_name,
            file_content=csv_content,
            filename="users.csv",
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Expected 404 when importing CSV for non-existent project",
    )


@pytest.mark.project
@pytest.mark.api
def test_import_empty_csv(project_utils, project):
    """Test importing CSV with header only fails with 422."""
    created_project = project()
    empty_csv = b"""email,role
"""

    with pytest.raises(HTTPError) as exc_info:
        project_utils.import_users_from_csv(
            project_name=created_project.name,
            file_content=empty_csv,
            filename="empty.csv",
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(422),
        "Expected 422 for CSV with no data rows",
    )
