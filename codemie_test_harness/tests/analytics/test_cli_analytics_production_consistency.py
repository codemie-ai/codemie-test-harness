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

"""Read-only release regression of the CLI Analytics read API on real data.

Every test only reads (GET) and is safe on Production: no project, user or ingest is created.
The figures come from whatever the stand holds, so the tests assert the contracts that tie the
endpoints together instead of fixed values: one session count, one cost and one token total
reported by every endpoint, breakdowns that add up to their totals, filters that return exactly
the rows of their aggregate, and a session detail that agrees with its list row.

All endpoints are read once per module for one closed window ([today-8d, today-1d] UTC) so
sessions still being ingested do not shift the totals between two requests. A shared stand
still changes past windows (other runs ingest back-dated sessions and delete their projects),
so figures that are compared with each other are read while the window does not change (see
_consistent_read).
"""

import math
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Callable, TypeVar

import pytest
import requests
from hamcrest import (
    assert_that,
    close_to,
    contains_string,
    equal_to,
    greater_than,
    is_in,
    less_than,
    less_than_or_equal_to,
    not_,
)

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    INGEST_PREFIX,
    REQUEST_TIMEOUT,
    CliAnalyticsApi,
)

pytestmark = [pytest.mark.cli_analytics, pytest.mark.api, pytest.mark.prod_regression]

T = TypeVar("T")

MAX_PER_PAGE = 1000
CONSISTENT_READ_ATTEMPTS = 3
# The backend caches /users, /user-charts and /cost answers for 30 s per pod
# (CLI_ANALYTICS_DASHBOARD_CACHE_TTL_S) while /overview is live: once the Overview has not
# changed for longer than that, every cached answer was built from the current data.
SETTLE_S = 40
TOOL_USAGE_LIMIT = 20
DETAIL_SAMPLE = 10
MONEY = {"rel": 1e-6, "abs": 0.01}
# Fields the session list row and the detail compute from the same facts. api_call_count and
# ctx_per_call are list-only (the detail model leaves them at 0) and user_email holds the
# developer name in the detail, so they are not compared.
DETAIL_FIELDS = (
    "developer_name",
    "repository",
    "branch",
    "prompt",
    "start_time",
    "duration_ms",
    "model_name",
    "turns",
    "tool_call_count",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "net_lines",
    "delivery_framework",
)
TIME_PERIODS = {
    "last_hour": timedelta(hours=1),
    "last_6_hours": timedelta(hours=6),
    "last_24_hours": timedelta(hours=24),
    "last_7_days": timedelta(days=7),
}
DAY_BASED_PERIODS = {"last_7_days"}


def _pct(part: float, whole: float) -> float:
    """Backend percentage: one decimal, half up; 0.0 for an empty whole."""
    return math.floor(part / whole * 1000 + 0.5) / 10 if whole else 0.0


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _approx(value: float):
    """A money matcher with the tolerance of MONEY: relative to the value, never below a cent."""
    if not isinstance(value, (int, float)):
        return equal_to(value)
    return close_to(value, max(MONEY["rel"] * abs(value), MONEY["abs"]))


class PagesDisagree(AssertionError):
    """The pages of one query do not add up to the total it reports."""


def _read_all_rows(cli_api, endpoint: str, **params) -> dict:
    """Every row of a paged endpoint, read page by page, with the total it reports."""
    rows, totals, page = [], set(), 0
    while True:
        data = cli_api.get_data(endpoint, page=page, per_page=MAX_PER_PAGE, **params)
        total = data.get("pagination", data)["total_count"]
        totals.add(total)
        rows.extend(data["rows"])
        if len(rows) >= total or not data["rows"]:
            break
        page += 1
    if totals != {len(rows)}:
        raise PagesDisagree(f"{endpoint} {params}: {len(rows)} rows, totals {totals}")
    return {"rows": rows, "total_count": total}


def _read_all_sessions(cli_api, live: bool = False, **params) -> list[dict]:
    """Every session of a query, read page by page.

    The pages of a closed window must add up to its total without a repeat. A ``live`` query
    (a period that ends now) gains sessions while it is read, which shifts later pages: a
    session seen twice is kept once and the total is not compared.
    """
    sessions, totals, page = [], set(), 0
    while True:
        data = cli_api.get_data("sessions", page=page, per_page=MAX_PER_PAGE, **params)
        totals.add(data["total"])
        sessions.extend(data["sessions"])
        if len(sessions) >= data["total"] or not data["sessions"]:
            break
        page += 1
    unique = list({s["trace_id"]: s for s in sessions}.values())
    if live:
        return unique
    if totals != {len(sessions)} or len(unique) != len(sessions):
        raise PagesDisagree(
            f"sessions {params}: {len(sessions)} rows ({len(unique)} distinct), "
            f"totals {totals}"
        )
    return sessions


