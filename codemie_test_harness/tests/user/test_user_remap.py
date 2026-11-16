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

"""API tests for the SuperAdmin user-id remap endpoint (POST /v1/admin/users/remap)."""

import logging

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_item,
    instance_of,
    is_not,
)
from requests import HTTPError

from codemie_sdk.models.user import CodeMieUserDetail
from codemie_sdk.models.workflow import WorkflowMode

from codemie_test_harness.tests.utils.assistant_utils import AssistantUtils
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.conversation_utils import ConversationUtils
from codemie_test_harness.tests.utils.workflow_utils import WorkflowUtils
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def remap_project(admin_utils, project_utils):
    """A project for `test_remap_moves_owned_content_to_new_user_id`: created empty,
    cascade-deleted afterwards (needed over plain `delete_project` since the test scopes
    budgets, an assistant and a workflow to it — `delete_project_cascade` also unassigns
    every member but the creator, so neither old_user_id nor new_user_id needs an
    explicit `remove_user_from_project` once the test is done with them).
    """
    name = get_random_name()
    admin_utils.create_project(name)
    yield name
    try:
        project_utils.delete_project_cascade(name)
    except Exception as e:
        logger.warning(f"Failed to delete project {name}: {e}")


@pytest.fixture
def owned_conversation_factory(admin_user, user_utils):
    """Factory: create a conversation as `admin_user`'s client, deleted afterwards.

    `delete_project_cascade` removes assistants, workflows and budgets scoped to a
    project, but not conversations, so a conversation created for one of these tests
    needs this explicit cleanup instead.

    Conversation ownership is checked by matching the caller's id to
    `conversation.user_id` — there's no admin delete-by-id or delete-by-user-id route.
    Once a test remaps `old_user_id` to `new_user_id`, `old_user_client`'s token can no
    longer delete a conversation now owned by `new_user_id`, and `new_user_id` has no
    client of its own to delete it with either (it's a synthetic id with no backend
    account behind it). Call `note_remap(new_user_id)` right after remapping so
    teardown remaps the row back to `old_user_id` before deleting with
    `old_user_client`, which owns it again at that point.
    """
    old_user_id, old_user_client = admin_user.user_id, admin_user.client
    conversation_utils = ConversationUtils(old_user_client)
    created_ids = []
    current_owner_id = old_user_id

    def _create(**kwargs):
        conversation = conversation_utils.create_conversation(**kwargs)
        created_ids.append(conversation["id"])
        return conversation

    def _note_remap(new_owner_id):
        nonlocal current_owner_id
        current_owner_id = new_owner_id

    _create.note_remap = _note_remap
    yield _create
    if created_ids and current_owner_id != old_user_id:
        try:
            user_utils.remap_user(current_owner_id, old_user_id)
        except Exception as e:
            logger.warning(
                f"Failed to remap conversation owner {current_owner_id} back to "
                f"{old_user_id} for cleanup: {e}"
            )
    for conversation_id in created_ids:
        try:
            conversation_utils.delete_conversation(conversation_id)
        except Exception as e:
            logger.warning(f"Failed to delete conversation {conversation_id}: {e}")


@pytest.mark.user
@pytest.mark.api
def test_remap_moves_user_to_new_id(user_utils, admin_user, new_user_id_factory):
    # @case identity-remap-migration_TC_001
    old_user_id = admin_user.user_id
    new_user_id = new_user_id_factory()

    remapped = user_utils.remap_user(old_user_id, new_user_id)

    assert_that(
        remapped,
        instance_of(CodeMieUserDetail),
        "remap should return a CodeMieUserDetail",
    )
    assert_that(
        remapped.id,
        equal_to(new_user_id),
        "Remapped user detail should carry the new id",
    )

    detail = user_utils.get_admin_user(new_user_id)
    assert_that(
        detail.id,
        equal_to(new_user_id),
        "Admin user detail for the new id should resolve after the remap",
    )
    assert_that(
        detail.email,
        equal_to(remapped.email),
        "Email should be preserved across the remap",
    )


