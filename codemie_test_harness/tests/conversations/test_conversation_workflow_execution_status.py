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

"""Workflow execution status/thoughts hydrate on conversation GET (AC-1, AC-4).

Backend fix: GET v1/conversations/{id} now copies execution.overall_status onto the
rehydrated assistant turn as executionStatus, and thoughts[] includes the currently
running/visible workflow state — so the frontend can tell, from a single GET, whether
a workflow turn is still alive (rather than showing an empty answer node) after a
page reload.

Evidence:
- src/codemie/rest_api/models/conversation.py:135 (GeneratedMessage.execution_status)
- src/codemie/service/conversation/history_materializer.py:118 (copied from overall_status)
- src/store/chats.ts:236 (frontend observable: GET v1/conversations/{id} ->
  history[].executionStatus, history[].thoughts[])
"""

import pytest
from codemie_sdk.models.workflow import ExecutionStatus
from hamcrest import assert_that, empty, equal_to, is_not

from codemie_test_harness.tests import CredentialsManager


@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.conversations
@pytest.mark.api
def test_get_conversation_restores_execution_status_and_thoughts(
    assistant,
    conversation_utils,
    workflow_with_assistant,
    workflow_utils,
):
    """AC-1: after a workflow execution finishes, GET v1/conversations/{id} exposes
    history[].executionStatus matching execution.overall_status, and history[].thoughts[]
    is populated for that turn (not empty) — the data a page reload relies on to restore
    progress instead of rendering a blank assistant turn.
    """
    created_assistant = assistant(
        system_prompt="You are the math expert. Do not format output as markdown"
    )
    created_workflow = workflow_with_assistant(created_assistant, "Run")

    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    completed_execution = workflow_utils.create_workflow_execution(
        workflow_id=created_workflow.id,
        user_input="Solve it, only answer: 2+2*2",
        conversation_id=conversation_id,
    )

    conversation_details = conversation_utils.get_conversation_by_id(conversation_id)
    assistant_turn = conversation_details.history[1]

    assert_that(
        assistant_turn.executionStatus,
        equal_to(completed_execution.status.value),
        "history[].executionStatus must mirror execution.overall_status",
    )
    assert_that(
        assistant_turn.thoughts,
        is_not(empty()),
        "history[].thoughts[] must be populated for the turn after reload, not empty",
    )


@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.conversations
@pytest.mark.api
def test_get_conversation_reports_in_progress_execution_status_while_running(
    assistant,
    conversation_utils,
    workflow_with_assistant,
    workflow_utils,
):
    """AC-4: while a workflow turn's execution.overall_status is IN_PROGRESS, GET
    v1/conversations/{id} reports history[].executionStatus == "In Progress" for that
    turn (the value the frontend's refreshWorkflowExecutionIds patch relies on to keep
    inProgress=true for a still-running turn — see
    src/store/__tests__/chats.refreshWorkflowExecutionIds.test.ts:170).

    Polls immediately after creating the execution (before it is given time to
    complete) so the assertion captures a genuine mid-run GET rather than racing a
    fixed sleep.
    """
    created_assistant = assistant(
        system_prompt="You are the math expert. Do not format output as markdown"
    )
    created_workflow = workflow_with_assistant(created_assistant, "Run")

    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    execution, executions_service = workflow_utils.create_workflow_execution_no_wait(
        workflow_id=created_workflow.id,
        user_input="Solve it, only answer: 2+2*2",
        conversation_id=conversation_id,
    )

    timeout = int(CredentialsManager.get_parameter("DEFAULT_TIMEOUT", "120"))
    stop_statuses = {
        ExecutionStatus.IN_PROGRESS,
        ExecutionStatus.SUCCEEDED,
        ExecutionStatus.FAILED,
        ExecutionStatus.ABORTED,
        ExecutionStatus.INTERRUPTED,
    }

    try:
        live_execution = workflow_utils.poll_execution_until_status(
            executions_service, execution.execution_id, stop_statuses, timeout=timeout
        )
        observed_in_progress = (
            live_execution is not None
            and live_execution.status == ExecutionStatus.IN_PROGRESS
        )
        if observed_in_progress:
            # Check the conversation immediately, before wait_for_completion (in
            # finally) drives the run past IN_PROGRESS.
            conversation_details = conversation_utils.get_conversation_by_id(
                conversation_id
            )
            assistant_turn = conversation_details.history[1]
            assert_that(
                assistant_turn.executionStatus,
                equal_to(ExecutionStatus.IN_PROGRESS.value),
                "history[].executionStatus must report 'In Progress' while the "
                "underlying execution is still running",
            )
    finally:
        # Drive the run to completion so it doesn't leak into later tests.
        workflow_utils.wait_for_completion(
            service=executions_service, _id=execution.execution_id
        )

    assert_that(
        observed_in_progress,
        equal_to(True),
        "expected to observe executionStatus == 'In Progress' via GET "
        "v1/conversations/{id} while the workflow turn was still running",
    )