def _session_ids(cli_api, live: bool = False, **params) -> set[str]:
    return {s["trace_id"] for s in _read_all_sessions(cli_api, live, **params)}


_settled = {"state": None, "since": 0.0}


def _settled_state(cli_api, window: dict) -> dict:
    """The window's live Overview KPIs once they have not changed for SETTLE_S seconds.

    The state and the time it was first seen are kept across tests, so a quiet window waits
    once per module; a window that keeps changing fails after a few settle periods.
    """
    deadline = time.monotonic() + CONSISTENT_READ_ATTEMPTS * SETTLE_S
    while True:
        state = cli_api.get_data("overview", **window)["kpis"]
        now = time.monotonic()
        if state != _settled["state"]:
            _settled.update(state=state, since=now)
        remaining = SETTLE_S - (now - _settled["since"])
        if remaining <= 0:
            return state
        if now + remaining > deadline:
            pytest.fail(
                f"The window {window} did not stay unchanged for {SETTLE_S}s: other runs "
                "keep changing it, so its cached and live figures cannot be compared"
            )
        time.sleep(remaining)


def _consistent_read(cli_api, window: dict, read: Callable[[], T]) -> T:
    """``read()`` taken on a settled window, between two identical Overview reads of it.

    Other runs on a shared stand ingest back-dated sessions into past windows and delete their
    projects, which removes sessions again. Figures read on both sides of such a change describe
    different data, and a cached answer can still describe the data before it (SETTLE_S). So
    the read starts once the window has settled and is taken again, at most
    CONSISTENT_READ_ATTEMPTS times, until the window has not changed around it. Pages that
    disagree with their total count as a change only when the window did change; otherwise they
    fail the test. Assertions run once, on that one state of the stand; a window that changes
    during every read fails the test.
    """
    changes = []
    for _ in range(CONSISTENT_READ_ATTEMPTS):
        before = _settled_state(cli_api, window)
        try:
            result, disagreement = read(), None
        except PagesDisagree as error:
            result, disagreement = None, error
        after = cli_api.get_data("overview", **window)["kpis"]
        if after == before:
            if disagreement:
                raise disagreement  # the window did not change: its pages are wrong
            return result
        changes.append((before["total_sessions"], after["total_sessions"]))
    pytest.fail(
        f"The window {window} changed during each of {CONSISTENT_READ_ATTEMPTS} reads "
        f"(sessions before, after: {changes}); its figures cannot be compared"
    )


def _assert_same_sessions(returned: set[str], expected: set[str], what: str) -> None:
    """Fails with the sessions missing from and unexpected in ``returned``, not both lists."""
    assert_that(
        {
            "missing": sorted(expected - returned),
            "unexpected": sorted(returned - expected),
        },
        equal_to({"missing": [], "unexpected": []}),
        what,
    )


def _spend_sessions(snapshot) -> int:
    """Sessions with a cost row: Cost's average spreads the total cost over them, not over all."""
    kpis = snapshot["cost"]["kpis"]
    if not kpis["avg_cost_per_session"]:
        assert_that(kpis["total_cost_usd"] or 0, equal_to(0), "cost without an average")
        return 0
    count = kpis["total_cost_usd"] / kpis["avg_cost_per_session"]
    assert_that(
        abs(count - round(count)),
        less_than(1e-3),
        f"total_cost_usd / avg_cost_per_session = {count} is a whole number of sessions",
    )
    return round(count)


def _top_repository(snapshot) -> dict:
    """The attributed repository with the most sessions; skips when there is none."""
    repo = next(
        (r for r in snapshot["repositories_by_name"]["rows"] if r["repository"]), None
    )
    if repo is None:
        pytest.skip("no session in the window reports a repository")
    return repo


@pytest.fixture(scope="module")
def cli_api(client, cli_analytics_enabled) -> CliAnalyticsApi:
    return CliAnalyticsApi(client)


