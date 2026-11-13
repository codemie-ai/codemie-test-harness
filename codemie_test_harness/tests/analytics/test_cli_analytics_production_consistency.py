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
sessions still being ingested do not shift the totals between two requests.
"""

import math
from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest
import requests
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    greater_than,
    is_in,
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

MAX_PER_PAGE = 1000
TOOL_USAGE_LIMIT = 20
DETAIL_SAMPLE = 10
MONEY = {"rel": 1e-6, "abs": 0.01}
TOOL_SUCCESS_DEFECT = (
    "known defect: session detail counts tool calls from tool_facts_daily but successes "
    "from at most 20 TOOL/EXEC spans, so it reports a lower success rate than every "
    "aggregate of the same session"
)
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
    return pytest.approx(value, **MONEY)


def _read_all_rows(cli_api, endpoint: str, **params) -> dict:
    """Every row of a paged endpoint, read page by page, with the total it reports."""
    rows, page = [], 0
    while True:
        data = cli_api.get_data(endpoint, page=page, per_page=MAX_PER_PAGE, **params)
        total = data.get("pagination", data)["total_count"]
        rows.extend(data["rows"])
        if len(rows) >= total or not data["rows"]:
            break
        page += 1
    assert_that(len(rows), equal_to(total), f"{endpoint} rows read page by page")
    return {"rows": rows, "total_count": total}


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
    """Closed window [today-8d 00:00, today-1d 00:00) UTC; its data no longer moves."""
    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return {
        "start_date": (today - timedelta(days=8)).isoformat(),
        "end_date": (today - timedelta(days=1)).isoformat(),
    }


@pytest.fixture(scope="module")
def snapshot(cli_api, window) -> dict:
    """Every aggregate endpoint read once for the window."""
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
    data["sessions"] = cli_api.get_data(
        "sessions", page=0, per_page=MAX_PER_PAGE, **window
    )
    if not data["overview"]["kpis"]["total_sessions"]:
        pytest.skip(f"No CLI sessions in the window {window}: nothing to reconcile")
    return data


@pytest.fixture(scope="module")
def all_sessions(snapshot) -> list[dict]:
    """Every session of the window; the window must fit one page to be reconciled row by row."""
    sessions = snapshot["sessions"]
    if sessions["total"] > MAX_PER_PAGE:
        pytest.skip(
            f"{sessions['total']} sessions do not fit one page of {MAX_PER_PAGE}"
        )
    assert_that(len(sessions["sessions"]), equal_to(sessions["total"]))
    return sessions["sessions"]


def _kpis(snapshot) -> dict:
    return snapshot["overview"]["kpis"]


# ── Totals reported by more than one endpoint ─────────────────────────────────


def test_session_count_is_the_same_on_every_endpoint(snapshot):
    """Overview, Cost, Sessions and the Efficiency depth histogram count the same sessions."""
    total = _kpis(snapshot)["total_sessions"]

    assert_that(snapshot["cost"]["kpis"]["total_sessions"], equal_to(total), "cost")
    assert_that(snapshot["sessions"]["total"], equal_to(total), "sessions.total")
    depth = sum(b["count"] for b in snapshot["efficiency"]["session_depth"])
    assert_that(depth, equal_to(total), "sum of efficiency.session_depth")


def test_total_cost_reconciles_across_endpoints_and_breakdowns(snapshot, all_sessions):
    """One total cost: Overview = Cost = Efficiency = Σ by model = Σ by user = Σ sessions."""
    total = _kpis(snapshot)["total_cost_usd"]
    cost = snapshot["cost"]

    assert cost["kpis"]["total_cost_usd"] == _approx(total)
    assert snapshot["efficiency"]["kpis"]["total_cost_usd"] == _approx(total)
    assert sum(r["cost_usd"] for r in cost["cost_by_model"]) == _approx(total)
    assert sum(r["cost_usd"] for r in cost["cost_by_user"]) == _approx(total)
    assert sum(s["cost_usd"] for s in all_sessions) == _approx(total)
    assert cost["kpis"]["avg_cost_per_session"] == _approx(
        total / cost["kpis"]["total_sessions"]
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
    assert sum(r["cost_usd"] for r in chart_rows) == _approx(kpis["total_cost_usd"])

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

    assert_that(dead["count"], equal_to(kpis["dead_sessions"]))
    assert_that(
        dead["pct_of_sessions"], equal_to(_pct(dead["count"], kpis["total_sessions"]))
    )
    if dead["count"]:
        assert dead["avg_cost_per_dead"] == _approx(
            dead["wasted_cost_usd"] / dead["count"]
        )
    assert_that(
        dead["wasted_cost_usd"], less_than_or_equal_to(kpis["total_cost_usd"] + 0.01)
    )
    assert_that(eff["kpis"]["bloat_pct"], equal_to(kpis["bloat_pct"]))
    assert eff["kpis"]["avg_context_per_call"] == _approx(kpis["avg_context_per_call"])
    assert eff["kpis"]["cache_read_cost_usd"] == _approx(kpis["cache_read_cost_usd"])
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
        assert_that(
            row["net_lines"], equal_to(row["lines_added"] - row["lines_removed"]), row
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
    """Paged repositories: correct total_count/has_more and pages that concatenate to the full list."""
    full = [r["repository"] for r in snapshot["repositories_by_name"]["rows"]]
    per_page = max(1, min(5, len(full) // 2 or 1))

    paged, page = [], 0
    while True:
        data = cli_api.get_data("repositories", page=page, per_page=per_page, **window)
        pagination = data["pagination"]
        assert_that(pagination["total_count"], equal_to(len(full)))
        paged.extend(r["repository"] for r in data["rows"])
        assert_that(
            pagination["has_more"], equal_to(len(paged) < len(full)), f"page {page}"
        )
        if not pagination["has_more"]:
            break
        page += 1

    assert_that(paged, equal_to(full))


def test_unattributed_filter_returns_sessions_without_repository(
    cli_api, window, all_sessions
):
    """is_unattributed=true returns exactly the sessions that report no repository."""
    expected = sorted(s["trace_id"] for s in all_sessions if not s["repository"])

    data = cli_api.get_data(
        "sessions", is_unattributed="true", per_page=MAX_PER_PAGE, **window
    )

    assert_that(sorted(s["trace_id"] for s in data["sessions"]), equal_to(expected))


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
        assert _ts(s["start_time"]) <= end, s["trace_id"]


def test_session_pages_are_disjoint_and_contiguous(cli_api, window, snapshot):
    """Pages 0 and 1 of 20 are exactly the first 40 sessions, without repeats or gaps."""
    if snapshot["sessions"]["total"] < 40:
        pytest.skip("fewer than 40 sessions in the window")
    page0 = cli_api.get_data("sessions", page=0, per_page=20, **window)
    page1 = cli_api.get_data("sessions", page=1, per_page=20, **window)
    first40 = cli_api.get_data("sessions", page=0, per_page=40, **window)

    ids = [s["trace_id"] for s in page0["sessions"] + page1["sessions"]]
    assert_that(len(set(ids)), equal_to(40))
    assert_that(ids, equal_to([s["trace_id"] for s in first40["sessions"]]))
    assert_that((page1["page"], page1["per_page"]), equal_to((1, 20)))


def test_session_detail_matches_its_list_row(cli_api, window):
    """The detail of the most expensive sessions repeats the figures of their list rows."""
    rows = cli_api.get_data(
        "sessions", sort_by="cost_usd", per_page=DETAIL_SAMPLE, **window
    )["sessions"]
    assert_that(len(rows), greater_than(0))

    for row in rows:
        detail = cli_api.get_data(f"sessions/{row['trace_id']}")
        assert_that(detail["trace_id"], equal_to(row["trace_id"]))
        actual = {k: detail[k] for k in DETAIL_FIELDS}
        assert_that(
            actual, equal_to({k: row[k] for k in DETAIL_FIELDS}), row["trace_id"]
        )
        assert detail["cost_usd"] == _approx(row["cost_usd"]), row["trace_id"]
        assert_that(
            detail["tool_calls_success"],
            equal_to(sum(t["success_count"] for t in detail["tools"])),
            row["trace_id"],
        )


def test_session_detail_tool_success_matches_its_aggregate(cli_api, window):
    """A session's detail reports the tool calls and success rate the aggregates count for it.

    The session is isolated in the aggregates by a one-second window at its start, its user
    and its repository; only sessions that are alone in that slice are compared. Only the
    known defect is expected to fail: the same call count with a lower detail success rate.
    Any other difference, an error status or a wrong count fails the test.
    """
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

    if not compared:
        pytest.skip("no session with tool calls is alone in its aggregate slice")
    mismatched = [c for c in compared if c[1] != c[2]]
    unexpected = [c for c in mismatched if c[1][0] != c[2][0] or not c[1][1] < c[2][1]]
    assert_that(unexpected, equal_to([]), "(trace_id, detail, aggregate) of mismatches")
    if mismatched:
        pytest.xfail(f"{TOOL_SUCCESS_DEFECT}: {mismatched}")


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
    user = snapshot["user-charts"]["rows"][0]
    params = {**window, "users": user["user_email"]}

    kpis = cli_api.get_data("overview", **params)["kpis"]
    sessions = cli_api.get_data("sessions", per_page=MAX_PER_PAGE, **params)
    cost_users = cli_api.get_data("cost", **params)["cost_by_user"]

    assert_that(
        (kpis["total_sessions"], kpis["total_turns"], kpis["total_tool_calls"]),
        equal_to((user["session_count"], user["turns"], user["tool_calls"])),
    )
    assert kpis["total_cost_usd"] == _approx(user["cost_usd"])
    assert_that(kpis["tool_call_success_rate"], equal_to(user["tool_success_rate"]))
    assert_that(sessions["total"], equal_to(user["session_count"]))
    assert_that(
        {s["user_email"] for s in sessions["sessions"]}, equal_to({user["user_email"]})
    )
    assert_that([r["user_email"] for r in cost_users], equal_to([user["user_email"]]))


def test_repository_filter_returns_exactly_that_repository_row(
    cli_api, window, snapshot
):
    """Filtered by the top repository, Overview and Sessions report exactly its row."""
    repo = _top_repository(snapshot)
    params = {**window, "repositories": repo["repository"]}

    kpis = cli_api.get_data("overview", **params)["kpis"]
    sessions = cli_api.get_data("sessions", per_page=MAX_PER_PAGE, **params)

    assert_that(
        (kpis["total_sessions"], kpis["total_turns"], kpis["total_tool_calls"]),
        equal_to((repo["session_count"], repo["turns"], repo["tool_calls"])),
    )
    assert kpis["total_cost_usd"] == _approx(repo["cost_usd"])
    assert_that(kpis["net_lines"], equal_to(repo["net_lines"]))
    assert_that(kpis["tool_call_success_rate"], equal_to(repo["tool_success_rate"]))
    assert_that(
        {s["repository"] for s in sessions["sessions"]}, equal_to({repo["repository"]})
    )
    assert_that(sessions["total"], equal_to(repo["session_count"]))


def test_branch_filter_returns_that_branchs_sessions(
    cli_api, window, snapshot, all_sessions
):
    """branch= returns exactly the sessions on that branch, as many as its repository rows count."""
    branches = Counter(s["branch"] for s in all_sessions if s["branch"])
    if not branches:
        pytest.skip("no session in the window reports a branch")
    branch, expected = branches.most_common(1)[0]
    branch_rows = [
        b
        for r in snapshot["repositories"]["rows"]
        for b in (r["branches"] or [])
        if b.get("branch") == branch
    ]

    data = cli_api.get_data("sessions", branch=branch, per_page=MAX_PER_PAGE, **window)

    assert_that(data["total"], equal_to(expected))
    assert_that({s["branch"] for s in data["sessions"]}, equal_to({branch}))
    assert_that(sum(b["session_count"] for b in branch_rows), equal_to(expected))


def test_framework_filter_and_framework_labels(cli_api, window, snapshot, all_sessions):
    """Sessions only report known frameworks, and framework= returns exactly that framework's sessions."""
    labels = snapshot["frameworks"]
    used = Counter(s["delivery_framework"] for s in all_sessions)
    for framework in used:
        assert_that(framework, is_in(labels))
    framework, expected = used.most_common(1)[0]

    data = cli_api.get_data(
        "sessions", framework=framework, per_page=MAX_PER_PAGE, **window
    )

    assert_that(data["total"], equal_to(expected))
    assert_that(
        {s["delivery_framework"] for s in data["sessions"]}, equal_to({framework})
    )


