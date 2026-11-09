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

"""Fixtures for tool-call confirmation tests."""

from __future__ import annotations

import json
from typing import Generator

import pytest

from codemie_sdk.models.assistant import (
    AssistantChatRequest,
    ToolCallPolicy,
    ToolDetails,
    ToolKitDetails,
    ToolPermissionsConfig,
)
from codemie_test_harness.tests.enums.tools import (
    ProjectManagementTool,
    ResearchToolName,
    Toolkit,
)
from codemie_test_harness.tests.test_data.sub_assistant_tool_confirmation_test_data import (
    JIRA_WRITER_DESCRIPTION,
    JIRA_WRITER_SYSTEM_PROMPT,
    ORCHESTRATOR_SYSTEM_PROMPT,
)
from codemie_test_harness.tests.test_data.tool_call_permissions_test_data import (
    APPROVAL_SYSTEM_PROMPT,
    approval_research_tools,
    get_approval_tool_prompt,
    multi_tool_research_tools,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.tool_confirmation_utils import (
    PausedCall,
    SubAssistantChain,
    trigger_ticket_creation,
)


# ---------------------------------------------------------------------------
# ASK_FOR_APPROVAL assistant fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", params=approval_research_tools)
def approval_tool(request) -> ResearchToolName:
    """Research tool under test; parametrizes every test that depends on it."""
    return request.param


@pytest.fixture(scope="module")
def ask_for_approval_assistant(default_llm, assistant_utils, approval_tool):
    """Create an assistant with ASK_FOR_APPROVAL policy and ``approval_tool``.

    Scoped to ``module`` so the assistant is created once per tool per test
    module and deleted after all tests for that tool complete.
    """
    from codemie_sdk.models.assistant import ToolDetails, ToolKitDetails

    toolkits = [
        ToolKitDetails(
            toolkit="Research",
            tools=[ToolDetails(name=approval_tool.value)],
        )
    ]
    created = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        toolkits=toolkits,
        system_prompt=APPROVAL_SYSTEM_PROMPT,
        tool_permissions=ToolPermissionsConfig(
            tool_call_policy=ToolCallPolicy.ASK_FOR_APPROVAL,
            allow_override=True,
        ),
    )
    yield created
    try:
        get_client().assistants.delete(created.id)
    except Exception:
        pass


@pytest.fixture(scope="module")
def multi_tool_approval_assistant(default_llm, assistant_utils):
    """Create an ASK_FOR_APPROVAL assistant with Wikipedia, Google Search and
    Web Scrapper configured together."""
    from codemie_sdk.models.assistant import ToolDetails, ToolKitDetails

    toolkits = [
        ToolKitDetails(
            toolkit="Research",
            tools=[ToolDetails(name=tool.value) for tool in multi_tool_research_tools],
        )
    ]
    created = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        toolkits=toolkits,
        system_prompt=APPROVAL_SYSTEM_PROMPT,
        tool_permissions=ToolPermissionsConfig(
            tool_call_policy=ToolCallPolicy.ASK_FOR_APPROVAL,
            allow_override=True,
        ),
    )
    yield created
    try:
        get_client().assistants.delete(created.id)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helper: trigger a tool-call interruption and return conversation_id
# ---------------------------------------------------------------------------


def _iter_stream_chunks(response) -> Generator[dict, None, None]:
    """Yield parsed JSON chunks from a concatenated-NDJSON streaming response."""
    decoder = json.JSONDecoder()
    buffer = ""
    try:
        for raw_chunk in response.iter_content(chunk_size=None):
            if not raw_chunk:
                continue
            buffer += (
                raw_chunk.decode("utf-8") if isinstance(raw_chunk, bytes) else raw_chunk
            )
            while buffer.lstrip():
                buffer = buffer.lstrip()
                try:
                    chunk, end = decoder.raw_decode(buffer)
                    buffer = buffer[end:]
                    yield chunk
                except json.JSONDecodeError:
                    break
    finally:
        response.close()


def _trigger_tool_call_interruption(
    assistant_id: str, conversation_id: str, tool: ResearchToolName
) -> bool:
    """Send a ``tool``-triggering message and return True when the stream is interrupted.

    Returns True when ``thought.interrupted=True`` is found in the stream,
    indicating a pending tool-call checkpoint now exists for the conversation.

    The stream is read to the end: the backend saves the paused turn before its
    final chunk, so stopping at the interrupted chunk disconnects the client and
    an immediate resume gets 409 "The paused turn is still being saved".
    """
    client = get_client()
    request = AssistantChatRequest(
        text=get_approval_tool_prompt(tool),
        conversation_id=conversation_id,
        stream=True,
    )
    response = client.assistants.chat(assistant_id, request)

    interrupted = False
    for chunk in _iter_stream_chunks(response):
        thought = chunk.get("thought") or {}
        if thought.get("interrupted") is True:
            interrupted = True

    return interrupted