@pytest.fixture(scope="module")
def window() -> dict:
    """Closed window [today-8d 00:00, today-1d 00:00) UTC; real sessions in it no longer move.

    The harness's own CLI Analytics tests seed back-dated sessions into it (``seed_day_start``:
    today-2, with a day on either side), so compared figures are read on a settled window.
    """
    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return {
        "start_date": (today - timedelta(days=8)).isoformat(),
        "end_date": (today - timedelta(days=1)).isoformat(),
    }


def _read_snapshot(cli_api, window: dict) -> dict:
    data = {
        name: cli_api.get_data(name, **window)
        for name in (
            "overview",
            "cost",
            "efficiency",
            "user-charts",
            "tools",
            "activity",
            "frameworks",
        )
    }
    data["users"] = _read_all_rows(cli_api, "users", **window)
    data["repositories"] = cli_api.get_data(
        "repositories", include_branches=True, **window
    )
    data["repositories_by_name"] = _read_all_rows(cli_api, "repositories", **window)
    data["sessions"] = _read_all_sessions(cli_api, **window)
    return data


@pytest.fixture(scope="module")
def snapshot(cli_api, window) -> dict:
    """Every aggregate endpoint and every session of the window, read in one consistent state."""
    data = _consistent_read(cli_api, window, lambda: _read_snapshot(cli_api, window))
    if not data["overview"]["kpis"]["total_sessions"]:
        pytest.skip(f"No CLI sessions in the window {window}: nothing to reconcile")
    return data


@pytest.fixture(scope="module")
def all_sessions(snapshot) -> list[dict]:
    """Every session of the window, read page by page with the snapshot."""
    return snapshot["sessions"]


def _kpis(snapshot) -> dict:
    return snapshot["overview"]["kpis"]


# ── Totals reported by more than one endpoint ─────────────────────────────────


def test_session_count_is_the_same_on_every_endpoint(snapshot):
    """Overview, Cost, Sessions and the Efficiency depth histogram count the same sessions."""
    total = _kpis(snapshot)["total_sessions"]

    assert_that(snapshot["cost"]["kpis"]["total_sessions"], equal_to(total), "cost")
    assert_that(len(snapshot["sessions"]), equal_to(total), "sessions, every page")
    depth = sum(b["count"] for b in snapshot["efficiency"]["session_depth"])
    assert_that(depth, equal_to(total), "sum of efficiency.session_depth")


def test_total_cost_reconciles_across_endpoints_and_breakdowns(snapshot, all_sessions):
    """One total cost: Overview = Cost = Efficiency = Σ by model = Σ by user = Σ sessions."""
    total = _kpis(snapshot)["total_cost_usd"]
    cost = snapshot["cost"]

    assert_that(cost["kpis"]["total_cost_usd"], _approx(total))
    assert_that(snapshot["efficiency"]["kpis"]["total_cost_usd"], _approx(total))
    assert_that(sum(r["cost_usd"] for r in cost["cost_by_model"]), _approx(total))
    assert_that(sum(r["cost_usd"] for r in cost["cost_by_user"]), _approx(total))
    assert_that(sum(s["cost_usd"] or 0 for s in all_sessions), _approx(total))
    spend_sessions = _spend_sessions(snapshot)
    assert_that(spend_sessions, greater_than(0), "sessions with a cost row")
    assert_that(
        spend_sessions,
        less_than_or_equal_to(cost["kpis"]["total_sessions"]),
        "avg_cost_per_session averages over the sessions with a cost row",
    )


def test_token_totals_reconcile_with_token_kinds_and_sessions(snapshot, all_sessions):
    """total_tokens is the sum of the four token kinds, and each kind sums over the sessions."""
    kpis = _kpis(snapshot)
    kinds = {
        "total_input_tokens": "input_tokens",
        "total_output_tokens": "output_tokens",
        "total_cache_creation_tokens": "cache_creation_tokens",
        "total_cache_read_tokens": "cache_read_tokens",
    }

    assert_that(kpis["total_tokens"], equal_to(sum(kpis[k] for k in kinds)))
    assert_that(
        snapshot["cost"]["kpis"]["total_tokens"], equal_to(kpis["total_tokens"])
    )
    for kpi, field in kinds.items():
        assert_that(sum(s[field] for s in all_sessions), equal_to(kpis[kpi]), kpi)


