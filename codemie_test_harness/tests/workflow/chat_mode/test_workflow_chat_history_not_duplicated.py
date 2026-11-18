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

import re

import pytest
from hamcrest import assert_that, equal_to, greater_than, has_length

from codemie_test_harness.tests.test_data.workflow_chat_history_test_data import (
    FIXED_REPLY_SYSTEM_PROMPT,
    workflow_chat_history_data,
)

HISTORY_HEADER = "# Previous Workflow Executions"
CURRENT_REQUEST_HEADER = "## Current Request"
OUTPUT_LABEL = "**Workflow Output:**"
EXECUTION_HEADING = re.compile(r"(?m)^## Execution \d+$")
USER_INPUT_LINE = re.compile(r"(?m)^\*\*User Input:\*\* (.*)$")


@pytest.fixture
def workflow_conversation(assistant, workflow_with_assistant, conversation_utils):
    """Workflow with one assistant state and a workflow conversation for it.

    Yields ``(workflow, conversation_id)``. Teardown best-effort deletes the
    conversation before the workflow fixture removes the workflow.
    """
    created_assistant = assistant(system_prompt=FIXED_REPLY_SYSTEM_PROMPT)
    created_workflow = workflow_with_assistant(created_assistant, "Run")

    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    yield created_workflow, conversation_id

    try:
        conversation_utils.delete_conversation(conversation_id)
    except Exception:
        pass


# @case workflow-chat-recursively-duplicates-previous_TC_001
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.conversations
@pytest.mark.api
def test_workflow_chat_third_execution_holds_each_earlier_input_and_output_once(
    workflow_conversation, workflow_utils
):
    """The history in the third execution prompt lists each earlier input and output once.

    The stored prompt of an execution is its history block followed by the raw user
    input. The history must be built from the raw inputs of the earlier executions,
    not from their stored prompts, or the earlier blocks nest and repeat. User inputs
    are counted on their ``**User Input:**`` lines: a workflow output may quote an
    input in its own text, so a raw count of the input text would be wrong.
    """
    created_workflow, conversation_id = workflow_conversation
    data = workflow_chat_history_data()

    # Step 1-2: two messages, each completed before the next one is sent
    first_execution = workflow_utils.send_workflow_chat_message(
        created_workflow.id, conversation_id, data.first_input
    )
    second_execution = workflow_utils.send_workflow_chat_message(
        created_workflow.id, conversation_id, data.second_input
    )

    # The history renders the output of the latest state of each earlier run
    first_output = workflow_utils.get_last_state_output(
        created_workflow.id, first_execution.execution_id
    )
    second_output = workflow_utils.get_last_state_output(
        created_workflow.id, second_execution.execution_id
    )
    assert_that(len(first_output), greater_than(0), "First execution has no output")
    assert_that(len(second_output), greater_than(0), "Second execution has no output")

    # Step 3: third message, then read its stored prompt
    third_execution = workflow_utils.send_workflow_chat_message(
        created_workflow.id, conversation_id, data.third_input
    )
    prompt = third_execution.prompt

    history, _, current_request = prompt.rpartition(CURRENT_REQUEST_HEADER)
    execution_blocks = EXECUTION_HEADING.split(history)[1:]

    assert_that(
        prompt.count(HISTORY_HEADER),
        equal_to(1),
        "The history block must not be nested inside itself",
    )
    assert_that(
        execution_blocks,
        has_length(2),
        "Two earlier executions must be listed once each",
    )
    first_block, second_block = execution_blocks

    assert_that(
        USER_INPUT_LINE.findall(history),
        has_length(2),
        "The history must hold one user input line per earlier execution",
    )
    assert_that(
        USER_INPUT_LINE.findall(first_block),
        equal_to([data.first_input]),
        "Execution 1 must list only the first user input, once",
    )
    assert_that(
        USER_INPUT_LINE.findall(second_block),
        equal_to([data.second_input]),
        "Execution 2 must list only the second user input, once",
    )
    assert_that(
        first_block.count(OUTPUT_LABEL),
        equal_to(1),
        "Execution 1 must render one workflow output",
    )
    assert_that(
        second_block.count(OUTPUT_LABEL),
        equal_to(1),
        "Execution 2 must render one workflow output",
    )
    assert_that(
        first_block.count(first_output),
        equal_to(1),
        "First workflow output must appear exactly once under Execution 1",
    )
    assert_that(
        second_block.count(second_output),
        equal_to(1),
        "Second workflow output must appear exactly once under Execution 2",
    )
    assert_that(
        current_request.count(data.third_input),
        equal_to(1),
        "The current request must hold the third user input",
    )
