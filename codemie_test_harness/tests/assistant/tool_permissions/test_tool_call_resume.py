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

"""
API test suite — Tool-call confirmation (allow / deny resume)

Every test runs once per research tool (Wikipedia, Google Search, Web
Scrapper) via the ``approval_tool`` fixture (regression).

Covers:
  TC_003  Allow action returns NDJSON stream (AC-3)
  TC_004  Deny action returns NDJSON stream (AC-4)
  TC_007  Both allow and deny paths return StreamingResponse (AC-6)
          Manual approval respected when several research tools
                        are configured on one assistant (AC-4)

All tests require:
  - A conversation that has a pending tool-call checkpoint (``pending_tool_call`` fixture)
"""

from __future__ import annotations


import pytest
from hamcrest import assert_that, equal_to, contains_string, greater_than

from codemie_sdk.models.assistant import ToolCallAction, ToolCallResumeRequest
from codemie_test_harness.tests.enums.tools import ResearchToolName
from codemie_test_harness.tests.test_data.tool_call_permissions_test_data import (
    approval_research_tools,
)
from codemie_test_harness.tests.utils.client_factory import get_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_NDJSON_MEDIA_TYPE = "application/x-ndjson"


def _consume_resume_stream(response) -> list[dict]:
    """Consume a concatenated-NDJSON streaming response and return all parsed chunks."""
    from codemie_test_harness.tests.assistant.tool_permissions.conftest import (
        _iter_stream_chunks,
    )

    return list(_iter_stream_chunks(response))


# ---------------------------------------------------------------------------
# TC_003 — Allow action triggers tool execution and streams LLM continuation
# ---------------------------------------------------------------------------


@pytest.mark.api
@pytest.mark.assistant
def test_resume_allow_returns_ndjson_stream(pending_tool_call):
    """
    POST /resume with action=allow returns HTTP 200 NDJSON stream that
    contains tool execution output followed by the LLM's continued response.

    AC-3: Clicking Allow invokes the tool and the LLM continues streaming.
    """
    client = get_client()
    assistant_id = pending_tool_call["assistant_id"]
    conversation_id = pending_tool_call["conversation_id"]

    request = ToolCallResumeRequest(
        conversation_id=conversation_id,
        action=ToolCallAction.ALLOW,
        stream=True,
    )

    # Step 1: POST /resume — must return HTTP 200 with NDJSON content type
    response = client.assistants.resume_tool_call(assistant_id, request)

    assert_that(
        response.status_code,
        equal_to(200),
        "POST /resume with action=allow must return HTTP 200",
    )
    assert_that(
        response.headers.get("content-type", ""),
        contains_string(_NDJSON_MEDIA_TYPE),
        "POST /resume with action=allow must return application/x-ndjson content-type",
    )

    # Step 2: Consume the stream — must contain at least one chunk, ending with last=True
    chunks = _consume_resume_stream(response)
    assert_that(
        len(chunks),
        greater_than(0),
        "Resume stream must produce at least one NDJSON chunk",
    )

    last_chunk = chunks[-1]
    assert_that(
        last_chunk.get("last"),
        equal_to(True),
        f"Resume stream must close with a chunk where last=True; got last chunk: {last_chunk}",
    )

    # AC-3: tool ran AND LLM continued — both must be present in the stream.
    # Tool execution is represented as a thought with metadata.replay_type="tool"
    # that has finished (in_progress=False). LLM continuation is a thought from
    # "Codemie Thoughts" that is not interrupted.
    non_final = chunks[:-1]
    tool_executed = any(
        chunk.get("thought", {}).get("metadata", {}).get("replay_type") == "tool"
        and not chunk.get("thought", {}).get("in_progress")
        for chunk in non_final
    )
    llm_continued = any(
        chunk.get("thought", {}).get("author_name") == "Codemie Thoughts"
        and not chunk.get("thought", {}).get("interrupted")
        for chunk in non_final
    )
    assert_that(
        tool_executed,
        equal_to(True),
        f"Resume allow stream must contain a completed tool-execution thought. Got: {non_final[:5]}",
    )
    assert_that(
        llm_continued,
        equal_to(True),
        f"Resume allow stream must contain a non-interrupted LLM thought. Got: {non_final[:5]}",
    )


# ---------------------------------------------------------------------------
# TC_004 — Deny action injects denial ToolMessages without executing the tool
# ---------------------------------------------------------------------------