def test_user_rows_add_up_to_overview_and_pages_match_charts(snapshot):
    """Per-user rows sum to the Overview KPIs; the paged Users table lists the chart rows in order."""
    kpis = _kpis(snapshot)
    chart_rows = snapshot["user-charts"]["rows"]
    users = snapshot["users"]

    for field, kpi in (
        ("session_count", "total_sessions"),
        ("turns", "total_turns"),
        ("tool_calls", "total_tool_calls"),
    ):
        assert_that(sum(r[field] for r in chart_rows), equal_to(kpis[kpi]), field)
    assert_that(sum(r["cost_usd"] for r in chart_rows), _approx(kpis["total_cost_usd"]))

    costs = [r["cost_usd"] for r in chart_rows]
    assert_that(costs, equal_to(sorted(costs, reverse=True)), "rows by cost DESC")
    assert_that(users["total_count"], equal_to(len(chart_rows)))
    assert_that(
        [r["user_email"] for r in users["rows"]],
        equal_to([r["user_email"] for r in chart_rows]),
    )


def test_tool_usage_rows_are_consistent(snapshot):
    """Top tools: at most 20, by calls DESC, success ≤ calls, rate = success/calls, Σ ≤ KPI."""
    rows = snapshot["tools"]["tool_usage"]

    assert_that(len(rows), less_than_or_equal_to(TOOL_USAGE_LIMIT))
    calls = [r["call_count"] for r in rows]
    assert_that(calls, equal_to(sorted(calls, reverse=True)))
    for row in rows:
        assert_that(row["success_count"], less_than_or_equal_to(row["call_count"]), row)
        assert_that(
            row["success_rate"],
            equal_to(_pct(row["success_count"], row["call_count"])),
            row,
        )
    assert_that(sum(calls), less_than_or_equal_to(_kpis(snapshot)["total_tool_calls"]))


def test_activity_heatmap_matches_hour_and_weekday_totals(snapshot):
    """The 7×24 heat map rows sum to by_weekday and its columns to by_hour."""
    activity = snapshot["activity"]
    heat = activity["heat"]

    assert_that((len(heat), {len(row) for row in heat}), equal_to((7, {24})))
    assert_that([sum(row) for row in heat], equal_to(activity["by_weekday"]))
    assert_that(
        [sum(row[h] for row in heat) for h in range(24)], equal_to(activity["by_hour"])
    )


def test_efficiency_figures_match_overview(snapshot):
    """Dead sessions, bloat, context per call and cache-read cost agree with the Overview."""
    kpis = _kpis(snapshot)
    eff = snapshot["efficiency"]
    dead = eff["dead_sessions"]

    spend_sessions = _spend_sessions(snapshot)

    assert_that(dead["count"], equal_to(kpis["dead_sessions"]))
    # A dead session cost money and changed no file: it is one of the sessions with a cost
    # row, and its share is taken of them, the denominator of Cost's average too.
    assert_that(dead["count"], less_than_or_equal_to(spend_sessions))
    assert_that(dead["pct_of_sessions"], equal_to(_pct(dead["count"], spend_sessions)))
    if dead["count"]:
        assert_that(
            dead["avg_cost_per_dead"], _approx(dead["wasted_cost_usd"] / dead["count"])
        )
    assert_that(
        dead["wasted_cost_usd"], less_than_or_equal_to(kpis["total_cost_usd"] + 0.01)
    )
    assert_that(eff["kpis"]["bloat_pct"], equal_to(kpis["bloat_pct"]))
    assert_that(
        eff["kpis"]["avg_context_per_call"], _approx(kpis["avg_context_per_call"])
    )
    assert_that(
        eff["kpis"]["cache_read_cost_usd"], _approx(kpis["cache_read_cost_usd"])
    )
    assert_that(eff["code_changes"]["net_lines"], equal_to(kpis["net_lines"]))
    assert_that(
        eff["code_changes"]["files_changed"], equal_to(kpis["total_files_changed"])
    )


# ── Repositories ──────────────────────────────────────────────────────────────


