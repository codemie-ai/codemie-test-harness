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

"""A CLI session resumed across two ingest batches is one session with combined totals;
a second, distinct session id is not merged into it.

Grounded in src/codemie/repository/cli_analytics/postgres/rollups.py and reader.py
(codemie, read-only sibling repo):
- cost_daily sums input/output/cache tokens per session_id across every ingested usage
  request, whichever batch sent it (get_session_detail_cost / get_sessions: plain SUM).
- session_dims.started_at/last_event_at are at least the MIN/MAX of hook events whose
  event_type is one of the 13 DIMENSION_HOOK_TYPES (agent.session.start/end,
  agent.prompt.submit, agent.tool.start/end/error, ...), merged across every batch of the
  same session_id (ON CONFLICT (session_id) DO UPDATE ... LEAST/GREATEST). This session
  also sends OTLP tool/interaction spans (below), and this environment's observed
  last_event_at has matched a span's own timestamp rather than only a hook dimension
  event's, so this test places the hook agent.session.end event's own timestamp past every
  span it sends (min_session_end_offset_s on build_hook_events) -- making it unambiguously
  the session's last dimension event, and duration_ms exactly computable from that offset,
  regardless of whether span timestamps also feed last_event_at on this environment.
- tool_call_count / tool_calls_success / tools[] come only from `claude_code.tool` /
  `claude_code.tool.execution` OTLP spans (get_session_detail_tools: a spans-only query,
  success_count = count of TOOL_EXECUTION spans with success='true' joined by tool_use_id).
- turns comes from `claude_code.interaction` spans once any tool/exec/interaction span
  exists for the session (rollups.py _NO_SPAN_OF_KIND disables the agent.prompt.submit hook
  fallback for turns_daily AND tool_facts_daily the moment any such span exists) -- hence
  this test also sends interaction spans, or turns would silently stay 0.
- developer_name resolves to the authenticated sender's email (hook_events.user_email /
  session_dims.jwt_email), not the event payload's own developer_name field (see
  get_session_detail_meta's coalesce(jwt_email, dev_name_max, developer_name, 'unknown')).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.otlp_builder import (
    build_hook_events,
    build_interaction_spans,
    build_tool_spans,
)
from codemie_test_harness.tests.utils.analytics_utils import CLI_SESSION_ROLLUP_TIMEOUT
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CliAnalyticsApi,
    INGEST_PREFIX,
)

# Per-batch token counts (arbitrary but distinct, so a totals mismatch names which batch is
# missing): initial run, then the resumed run.
_BATCH_1_TOKENS = {
    "input_tokens": 5,
    "output_tokens": 7,
    "cache_read_tokens": 11,
    "cache_creation_tokens": 13,
}
_BATCH_2_TOKENS = {
    "input_tokens": 17,
    "output_tokens": 19,
    "cache_read_tokens": 23,
    "cache_creation_tokens": 29,
}
_EXPECTED_TOTALS = {
    "input_tokens": _BATCH_1_TOKENS["input_tokens"] + _BATCH_2_TOKENS["input_tokens"],
    "output_tokens": _BATCH_1_TOKENS["output_tokens"]
    + _BATCH_2_TOKENS["output_tokens"],
    "cache_read_tokens": _BATCH_1_TOKENS["cache_read_tokens"]
    + _BATCH_2_TOKENS["cache_read_tokens"],
    "cache_creation_tokens": _BATCH_1_TOKENS["cache_creation_tokens"]
    + _BATCH_2_TOKENS["cache_creation_tokens"],
}
# The tool/exec OTLP spans (build_tool_spans) this test sends start _TOOL_SPANS_START_OFFSET
# into batch2's timeline and run, for 2 calls spaced 2s apart (its own fixed per-call gap),
# each a 1s claude_code.tool span immediately followed by a 0.5s claude_code.tool.execution
# span: the last span ends at _TOOL_SPANS_START_OFFSET + (2 - 1) * 2 + 1 + 0.5 = 5.5s into
# batch2's timeline. _SESSION_END_OFFSET_S forces the hook agent.session.end event's own
# offset past that (plus margin), so it -- not a span -- is unambiguously batch2's last
# dimension event: duration_ms is exactly computable from it, batch2 itself starting
# _RESUME_OFFSET after batch1.
_RESUME_OFFSET = timedelta(seconds=60)
_TOOL_SPANS_START_OFFSET = timedelta(seconds=2)
_SESSION_END_OFFSET_S = 7.0
_EXPECTED_DURATION_MS = int(
    (_RESUME_OFFSET + timedelta(seconds=_SESSION_END_OFFSET_S)).total_seconds() * 1000
)
_EXPECTED_TOOL_CALL_COUNT = 2
_EXPECTED_TOOL_SUCCESS_COUNT = 1  # Bash succeeds, Write errors
_EXPECTED_TOOLS = {
    "Bash": (1, 1),
    "Write": (1, 0),
}  # tool_name -> (call_count, success_count)
_EXPECTED_TURNS = 2

_OTHER_SESSION_TOKENS = {
    "input_tokens": 101,
    "output_tokens": 103,
    "cache_read_tokens": 107,
    "cache_creation_tokens": 109,
}


def _fetch_detail(api: CliAnalyticsApi, trace_id: str) -> dict | None:
    """Raw session detail, or None on a 404 (not rolled up yet). The SDK's
    CliAnalyticsSessionRow ignores turns/tool_call_count/tool_calls_success/tools, so
    those fields can only be read through the raw endpoint."""
    response = api.request("GET", f"{INGEST_PREFIX}/sessions/{trace_id}")
    if response.status_code == 404:
        return None
    assert_that(
        response.status_code,
        equal_to(200),
        f"unexpected status fetching session detail for {trace_id!r}: "
        f"{response.status_code} {response.text[:300]!r}",
    )
    return response.json()["data"]


def _tokens(detail: dict) -> dict:
    return {k: detail.get(k) for k in _BATCH_1_TOKENS}


def _is_fully_rolled_up(detail: dict | None) -> bool:
    return (
        detail is not None
        and detail.get("duration_ms", 0) > 0
        and detail.get("tool_call_count", 0) >= _EXPECTED_TOOL_CALL_COUNT
        and detail.get("turns", 0) >= _EXPECTED_TURNS
    )


@pytest.fixture(scope="module")
def isolated_cli_analytics_project(
    cli_analytics_isolated_environment, create_cli_analytics_project
):
    """A disposable project created only on a stand declared disposable."""
    return create_cli_analytics_project()


@pytest.mark.cli_analytics
@pytest.mark.api
def test_resumed_session_reports_combined_totals_and_a_distinct_session_stays_separate(
    analytics_utils, isolated_cli_analytics_project, client
):
    # @case execute-repeatable-isolated-integration_TC_004
    """One session id is ingested in two batches (an initial run, then a resumed run):
    two prompts/usage requests with non-zero input/output/cache tokens, plus a
    successful and a failing tool call. A second, distinct session id is ingested once
    in the same project and repository as a not-merged negative control.
    """
    project = isolated_cli_analytics_project
    developer_name = client.users.about_me().email
    api = CliAnalyticsApi(client)
    base = datetime.now(timezone.utc)

    session_id = f"autotest-cli-resumed-{uuid.uuid4().hex[:12]}"
    repository = f"autotest/resumed-{uuid.uuid4().hex[:12]}"
    assert session_id not in repository
    tool_calls = [
        {
            "tool_name": "Bash",
            "tool_use_id": f"{session_id}-bash",
            "outcome": "success",
            "success": True,
        },
        {
            "tool_name": "Write",
            "tool_use_id": f"{session_id}-write",
            "outcome": "error",
            "success": False,
        },
    ]

    # Batch 1: the initial run opens the session.
    batch1 = build_hook_events(
        session_id,
        project,
        developer_name,
        repository,
        "Autotest TC-004 resumed session, initial run",
        now=base,
        session_start=True,
        session_end=False,
        **_BATCH_1_TOKENS,
    )
    analytics_utils.ingest_cli_event_hooks(batch1, project=project)

    # The initial run must be rolled up on its own before the resume, so the final totals
    # prove that a later batch is added to an existing session, not ingested together with it.
    initial = poll_until(
        lambda: _fetch_detail(api, session_id),
        lambda d: d is not None and _tokens(d) == _BATCH_1_TOKENS,
        timeout=CLI_SESSION_ROLLUP_TIMEOUT,
        interval=5,
    )
    assert_that(
        _tokens(initial) if initial else None,
        equal_to(_BATCH_1_TOKENS),
        f"initial run of {session_id!r} rolled up alone, last seen detail: {initial}",
    )

    # Batch 2: the resumed run, 60 s later, closes the session and reports the tool calls.
    resumed_at = base + _RESUME_OFFSET
    batch2 = build_hook_events(
        session_id,
        project,
        developer_name,
        repository,
        "Autotest TC-004 resumed session, resumed run",
        now=resumed_at,
        batch_id="-resumed",
        session_start=False,
        session_end=True,
        tool_calls=[
            {
                "tool_name": c["tool_name"],
                "tool_use_id": c["tool_use_id"],
                "outcome": c["outcome"],
            }
            for c in tool_calls
        ],
        min_session_end_offset_s=_SESSION_END_OFFSET_S,
        **_BATCH_2_TOKENS,
    )
    analytics_utils.ingest_cli_event_hooks(batch2, project=project)

    # The real tool outcomes and the turn count both need OTLP spans: see the module docstring.
    tool_spans = build_tool_spans(
        session_id,
        [
            {
                "tool_name": c["tool_name"],
                "tool_use_id": c["tool_use_id"],
                "success": c["success"],
            }
            for c in tool_calls
        ],
        resource_project=project,
        now=resumed_at + _TOOL_SPANS_START_OFFSET,
    )
    analytics_utils.ingest_cli_otlp_traces(tool_spans, project=project)
    interaction_spans = build_interaction_spans(
        session_id, _EXPECTED_TURNS, resource_project=project, now=base
    )
    analytics_utils.ingest_cli_otlp_traces(interaction_spans, project=project)

    # Negative control: a second, distinct session in the same project, seeded once.
    other_session_id = f"autotest-cli-other-{uuid.uuid4().hex[:12]}"
    other_batch = build_hook_events(
        other_session_id,
        project,
        developer_name,
        repository,
        "Autotest TC-004 unrelated session",
        now=base,
        **_OTHER_SESSION_TOKENS,
    )
    analytics_utils.ingest_cli_event_hooks(other_batch, project=project)

    analytics_utils.wait_for_cli_session(session_id, timeout=CLI_SESSION_ROLLUP_TIMEOUT)
    analytics_utils.wait_for_cli_session_end(
        session_id, timeout=CLI_SESSION_ROLLUP_TIMEOUT
    )
    other_session = analytics_utils.wait_for_cli_session(
        other_session_id, timeout=CLI_SESSION_ROLLUP_TIMEOUT
    )

    # Tool/turn facts are span-derived and may lag the hook-based rollup above, so poll the
    # raw endpoint separately until both are present, failing with the last seen body instead
    # of silently asserting on a stale/zeroed detail.
    detail = poll_until(
        lambda: _fetch_detail(api, session_id),
        _is_fully_rolled_up,
        timeout=CLI_SESSION_ROLLUP_TIMEOUT,
        interval=5,
    )
    assert_that(
        _is_fully_rolled_up(detail),
        equal_to(True),
        f"session {session_id!r} tool/turn rollup incomplete after {CLI_SESSION_ROLLUP_TIMEOUT}s, "
        f"last seen detail: {detail}",
    )

    assert_that(detail["trace_id"], equal_to(session_id), f"detail: {detail}")
    assert_that(detail["developer_name"], equal_to(developer_name), f"detail: {detail}")
    assert_that(
        {k: detail[k] for k in _EXPECTED_TOTALS},
        equal_to(_EXPECTED_TOTALS),
        f"token/cache totals across the resumed session's two batches, detail: {detail}",
    )
    assert_that(
        detail["turns"], equal_to(_EXPECTED_TURNS), f"turn count, detail: {detail}"
    )
    assert_that(
        detail["tool_call_count"],
        equal_to(_EXPECTED_TOOL_CALL_COUNT),
        f"tool call count, detail: {detail}",
    )
    assert_that(
        detail["tool_calls_success"],
        equal_to(_EXPECTED_TOOL_SUCCESS_COUNT),
        f"tool success count, detail: {detail}",
    )
    assert_that(
        {
            t["tool_name"]: (t["call_count"], t["success_count"])
            for t in detail["tools"]
        },
        equal_to(_EXPECTED_TOOLS),
        f"per-tool call/success counts, detail: {detail}",
    )
    assert_that(
        detail["duration_ms"],
        equal_to(_EXPECTED_DURATION_MS),
        f"session duration, detail: {detail}",
    )

    # List API: the project holds exactly the two seeded sessions, the resumed one as a
    # single row with the combined totals.
    listing = analytics_utils.get_cli_analytics_sessions(projects=project).data
    listed_ids = sorted(s.trace_id for s in listing.sessions)
    assert_that(
        (listing.total, listed_ids),
        equal_to((2, sorted((session_id, other_session_id)))),
        f"sessions list for project {project!r}: each seeded session exactly once, nothing else",
    )
    by_trace_id = {s.trace_id: s for s in listing.sessions}
    listed = by_trace_id[session_id]
    assert_that(
        {
            "input_tokens": listed.input_tokens,
            "output_tokens": listed.output_tokens,
            "cache_read_tokens": listed.cache_read_tokens,
            "cache_creation_tokens": listed.cache_creation_tokens,
            "duration_ms": listed.duration_ms,
        },
        equal_to({**_EXPECTED_TOTALS, "duration_ms": _EXPECTED_DURATION_MS}),
        f"sessions list row for the resumed session {session_id!r}: {listed}",
    )

    # Negative control: the second session is its own row with its own totals, not merged.
    assert_that(other_session.trace_id, equal_to(other_session_id))
    assert_that(
        {
            "input_tokens": other_session.input_tokens,
            "output_tokens": other_session.output_tokens,
            "cache_read_tokens": other_session.cache_read_tokens,
            "cache_creation_tokens": other_session.cache_creation_tokens,
        },
        equal_to(_OTHER_SESSION_TOKENS),
        f"the unrelated session's own totals must not include the resumed session's events: {other_session}",
    )
    other_listed = by_trace_id[other_session_id]
    assert_that(
        {
            "input_tokens": other_listed.input_tokens,
            "output_tokens": other_listed.output_tokens,
            "cache_read_tokens": other_listed.cache_read_tokens,
            "cache_creation_tokens": other_listed.cache_creation_tokens,
        },
        equal_to(_OTHER_SESSION_TOKENS),
        f"sessions list row for the unrelated session {other_session_id!r}: {other_listed}",
    )
    # And the resumed session's own totals were not inflated by the unrelated session either.
    assert_that(
        {k: detail[k] for k in _EXPECTED_TOTALS},
        equal_to(_EXPECTED_TOTALS),
        f"the resumed session's totals must not have absorbed the unrelated session's events: {detail}",
    )