@pytest.mark.api
@pytest.mark.assistant
def test_resume_deny_returns_ndjson_stream_with_aborted_thought(pending_tool_call):
    """
    POST /resume with action=deny returns HTTP 200 NDJSON stream.  The stream
    must contain an aborted thought with message 'Tool call was denied by the user.'
    and the tool must NOT have been executed.

    AC-4: Clicking Deny injects denial ToolMessages for all tool_call_ids without
    executing the tool; the LLM streams a continuation acknowledging the denial.
    """
    _TOOL_CALL_DENIED = "Tool call was denied by the user."

    client = get_client()
    assistant_id = pending_tool_call["assistant_id"]
    conversation_id = pending_tool_call["conversation_id"]

    request = ToolCallResumeRequest(
        conversation_id=conversation_id,
        action=ToolCallAction.DENY,
        stream=True,
    )

    # Step 1: POST /resume with action=deny — must return HTTP 200 NDJSON
    response = client.assistants.resume_tool_call(assistant_id, request)

    assert_that(
        response.status_code,
        equal_to(200),
        "POST /resume with action=deny must return HTTP 200",
    )
    assert_that(
        response.headers.get("content-type", ""),
        contains_string(_NDJSON_MEDIA_TYPE),
        "POST /resume with action=deny must return application/x-ndjson content-type",
    )

    # Step 2: Consume stream — must contain the denial aborted thought
    chunks = _consume_resume_stream(response)
    assert_that(
        len(chunks),
        greater_than(0),
        "Deny resume stream must produce at least one NDJSON chunk",
    )

    # AC-4 observable: denied thought must carry both the denial message AND
    # aborted=True (backend:tool_call_confirmation_mixin.py:~154).
    # Checking only the message text would pass a non-aborted thought that
    # happens to include the denial string — check both fields together.
    denied_message_found = any(
        chunk.get("thought", {}).get("message") == _TOOL_CALL_DENIED
        and chunk.get("thought", {}).get("aborted") is True
        for chunk in chunks
    )
    assert_that(
        denied_message_found,
        equal_to(True),
        f"Resume stream for deny must contain a thought with message "
        f"'{_TOOL_CALL_DENIED}' AND aborted=True. Chunks received: {chunks[:3]}",
    )

    last_chunk = chunks[-1]
    assert_that(
        last_chunk.get("last"),
        equal_to(True),
        f"Deny resume stream must close with a chunk where last=True; got last chunk: {last_chunk}",
    )


# ---------------------------------------------------------------------------
# TC_007 — Both allow and deny paths return StreamingResponse
# ---------------------------------------------------------------------------


@pytest.mark.api
@pytest.mark.assistant
@pytest.mark.parametrize("action", [ToolCallAction.ALLOW, ToolCallAction.DENY])
def test_resume_returns_streaming_response_for_both_actions(
    action: ToolCallAction,
    conversation_utils,
    ask_for_approval_assistant,
    approval_tool,
):
    """
    handle_tool_call_resume() returns StreamingResponse(media_type=NDJSON) for
    both the allow and deny paths.  Each parametrized invocation creates its
    own pending checkpoint so the sub-cases are fully independent.

    AC-6: The resumed stream is processed identically to a regular chat response
    for both Allow and Deny decisions.
    """
    from codemie_test_harness.tests.assistant.tool_permissions.conftest import (
        _trigger_tool_call_interruption,
    )

    client = get_client()
    assistant = ask_for_approval_assistant

    # Each parametrize run needs a fresh pending checkpoint
    conversation = conversation_utils.create_conversation(
        initial_assistant_id=assistant.id, folder=""
    )
    conversation_id = conversation.get("id")

    try:
        interrupted = _trigger_tool_call_interruption(
            assistant.id, conversation_id, approval_tool
        )
        if not interrupted:
            pytest.fail(f"No interruption triggered for action={action.value}.")

        request = ToolCallResumeRequest(
            conversation_id=conversation_id,
            action=action,
            stream=True,
        )
        response = client.assistants.resume_tool_call(assistant.id, request)

        assert_that(
            response.status_code,
            equal_to(200),
            f"POST /resume action={action.value} must return HTTP 200",
        )
        assert_that(
            response.headers.get("content-type", ""),
            contains_string(_NDJSON_MEDIA_TYPE),
            f"POST /resume action={action.value} must return application/x-ndjson",
        )

        chunks = _consume_resume_stream(response)
        assert_that(
            len(chunks),
            greater_than(0),
            f"Resume stream for action={action.value} must produce at least one chunk",
        )
        assert_that(
            chunks[-1].get("last"),
            equal_to(True),
            f"Resume stream for action={action.value} must close with last=True",
        )
    finally:
        try:
            conversation_utils.delete_conversation(conversation_id)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Manual approval with several research tools configured
# ---------------------------------------------------------------------------


@pytest.mark.api
@pytest.mark.assistant
@pytest.mark.parametrize("tool", approval_research_tools)
def test_multi_tool_assistant_interrupts_for_each_research_tool(
    tool: ResearchToolName,
    conversation_utils,
    multi_tool_approval_assistant,
):
    """
    An ASK_FOR_APPROVAL assistant with Wikipedia, Google Search and Web
    Scrapper configured together must pause for approval whichever tool the
    LLM calls, and Deny must prevent the tool from running.

    AC-1/AC-4: Manual approval is respected for assistants with several
    research tools. AC-3: a denied tool call is not executed.
    """
    from codemie_test_harness.tests.assistant.tool_permissions.conftest import (
        _trigger_tool_call_interruption,
    )

    client = get_client()
    assistant = multi_tool_approval_assistant
    conversation = conversation_utils.create_conversation(
        initial_assistant_id=assistant.id, folder=""
    )
    conversation_id = conversation.get("id")

    try:
        interrupted = _trigger_tool_call_interruption(
            assistant.id, conversation_id, tool
        )
        assert_that(
            interrupted,
            equal_to(True),
            f"{tool.value} call must pause for approval under the Manual policy",
        )

        response = client.assistants.resume_tool_call(
            assistant.id,
            ToolCallResumeRequest(
                conversation_id=conversation_id,
                action=ToolCallAction.DENY,
                stream=True,
            ),
        )
        chunks = _consume_resume_stream(response)
        tool_executed = any(
            (chunk.get("thought") or {}).get("metadata", {}).get("replay_type")
            == "tool"
            and not (chunk.get("thought") or {}).get("in_progress")
            and not (chunk.get("thought") or {}).get("aborted")
            for chunk in chunks
        )
        assert_that(
            tool_executed,
            equal_to(False),
            f"Denied {tool.value} call must not be executed. Chunks: {chunks[:5]}",
        )
    finally:
        try:
            conversation_utils.delete_conversation(conversation_id)
        except Exception:
            pass
