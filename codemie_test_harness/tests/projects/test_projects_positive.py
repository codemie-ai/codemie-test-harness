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

"""Positive flow tests for project management API endpoints."""

import logging

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than,
    has_length,
    instance_of,
    not_none,
    is_in,
    not_,
)
from requests import HTTPError

from codemie_sdk.models.project import BulkAssignmentUserItem
from codemie_test_harness.tests.test_data.projects_test_data import (
    get_project_create_data,
    get_project_create_data_with_display_name,
    get_project_update_data,
    list_projects_test_data,
    user_assignment_test_data,
    csv_import_test_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.project_utils import ProjectUtils

logger = logging.getLogger(__name__)


# CRUD Operations - Positive Flows


@pytest.mark.project
@pytest.mark.api
@pytest.mark.smoke
def test_create_project(project_utils, project):
    """Test creating a new project with basic fields.

    A description sent on create is stored and returned exactly
    as entered, verified via an independent get_project_detail read; this also stands as the
    R-13 backward-compatibility check for a client that always sends a description on create.
    """
    description = f"Exact match description {get_random_name()}"
    response = project(description=description)

    assert_that(response.name, not_none())
    assert_that(
        response.description,
        equal_to(description),
        "Create response must echo the description exactly as entered",
    )
    assert_that(response.project_type, equal_to("shared"))
    assert_that(response.created_by, not_none())
    assert_that(response.created_at, not_none())
    assert_that(response.cost_center_id, equal_to(None))

    # Independent-channel check: a separate get_project_detail round trip, not the create
    # response, proves the description round-tripped through persistence unchanged.
    detail = project_utils.get_project_detail(response.name)
    assert_that(
        detail.description,
        equal_to(description),
        "get_project_detail (an independent read) must return the same description "
        "that was submitted on create",
    )


@pytest.fixture
def created_project_names(project_utils):
    """Tracks project names created directly via ``project_utils.create_project`` and cleans
    them up on teardown.

    Used instead of the ``project`` factory fixture when a test needs a create call whose
    ``description`` is genuinely omitted from the payload: ``project``'s fallback
    (``conftest.py``) substitutes a generated description whenever ``description`` is falsy,
    which would mask exactly the omission this fixture's caller needs to exercise.
    """
    names = []
    yield names
    for name in names:
        try:
            project_utils.delete_project_cascade(name)
        except Exception as e:
            logger.error(f"Failed to delete project {name}: {e}")


@pytest.mark.project
@pytest.mark.api
def test_create_project_without_description_succeeds(
    project_utils, created_project_names
):
    """Description omitted entirely from the create payload still
    succeeds; the create response and, independently, a list_projects search both show no
    description for the project.
    """
    name = get_random_name()

    response = project_utils.create_project(name=name)
    created_project_names.append(name)

    assert_that(response.name, equal_to(name))
    assert_that(
        response.description,
        equal_to(None),
        "A create request that omits description entirely must return description=None",
    )

    # Independent-channel check: a separate list_projects search, not the create response,
    # is the oracle for "appears in the projects list with no description" (AC-2).
    listed = project_utils.list_projects(search=name)
    matches = [p for p in listed.data if p.name == name]
    assert_that(
        matches,
        has_length(1),
        f"Project '{name}' created without a description must still appear in "
        f"list_projects search results",
    )
    assert_that(
        matches[0].description,
        equal_to(None),
        "list_projects (an independent read) must show no description for a project "
        "created without one",
    )


@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize(
    "whitespace_description",
    ["   ", "\n\n\n"],
    ids=["spaces_only", "newline_only"],
)
def test_create_project_with_whitespace_only_description_normalizes_to_none(
    project_utils, created_project_names, whitespace_description
):
    """A whitespace-only description on create is not rejected
    and normalizes to no description, verified via an independent get_project_detail read
    (proving the value became None and was not merely stored as spaces/newlines).
    """
    name = get_random_name()

    project_utils.create_project(name=name, description=whitespace_description)
    created_project_names.append(name)

    # Independent-channel check: a separate get_project_detail round trip, not the create
    # call's own response, proves the whitespace-only value normalized to None.
    detail = project_utils.get_project_detail(name)
    assert_that(
        detail.description,
        equal_to(None),
        "A whitespace-only description on create must normalize to None, not be stored "
        "as-is or rejected",
    )


@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize(
    "whitespace_description",
    ["   ", "\n\n\n"],
    ids=["spaces_only", "newline_only"],
)
def test_update_project_with_whitespace_only_description_normalizes_to_none(
    project_utils, project, whitespace_description
):
    """A whitespace-only description on update is not rejected
    and normalizes to no description (CR-001's PATCH-side clear treatment), verified via an
    independent get_project_detail read.
    """
    description = f"Description to be whitespace-cleared {get_random_name()}"
    created_project = project(description=description)

    before = project_utils.get_project_detail(created_project.name)
    assert_that(
        before.description,
        equal_to(description),
        "Setup precondition: project must start with a real, non-empty description",
    )

    project_utils.update_project(
        project_name=created_project.name,
        description=whitespace_description,
    )

    # Independent-channel check: a separate get_project_detail round trip, not the update
    # call's own response, proves the whitespace-only PATCH value normalized to None.
    after = project_utils.get_project_detail(created_project.name)
    assert_that(
        after.description,
        equal_to(None),
        "A whitespace-only description on update must normalize to None, not be stored "
        "as-is or rejected",
    )


@pytest.mark.project
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.sanity
def test_list_projects(project_utils):
    """Test listing projects with default parameters."""
    response = project_utils.list_projects()

    assert_that(response.data, instance_of(list))
    assert_that(response.pagination.total, greater_than(0))
    assert_that(response.pagination.page, equal_to(0))
    assert_that(response.pagination.per_page, equal_to(20))


@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize("params", list_projects_test_data)
def test_list_projects_with_params(project_utils, params):
    """Test listing projects with different parameters."""
    response = project_utils.list_projects(**params)

    assert_that(response.data, instance_of(list))
    assert_that(response.pagination.page, equal_to(params.get("page", 0)))
    assert_that(response.pagination.per_page, equal_to(params.get("per_page", 20)))


@pytest.mark.project
@pytest.mark.api
def test_list_projects_pagination_last_page(project_utils):
    """Test listing projects - navigating to last page."""
    per_page = 10
    # Get first page to know total (per_page must be >= 10)
    first_page = project_utils.list_projects(per_page=per_page)
    total_pages = (
        first_page.pagination.total + per_page - 1
    ) // per_page  # Ceiling division

    if total_pages > 1:
        # Get last page
        last_page = project_utils.list_projects(page=total_pages - 1, per_page=per_page)
        assert_that(last_page.pagination.page, equal_to(total_pages - 1))
        assert_that(len(last_page.data), greater_than(0))


@pytest.mark.project
@pytest.mark.api
@pytest.mark.smoke
def test_list_projects_with_search(project_utils, project):
    """Test listing projects with search filter."""
    created_project = project()
    project_name = created_project.name

    response = project_utils.list_projects(search=project_name[:5])

    assert_that(response.data, instance_of(list))
    project_names = [p.name for p in response.data]
    assert_that(project_name, is_in(project_names))


@pytest.mark.project
@pytest.mark.api
def test_list_projects_with_search_finds_project_by_name_when_display_name_set(
    project_utils, project
):
    """Regression: search by Name must find a project that also has a Display Name."""
    data = get_project_create_data_with_display_name()
    created_project = project(
        name=data["name"],
        description=data["description"],
        display_name=data["display_name"],
    )

    response = project_utils.list_projects(search=created_project.name)

    assert_that(response.data, instance_of(list))
    project_names = [p.name for p in response.data]
    assert_that(
        created_project.name,
        is_in(project_names),
        "Project with a display_name set must still be found when searching by its Name",
    )


@pytest.mark.project
@pytest.mark.api
@pytest.mark.smoke
def test_get_project_detail(project_utils, project):
    """Test getting project details."""
    created_project = project()
    response = project_utils.get_project_detail(created_project.name)

    assert_that(response.name, equal_to(created_project.name))
    assert_that(response.description, equal_to(created_project.description))
    assert_that(response.project_type, equal_to("shared"))
    assert_that(response.members, instance_of(list))
    assert_that(response.user_count, greater_than(0))


@pytest.mark.project
@pytest.mark.api
def test_get_project_detail_members_list(project_utils, project):
    """Test that project detail includes members list."""
    created_project = project()
    response = project_utils.get_project_detail(created_project.name)

    # Verify members list structure
    assert_that(response.members, instance_of(list))
    assert_that(response.members, has_length(greater_than(0)))

    # Verify first member has required fields
    first_member = response.members[0]
    assert_that(first_member.user_id, not_none())
    assert_that(first_member.is_project_admin, instance_of(bool))


@pytest.mark.project
@pytest.mark.api
@pytest.mark.smoke
def test_update_project(project_utils, project):
    """Test updating a project's description."""
    created_project = project()
    update_data = get_project_update_data()

    response = project_utils.update_project(
        project_name=created_project.name,
        description=update_data["description"],
    )

    assert_that(response.name, equal_to(created_project.name))
    assert_that(response.description, equal_to(update_data["description"]))


def _snapshot_immutable_fields(detail):
    """Comparable ``ProjectDetailResponse`` fields that a description-only update must
    never change.

    Excludes ``name`` (the lookup key) and membership fields (``members``, ``user_count``,
    ``admin_count``), which no description update path can affect.
    """
    return {
        "display_name": detail.display_name,
        "project_type": detail.project_type,
        "cost_center_id": detail.cost_center_id,
        "created_by": detail.created_by,
        "created_at": detail.created_at,
        "chargeback_attribution": detail.chargeback_attribution,
    }


@pytest.mark.project
@pytest.mark.api
def test_update_project_adds_description_when_previously_none(
    project_utils, created_project_names
):
    """Updating only ``description`` on a project that had none
    stores the new value and leaves every other field (display_name, project_type,
    cost_center_id, created_by, created_at, chargeback_attribution) unchanged.
    """
    name = get_random_name()
    display_name = f"Display {get_random_name()}"
    project_utils.create_project(name=name, description="", display_name=display_name)
    created_project_names.append(name)

    before = project_utils.get_project_detail(name)
    assert_that(
        before.description,
        equal_to(None),
        "Setup precondition: project must start with no description",
    )
    before_snapshot = _snapshot_immutable_fields(before)

    new_description = f"Updated project description {get_random_name()}"
    project_utils.update_project(project_name=name, description=new_description)

    # Independent-channel check: a separate get_project_detail round trip, not the update
    # call's own response, is the oracle for both the new value and field isolation.
    after = project_utils.get_project_detail(name)
    assert_that(
        after.description,
        equal_to(new_description),
        "get_project_detail (an independent read) must show the newly added description",
    )
    after_snapshot = _snapshot_immutable_fields(after)
    for field, before_value in before_snapshot.items():
        assert_that(
            after_snapshot[field],
            equal_to(before_value),
            f"Adding a description must not change '{field}' "
            f"(before={before_value!r}, after={after_snapshot[field]!r})",
        )


@pytest.mark.project
@pytest.mark.api
def test_update_project_clear_description_removes_it_immediately(
    project_utils, project
):
    """Clearing an existing description via
    ``clear_description=True`` nulls it in the update call's own response and, independently,
    on a follow-up ``get_project_detail`` read, immediately, without touching any other field.
    """
    description = f"Description to be cleared {get_random_name()}"
    display_name = f"Display {get_random_name()}"
    created_project = project(description=description, display_name=display_name)

    before = project_utils.get_project_detail(created_project.name)
    assert_that(
        before.description,
        equal_to(description),
        "Setup precondition: description must be set before clearing",
    )
    before_snapshot = _snapshot_immutable_fields(before)

    response = project_utils.update_project(
        project_name=created_project.name,
        clear_description=True,
    )
    assert_that(
        response.description,
        equal_to(None),
        "The update call's own response must carry description=None after clearing",
    )

    # Independent-channel check: a separate get_project_detail round trip, not the update
    # call's own response, proves the clear persisted and is visible on a fresh read.
    after = project_utils.get_project_detail(created_project.name)
    assert_that(
        after.description,
        equal_to(None),
        "get_project_detail (an independent read) must also show no description "
        "immediately after clearing",
    )
    after_snapshot = _snapshot_immutable_fields(after)
    for field, before_value in before_snapshot.items():
        assert_that(
            after_snapshot[field],
            equal_to(before_value),
            f"Clearing the description must not change '{field}' "
            f"(before={before_value!r}, after={after_snapshot[field]!r})",
        )


@pytest.mark.project
@pytest.mark.api
def test_update_project_display_name_only_leaves_description_untouched(
    project_utils, project
):
    """Updating only ``display_name`` (no ``description`` or
    ``clear_description`` in the payload) leaves an existing description untouched, verified
    on an independent ``get_project_detail`` read.
    """
    description = f"Description that must survive {get_random_name()}"
    created_project = project(description=description)

    before = project_utils.get_project_detail(created_project.name)
    assert_that(
        before.description,
        equal_to(description),
        "Setup precondition: description must be set before the display_name-only update",
    )

    new_display_name = f"Updated Display {get_random_name()}"
    project_utils.update_project(
        project_name=created_project.name,
        display_name=new_display_name,
    )

    # Independent-channel check: a separate get_project_detail round trip, not the update
    # call's own response, is the oracle for "description survives an unrelated update".
    after = project_utils.get_project_detail(created_project.name)
    assert_that(
        after.description,
        equal_to(description),
        "get_project_detail (an independent read) must show the original description "
        "unchanged after a display_name-only update",
    )
    assert_that(
        after.display_name,
        equal_to(new_display_name),
        "get_project_detail must show the new display_name after the update",
    )


@pytest.mark.project
@pytest.mark.api
@pytest.mark.smoke
def test_delete_project(project_utils):
    """Test deleting a project."""
    # Create a project to delete
    project_data = get_project_create_data()
    created_project = project_utils.create_project(
        name=project_data["name"],
        description=project_data["description"],
    )

    # Delete the project
    response = project_utils.delete_project(created_project.name)

    assert_that(response.message, instance_of(str))
    assert_that(response.name, equal_to(created_project.name))


@pytest.mark.project
@pytest.mark.api
def test_delete_project_same_name_recreate_denies_old_creator_admin(project_utils):
    """Regression: recreating a deleted project under the same name
    must not inherit membership/Project Admin access from the deleted project's creator.

    Requires the AUTH_USERNAME_PROJECT/AUTH_USERNAME_DEFAULT test personas
    (preview-environment accounts, matching the sibling roles suite); this test
    is not environment-gated here so a missing persona surfaces as an explicit
    authentication failure rather than a silent skip.

    Chained checkpoints (one register requirement each):
    - TC-001 (R-4): a *different* user recreating the same project name becomes its
      sole member/admin; the original creator is entirely absent from the roster,
      read through a third, uninvolved session (the `project_utils` fixture's
      default client, never used for either persona's create/delete/assign calls).
    - TC-002 (R-1): the original creator's own session is denied access outright
      (404) against the recreated project, proving their membership row for the
      name was actually removed, not merely hidden from one response shape.
    - TC-003 (R-2): a fresh, legitimate reassignment of the former creator back
      onto the recreated project succeeds (not 409), proving no leftover row for
      (former creator, project name) survived to block or corrupt a clean insert.
    """
    creator_client = get_client(
        username=CredentialsManager.get_parameter("AUTH_USERNAME_PROJECT"),
        password=CredentialsManager.get_parameter("AUTH_PASSWORD_PROJECT"),
    )
    recreator_client = get_client(
        username=CredentialsManager.get_parameter("AUTH_USERNAME_DEFAULT"),
        password=CredentialsManager.get_parameter("AUTH_PASSWORD_DEFAULT"),
    )
    creator_project_utils = ProjectUtils(creator_client)
    recreator_project_utils = ProjectUtils(recreator_client)
    creator_id = creator_client.users.about_me().user_id
    recreator_id = recreator_client.users.about_me().user_id

    project_data = get_project_create_data()
    project_name = project_data["name"]
    original_deleted = False
    recreated = False

    try:
        creator_project_utils.create_project(
            name=project_name, description=project_data["description"]
        )

        # Baseline (own data, own creation): the creator is the recreated
        # project's sole member/admin before deletion.
        baseline = creator_project_utils.get_project_detail(project_name)
        assert_that(baseline.members, has_length(1))
        assert_that(baseline.members[0].user_id, equal_to(creator_id))
        assert_that(baseline.members[0].is_project_admin, equal_to(True))

        creator_project_utils.delete_project(project_name)
        original_deleted = True

        # A different user recreates the exact same project name; this succeeds
        # (201) because the deleted Application row was hard-deleted, not a 409.
        recreator_project_utils.create_project(
            name=project_name,
            description="Recreated after delete, same name",
        )
        recreated = True

        # TC-001 (R-4) — independent-channel roster read from a third, uninvolved
        # session, not the recreator's own create response.
        recreated_detail = project_utils.get_project_detail(project_name)
        member_ids = [member.user_id for member in recreated_detail.members]
        assert_that(recreated_detail.members, has_length(1))
        assert_that(member_ids, equal_to([recreator_id]))
        assert_that(recreated_detail.members[0].is_project_admin, equal_to(True))
        assert_that(
            creator_id,
            not_(is_in(member_ids)),
            "Former creator must be entirely absent from the recreated project's roster",
        )

        # TC-002 (R-1) — the former creator's own session, a channel independent
        # of TC-001's third-party roster read, must be denied access outright.
        with pytest.raises(HTTPError) as exc_info:
            creator_project_utils.get_project_detail(project_name)
        assert_that(
            exc_info.value.response.status_code,
            equal_to(404),
            "Former creator's own session must get 404 against the recreated "
            "project, proving their membership row for the name was removed",
        )

        # TC-003 (R-2) — a fresh, legitimate reassignment must succeed (not 409),
        # proving no leftover row for (former creator, project name) survived.
        assign_response = recreator_project_utils.assign_user_to_project(
            project_name=project_name,
            user_id=creator_id,
            is_project_admin=False,
        )
        assert_that(assign_response.project_name, equal_to(project_name))
        assert_that(assign_response.user_id, equal_to(creator_id))
        assert_that(assign_response.is_project_admin, equal_to(False))

        # Secondary, independent confirmation of TC-003: a fresh third-client GET,
        # not the assignment call's own response.
        final_detail = project_utils.get_project_detail(project_name)
        members_by_id = {member.user_id: member for member in final_detail.members}
        assert_that(creator_id, is_in(members_by_id))
        assert_that(members_by_id[creator_id].is_project_admin, equal_to(False))
    finally:
        if recreated:
            try:
                recreator_project_utils.remove_user_from_project(
                    project_name, creator_id
                )
            except Exception as e:
                logger.warning(
                    "Could not remove creator %s from recreated project %s "
                    "(skipped): %s",
                    creator_id,
                    project_name,
                    e,
                )
            try:
                recreator_project_utils.delete_project(project_name)
            except Exception as e:
                logger.error(
                    "Failed to delete recreated project %s: %s", project_name, e
                )
        elif not original_deleted:
            try:
                creator_project_utils.delete_project(project_name)
            except Exception as e:
                logger.error(
                    "Failed to delete original project %s: %s", project_name, e
                )


# User Assignment - Positive Flows


@pytest.mark.project
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize("is_project_admin", user_assignment_test_data)
def test_assign_user_to_project(project_utils, project, user_utils, is_project_admin):
    """Test assigning a user to a project.

    Uses bulk_assign for upsert capability since creator may be auto-assigned.
    """
    created_project = project()
    user_data = user_utils.get_about_me()
    user_id = user_data.user_id

    # Check if user is already assigned
    project_detail = project_utils.get_project_detail(created_project.name)
    is_already_assigned = any(
        member.user_id == user_id for member in project_detail.members
    )

    if is_already_assigned:
        # Use bulk assign which does upsert
        response = project_utils.bulk_assign_users_to_project(
            project_name=created_project.name,
            users=[
                BulkAssignmentUserItem(
                    user_id=user_id, is_project_admin=is_project_admin
                )
            ],
        )
        assert_that(response.project_name, equal_to(created_project.name))
        assert_that(response.total, equal_to(1))
        assert_that(response.results[0].user_id, equal_to(user_id))
        assert_that(response.results[0].action, is_in(["assigned", "updated"]))
    else:
        # User not assigned, test regular assign
        response = project_utils.assign_user_to_project(
            project_name=created_project.name,
            user_id=user_id,
            is_project_admin=is_project_admin,
        )
        assert_that(response.project_name, equal_to(created_project.name))
        assert_that(response.user_id, equal_to(user_id))
        assert_that(response.is_project_admin, equal_to(is_project_admin))


@pytest.mark.project
@pytest.mark.api
@pytest.mark.smoke
def test_update_user_project_assignment(project_utils, project, user_utils):
    """Test updating a user's project admin role."""
    created_project = project()
    user_data = user_utils.get_about_me()
    user_id = user_data.user_id

    # Check if user is already assigned
    project_detail = project_utils.get_project_detail(created_project.name)
    is_already_assigned = any(
        member.user_id == user_id for member in project_detail.members
    )

    if not is_already_assigned:
        # Assign user as regular member first
        project_utils.bulk_assign_users_to_project(
            project_name=created_project.name,
            users=[BulkAssignmentUserItem(user_id=user_id, is_project_admin=False)],
        )

    # Update to project admin
    response = project_utils.update_user_project_assignment(
        project_name=created_project.name,
        user_id=user_id,
        is_project_admin=True,
    )

    assert_that(response.project_name, equal_to(created_project.name))
    assert_that(response.user_id, equal_to(user_id))
    assert_that(response.is_project_admin, equal_to(True))


@pytest.mark.project
@pytest.mark.api
def test_bulk_assign_users_to_project(project_utils, project, user_utils):
    """Test bulk assigning users to a project.

    Bulk assign does upsert, so it works even if user is already assigned.
    """
    created_project = project()
    user_data = user_utils.get_about_me()
    user_id = user_data.user_id

    users = [
        BulkAssignmentUserItem(user_id=user_id, is_project_admin=False),
    ]

    response = project_utils.bulk_assign_users_to_project(
        project_name=created_project.name,
        users=users,
    )

    assert_that(response.project_name, equal_to(created_project.name))
    assert_that(response.total, equal_to(1))
    assert_that(response.results, has_length(1))
    assert_that(response.results[0].user_id, equal_to(user_id))
    assert_that(response.results[0].action, is_in(["assigned", "updated"]))


@pytest.mark.project
@pytest.mark.api
@pytest.mark.smoke
def test_assign_and_remove_user_from_project(project_utils, project, user_utils):
    """Test complete flow: assign a user to project and then remove them.

    Finds a non-creator user from existing projects and uses them for testing.
    """
    # Get current user (who will be the project creator)
    current_user = user_utils.get_about_me()
    current_user_id = current_user.user_id

    # Find a user from existing projects who is not the current user
    # Limit to 10 projects to avoid excessive API calls (minimum per_page is 10)
    projects_response = project_utils.list_projects(per_page=10)
    test_user_id = None

    for proj in projects_response.data:
        # Get project details with members
        project_detail = project_utils.get_project_detail(proj.name)

        # Look for a member who is not the current user
        for member in project_detail.members:
            if member.user_id != current_user_id:
                test_user_id = member.user_id
                break

        if test_user_id:
            break

    # Skip test if no other user found (e.g., fresh environment, single-user setup)
    if not test_user_id:
        pytest.skip("No other users found in existing projects to test with")

    # Create a new project for testing
    test_project = project()

    # Assign the found user to the project
    assign_response = project_utils.assign_user_to_project(
        project_name=test_project.name,
        user_id=test_user_id,
        is_project_admin=False,
    )

    assert_that(assign_response.project_name, equal_to(test_project.name))
    assert_that(assign_response.user_id, equal_to(test_user_id))
    assert_that(assign_response.is_project_admin, equal_to(False))

    # Verify user is in the project members
    project_detail = project_utils.get_project_detail(test_project.name)
    member_ids = [m.user_id for m in project_detail.members]
    assert_that(test_user_id, is_in(member_ids))

    # Remove the user from the project
    remove_response = project_utils.remove_user_from_project(
        project_name=test_project.name,
        user_id=test_user_id,
    )

    assert_that(remove_response.project_name, equal_to(test_project.name))
    assert_that(remove_response.user_id, equal_to(test_user_id))

    # Verify user is no longer in the project members
    project_detail_after = project_utils.get_project_detail(test_project.name)
    member_ids_after = [m.user_id for m in project_detail_after.members]
    assert_that(test_user_id, not_(is_in(member_ids_after)))


# CSV Import - Positive Flows


@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize("csv_content,filename", csv_import_test_data)
def test_validate_users_from_csv(project_utils, project, csv_content, filename):
    """Test CSV validation returns per-row errors for invalid/unknown-user data."""
    created_project = project()
    response = project_utils.validate_users_from_csv(
        project_name=created_project.name,
        file_content=csv_content,
        filename=filename,
    )

    errors = [user.error for user in response.users if user.error is not None]
    assert_that(errors, has_length(greater_than(0)))


@pytest.mark.project
@pytest.mark.api
@pytest.mark.smoke
def test_import_users_from_csv(project_utils, project, user_utils):
    """Test importing users from CSV file.

    Creates a CSV with the current user (guaranteed to exist).
    """
    created_project = project()
    # Get current user info
    user_data = user_utils.get_about_me()
    current_user_email = user_data.email

    # Create CSV content with current user
    csv_content = f"""email,role
{current_user_email},project_admin
""".encode("utf-8")

    # First validate the CSV
    validation_response = project_utils.validate_users_from_csv(
        project_name=created_project.name,
        file_content=csv_content,
        filename="users.csv",
    )

    # Verify validation passes
    assert_that(validation_response.users, has_length(1))
    validated_user = validation_response.users[0]
    assert_that(validated_user.email, equal_to(current_user_email))
    assert_that(
        validated_user.error,
        equal_to(None),
        "CSV validation should pass for current user",
    )

    # Import users from CSV
    response = project_utils.import_users_from_csv(
        project_name=created_project.name,
        file_content=csv_content,
        filename="users.csv",
    )

    # Verify import response
    assert_that(response.project_name, equal_to(created_project.name))
    assert_that(response.total, equal_to(1))
    assert_that(response.results, has_length(1))

    # Verify user was assigned or updated
    result = response.results[0]
    assert_that(result.action, is_in(["assigned", "updated"]))
    assert_that(result.is_project_admin, equal_to(True))
