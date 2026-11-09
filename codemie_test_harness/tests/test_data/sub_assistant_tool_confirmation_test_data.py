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

"""Test data for tool-call confirmation inside sub-assistants."""

import uuid
from typing import Sequence

import pytest

from codemie_sdk.models.assistant import ToolCallPolicy

# Texts the platform writes into the saved steps and into error bodies.
WAITING_MESSAGE = "Tool call is waiting for user approval."
DENIED_MESSAGE = "Tool call was denied by the user."
UNAVAILABLE_MESSAGE = (
    "Tool call needs user confirmation, which is not available in this channel. "
    "The tool was not run."
)
NO_PENDING_MESSAGE = "No pending tool call found for this conversation."
NOT_STREAMED_MESSAGE = (
    "A tool call resume is always streamed; stream=false is not supported."
)
CONVERSATION_ACCESS_DENIED_MESSAGE = "Conversation not found or access denied."

# Reply a plain sub-assistant gives, so a test can see the sub-assistant ran.
SUB_ASSISTANT_REPLY_MARKER = "SUBASSISTANT_REPLY_OK_7Q2"

JIRA_WRITER_SYSTEM_PROMPT = """
    You are a Jira specialist assistant. When you receive a request, you MUST
    immediately call the Generic Jira Tool with exactly the parameters the
    request gives you.

    CRITICAL RULES:
    1. ALWAYS call the tool for EVERY request - never answer before calling it
    2. Never ask the user for confirmation yourself - just call the tool
    3. After the tool returns, or if the call was denied, report in one
       sentence what happened
"""

JIRA_WRITER_DESCRIPTION = (
    "Jira specialist: reads and creates Jira issues through the Generic Jira Tool"
)

ORCHESTRATOR_SYSTEM_PROMPT = (
    "You are a coordinator assistant without tools of your own. For every request "
    "you MUST delegate the work to your sub-assistant and then report its outcome. "
    "Never answer without delegating."
)

PLAIN_SUB_ASSISTANT_SYSTEM_PROMPT = (
    "You answer every request with exactly this word and nothing else: "
    f"{SUB_ASSISTANT_REPLY_MARKER}"
)

PLAIN_SUB_ASSISTANT_DESCRIPTION = (
    "Answers every request with a fixed marker word; use it for any request"
)

ORCHESTRATOR_REPLY_SYSTEM_PROMPT = (
    "You are a coordinator assistant without tools of your own. For every request "
    "you MUST delegate to your sub-assistant and then give its answer back "
    "verbatim. Never answer without delegating."
)

PLAIN_DELEGATION_REQUEST = (
    "Delegate this request to your sub-assistant and give me its answer verbatim."
)


def unique_ticket_summary() -> str:
    """Summary of a ticket the test asks for; "Autotest" is what the session cleanup sweeps."""
    return f"Autotest sub-assistant confirmation {uuid.uuid4().hex[:8]}"


def create_ticket_request(delegates: Sequence[str], seed, summary: str) -> str:
    """User message: have the last assistant of the ``delegates`` chain create a Jira issue."""
    chain = " -> ".join(f"'{name}'" for name in delegates)
    return (
        f"Delegate this task along the chain of sub-assistants {chain}. The last "
        "assistant of the chain must create a new Jira issue by calling the Generic "
        "Jira Tool with exactly these parameters: relative_url=/rest/api/2/issue "
        "method=POST "
        f"params={{'fields': {{'project': {{'key': '{seed.project_key}'}}, "
        f"'summary': '{summary}', 'description': 'Created by an automated test', "
        "'issuetype': {'name': 'Task'}}}. Then report the result."
    )


def read_then_create_request(delegate: str, seed, summary: str) -> str:
    """User message: the sub-assistant reads a Jira issue first, then creates one."""
    return (
        f"Delegate this task to your sub-assistant '{delegate}', which must do two "
        "steps strictly in order. Step 1: call the Generic Jira Tool with "
        f"relative_url=/rest/api/2/issue/{seed.key} method=GET and wait for its "
        "result. Step 2: only after step 1 has returned, create a new Jira issue by "
        "calling the Generic Jira Tool with relative_url=/rest/api/2/issue "
        "method=POST and params={'fields': {'project': {'key': <the project key "
        "found in fields.project.key of the step 1 result>}, "
        f"'summary': '{summary}', 'description': 'Created by an automated test', "
        "'issuetype': {'name': 'Task'}}}. Do not start step 2 before step 1 has "
        "returned."
    )


# Every tool-call policy a sub-assistant can carry (the orchestrator must keep it).
sub_assistant_policies = [
    pytest.param(ToolCallPolicy.AUTO_APPROVE, id="auto_approve"),
    pytest.param(ToolCallPolicy.APPROVE_FOR_ME, id="approve_for_me"),
    pytest.param(ToolCallPolicy.ASK_FOR_APPROVAL, id="ask_for_approval"),
]

# Resume requests that must be refused: (stream flag, expected status, expected message).
refused_resume_requests = [
    pytest.param(True, 404, NO_PENDING_MESSAGE, id="no_pending_call"),
    pytest.param(False, 422, NOT_STREAMED_MESSAGE, id="stream_false"),
]