def test_search_matches_prompt_repository_or_branch(
    cli_api, window, snapshot, all_sessions
):
    """search= keeps exactly the sessions whose prompt, repository or branch contains the term,
    case-insensitively."""
    term = _top_repository(snapshot)["repository"].split("/")[-1].upper()
    lowered = term.lower()
    expected = sorted(
        s["trace_id"]
        for s in all_sessions
        if lowered in s["prompt"].lower()
        or lowered in (s["repository"] or "").lower()
        or lowered in (s["branch"] or "").lower()
    )

    data = cli_api.get_data("sessions", search=term, per_page=MAX_PER_PAGE, **window)

    assert_that(len(expected), greater_than(0))
    assert_that(sorted(s["trace_id"] for s in data["sessions"]), equal_to(expected))


@pytest.mark.parametrize("period", sorted(TIME_PERIODS))
def test_time_period_selects_the_same_sessions_as_its_date_range(cli_api, period):
    """time_period selects the sessions of the equivalent start_date/end_date range.

    Sessions that started well inside the period (a minute from either edge) must be returned,
    and nothing that started before the period may be."""
    before = datetime.now(timezone.utc)
    data = cli_api.get_data("sessions", time_period=period, per_page=MAX_PER_PAGE)
    if data["total"] > MAX_PER_PAGE:
        pytest.skip(f"{data['total']} sessions in {period} do not fit one page")

    earliest = before - TIME_PERIODS[period]
    if period in DAY_BASED_PERIODS:
        earliest = earliest.replace(hour=0, minute=0, second=0, microsecond=0)
    margin = timedelta(minutes=1)

    def ids(start: datetime, end: datetime) -> set[str]:
        page = cli_api.get_data(
            "sessions",
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            per_page=MAX_PER_PAGE,
        )
        return {s["trace_id"] for s in page["sessions"]}

    returned = {s["trace_id"] for s in data["sessions"]}
    inner = ids(earliest + margin, before - margin)
    # the API rejects an end_date in the future, so the outer range ends at the last instant read
    outer = ids(earliest - margin, datetime.now(timezone.utc))
    assert_that(
        sorted(inner - returned), equal_to([]), "sessions inside the period missing"
    )
    assert_that(
        sorted(returned - outer), equal_to([]), "sessions outside the period returned"
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