def test_repository_rows_are_internally_consistent(snapshot, all_sessions):
    """Each (project, repository) row: net = added − removed, rate = success/calls, its branches
    sum to it; the rows, the unattributed bucket included, count every session once, and match
    the per-repository rows of the paged mode."""
    rows = snapshot["repositories"]["rows"]
    assert_that(len(rows), greater_than(0), "repositories in the window")

    for row in rows:
        lines = (row["lines_added"], row["lines_removed"])
        assert_that(
            row["net_lines"],
            equal_to(None if None in lines else lines[0] - lines[1]),
            f"net lines of {row['repository']}: unknown without line data",
        )
        assert_that(
            row["tool_calls_success"], less_than_or_equal_to(row["tool_calls"]), row
        )
        assert_that(
            row["tool_success_rate"],
            equal_to(_pct(row["tool_calls_success"], row["tool_calls"])),
            row["repository"],
        )
        branches = row["branches"] or []
        assert_that(
            sum(b["session_count"] for b in branches),
            equal_to(row["session_count"]),
            f"branches of {row['repository']}",
        )

    assert_that(
        sum(r["session_count"] for r in rows),
        equal_to(_kpis(snapshot)["total_sessions"]),
    )
    unattributed = sum(1 for s in all_sessions if not s["repository"])
    assert_that(
        sum(r["session_count"] for r in rows if not r["repository"]),
        equal_to(unattributed),
    )
    per_name = Counter()
    for row in rows:
        per_name[row["repository"]] += row["session_count"]
    by_name = snapshot["repositories_by_name"]["rows"]
    assert_that(
        {r["repository"]: r["session_count"] for r in by_name}, equal_to(dict(per_name))
    )
    assert_that(len(by_name), equal_to(len(per_name)), "one paged row per repository")


def test_repository_pages_partition_the_full_list(cli_api, window, snapshot):
    """Paged repositories: correct total_count/has_more and pages that concatenate to the full list.

    About four pages, the last one partial, whatever the number of repositories: a fixed small
    page would take hundreds of requests on a busy stand."""
    per_page = len(snapshot["repositories_by_name"]["rows"]) // 4 + 1

    def read():
        full = _read_all_rows(cli_api, "repositories", **window)["rows"]
        pages, page = [], 0
        while True:
            data = cli_api.get_data(
                "repositories", page=page, per_page=per_page, **window
            )
            pages.append(data)
            if not data["pagination"]["has_more"] or not data["rows"]:
                return [r["repository"] for r in full], pages
            page += 1

    full, pages = _consistent_read(cli_api, window, read)

    paged = []
    for number, data in enumerate(pages):
        assert_that(data["pagination"]["total_count"], equal_to(len(full)))
        paged.extend(r["repository"] for r in data["rows"])
        assert_that(
            data["pagination"]["has_more"],
            equal_to(len(paged) < len(full)),
            f"page {number}",
        )
    assert_that(paged, equal_to(full))


def test_unattributed_filter_returns_sessions_without_repository(cli_api, window):
    """is_unattributed=true returns exactly the sessions that report no repository."""
    sessions, returned = _consistent_read(
        cli_api,
        window,
        lambda: (
            _read_all_sessions(cli_api, **window),
            _session_ids(cli_api, is_unattributed="true", **window),
        ),
    )

    expected = {s["trace_id"] for s in sessions if not s["repository"]}
    _assert_same_sessions(returned, expected, "is_unattributed=true")


# ── Sessions list and detail ──────────────────────────────────────────────────


@pytest.mark.parametrize("sort_by", ["start_time", "cost_usd", "ctx_per_call"])
def test_sessions_are_sorted_and_inside_the_window(cli_api, window, sort_by):
    """Sessions come sorted DESC by the requested key and none starts after the window.

    A session belongs to the window by its first hook time; its reported start_time is the
    earliest of that and its OTel activity, so it may precede the window but never follow it."""
    data = cli_api.get_data("sessions", sort_by=sort_by, per_page=200, **window)
    sessions = data["sessions"]
    assert_that(len(sessions), greater_than(0))

    keys = [s[sort_by] for s in sessions]
    non_null_keys = [key for key in keys if key is not None]
    assert_that(
        non_null_keys,
        equal_to(sorted(non_null_keys, reverse=True)),
        f"non-null {sort_by} values sorted DESC: {keys}",
    )
    if len(non_null_keys) != len(keys):
        assert_that(
            keys,
            equal_to([*non_null_keys, *([None] * (len(keys) - len(non_null_keys)))]),
            f"null {sort_by} values trail sortable rows: {keys}",
        )
    end = _ts(window["end_date"])
    for s in sessions:
        assert_that(_ts(s["start_time"]), less_than_or_equal_to(end), s["trace_id"])