# ---------------------------------------------------------------------------
# Pending-checkpoint fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def pending_tool_call(
    ask_for_approval_assistant, approval_tool, conversation_utils
) -> Generator[dict, None, None]:
    """Provide a conversation ID that has a pending tool-call checkpoint.

    Creates a new conversation, sends a tool-triggering message, and
    confirms the interrupted-thought event before yielding
    ``{"assistant_id": ..., "conversation_id": ...}``.

    Skips the test if no interruption is detected (LLM did not invoke the tool).
    """
    assistant = ask_for_approval_assistant
    conversation = conversation_utils.create_conversation(
        initial_assistant_id=assistant.id, folder=""
    )
    conversation_id = conversation.get("id")

    interrupted = _trigger_tool_call_interruption(
        assistant.id, conversation_id, approval_tool
    )
    if not interrupted:
        try:
            conversation_utils.delete_conversation(conversation_id)
        except Exception:
            pass
        pytest.fail("No tool-call interruption detected — LLM did not invoke the tool.")

    yield {"assistant_id": assistant.id, "conversation_id": conversation_id}

    try:
        conversation_utils.delete_conversation(conversation_id)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Orchestrator with sub-assistants whose last member owns the Jira tool
# ---------------------------------------------------------------------------


@pytest.fixture()
def sub_assistant_chain(
    assistant_factory, conversation_utils, default_llm, jira_integration
):
    """Factory: build an orchestrator, its sub-assistants and a conversation on it.

    The orchestrator delegates to one sub-assistant, the writer, which owns the
    Jira tool and carries ``policy``. Assistants are deleted by
    ``assistant_factory``; the conversations are deleted here.
    """
    conversation_ids: list[str] = []

    def _build(
        policy: ToolCallPolicy = ToolCallPolicy.ASK_FOR_APPROVAL,
        shared: bool = False,
    ) -> SubAssistantChain:
        writer = assistant_factory.create(
            llm_model_type=default_llm.base_name,
            system_prompt=JIRA_WRITER_SYSTEM_PROMPT,
            description=JIRA_WRITER_DESCRIPTION,
            toolkits=[
                ToolKitDetails(
                    toolkit=Toolkit.PROJECT_MANAGEMENT,
                    tools=[
                        ToolDetails(
                            name=ProjectManagementTool.JIRA,
                            settings=jira_integration,
                        )
                    ],
                )
            ],
            tool_permissions=ToolPermissionsConfig(
                tool_call_policy=policy, allow_override=True
            ),
        )
        delegates = [writer]
        root = assistant_factory.create(
            llm_model_type=default_llm.base_name,
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            assistant_ids=[delegates[0].id],
            shared=shared,
        )
        conversation = conversation_utils.create_conversation(
            initial_assistant_id=root.id, folder=""
        )
        conversation_id = conversation.get("id")
        conversation_ids.append(conversation_id)
        return SubAssistantChain(
            root=root, delegates=delegates, conversation_id=conversation_id
        )

    yield _build

    for conversation_id in conversation_ids:
        try:
            conversation_utils.delete_conversation(conversation_id)
        except Exception:
            pass


@pytest.fixture()
def paused_sub_assistant_call(sub_assistant_chain, jira_seed_issue) -> PausedCall:
    """An orchestrator whose ASK_FOR_APPROVAL sub-assistant has a Jira write call
    waiting for a decision.

    The stream of the turn is read to the end before the fixture yields.
    """
    return trigger_ticket_creation(sub_assistant_chain(), jira_seed_issue)


@pytest.fixture()
def conversation_without_pending_call(
    assistant_factory, conversation_utils, default_llm
) -> Generator[tuple, None, None]:
    """A plain assistant and a conversation on it that has no tool call waiting.

    Yields ``(assistant, conversation_id)``.
    """
    assistant = assistant_factory.create(llm_model_type=default_llm.base_name)
    conversation = conversation_utils.create_conversation(
        initial_assistant_id=assistant.id, folder=""
    )
    conversation_id = conversation.get("id")

    yield assistant, conversation_id

    try:
        conversation_utils.delete_conversation(conversation_id)
    except Exception:
        pass