@pytest.mark.user
@pytest.mark.api
def test_remap_moves_owned_content_to_new_user_id(
    user_utils,
    assistant_utils,
    workflow_utils,
    admin_project_budget_utils,
    admin_user,
    new_user_id_factory,
    remap_project,
    owned_conversation_factory,
    default_llm,
):
    # @case identity-remap-migration_TC_003
    old_user_id, old_user_client = admin_user.user_id, admin_user.client
    new_user_id = new_user_id_factory()
    project_name = remap_project

    old_user_assistant_utils = AssistantUtils(old_user_client)
    old_user_workflow_utils = WorkflowUtils(old_user_client)

    # --- content owned by old_user_id, created before the remap ---

    user_utils.assign_user_to_project(old_user_id, project_name)

    group_response = admin_project_budget_utils.create_budget_group(
        project_name, name=get_random_name()
    )
    budget_id = admin_project_budget_utils.budget_ids_by_category(group_response)[
        "platform"
    ]
    admin_project_budget_utils.override_member(budget_id, old_user_id, 20.0, 10.0)

    assistant = old_user_assistant_utils.create_assistant(project_name=project_name)

    conversation = owned_conversation_factory(initial_assistant_id=assistant.id)
    conversation_id = conversation["id"]

    workflow_assistant = AssistantModel(
        id="remap_state",
        model=default_llm.base_name,
        system_prompt="You are a helpful assistant",
    )
    workflow_state = StateModel(id="remap_state", assistant_id="remap_state")
    workflow_yaml = prepare_yaml_content(
        WorkflowYamlModel(
            assistants=[workflow_assistant], states=[workflow_state]
        ).model_dump(exclude_none=True)
    )
    workflow = old_user_workflow_utils.create_workflow(
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=workflow_yaml,
        project_name=project_name,
    )

    # --- confirm everything resolves under old_user_id before the remap ---

    assert_that(
        user_utils.get_user_project_names(old_user_id),
        has_item(project_name),
        "Project membership should be listed under old_user_id before the remap",
    )
    pre_budget = admin_project_budget_utils.get_budget(budget_id)
    pre_member_ids = [a["user_id"] for a in pre_budget["member_allocations"]]
    assert_that(
        pre_member_ids,
        has_item(old_user_id),
        "Budget member allocation should be listed under old_user_id before the remap",
    )
    pre_assistant = assistant_utils.get_assistant_by_id(assistant.id)
    assert_that(
        pre_assistant.created_by.user_id,
        equal_to(old_user_id),
        "Assistant should be owned by old_user_id before the remap",
    )
    pre_conversation = user_utils.get_admin_user_conversation(
        old_user_id, conversation_id
    )
    assert_that(
        pre_conversation.user_id,
        equal_to(old_user_id),
        "Conversation should be owned by old_user_id before the remap",
    )
    pre_workflow = workflow_utils.get_workflow(workflow.id)
    assert_that(
        pre_workflow.created_by.user_id,
        equal_to(old_user_id),
        "Workflow should be owned by old_user_id before the remap",
    )

    # --- remap ---

    user_utils.remap_user(old_user_id, new_user_id)
    owned_conversation_factory.note_remap(new_user_id)

    # --- confirm content now resolves under new_user_id after the remap ---

    assert_that(
        user_utils.get_user_project_names(new_user_id),
        has_item(project_name),
        "Project membership should be listed under new_user_id after the remap",
    )
    post_budget = admin_project_budget_utils.get_budget(budget_id)
    post_member_ids = [a["user_id"] for a in post_budget["member_allocations"]]
    assert_that(
        post_member_ids,
        has_item(new_user_id),
        "Budget member allocation should be listed under new_user_id after the remap",
    )
    assert_that(
        post_member_ids,
        is_not(has_item(old_user_id)),
        "Budget member allocation should no longer be listed under old_user_id",
    )
    post_assistant = assistant_utils.get_assistant_by_id(assistant.id)
    assert_that(
        post_assistant.created_by.user_id,
        equal_to(new_user_id),
        "Assistant should be owned by new_user_id after the remap",
    )
    post_conversation = user_utils.get_admin_user_conversation(
        new_user_id, conversation_id
    )
    assert_that(
        post_conversation.user_id,
        equal_to(new_user_id),
        "Conversation should be owned by new_user_id after the remap",
    )
    post_workflow = workflow_utils.get_workflow(workflow.id)
    assert_that(
        post_workflow.created_by.user_id,
        equal_to(new_user_id),
        "Workflow should be owned by new_user_id after the remap",
    )


