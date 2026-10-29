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

import pytest
from hamcrest import assert_that, equal_to, has_item, is_not
from requests import HTTPError

from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.fixture
def workflow_conversation_execution(
    workflow_with_virtual_assistant, conversation_utils, workflow_utils
):
    """Create a workflow, a workflow conversation, and an execution linked to it.

    Reproduces the preconditions at the API layer: a workflow
    execution whose ``conversation_id`` points to a live conversation.

    Yields a ``(workflow, conversation_id, execution)`` tuple. Teardown
    best-effort deletes the conversation (may already be deleted by the test),
    the execution (may already be gone once its conversation is deleted), then
    the workflow.
    """
    created_workflow = workflow_with_virtual_assistant(get_random_name())

    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    execution = workflow_utils.create_workflow_execution(
        workflow_id=created_workflow.id,
        user_input=f"Say hello {get_random_name()}",
        conversation_id=conversation_id,
    )

    yield created_workflow, conversation_id, execution

    try:
        conversation_utils.delete_conversation(conversation_id)
    except Exception:
        pass
    try:
        workflow_utils.delete_workflow_execution(
            created_workflow.id, execution.execution_id
        )
    except Exception:
        pass
    try:
        workflow_utils.delete_workflow(created_workflow)
    except Exception:
        pass


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_workflow_execution_removed_after_conversation_deleted(
    workflow_conversation_execution, conversation_utils, workflow_utils
):
    """A workflow execution linked to a live conversation must not
    be deletable (400); once its conversation is deleted, the execution no longer
    lingers as an orphaned, permanently-blocked history entry — it is removed.
    """
    created_workflow, conversation_id, execution = workflow_conversation_execution

    with pytest.raises(HTTPError) as exc_info:
        workflow_utils.delete_workflow_execution(
            created_workflow.id, execution.execution_id
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "Expected 400 Bad Request while the execution's conversation still exists",
    )
    assert_that(
        exc_info.value.response.json()["error"]["details"],
        equal_to(
            "This workflow execution is part of a conversation and cannot be deleted. "
        ),
    )

    conversation_utils.delete_conversation(conversation_id)

    remaining_execution_ids = [
        remaining.execution_id
        for remaining in workflow_utils.get_executions(created_workflow)
    ]
    assert_that(
        remaining_execution_ids,
        is_not(has_item(execution.execution_id)),
        "Execution should no longer be listed once its linked conversation is deleted",
    )

    with pytest.raises(HTTPError) as exc_info_get:
        workflow_utils.get_workflow_execution(
            created_workflow.id, execution.execution_id
        )
    assert_that(
        exc_info_get.value.response.status_code,
        equal_to(404),
        "Deleted-conversation execution should no longer be retrievable",
    )
