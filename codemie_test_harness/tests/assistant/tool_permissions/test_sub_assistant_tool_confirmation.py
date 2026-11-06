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
API test suite — Tool-call confirmation inside sub-assistants.

An orchestrator delegates to a sub-assistant whose tool-call policy needs
confirmation. The sub-assistant's own call must pause under the delegation
step, wait for Allow / Deny on the orchestrator's conversation, and let both
turns finish after the decision.

The write call used throughout is a POST through the Generic Jira Tool; the
read call is a GET. The tool reports a call as safe only for GET, HEAD and
OPTIONS, so under "approve for me" a GET runs unasked and a POST waits.

Tests that need a paused call start from the ``paused_sub_assistant_call``
fixture or from the ``sub_assistant_chain`` factory (both in ``conftest.py``).
"""

from __future__ import annotations

import uuid

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    empty,
    equal_to,
    has_item,
    is_not,
    not_none,
)
from requests import HTTPError

from codemie_sdk.models.assistant import (
    AssistantChatRequest,
    ToolCallAction,
    ToolCallPolicy,
    ToolCallResumeRequest,
    ToolPermissionsConfig,
)
from codemie_test_harness.tests.test_data.sub_assistant_tool_confirmation_test_data import (
    CONVERSATION_ACCESS_DENIED_MESSAGE,
    DENIED_MESSAGE,
    ORCHESTRATOR_REPLY_SYSTEM_PROMPT,
    PLAIN_DELEGATION_REQUEST,
    PLAIN_SUB_ASSISTANT_DESCRIPTION,
    PLAIN_SUB_ASSISTANT_SYSTEM_PROMPT,
    SUB_ASSISTANT_REPLY_MARKER,
    UNAVAILABLE_MESSAGE,
    WAITING_MESSAGE,
    create_ticket_request,
    read_then_create_request,
    refused_resume_requests,
    sub_assistant_policies,
    unique_ticket_summary,
)
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.tool_confirmation_utils import (
    error_message,
    final_reply,
    jira_call_method,
    normalize_name,
    parent_of,
    resume_and_read,
    saved_thoughts,
    start_turn,
    thoughts_by_id,
    trigger_ticket_creation,
    waiting_thoughts,
)

_SAVE_WAIT_SECONDS = 30
_BACKGROUND_WAIT_SECONDS = 240


def _no_waiting_step(thoughts: list[dict]) -> bool:
    return not any(thought.get("interrupted") is True for thought in thoughts)


def _first_waiting(chunks: list[dict]) -> dict:
    waiting = waiting_thoughts(chunks)
    assert_that(
        waiting,
        is_not(empty()),
        "The sub-assistant's write call must pause; the stream held no waiting step",
    )
    return waiting[0]


def _is_executed_jira_call(thought: dict) -> bool:
    """A Jira tool step that ran: finished, neither denied nor still waiting."""
    return (
        jira_call_method(thought) is not None
        and not thought.get("aborted")
        and not thought.get("interrupted")
        and not thought.get("in_progress")
    )


# ---------------------------------------------------------------------------
# TC_001 — the nested write call pauses under the delegation step
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.jira
@pytest.mark.api
def test_sub_assistant_write_call_waits_under_delegation_step(
    paused_sub_assistant_call,
):
    # @case tool-call-confirmation-inside-sub-assistants_TC_001
    chunks = paused_sub_assistant_call.chunks
    writer = paused_sub_assistant_call.chain.writer

    waiting = waiting_thoughts(chunks)
    call = _first_waiting(chunks)
    delegation = parent_of(call, thoughts_by_id(chunks))

    assert_that(
        [thought for thought in waiting if not thought.get("parent_id")],
        empty(),
        "No waiting step may sit at the top level; the orchestrator itself needs no approval",
    )
    assert_that(
        delegation,
        not_none(),
        f"The waiting step's parent_id {call.get('parent_id')!r} must be a step of the stream",
    )
    assert_that(
        normalize_name(delegation.get("author_name")),
        equal_to(normalize_name(writer.name)),
        "The waiting step must be nested under the delegation step of the sub-assistant",
    )
    assert_that(
        call.get("message"),
        equal_to(WAITING_MESSAGE),
        "The waiting step must carry the waiting-for-approval message",
    )
    assert_that(
        call.get("in_progress"),
        equal_to(False),
        "A waiting step is not in progress",
    )
    assert_that(
        jira_call_method(call),
        equal_to("POST"),
        f"The waiting step must be the Jira write call; got input: {call.get('input_text')}",
    )


# ---------------------------------------------------------------------------
# TC_002 — Allow runs the nested call and both turns finish
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.jira
@pytest.mark.api
def test_allow_on_nested_waiting_call_runs_it_and_both_turns_finish(
    client, paused_sub_assistant_call
):
    # @case tool-call-confirmation-inside-sub-assistants_TC_002
    pause = paused_sub_assistant_call
    call = _first_waiting(pause.chunks)
    delegation = parent_of(call, thoughts_by_id(pause.chunks))
    assert_that(delegation, not_none(), "The waiting step must have a delegation step")

    chunks = resume_and_read(
        client, pause.chain.root.id, pause.chain.conversation_id, ToolCallAction.ALLOW
    )

    resumed = thoughts_by_id(chunks).get(call["id"])
    assert_that(
        resumed,
        not_none(),
        "The resumed stream must carry the step that was waiting",
    )
    assert_that(
        bool(resumed.get("interrupted")),
        equal_to(False),
        "After Allow the nested step must no longer wait",
    )
    assert_that(
        bool(resumed.get("aborted")),
        equal_to(False),
        "After Allow the nested step must not be aborted",
    )
    assert_that(
        resumed.get("in_progress"),
        equal_to(False),
        "After Allow the nested step must run to completion",
    )
    assert_that(
        resumed.get("message"),
        is_not(equal_to(WAITING_MESSAGE)),
        "The waiting message must be replaced by the tool result",
    )
    assert_that(
        chunks[-1].get("last"),
        equal_to(True),
        f"The resumed stream must close with last=True; got: {chunks[-1]}",
    )
    assert_that(
        final_reply(chunks).strip(),
        is_not(equal_to("")),
        "The orchestrator must produce its final reply after the sub-assistant finished",
    )

    saved = poll_until(
        lambda: saved_thoughts(pause.chain.conversation_id),
        _no_waiting_step,
        timeout=_SAVE_WAIT_SECONDS,
    )
    assert_that(
        [thought for thought in saved if thought.get("interrupted") is True],
        empty(),
        "No step may still wait in the saved history after Allow",
    )
    saved_delegation = [t for t in saved if t.get("id") == delegation["id"]]
    assert_that(
        saved_delegation,
        is_not(empty()),
        "The delegation step must be in the saved history",
    )
    assert_that(
        saved_delegation[0].get("in_progress"),
        equal_to(False),
        "The sub-assistant's delegation step must be finished after Allow",
    )


# ---------------------------------------------------------------------------
# TC_003 — Deny skips the nested call and both turns finish
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.jira
@pytest.mark.api
def test_deny_on_nested_waiting_call_skips_it_and_both_turns_finish(
    client, paused_sub_assistant_call
):
    # @case tool-call-confirmation-inside-sub-assistants_TC_003
    pause = paused_sub_assistant_call
    writer = pause.chain.writer
    _first_waiting(pause.chunks)

    chunks = resume_and_read(
        client, pause.chain.root.id, pause.chain.conversation_id, ToolCallAction.DENY
    )

    assert_that(
        [t for t in thoughts_by_id(chunks).values() if _is_executed_jira_call(t)],
        empty(),
        "A denied Jira call must not run",
    )
    assert_that(
        chunks[-1].get("last"),
        equal_to(True),
        f"The resumed stream must close with last=True; got: {chunks[-1]}",
    )
    assert_that(
        final_reply(chunks).strip(),
        is_not(equal_to("")),
        "The orchestrator must produce its final reply after the denial",
    )

    saved = poll_until(
        lambda: saved_thoughts(pause.chain.conversation_id),
        _no_waiting_step,
        timeout=_SAVE_WAIT_SECONDS,
    )
    denied = [
        t
        for t in saved
        if t.get("message") == DENIED_MESSAGE and t.get("aborted") is True
    ]
    assert_that(
        denied,
        is_not(empty()),
        f"The saved history must hold a step with message '{DENIED_MESSAGE}' and aborted=True. "
        f"Saved steps: {[(t.get('message'), t.get('aborted')) for t in saved]}",
    )
    assert_that(
        bool(denied[0].get("interrupted")),
        equal_to(False),
        "A denied step must no longer wait",
    )
    saved_parent = {t["id"]: t for t in saved if t.get("id")}.get(
        denied[0].get("parent_id")
    )
    assert_that(
        saved_parent,
        not_none(),
        "The denied step must stay nested under a saved step",
    )
    assert_that(
        normalize_name(saved_parent.get("author_name")),
        equal_to(normalize_name(writer.name)),
        "The denied step must stay under the sub-assistant's delegation step",
    )
    assert_that(
        [t for t in saved if t.get("interrupted") is True],
        empty(),
        "No step may still wait in the saved history after Deny",
    )


# ---------------------------------------------------------------------------
# TC_004 — approve-for-me: the read call runs unasked, the write call waits
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.jira
@pytest.mark.api
def test_approve_for_me_sub_assistant_runs_read_call_and_pauses_on_write_call(
    client, sub_assistant_chain, jira_seed_issue
):
    # @case tool-call-confirmation-inside-sub-assistants_TC_004
    chain = sub_assistant_chain(policy=ToolCallPolicy.APPROVE_FOR_ME)

    chunks = start_turn(
        client,
        chain.root.id,
        chain.conversation_id,
        read_then_create_request(
            chain.writer.name, jira_seed_issue, unique_ticket_summary()
        ),
    )

    steps = list(thoughts_by_id(chunks).values())
    reads = [t for t in steps if jira_call_method(t) == "GET"]
    writes = [t for t in steps if jira_call_method(t) == "POST"]

    assert_that(
        [t for t in reads if _is_executed_jira_call(t)],
        is_not(empty()),
        "The read-only Jira call must run to completion without asking",
    )
    assert_that(
        [t for t in reads if t.get("interrupted")],
        empty(),
        "The read-only Jira call must never wait for approval",
    )
    assert_that(
        [
            t
            for t in writes
            if t.get("interrupted") is True and t.get("message") == WAITING_MESSAGE
        ],
        is_not(empty()),
        f"The Jira write call must wait for approval. Write steps: "
        f"{[(t.get('interrupted'), t.get('message')) for t in writes]}",
    )
    assert_that(
        {jira_call_method(t) for t in waiting_thoughts(chunks)},
        equal_to({"POST"}),
        "Only the write call may be waiting",
    )


# ---------------------------------------------------------------------------
# TC_007 — the waiting nested step is saved and still resumes after a reload
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.jira
@pytest.mark.api
def test_waiting_nested_step_survives_reload_and_still_resumes(
    client, paused_sub_assistant_call
):
    # @case tool-call-confirmation-inside-sub-assistants_TC_007
    pause = paused_sub_assistant_call
    streamed = _first_waiting(pause.chunks)
    delegation = parent_of(streamed, thoughts_by_id(pause.chunks))
    assert_that(delegation, not_none(), "The waiting step must have a delegation step")

    # A reload reads the conversation again with a fresh request.
    saved = poll_until(
        lambda: saved_thoughts(pause.chain.conversation_id),
        lambda thoughts: not _no_waiting_step(thoughts),
        timeout=_SAVE_WAIT_SECONDS,
    )
    reloaded = [t for t in saved if t.get("interrupted") is True]
    assert_that(
        [t.get("id") for t in reloaded],
        has_item(streamed["id"]),
        "The saved history must still hold the step that was waiting",
    )
    waiting = next(t for t in reloaded if t["id"] == streamed["id"])
    assert_that(
        waiting.get("parent_id"),
        equal_to(delegation["id"]),
        "The saved waiting step must stay under the delegation step",
    )
    assert_that(
        waiting.get("message"),
        equal_to(WAITING_MESSAGE),
        "The saved waiting step must keep the waiting message",
    )

    chunks = resume_and_read(
        client, pause.chain.root.id, pause.chain.conversation_id, ToolCallAction.ALLOW
    )
    assert_that(
        chunks[-1].get("last"),
        equal_to(True),
        f"The resume after a reload must stream to the end; got: {chunks[-1]}",
    )
    after = poll_until(
        lambda: saved_thoughts(pause.chain.conversation_id),
        _no_waiting_step,
        timeout=_SAVE_WAIT_SECONDS,
    )
    assert_that(
        [t for t in after if t.get("interrupted") is True],
        empty(),
        "No step may still wait after the resume",
    )


# ---------------------------------------------------------------------------
# TC_011 — a sub-assistant stays available under every tool-call policy
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.api
@pytest.mark.parametrize("policy", sub_assistant_policies)
def test_orchestrator_delegates_to_sub_assistant_under_each_policy(
    client, assistant_factory, default_llm, policy
):
    # @case tool-call-confirmation-inside-sub-assistants_TC_011
    sub_assistant = assistant_factory.create(
        llm_model_type=default_llm.base_name,
        system_prompt=PLAIN_SUB_ASSISTANT_SYSTEM_PROMPT,
        description=PLAIN_SUB_ASSISTANT_DESCRIPTION,
        tool_permissions=ToolPermissionsConfig(
            tool_call_policy=policy, allow_override=True
        ),
    )
    orchestrator = assistant_factory.create(
        llm_model_type=default_llm.base_name,
        system_prompt=ORCHESTRATOR_REPLY_SYSTEM_PROMPT,
        assistant_ids=[sub_assistant.id],
    )

    chunks = start_turn(
        client, orchestrator.id, str(uuid.uuid4()), PLAIN_DELEGATION_REQUEST
    )

    delegation_steps = [
        t
        for t in thoughts_by_id(chunks).values()
        if normalize_name(t.get("author_name")) == normalize_name(sub_assistant.name)
    ]
    assert_that(
        delegation_steps,
        is_not(empty()),
        f"A delegation step for the sub-assistant must appear under policy {policy.value}",
    )
    assert_that(
        waiting_thoughts(chunks),
        empty(),
        "A sub-assistant without tools has nothing to confirm",
    )
    assert_that(
        final_reply(chunks),
        contains_string(SUB_ASSISTANT_REPLY_MARKER),
        f"The sub-assistant must answer through the orchestrator under policy {policy.value}",
    )


# ---------------------------------------------------------------------------
# TC_012 — a run that cannot be resumed denies the call and does not run it
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.jira
@pytest.mark.api
def test_background_run_denies_confirmation_needing_call_without_running_it(
    client, sub_assistant_chain, jira_seed_issue
):
    # @case tool-call-confirmation-inside-sub-assistants_TC_012
    chain = sub_assistant_chain()

    response = client.assistants.chat(
        chain.root.id,
        AssistantChatRequest(
            text=create_ticket_request(
                [assistant.name for assistant in chain.delegates],
                jira_seed_issue,
                unique_ticket_summary(),
            ),
            conversation_id=chain.conversation_id,
            stream=False,
            background_task=True,
        ),
    )
    assert_that(
        response.task_id,
        not_none(),
        "A background chat must answer with the id of its task",
    )

    saved = poll_until(
        lambda: saved_thoughts(chain.conversation_id),
        lambda thoughts: any(t.get("message") == UNAVAILABLE_MESSAGE for t in thoughts),
        timeout=_BACKGROUND_WAIT_SECONDS,
        interval=5,
    )

    refused = [t for t in saved if t.get("message") == UNAVAILABLE_MESSAGE]
    assert_that(
        refused,
        is_not(empty()),
        f"The saved history must hold a step with message '{UNAVAILABLE_MESSAGE}'. "
        f"Saved steps: {[(t.get('author_name'), t.get('message')) for t in saved]}",
    )
    assert_that(
        refused[0].get("aborted"),
        equal_to(True),
        "The refused step must end aborted",
    )
    assert_that(
        [t for t in saved if t.get("interrupted") is True],
        empty(),
        "A run that cannot be resumed must not pause",
    )
    jira_calls = [t for t in saved if jira_call_method(t) is not None]
    assert_that(
        [t for t in jira_calls if t.get("aborted") is not True],
        empty(),
        "No Jira call may have run in a run that cannot ask for approval",
    )


# ---------------------------------------------------------------------------
# TC_013 — a refused resume answers 404 / 422 with its message
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("stream, status_code, message", refused_resume_requests)
def test_refused_resume_answers_status_and_message(
    client, conversation_without_pending_call, stream, status_code, message
):
    # @case tool-call-confirmation-inside-sub-assistants_TC_013
    assistant, conversation_id = conversation_without_pending_call

    with pytest.raises(HTTPError) as exc_info:
        client.assistants.resume_tool_call(
            assistant.id,
            ToolCallResumeRequest(
                conversation_id=conversation_id,
                action=ToolCallAction.ALLOW,
                stream=stream,
            ),
        )

    response = exc_info.value.response
    assert_that(
        response.status_code,
        equal_to(status_code),
        f"Resume with stream={stream} and no pending call must answer {status_code}",
    )
    assert_that(
        error_message(response),
        equal_to(message),
        "The refusal must carry its documented message",
    )


# ---------------------------------------------------------------------------
# TC_014 — a user without access to the conversation cannot resume it
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.jira
@pytest.mark.api
def test_resume_by_user_without_conversation_access_answers_403(
    client, regular_client, sub_assistant_chain, jira_seed_issue
):
    """The orchestrator is shared in the project so the second user may read it:
    the refusal under test is the one on the conversation, not on the assistant."""
    # @case tool-call-confirmation-inside-sub-assistants_TC_014
    chain = sub_assistant_chain(shared=True)
    pause = trigger_ticket_creation(chain, jira_seed_issue)
    _first_waiting(pause.chunks)

    with pytest.raises(HTTPError) as exc_info:
        regular_client.assistants.resume_tool_call(
            chain.root.id,
            ToolCallResumeRequest(
                conversation_id=chain.conversation_id,
                action=ToolCallAction.ALLOW,
                stream=True,
            ),
        )

    response = exc_info.value.response
    assert_that(
        response.status_code,
        equal_to(403),
        "A user without access to the conversation must be refused with 403",
    )
    assert_that(
        error_message(response),
        equal_to(CONVERSATION_ACCESS_DENIED_MESSAGE),
        "The refusal must name the conversation, not the assistant",
    )

    chunks = resume_and_read(
        client, chain.root.id, chain.conversation_id, ToolCallAction.ALLOW
    )
    assert_that(
        chunks[-1].get("last"),
        equal_to(True),
        "The pending call must still be resumable by its owner after the refusal",
    )


# ---------------------------------------------------------------------------
# TC_015 — pause and resume work for a sub-assistant of a sub-assistant
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.jira
@pytest.mark.api
def test_pause_and_resume_work_two_delegation_levels_deep(
    client, sub_assistant_chain, jira_seed_issue
):
    # @case tool-call-confirmation-inside-sub-assistants_TC_015
    chain = sub_assistant_chain(depth=2)
    relay, writer = chain.delegates
    pause = trigger_ticket_creation(chain, jira_seed_issue)

    call = _first_waiting(pause.chunks)
    index = thoughts_by_id(pause.chunks)
    inner = parent_of(call, index)
    assert_that(
        inner, not_none(), "The waiting step must be nested under a delegation step"
    )
    outer = parent_of(inner, index)
    assert_that(
        outer,
        not_none(),
        "The inner delegation step must itself be nested under a delegation step",
    )
    assert_that(
        normalize_name(inner.get("author_name")),
        equal_to(normalize_name(writer.name)),
        "The waiting step must sit under the delegation step of the inner sub-assistant",
    )
    assert_that(
        normalize_name(outer.get("author_name")),
        equal_to(normalize_name(relay.name)),
        "The inner delegation step must sit under the delegation step of the outer sub-assistant",
    )
    assert_that(
        bool(outer.get("parent_id")),
        equal_to(False),
        "The outer delegation step must be a top-level step",
    )

    chunks = resume_and_read(
        client, chain.root.id, chain.conversation_id, ToolCallAction.ALLOW
    )
    assert_that(
        chunks[-1].get("last"),
        equal_to(True),
        f"The resumed stream must close with last=True; got: {chunks[-1]}",
    )
    assert_that(
        final_reply(chunks).strip(),
        is_not(equal_to("")),
        "The orchestrator must produce its final reply",
    )

    saved = poll_until(
        lambda: saved_thoughts(chain.conversation_id),
        _no_waiting_step,
        timeout=_SAVE_WAIT_SECONDS,
    )
    assert_that(
        [t for t in saved if t.get("interrupted") is True],
        empty(),
        "No step may still wait in the saved history after Allow",
    )
    for assistant in (relay, writer):
        delegation_steps = [
            t
            for t in saved
            if normalize_name(t.get("author_name")) == normalize_name(assistant.name)
        ]
        assert_that(
            delegation_steps,
            is_not(empty()),
            f"The saved history must hold the delegation step of {assistant.name}",
        )
        assert_that(
            [t for t in delegation_steps if t.get("in_progress")],
            empty(),
            f"The turn of {assistant.name} must be finished after Allow",
        )
