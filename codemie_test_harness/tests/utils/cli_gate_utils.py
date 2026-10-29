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

"""Shared pieces of the CLI Analytics project gate tests (payloads, read checks, waits).

Constants and the endpoint combinations E1-E7 live in test_data/cli_analytics_test_data.py.

Absence ("this discarded session was not stored") is black-box evidence only: nothing is observed
within a bounded window, see ABSENCE_WINDOW_S. Row-level proof that a discard writes nothing is
backend testing.
"""

import json
import time
import uuid
from dataclasses import dataclass

from hamcrest import assert_that, empty, equal_to, not_

from codemie_test_harness.ingest_sender import post_ingest
from codemie_test_harness.otlp_builder import (
    PROJECT_KEY,
    build_hook_events,
    build_logs,
    build_metrics,
    build_traces,
    ndjson_bytes,
)
from codemie_test_harness.tests import VERIFY_SSL
from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    ABSENCE_POLL_S,
    ABSENCE_WINDOW_S,
    E7,
    PRESENCE_POLL_S,
    PRESENCE_TIMEOUT_S,
    STABLE_SESSION_FIELDS,
    Combo,
    ContextCase,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name, poll_until
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CT_PROTOBUF,
    INGEST_PREFIX,
    REQUEST_TIMEOUT,
    CliAnalyticsApi,
    Discard,
    IngestClient,
    assert_accepted,
    assert_discard,
    parse_discard_response,
)

_BUILDERS = {"logs": build_logs, "metrics": build_metrics, "traces": build_traces}
# Hook sessions of this process share one prefix, so one search finds them all and no session of
# another run or worker on the shared stand (observe_absence_window).
SESSION_PREFIX = f"autotest-gate-{uuid.uuid4().hex[:8]}-"
_SESSIONS_PAGE = 500


@dataclass
class Batch:
    """One valid request body; session_id/repo are set for hook batches only."""

    body: bytes
    wire_count: int
    session_id: str | None = None
    repo: str | None = None


def make_batch(combo, n=None, names=(), resource_project=None) -> Batch:
    """A valid batch. Hooks: n events (default 4) of a fresh session; OTLP: n records (default 2).
    `names` are explicit codemie_project_name values, cycled over the records."""
    if combo.signal == "event-hooks":
        session_id = f"{SESSION_PREFIX}{uuid.uuid4().hex[:12]}"
        repo = f"autotest/{session_id}"
        events = build_hook_events(session_id, None, "autotest", repo, "gate")
        events = events[: n or 4]
        for i, event in enumerate(events):
            if names:
                event[PROJECT_KEY] = names[i % len(names)]
        return Batch(ndjson_bytes(events), len(events), session_id, repo)
    payload = _BUILDERS[combo.signal](n or 2, list(names), resource_project)
    body = payload.protobuf if combo.ct == CT_PROTOBUF else payload.json
    return Batch(body, payload.wire_count)


def sessions_with(api: CliAnalyticsApi, repo: str) -> list:
    """Rows of the sessions read API whose repository matches `repo`."""
    r = api.request(
        "GET", f"{INGEST_PREFIX}/sessions", params={"search": repo, "per_page": 50}
    )
    assert_that(
        r.status_code, equal_to(200), f"sessions: {r.status_code} {r.text[:200]}"
    )
    return r.json()["data"]["sessions"]


def is_listed(api: CliAnalyticsApi, session_id: str, repo: str) -> bool:
    return any(row["trace_id"] == session_id for row in sessions_with(api, repo))


def listed_with_prefix(api: CliAnalyticsApi, prefix: str) -> set:
    """Ids of every listed session matching `prefix`, in as many requests as the pages need.
    Fails instead of returning a partial set: a truncated read would show a false absence."""
    rows, page = [], 0
    while True:
        r = api.request(
            "GET",
            f"{INGEST_PREFIX}/sessions",
            params={"search": prefix, "per_page": _SESSIONS_PAGE, "page": page},
        )
        assert_that(
            r.status_code, equal_to(200), f"sessions: {r.status_code} {r.text[:200]}"
        )
        data = r.json()["data"]
        rows += data["sessions"]
        if len(rows) >= data["total"]:
            return {row["trace_id"] for row in rows}
        assert_that(
            data["sessions"],
            not_(empty()),
            f"sessions page {page} ended before its total",
        )
        page += 1


