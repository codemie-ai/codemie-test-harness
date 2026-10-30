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

"""Workflow chat progress survives a page reload (AC-2, AC-3, AC-4).

Frontend fix: after a page reload, ChatPage hydrates the still-running turn from
GET v1/conversations/{id} (executionStatus + thoughts) and useWorkflowExecutionPoll
resumes polling, so the answer node shows an in-progress thought card (or the final
result) instead of being blank. If the state genuinely cannot be restored, a fallback
message is shown instead of an empty node.

Evidence:
- src/pages/chat/components/ChatHistory/ChatAiMessage/ChatAiMessage.tsx (thought
  in_progress -> StatusBadge "In Progress"; showRestoreFailed -> WORKFLOW_PROGRESS_
  RESTORE_FAILED_MESSAGE)
- src/constants/chats.ts (WORKFLOW_PROGRESS_RESTORE_FAILED_MESSAGE = "Workflow
  progress could not be restored.")
- src/store/chats.ts / src/store/__tests__/chats.refreshWorkflowExecutionIds.test.ts
  (refreshWorkflowExecutionIds patches thoughts/response/inProgress in place)
"""

import pytest
from codemie_sdk.models.workflow import ExecutionStatus
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage

_FINAL_EXECUTION_STATUSES = {
    ExecutionStatus.SUCCEEDED,
    ExecutionStatus.FAILED,
    ExecutionStatus.ABORTED,
    ExecutionStatus.INTERRUPTED,
}


@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.conversations
@pytest.mark.ui
@pytest.mark.prod_regression
def test_answer_node_shows_in_progress_thought_card_after_reload(
    page, slow_response_workflow, conversation_utils, workflow_utils
):
    """AC-2: while a workflow step is still running, the currently running step
    renders as an in-progress thought card (StatusBadge label 'In Progress') instead
    of a blank answer node.

    Drives the execution via the API and polls it directly (fast, tight loop) to
    confirm the run is genuinely IN_PROGRESS before opening the chat page, rather than
    racing a real page-reload round trip against a real LLM call — the UI is only
    involved for the actual assertion, on the same GET-conversation hydrate path a
    reload exercises.
    """
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=slow_response_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    execution, executions_service = workflow_utils.create_workflow_execution_no_wait(
        workflow_id=slow_response_workflow.id,
        user_input="Solve it, only answer: 2+2*2",
        conversation_id=conversation_id,
    )

    stop_statuses = {ExecutionStatus.IN_PROGRESS} | _FINAL_EXECUTION_STATUSES
    try:
        live_execution = workflow_utils.poll_execution_until_status(
            executions_service,
            execution.execution_id,
            stop_statuses,
            timeout=60,
            poll_interval=0.2,
        )
        observed_in_progress = (
            live_execution is not None
            and live_execution.status == ExecutionStatus.IN_PROGRESS
        )

        assert_that(
            observed_in_progress,
            equal_to(True),
            "expected the workflow execution to still be IN_PROGRESS before opening "
            "the chat page",
        )

        chat_page = ChatPage(page)
        chat_page.navigate_to(conversation_id)

        chat_page.should_have_in_progress_thought_visible()
    finally:
        try:
            workflow_utils.wait_for_completion(
                service=executions_service, _id=execution.execution_id, timeout=60
            )
        except Exception:
            pass
        try:
            conversation_utils.delete_conversation(conversation_id)
        except Exception:
            pass


@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_workflow_execution_progress_restored_after_reload(
    workflow_chat_reloaded_mid_execution,
):
    """AC-4 (ticket repro): send "hi" to a workflow chat, reload while the execution
    is still running, and verify progress is restored and displayed — the answer node
    is not empty.
    """
    chat_page, _chat_id = workflow_chat_reloaded_mid_execution

    chat_page.should_have_non_blank_workflow_progress()


@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.conversations
@pytest.mark.ui
@pytest.mark.prod_regression
def test_restore_failed_message_shown_when_execution_state_cannot_be_restored(
    page, test_workflow, conversation_utils
):
    """AC-3: when a workflow turn's execution state cannot be restored — no thoughts,
    no output, and an executionStatus that is neither RUNNING nor a terminal
    WORKFLOW_FINAL_STATUSES value (e.g. "Not Started") — the answer node shows
    WORKFLOW_PROGRESS_RESTORE_FAILED_MESSAGE instead of being empty.

    The exact combination of fields required to trigger this fallback (a workflow
    turn stuck in a non-running, non-terminal execution status with empty thoughts
    and output) is not reliably reproducible through timing alone, so the GET
    v1/conversations/{id} response is intercepted and replaced with this real,
    schema-valid payload shape (verbatim field names/casing taken from
    src/store/__tests__/chats.refreshWorkflowExecutionIds.test.ts) — the actual
    shipped frontend code (ChatAiMessage/chatHelpers) still does all the rendering.
    """
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=test_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    try:
        chat_page = ChatPage(page)
        chat_page.intercept_unrestorable_conversation(conversation_id, test_workflow.id)
        chat_page.navigate_to(conversation_id)

        chat_page.should_have_workflow_restore_failed_message_visible()
    finally:
        try:
            conversation_utils.delete_conversation(conversation_id)
        except Exception:
            pass