def test_session_pages_are_disjoint_and_contiguous(cli_api, window, snapshot):
    """Pages 0 and 1 of 20 are exactly the first 40 sessions, without repeats or gaps."""
    if len(snapshot["sessions"]) < 40:
        pytest.skip("fewer than 40 sessions in the window")
    page0, page1, first40 = _consistent_read(
        cli_api,
        window,
        lambda: tuple(
            cli_api.get_data("sessions", page=page, per_page=per_page, **window)
            for page, per_page in ((0, 20), (1, 20), (0, 40))
        ),
    )

    ids = [s["trace_id"] for s in page0["sessions"] + page1["sessions"]]
    assert_that(len(set(ids)), equal_to(40))
    assert_that(ids, equal_to([s["trace_id"] for s in first40["sessions"]]))
    assert_that((page1["page"], page1["per_page"]), equal_to((1, 20)))


def test_session_detail_matches_its_list_row(cli_api, window):
    """The detail of the most expensive sessions repeats the figures of their list rows."""

    def read():
        rows = cli_api.get_data(
            "sessions", sort_by="cost_usd", per_page=DETAIL_SAMPLE, **window
        )["sessions"]
        return [(row, cli_api.get_data(f"sessions/{row['trace_id']}")) for row in rows]

    pairs = _consistent_read(cli_api, window, read)
    assert_that(len(pairs), greater_than(0))

    for row, detail in pairs:
        assert_that(detail["trace_id"], equal_to(row["trace_id"]))
        actual = {k: detail[k] for k in DETAIL_FIELDS}
        assert_that(
            actual, equal_to({k: row[k] for k in DETAIL_FIELDS}), row["trace_id"]
        )
        assert_that(detail["cost_usd"], _approx(row["cost_usd"]), row["trace_id"])
        assert_that(
            detail["tool_calls_success"],
            equal_to(sum(t["success_count"] for t in detail["tools"])),
            row["trace_id"],
        )


def test_session_detail_tool_success_matches_its_aggregate(cli_api, window):
    """A session's detail reports the tool calls and success rate the aggregates count for it.

    The session is isolated in the aggregates by a one-second window at its start, its user
    and its repository; only sessions that are alone in that slice are compared. The detail,
    its list row and the Overview read the same tool rollup, so any difference fails.
    """

    def read():
        rows = cli_api.get_data("sessions", sort_by="cost_usd", per_page=30, **window)[
            "sessions"
        ]
        compared = []
        for row in rows:
            if not row["tool_call_count"] or not row["repository"]:
                continue
            start = _ts(row["start_time"])
            overview = cli_api.get_data(
                "overview",
                start_date=start.isoformat(),
                end_date=(start + timedelta(seconds=1)).isoformat(),
                users=row["user_email"],
                repositories=row["repository"],
            )["kpis"]
            if overview["total_sessions"] != 1:
                continue
            detail = cli_api.get_data(f"sessions/{row['trace_id']}")
            compared.append(
                (
                    row["trace_id"],
                    (detail["tool_call_count"], detail["tool_success_rate"]),
                    (overview["total_tool_calls"], overview["tool_call_success_rate"]),
                )
            )
            if len(compared) == DETAIL_SAMPLE:
                break
        return compared

    compared = _consistent_read(cli_api, window, read)

    if not compared:
        pytest.skip("no session with tool calls is alone in its aggregate slice")
    mismatched = [c for c in compared if c[1] != c[2]]
    assert_that(
        mismatched,
        equal_to([]),
        "(trace_id, (detail calls, rate), (aggregate calls, rate)) of mismatches",
    )


@pytest.mark.sanity
def test_unknown_session_returns_404(cli_api):
    """A trace id that does not exist answers 404 'Session not found', not an empty session."""
    response = cli_api.request(
        "GET", f"{INGEST_PREFIX}/sessions/00000000-0000-4000-8000-000000000000"
    )

    assert_that(response.status_code, equal_to(404))
    assert_that(response.json()["error"]["message"], equal_to("Session not found"))


# ── Filters ───────────────────────────────────────────────────────────────────


def test_user_filter_returns_exactly_that_users_row(cli_api, window, snapshot):
    """Filtered by the top user, every endpoint reports exactly that user's row."""
    email = snapshot["user-charts"]["rows"][0]["user_email"]
    params = {**window, "users": email}

    user, kpis, sessions, cost_users = _consistent_read(
        cli_api,
        window,
        lambda: (
            next(
                r
                for r in cli_api.get_data("user-charts", **window)["rows"]
                if r["user_email"] == email
            ),
            cli_api.get_data("overview", **params)["kpis"],
            _read_all_sessions(cli_api, **params),
            cli_api.get_data("cost", **params)["cost_by_user"],
        ),
    )

    assert_that(
        (kpis["total_sessions"], kpis["total_turns"], kpis["total_tool_calls"]),
        equal_to((user["session_count"], user["turns"], user["tool_calls"])),
    )
    assert_that(kpis["total_cost_usd"], _approx(user["cost_usd"]))
    assert_that(kpis["tool_call_success_rate"], equal_to(user["tool_success_rate"]))
    assert_that(len(sessions), equal_to(user["session_count"]))
    assert_that({s["user_email"] for s in sessions}, equal_to({user["user_email"]}))
    assert_that([r["user_email"] for r in cost_users], equal_to([user["user_email"]]))