def wait_until_listed(
    api: CliAnalyticsApi, sessions: dict, timeout=PRESENCE_TIMEOUT_S
) -> dict:
    """Poll until every {session_id: repo} is listed; returns what is still missing."""
    pending = dict(sessions)

    def _drop_listed() -> dict:
        for session_id, repo in list(pending.items()):
            if is_listed(api, session_id, repo):
                del pending[session_id]
        return dict(pending)

    return poll_until(
        _drop_listed, lambda missing: not missing, timeout, PRESENCE_POLL_S
    )


def observe_absence_window(
    api: CliAnalyticsApi,
    markers: dict,
    leaks: dict,
    last_send_at: float,
    window_s: float = ABSENCE_WINDOW_S,
    poll_s: float = ABSENCE_POLL_S,
) -> None:
    """Observe for `window_s` seconds measured from `last_send_at` (a time.monotonic() value
    taken after the last send), polling at EVERY poll both marker presence and leak absence.

    markers: {session_id: repo} of accepted sessions that must be listed.
    leaks: {discard class name: {session_id: repo}} that must never be listed.
    A leak at any poll fails at once naming its class. Passes only if every marker was listed
    AND the whole window elapsed with no leak. The window is a bounded test heuristic (see
    ABSENCE_WINDOW_S), not an ingestion SLA: "not observed within the window" is all it proves.

    One search per poll by SESSION_PREFIX (the sessions of this process, any project) is checked
    against all ids; every id must carry the prefix, else the search could not see it.
    """
    listed: set = set()
    ids = set(markers) | {sid for sessions in leaks.values() for sid in sessions}
    foreign = sorted(sid for sid in ids if not sid.startswith(SESSION_PREFIX))
    assert_that(foreign, empty(), "sessions not made by make_batch cannot be observed")

    def _poll() -> int:
        stored = listed_with_prefix(api, SESSION_PREFIX)
        listed.update(set(markers) & stored)
        for leak_class, sessions in leaks.items():
            leaked = sorted(set(sessions) & stored)
            assert_that(
                leaked,
                empty(),
                f"discard class {leak_class!r} was stored: {leaked}",
            )
        return len(listed)

    deadline = last_send_at + window_s
    poll_until(
        _poll,
        lambda _: time.monotonic() >= deadline,
        timeout=max(0.0, deadline - time.monotonic()),
        interval=poll_s,
    )
    missing = sorted(set(markers) - listed)
    assert_that(
        missing,
        empty(),
        f"accepted marker sessions were never listed within {window_s}s: {missing}",
    )


# ── Sending, project references, expected outcomes ──────────────────────────────


def post_batch(client, combo: Combo, batch: Batch, project: str | None):
    """POST a batch to its endpoint with the client's token; project None sends no header."""
    return IngestClient(client).post_signal(
        combo.signal, batch.body, combo.ct, project=project
    )


def post_body_to(domain: str, client, combo: Combo, body: bytes, project: str | None):
    """POST a raw body with the client's token to another backend (base URL without /v1)."""
    headers = {
        "Content-Type": combo.ct,
        "Authorization": f"Bearer {client.token}",
    }
    return post_ingest(
        f"{domain.rstrip('/')}{INGEST_PREFIX}/{combo.signal}",
        body,
        headers,
        project,
        VERIFY_SSL,
        REQUEST_TIMEOUT,
    )


def resolve_project(ref: str | None, ctx) -> str | None:
    """Project name of a reference of the test data (see PROJECT_STATES): p_on, p_off, deleted,
    unknown (fresh random name), empty, each with an optional :lower / :upper suffix."""
    if ref is None:
        return None
    name, _, transform = ref.partition(":")
    value = {
        "p_on": ctx.p_on,
        "p_off": ctx.p_off,
        "deleted": ctx.deleted,
        "unknown": get_random_name(),
        "empty": "",
    }[name]
    return getattr(value, transform)() if transform else value


def send_context_case(ctx, case: ContextCase, combo: Combo):
    """Send a fresh batch for a project-context class; returns (response, batch)."""
    batch = make_batch(
        combo,
        names=[resolve_project(ref, ctx) for ref in case.names],
        resource_project=resolve_project(case.resource, ctx),
    )
    response = post_batch(
        ctx.clients[case.sender], combo, batch, resolve_project(case.header, ctx)
    )
    return response, batch