@pytest.mark.user
@pytest.mark.api
def test_remap_to_existing_different_user_id_is_rejected_not_merged(
    user_utils, admin_user, second_admin_user
):
    # @case identity-remap-migration_TC_004
    old_user_id = admin_user.user_id
    existing_user_id = second_admin_user.user_id

    with pytest.raises(HTTPError) as exc_info:
        user_utils.remap_user(old_user_id, existing_user_id)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(409),
        "Remapping onto an id that already belongs to a different row should return 409",
    )
    assert_that(
        user_utils.error_text(exc_info.value),
        contains_string("User ID already exists"),
        "Error message should state the id already exists",
    )

    old_detail = user_utils.get_admin_user(old_user_id)
    assert_that(
        old_detail.id,
        equal_to(old_user_id),
        "old_user_id's row should still exist, unmerged, after the rejected remap",
    )
    new_detail = user_utils.get_admin_user(existing_user_id)
    assert_that(
        new_detail.id,
        equal_to(existing_user_id),
        "existing_user_id's row should still exist, unmerged, after the rejected remap",
    )


@pytest.mark.user
@pytest.mark.api
def test_remap_already_migrated_pair_is_idempotent(
    user_utils, admin_user, new_user_id_factory
):
    # @case identity-remap-migration_TC_005
    old_user_id = admin_user.user_id
    new_user_id = new_user_id_factory()
    first = user_utils.remap_user(old_user_id, new_user_id)

    second = user_utils.remap_user(old_user_id, new_user_id)

    assert_that(
        second,
        instance_of(CodeMieUserDetail),
        "Re-running the same remap should still return a CodeMieUserDetail, not an error",
    )
    assert_that(
        second.id,
        equal_to(first.id),
        "Re-running the same remap should return the same (already-migrated) user",
    )
    assert_that(
        second.email,
        equal_to(first.email),
        "Re-running the same remap should return the same user's email",
    )


@pytest.mark.user
@pytest.mark.api
def test_default_user_cannot_remap_user(user_utils, default_user_utils, admin_user):
    """A plain user holding none of the admin/maintainer/auditor roles must not be able
    to call the remap endpoint. `maintainer_client` cannot stand in for that actor here:
    the backend's own role normalization sets is_admin on every maintainer, so maintainer
    is proven admin-equivalent (or higher) throughout this suite, never a 403 case
    (see test_platform_roles.py). `default_user_utils` is the fixture this suite already
    uses to prove 403 on the sibling admin user-management endpoints. The target id is a
    bare string, not `new_user_id_factory`: a rejected call never creates a row to clean up.
    """
    old_user_id = admin_user.user_id
    new_user_id = f"autotest-remap-denied-{get_random_name()}"

    status = default_user_utils.remap_user_status_code(old_user_id, new_user_id)

    assert_that(
        status,
        equal_to(403),
        "Default user should be denied access to the remap endpoint",
    )

    old_detail = user_utils.get_admin_user(old_user_id)
    assert_that(
        old_detail.id,
        equal_to(old_user_id),
        "A rejected remap must not rewrite old_user_id's row",
    )


@pytest.mark.user
@pytest.mark.api
def test_remap_when_neither_id_exists_returns_404(user_utils):
    # @case identity-remap-migration_TC_006
    missing_old_id = f"autotest-remap-missing-old-{get_random_name()}"
    missing_new_id = f"autotest-remap-missing-new-{get_random_name()}"

    with pytest.raises(HTTPError) as exc_info:
        user_utils.remap_user(missing_old_id, missing_new_id)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Remapping when neither id exists should return 404, not a silent no-op",
    )
    assert_that(
        user_utils.error_text(exc_info.value),
        contains_string("User not found"),
        "Error message should state the user was not found",
    )


@pytest.mark.user
@pytest.mark.api
def test_remap_old_user_id_ceases_to_resolve(
    user_utils, admin_user, new_user_id_factory
):
    # @case identity-remap-migration_TC_009
    old_user_id = admin_user.user_id
    new_user_id = new_user_id_factory()

    user_utils.remap_user(old_user_id, new_user_id)

    status_code = user_utils.get_admin_user_status_code(old_user_id)
    assert_that(
        status_code,
        equal_to(404),
        "old_user_id should no longer resolve: its row's primary key was rewritten "
        "to new_user_id in place rather than the row being retained as a deactivated record",
    )