def test_repository_filter_returns_exactly_that_repository_row(
    cli_api, window, snapshot
):
    """Filtered by the top repository, Overview and Sessions report exactly its row."""
    name = _top_repository(snapshot)["repository"]
    params = {**window, "repositories": name}

    repo, kpis, sessions = _consistent_read(
        cli_api,
        window,
        lambda: (
            next(
                r
                for r in _read_all_rows(cli_api, "repositories", **window)["rows"]
                if r["repository"] == name
            ),
            cli_api.get_data("overview", **params)["kpis"],
            _read_all_sessions(cli_api, **params),
        ),
    )

    assert_that(
        (kpis["total_sessions"], kpis["total_turns"], kpis["total_tool_calls"]),
        equal_to((repo["session_count"], repo["turns"], repo["tool_calls"])),
    )
    assert_that(kpis["total_cost_usd"], _approx(repo["cost_usd"]))
    assert_that(kpis["net_lines"], equal_to(repo["net_lines"]))
    assert_that(kpis["tool_call_success_rate"], equal_to(repo["tool_success_rate"]))
    assert_that({s["repository"] for s in sessions}, equal_to({repo["repository"]}))
    assert_that(len(sessions), equal_to(repo["session_count"]))


def test_branch_filter_returns_that_branchs_sessions(cli_api, window, all_sessions):
    """branch= returns exactly the sessions on that branch, as many as its repository rows count."""
    branches = Counter(s["branch"] for s in all_sessions if s["branch"])
    if not branches:
        pytest.skip("no session in the window reports a branch")
    branch = branches.most_common(1)[0][0]

    sessions, repositories, filtered = _consistent_read(
        cli_api,
        window,
        lambda: (
            _read_all_sessions(cli_api, **window),
            cli_api.get_data("repositories", include_branches=True, **window)["rows"],
            _read_all_sessions(cli_api, branch=branch, **window),
        ),
    )

    expected = {s["trace_id"] for s in sessions if s["branch"] == branch}
    branch_rows = [
        b
        for r in repositories
        for b in (r["branches"] or [])
        if b.get("branch") == branch
    ]
    _assert_same_sessions(
        {s["trace_id"] for s in filtered}, expected, f"branch={branch}"
    )
    assert_that({s["branch"] for s in filtered}, equal_to({branch}))
    assert_that(sum(b["session_count"] for b in branch_rows), equal_to(len(expected)))


def test_framework_filter_and_framework_labels(cli_api, window, snapshot, all_sessions):
    """Sessions only report known frameworks, and framework= returns exactly that framework's sessions."""
    labels = snapshot["frameworks"]
    used = Counter(s["delivery_framework"] for s in all_sessions)
    for framework in used:
        assert_that(framework, is_in(labels))
    framework = used.most_common(1)[0][0]

    sessions, filtered = _consistent_read(
        cli_api,
        window,
        lambda: (
            _read_all_sessions(cli_api, **window),
            _read_all_sessions(cli_api, framework=framework, **window),
        ),
    )

    expected = {s["trace_id"] for s in sessions if s["delivery_framework"] == framework}
    _assert_same_sessions(
        {s["trace_id"] for s in filtered}, expected, f"framework={framework}"
    )
    assert_that({s["delivery_framework"] for s in filtered}, equal_to({framework}))


def test_search_matches_prompt_repository_or_branch(cli_api, window, snapshot):
    """search= keeps exactly the sessions whose prompt, repository or branch contains the term,
    case-insensitively."""
    term = _top_repository(snapshot)["repository"].split("/")[-1].upper()
    lowered = term.lower()

    sessions, returned = _consistent_read(
        cli_api,
        window,
        lambda: (
            _read_all_sessions(cli_api, **window),
            _session_ids(cli_api, search=term, **window),
        ),
    )

    expected = {
        s["trace_id"]
        for s in sessions
        if lowered in s["prompt"].lower()
        or lowered in (s["repository"] or "").lower()
        or lowered in (s["branch"] or "").lower()
    }
    assert_that(len(expected), greater_than(0))
    _assert_same_sessions(returned, expected, f"search={term}")