def assert_context_outcome(response, combo: Combo, batch: Batch, reason) -> None:
    """Accepted when reason is None, otherwise HTTP 200 discarding the whole batch for reason."""
    if reason is None:
        assert_accepted(response, combo.signal, combo.ct)
    else:
        assert_discard(response, combo.signal, combo.ct, batch.wire_count, reason)


@dataclass
class StorageProbe:
    markers: dict  # accepted sessions that must be listed: {session_id: repo}
    leaks: dict  # {discard class: {session_id: repo}} that must never be listed
    wire_counts: dict  # {case id: events of the batch sent}
    last_send_at: float  # time.monotonic() after the last send


def send_storage_probe(ctx, cases) -> StorageProbe:
    """Send one full hook session per case (the accepted ones are the markers and the control of
    the same shape, the discarded ones the leak candidates) and assert each reply on the way."""
    markers, leaks, wire_counts = {}, {}, {}
    for case in cases:
        response, batch = send_context_case(ctx, case, E7)
        assert_context_outcome(response, E7, batch, case.reason)
        wire_counts[case.id] = batch.wire_count
        if case.reason is None:
            markers[batch.session_id] = batch.repo
        else:
            leaks[case.id] = {batch.session_id: batch.repo}
    return StorageProbe(markers, leaks, wire_counts, time.monotonic())


@dataclass
class SentBatch:
    batch: Batch
    discard: Discard  # Discard(0, "") when accepted


def send_tracked(client, project, combo: Combo, sender="raw", batch=None) -> SentBatch:
    """Send a batch (a fresh one unless given) and report what the reply discarded. sender:
    "raw" is the plain HTTP sender, "sdk" the SDK method (hook events only)."""
    batch = batch or make_batch(combo)
    if sender == "sdk":
        events = [json.loads(line) for line in batch.body.decode().splitlines()]
        reply = client.analytics.send_cli_hook_events(events, project=project) or {}
        discard = Discard(reply.get("dropped", 0), reply.get("reason", ""))
    else:
        response = post_batch(client, combo, batch, project)
        discard = parse_discard_response(response, combo.signal, combo.ct)
    return SentBatch(batch, discard)


def assert_sent_accepted(sent: SentBatch, what: str) -> None:
    assert_that(
        sent.discard,
        equal_to(Discard(0, "")),
        f"{what}: expected the batch accepted, it was discarded",
    )


def assert_sent_discarded(sent: SentBatch, reason: str, what: str) -> None:
    assert_that(
        sent.discard,
        equal_to(Discard(sent.batch.wire_count, reason)),
        f"{what}: expected the whole batch discarded for {reason}",
    )


# ── Reading sessions back ───────────────────────────────────────────────────────


def listed_session_ids(api: CliAnalyticsApi, repo: str, project=None) -> set:
    """Session ids of the sessions list for a repository (and a project filter)."""
    params = {"search": repo, "per_page": 50}
    if project is not None:
        params["projects"] = project
    r = api.request("GET", f"{INGEST_PREFIX}/sessions", params=params)
    assert_that(
        r.status_code, equal_to(200), f"sessions: {r.status_code} {r.text[:200]}"
    )
    return {row["trace_id"] for row in r.json()["data"]["sessions"]}


def snapshot_session_view(client, project: str, session_id: str, repo: str) -> dict:
    """What a client reads about one session of a project: the status codes of the sessions,
    overview and repositories reads (all filtered by the project, so a change of that project's
    setting could show), whether the session is listed and the stable projection of its row
    (STABLE_SESSION_FIELDS; derived rollup metadata is left out on purpose)."""
    api = CliAnalyticsApi(client)
    by_project = {"projects": project}
    sessions = api.request(
        "GET",
        f"{INGEST_PREFIX}/sessions",
        params={"search": repo, "projects": project, "per_page": 50},
    )
    rows = (
        [
            row
            for row in sessions.json()["data"]["sessions"]
            if row["trace_id"] == session_id
        ]
        if sessions.status_code == 200
        else []
    )
    return {
        "sessions": sessions.status_code,
        "listed": bool(rows),
        "row": {key: rows[0].get(key) for key in STABLE_SESSION_FIELDS}
        if rows
        else None,
        "overview": api.request(
            "GET", f"{INGEST_PREFIX}/overview", params=by_project
        ).status_code,
        "repositories": api.request(
            "GET", f"{INGEST_PREFIX}/repositories", params=by_project
        ).status_code,
    }
