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

"""Workflow chat-mode guard for finished conversations (AC-4).

Creating a new workflow execution against an existing conversation_id is how
workflow chat mode resumes/continues a conversation. Once that conversation
is finished, WorkflowService._get_or_create_conversation must reject the
attempt with 409 instead of silently reusing the finished conversation.
"""

import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.conversations
@pytest.mark.api
def test_resuming_workflow_execution_on_finished_conversation_returns_409(
    assistant,
    conversation_utils,
    workflow_with_assistant,
    workflow_utils,
):
    """Creating a new workflow execution on an already-finished conversation returns 409."""
    created_assistant = assistant(
        system_prompt="You are the math expert. Do not format output as markdown"
    )
    created_workflow = workflow_with_assistant(created_assistant, "Run")

    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    # First execution creates/uses the conversation successfully.
    workflow_utils.create_workflow_execution(
        workflow_id=created_workflow.id,
        user_input="Solve it, only answer: 2+2*2",
        conversation_id=conversation_id,
    )

    conversation_utils.finish_conversation(conversation_id)

    # Resuming/appending to the now-finished conversation must be rejected.
    with pytest.raises(HTTPError) as exc_info:
        workflow_utils.create_workflow_execution(
            workflow_id=created_workflow.id,
            user_input=f"Continue please {get_random_name()}",
            conversation_id=conversation_id,
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(409),
        "Resuming a workflow execution on a finished conversation must return 409",
    )
