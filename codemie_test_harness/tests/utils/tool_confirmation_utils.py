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

"""Helpers for tool-call confirmation tests that span an orchestrator and its sub-assistants.

A chat and a resume both answer with a concatenated-NDJSON stream. Each chunk may carry a
``thought`` (a step of the run). A step waiting for the user is ``interrupted=True``; a
sub-assistant's steps are nested under the delegation step through ``parent_id``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

import requests
from hamcrest import assert_that, contains_string, equal_to

from codemie_sdk.models.assistant import (
    AssistantChatRequest,
    ToolCallAction,
    ToolCallResumeRequest,
)
from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.test_data.sub_assistant_tool_confirmation_test_data import (
    create_ticket_request,
    unique_ticket_summary,
)
from codemie_test_harness.tests.utils.client_factory import get_client

_NDJSON_MEDIA_TYPE = "application/x-ndjson"
_METHOD_PATTERN = re.compile(r"""['"]?method['"]?\s*[:=]\s*['"]?([A-Za-z]+)""")


@dataclass
class SubAssistantChain:
    """An orchestrator, the sub-assistants below it (top first) and a conversation on it."""

    root: object
    delegates: list
    conversation_id: str

    @property
    def writer(self):
        """The last assistant of the chain, the one that owns the Jira tool."""
        return self.delegates[-1]


@dataclass
class PausedCall:
    """A chain whose last assistant's write call is waiting for a decision."""

    chain: SubAssistantChain
    chunks: list[dict]


def normalize_name(name: Optional[str]) -> str:
    """Letters and digits only, lower case: a step shows an assistant name title-cased
    and with separators changed, so names are compared in this form."""
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def thought_of(chunk: dict) -> dict:
    """The chunk's thought; the final chunk carries ``"thought": null``."""
    return chunk.get("thought") or {}


def read_stream(response) -> list[dict]:
    """Read a streaming response to the end and return its parsed chunks."""
    # Imported here: the conftest imports this module for its fixtures.
    from codemie_test_harness.tests.assistant.tool_permissions.conftest import (
        _iter_stream_chunks,
    )

    return list(_iter_stream_chunks(response))


def thoughts_by_id(chunks: list[dict]) -> dict[str, dict]:
    """Last state of every step the stream carried, by step id."""
    return {
        thought["id"]: thought
        for thought in (thought_of(chunk) for chunk in chunks)
        if thought.get("id")
    }


def waiting_thoughts(chunks: list[dict]) -> list[dict]:
    """Steps that are waiting for the user in the stream (last state ``interrupted=True``)."""
    return [
        thought
        for thought in thoughts_by_id(chunks).values()
        if thought.get("interrupted") is True
    ]


def parent_of(thought: dict, index: dict[str, dict]) -> Optional[dict]:
    """The step ``thought`` is nested under, when it is in ``index``."""
    return index.get(thought.get("parent_id") or "")


def jira_call_method(thought: dict) -> Optional[str]:
    """HTTP method of the Generic Jira Tool call a step shows; None for any other step."""
    input_text = thought.get("input_text") or ""
    if "relative_url" not in input_text:
        return None
    match = _METHOD_PATTERN.search(input_text)
    return match.group(1).upper() if match else None


def final_reply(chunks: list[dict]) -> str:
    """The orchestrator's final reply: ``generated`` of the closing chunk."""
    last = chunks[-1] if chunks else {}
    return last.get("generated") or ""


def error_message(response) -> str:
    """``error.message`` of a platform error body."""
    return json.loads(response.content)["error"]["message"]


def saved_thoughts(conversation_id: str) -> list[dict]:
    """Every step saved in the conversation history, children included.

    Read from the raw conversation JSON: the SDK ``Thought`` model has neither
    ``interrupted`` nor ``aborted``.
    """
    response = requests.get(
        f"{API_DOMAIN}/v1/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {get_client().token}"},
        verify=VERIFY_SSL,
    )
    response.raise_for_status()

    found: list[dict] = []

    def walk(thoughts) -> None:
        for thought in thoughts or []:
            if isinstance(thought, dict):
                found.append(thought)
                walk(thought.get("children"))

    for item in response.json().get("history") or []:
        walk(item.get("thoughts"))
    return found


def start_turn(
    client, assistant_id: str, conversation_id: str, text: str
) -> list[dict]:
    """Send a streamed message and read the stream to the end.

    The backend saves a paused turn before the final chunk, so stopping at the
    interrupted chunk would disconnect the client and an immediate resume would
    be refused.
    """
    response = client.assistants.chat(
        assistant_id,
        AssistantChatRequest(text=text, conversation_id=conversation_id, stream=True),
    )
    return read_stream(response)


def trigger_ticket_creation(chain: SubAssistantChain, seed) -> PausedCall:
    """Ask the orchestrator to have the chain's last assistant create a Jira issue."""
    text = create_ticket_request(
        [assistant.name for assistant in chain.delegates],
        seed,
        unique_ticket_summary(),
    )
    chunks = start_turn(get_client(), chain.root.id, chain.conversation_id, text)
    return PausedCall(chain=chain, chunks=chunks)


def resume_and_read(
    client, assistant_id: str, conversation_id: str, action: ToolCallAction
) -> list[dict]:
    """Resume the waiting call with ``action`` and read the resumed stream to the end."""
    response = client.assistants.resume_tool_call(
        assistant_id,
        ToolCallResumeRequest(
            conversation_id=conversation_id, action=action, stream=True
        ),
    )
    assert_that(
        response.status_code,
        equal_to(200),
        f"POST /resume with action={action.value} must return HTTP 200",
    )
    assert_that(
        response.headers.get("content-type", ""),
        contains_string(_NDJSON_MEDIA_TYPE),
        f"POST /resume with action={action.value} must stream {_NDJSON_MEDIA_TYPE}",
    )
    return read_stream(response)