@pytest.mark.parametrize("period", sorted(TIME_PERIODS))
def test_time_period_selects_the_same_sessions_as_its_date_range(cli_api, period):
    """time_period selects the sessions of the equivalent start_date/end_date range.

    Sessions that started well inside the period (a minute from either edge) must be returned,
    and nothing that started before the period may be. The period ends now, so other runs add
    and remove sessions in it while it is read: the range is read before and after, and a
    session that appeared or disappeared in between is not compared."""
    before = datetime.now(timezone.utc)
    earliest = before - TIME_PERIODS[period]
    if period in DAY_BASED_PERIODS:
        earliest = earliest.replace(hour=0, minute=0, second=0, microsecond=0)
    margin = timedelta(minutes=1)

    def ids(start: datetime, end: datetime) -> set[str]:
        return _session_ids(
            cli_api, live=True, start_date=start.isoformat(), end_date=end.isoformat()
        )

    first = ids(earliest - margin, before)
    returned = _session_ids(cli_api, live=True, time_period=period)
    inner = ids(earliest + margin, before - margin)
    # the API rejects an end_date in the future, so the outer range ends at the last instant read
    outer = ids(earliest - margin, datetime.now(timezone.utc))
    moved = first ^ outer  # added or removed while the test read the period

    assert_that(
        sorted(inner - moved - returned),
        equal_to([]),
        "sessions inside the period missing",
    )
    assert_that(
        sorted(returned - moved - outer),
        equal_to([]),
        "sessions outside the period returned",
    )


# ── Contract: rejected input, caching, authentication ──────────────────────────


@pytest.mark.parametrize(
    "endpoint, params, status, message",
    [
        ("overview", {"time_period": "last_decade"}, 400, "Invalid"),
        (
            "overview",
            {"start_date": "2026-02-02T00:00:00Z", "end_date": "2026-01-01T00:00:00Z"},
            400,
            "start_date must be before end_date",
        ),
        ("sessions", {"per_page": 0}, 422, None),
        ("sessions", {"per_page": MAX_PER_PAGE + 1}, 422, None),
        ("sessions", {"page": -1}, 422, None),
        ("sessions", {"sort_by": "developer_name"}, 422, None),
        ("repositories", {"per_page": 0}, 422, None),
    ],
    ids=[
        "unknown-time-period",
        "reversed-dates",
        "per-page-zero",
        "per-page-over-max",
        "negative-page",
        "unsupported-sort",
        "repositories-per-page-zero",
    ],
)
def test_invalid_query_is_rejected(cli_api, endpoint, params, status, message):
    """Invalid filters and paging are rejected with a client error, never answered with data."""
    response = cli_api.request("GET", f"{INGEST_PREFIX}/{endpoint}", params=params)

    assert_that(response.status_code, equal_to(status), response.text[:300])
    assert_that(
        "data" in response.json(), equal_to(False), "error body carries no data"
    )
    if message:
        assert_that(response.text, contains_string(message))


@pytest.mark.sanity
def test_analytics_responses_are_not_publicly_cacheable(cli_api, window):
    """Per-user analytics are marked private, so no shared cache may serve them to another user."""
    response = cli_api.request("GET", f"{INGEST_PREFIX}/overview", params=window)

    assert_that(response.status_code, equal_to(200))
    cache_control = response.headers.get("Cache-Control", "").lower()
    assert_that(cache_control, not_(contains_string("public")))
    assert_that(
        "private" in cache_control or "no-store" in cache_control,
        equal_to(True),
        f"Cache-Control: {cache_control!r}",
    )


@pytest.mark.sanity
@pytest.mark.parametrize("endpoint", ["overview", "sessions", "users"])
def test_unauthenticated_request_gets_no_analytics(cli_analytics_enabled, endpoint):
    """Without a token the API answers 401/403 or redirects to sign-in; no analytics JSON leaks."""
    response = requests.get(
        f"{API_DOMAIN.rstrip('/')}{INGEST_PREFIX}/{endpoint}",
        verify=VERIFY_SSL,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=False,
    )

    assert_that(response.status_code, is_in((301, 302, 303, 307, 308, 401, 403)))
    assert_that(response.text, not_(contains_string('"data"')))
