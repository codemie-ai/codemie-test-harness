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

"""Read-only UI regression: CLI Analytics renders exactly what its API returned.

Every test captures the JSON of the request the dashboard itself fired and asserts
the figures on screen against it, formatted as the UI formats them (codemie-ui
``OverviewView``, ``SessionsView``, ``UsersView``, ``SessionBody``,
``formatCliAnalyticsCost``, ``formatTokens``). Live Production data changes between
any two requests, so nothing is compared across separate requests. Every check waits for
the page to render the captured figures: React updates the DOM after the response
arrives. Safe on Production: no data is created.

Not covered: Date / Last Active / Duration / Started cells (browser-local time and
duration formatting) and charts (canvas).
"""

import math
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import parse_qs, urlparse

import pytest
from hamcrest import assert_that, equal_to, greater_than, has_length

from codemie_test_harness.tests.ui.pageobject.analytics.cli_analytics_page import (
    CLIAnalyticsPage,
)
from codemie_test_harness.tests.ui.test_data.analytics_test_data import (
    CLIAnalyticsSection,
)

pytestmark = [
    pytest.mark.ui,
    pytest.mark.cli_analytics,
    pytest.mark.prod_regression,
]

DASH = "—"
NOT_REPORTED = "Not reported"
SESSIONS_PER_PAGE = 20
USERS_PER_PAGE = 50


# ── JavaScript formatting, as the UI does it (en-US) ──────────────────────────


def _to_fixed(x: float, digits: int) -> str:
    """``Number.prototype.toFixed``: exact binary value, ties away from zero."""
    q = Decimal(abs(x)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    return f"{'-' if x < 0 else ''}{q}"


def _locale(n: float, decimals: int | None = None) -> str:
    """``toLocaleString('en-US')`` for integers, or with fixed fraction digits."""
    if decimals is None:
        return f"{int(n):,}"
    q = Decimal(n).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    return f"{q:,}"


def _js_str(x: float) -> str:
    """``String(number)`` for finite numbers."""
    return str(int(x)) if float(x).is_integer() else repr(float(x))


def _js_round(x: float) -> int:
    """``Math.round``."""
    return math.floor(x + 0.5)


def _tokens(n: float) -> str:
    """``formatTokens``."""
    for scale, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= scale:
            return f"{_to_fixed(n / scale, 1)}{suffix}"
    return _js_str(n or 0)


def _cost(v: float) -> str:
    """``formatCliAnalyticsCost``."""
    if not v:
        return "$0.00"
    magnitude = abs(v)
    sign = "-" if v < 0 else ""
    if magnitude < 0.01:
        return f"{sign}${_to_fixed(magnitude, 4)}"
    if magnitude < 100:
        return f"{sign}${_to_fixed(magnitude, 2)}"
    return f"{sign}${_locale(_js_round(magnitude))}"


def _currency(v: float) -> str:
    """``MetricFormat.CURRENCY``."""
    sign = "-" if v < 0 else ""
    return f"{sign}${_locale(abs(v), 2)}"


def _tool_success(rate: float | None, calls: int | None) -> str:
    """``formatToolSuccess``."""
    return DASH if not calls else f"{_to_fixed(rate or 0, 2)}%"


def _all_tokens(row: dict) -> int:
    return sum(
        row.get(k) or 0
        for k in (
            "input_tokens",
            "output_tokens",
            "cache_read_tokens",
            "cache_creation_tokens",
        )
    )


# ── Expected rendering of API rows ─────────────────────────────────────────────


def _session_row_text(s: dict) -> dict[str, str]:
    return {
        "PROMPT": " ".join((s["prompt"] or DASH).split()),
        "REPOSITORY": NOT_REPORTED if s["repository"] is None else s["repository"],
        "BRANCH": NOT_REPORTED if s["branch"] is None else s["branch"],
        "FRAMEWORK": s["delivery_framework"] or DASH,
        "TURNS": _locale(s["turns"] or 0),
        "NET LINES": _locale(s["net_lines"] or 0),
        "INPUT": _locale(s["input_tokens"] or 0),
        "OUTPUT": _locale(s["output_tokens"] or 0),
        "CACHED": _locale(
            (s["cache_read_tokens"] or 0) + (s["cache_creation_tokens"] or 0)
        ),
        "COST": _cost(s["cost_usd"]),
    }


def _user_row_text(u: dict) -> dict[str, str]:
    return {
        "USER": u["developer_name"] or DASH,
        "SESSIONS": _locale(u["session_count"] or 0),
        "TURNS": _locale(u["turns"] or 0),
        "TOOL CALLS": _locale(u["tool_calls"] or 0),
        "TOOL SUCCESS": _tool_success(u["tool_success_rate"], u["tool_calls"]),
        "NET LINES": _locale(u["net_lines"] or 0),
        "TOP MODEL": u["top_model"] or DASH,
        "TOKENS": _tokens(_all_tokens(u)),
        "COST": _cost(u["cost_usd"] or 0),
    }


def _rendered(rows: list[dict[str, str]], columns) -> list[dict[str, str]]:
    return [{c: r[c] for c in columns} for r in rows]


def _assert_sessions_table(cli_analytics: CLIAnalyticsPage, data: dict):
    expected = [_session_row_text(s) for s in data["sessions"]]
    assert_that(expected, has_length(greater_than(0)), "sessions to render")
    _assert_table(cli_analytics, cli_analytics.session_rows, expected)


def _assert_table(cli_analytics: CLIAnalyticsPage, rows, expected: list[dict]):
    rendered = cli_analytics.rendered_when(
        lambda: _rendered(cli_analytics.read_table(rows), expected[0]), expected
    )
    assert_that(rendered, equal_to(expected))


def _headline_kpis(k: dict) -> dict[str, tuple[str, str | None]]:
    """Overview KPI cards: label -> (value, description or None when not asserted)."""
    sessions = k["total_sessions"]
    return {
        "Sessions": (_locale(sessions), None),
        "Turns": (
            _locale(k["total_turns"]),
            f"{_to_fixed(k['total_turns'] / max(1, sessions), 1)}/session",
        ),
        "Files Touched": (
            _locale(k["total_files_changed"]),
            f"net {'+' if k['net_lines'] >= 0 else ''}{k['net_lines']} lines",
        ),
        "Tool Calls": (
            _locale(k["total_tool_calls"]),
            f"{_to_fixed(k['tool_call_success_rate'], 1)}% success"
            if k["total_tool_calls"] > 0
            else DASH,
        ),
        "Est. Cost": (_currency(k["total_cost_usd"]), "tokens × pricing"),
    }


def _all_kpis(k: dict) -> dict[str, tuple[str, str | None]]:
    sessions = k["total_sessions"]
    return {
        **_headline_kpis(k),
        "Input Tokens": (_tokens(k["total_input_tokens"]), "prompts sent"),
        "Output Tokens": (_tokens(k["total_output_tokens"]), "completions"),
        "Cache Write": (_tokens(k["total_cache_creation_tokens"]), "written to cache"),
        "Cache Read": (_tokens(k["total_cache_read_tokens"]), "served from cache"),
        "Total Tokens": (_tokens(k["total_tokens"]), "across sessions"),
        "Cache-Read Cost": (_currency(k["cache_read_cost_usd"]), None),
        "Bloat %": (f"{_to_fixed(k['bloat_pct'], 2)}%", "cache reads / total cost"),
        "Dead Sessions": (
            _locale(k["dead_sessions"]),
            f"{_to_fixed(k['dead_sessions'] / max(1, sessions) * 100, 1)}% no file output",
        ),
        "Avg Context / Call": (_tokens(_js_round(k["avg_context_per_call"])), None),
    }


def _assert_kpis(cli_analytics: CLIAnalyticsPage, expected: dict):
    rendered = cli_analytics.rendered_when(
        lambda: _read_kpis(cli_analytics, expected), expected
    )
    assert_that(rendered, equal_to(expected))


def _read_kpis(cli_analytics: CLIAnalyticsPage, expected: dict) -> dict:
    return {
        label: (
            cli_analytics.metric_value(label).inner_text().strip(),
            None
            if desc is None
            else cli_analytics.metric_description(label).inner_text().strip(),
        )
        for label, (_, desc) in expected.items()
    }


@pytest.fixture
def overview(page) -> tuple[CLIAnalyticsPage, dict]:
    """CLI Analytics open on Overview, with the data the Overview rendered."""
    responses = {}
    cli_analytics = CLIAnalyticsPage(page).navigate_to(responses)
    cli_analytics.should_have_loaded_section(CLIAnalyticsSection.OVERVIEW)
    return cli_analytics, responses


@pytest.fixture
def sessions_section(overview) -> tuple[CLIAnalyticsPage, dict]:
    """CLI Analytics open on Sessions (default page 0, 20 rows, newest first)."""
    cli_analytics, _ = overview
    responses = {}
    cli_analytics.open_section(CLIAnalyticsSection.SESSIONS, responses)
    cli_analytics.should_have_loaded_section(CLIAnalyticsSection.SESSIONS)
    if not responses["sessions"]["sessions"]:
        pytest.skip("No CLI sessions in the default 30-day period")
    return cli_analytics, responses


def test_overview_kpi_cards_render_overview_api_figures(overview):
    """Every Overview KPI card shows the overview API figure, formatted, with its derived description."""
    cli_analytics, responses = overview
    expected = _all_kpis(responses["overview"]["kpis"])

    _assert_kpis(cli_analytics, expected)


def test_time_period_filter_reloads_overview_for_selected_period(overview):
    """Picking 'Last 7 Days' sends time_period=last_7_days, keeps it in the URL and re-renders the KPIs."""
    cli_analytics, _ = overview
    responses = {}
    cli_analytics.select_time_period(
        "Last 7 Days", "last_7_days", CLIAnalyticsSection.OVERVIEW, responses
    )
    cli_analytics.should_finish_loading().should_not_have_widget_errors()

    assert_that(
        parse_qs(urlparse(cli_analytics.page.url).query).get("time_period"),
        equal_to(["last_7_days"]),
        "time period in the URL",
    )
    _assert_kpis(cli_analytics, _headline_kpis(responses["overview"]["kpis"]))


def test_sessions_table_renders_sessions_api_rows(sessions_section):
    """The first Sessions page lists the API rows in API order with every figure formatted."""
    cli_analytics, responses = sessions_section
    data = responses["sessions"]

    assert_that(data["sessions"], has_length(min(SESSIONS_PER_PAGE, data["total"])))
    _assert_sessions_table(cli_analytics, data)


def test_sessions_pagination_renders_second_page(sessions_section):
    """Page 2 requests page=1 of 20, newest first, and renders exactly the rows it returned."""
    cli_analytics, responses = sessions_section
    first = responses["sessions"]
    if first["total"] <= SESSIONS_PER_PAGE:
        pytest.skip(f"Only {first['total']} sessions: a single page")

    second = cli_analytics.open_sessions_page(2)

    assert_that((second["page"], second["per_page"]), equal_to((1, SESSIONS_PER_PAGE)))
    assert_that(
        second["sessions"],
        has_length(min(SESSIONS_PER_PAGE, second["total"] - SESSIONS_PER_PAGE)),
        "page 2 rows",
    )
    starts = [
        datetime.fromisoformat(s["start_time"].replace("Z", "+00:00"))
        for s in second["sessions"]
    ]
    assert_that(starts, equal_to(sorted(starts, reverse=True)), "newest first")
    _assert_sessions_table(cli_analytics, second)


def test_sessions_framework_filter_lists_only_that_framework(sessions_section):
    """Picking a delivery framework requests it and lists only its sessions."""
    cli_analytics, responses = sessions_section
    offered = set(responses["frameworks"])
    framework = next(
        (
            s["delivery_framework"]
            for s in responses["sessions"]["sessions"]
            if s["delivery_framework"] in offered
        ),
        None,
    )
    if framework is None:
        pytest.skip("No session on the first page has an offered delivery framework")

    data = cli_analytics.filter_sessions_by_framework(framework)

    assert_that(data["total"], greater_than(0), f"sessions of {framework!r}")
    assert_that(
        {s["delivery_framework"] for s in data["sessions"]}, equal_to({framework})
    )
    _assert_sessions_table(cli_analytics, data)


def test_session_modal_renders_session_detail_api(sessions_section):
    """The first session's modal shows its detail API figures and the clicked row's identity."""
    cli_analytics, responses = sessions_section
    row = responses["sessions"]["sessions"][0]

    modal, s = cli_analytics.open_session_at(0, row["trace_id"])
    modal.should_have_session_details()

    calls = s["tool_call_count"] or 0
    expected = {
        "Cost": _cost(s["cost_usd"]),
        "Input": _tokens(s["input_tokens"]),
        "Output": _tokens(s["output_tokens"]),
        "Cache read": _tokens(s["cache_read_tokens"] or 0),
        "Cache create": _tokens(s["cache_creation_tokens"] or 0),
        "Total": _tokens(_all_tokens(s)),
        "Turns": _locale(s["turns"] or 0),
        "Tool calls": _locale(calls),
        "Agents": DASH if s["agent_count"] is None else str(s["agent_count"]),
        "Skills": DASH if s["skill_count"] is None else str(s["skill_count"]),
    }
    rendered = cli_analytics.rendered_when(
        lambda: {
            label: modal.metric_value(label).inner_text().strip() for label in expected
        },
        expected,
    )
    assert_that(rendered, equal_to(expected))

    ok_label = modal.metric_description("Tool calls")
    if s["tool_calls_success"] is not None and calls > 0:
        assert_that(
            ok_label.inner_text().strip(),
            equal_to(f"{_js_str(s['tool_success_rate'] or 0)}% ok"),
        )
    else:
        assert_that(ok_label.count(), equal_to(0), "no '% ok' without tool calls")

    subtitle = " · ".join(
        str(v)
        for v in (
            s["harness_name"],
            s["model_name"],
            s["repository"],
            s["branch"],
            s["delivery_framework"],
        )
        if v
    )
    assert_that(
        modal.root.get_by_text(subtitle, exact=True).count(),
        equal_to(1),
        f"subtitle {subtitle!r}",
    )
    # Identity only: turns and token figures of a live session change between the requests.
    for field in ("repository", "branch", "delivery_framework"):
        assert_that(s[field], equal_to(row[field]), f"detail vs clicked row: {field}")

    modal.close()
    modal.should_be_closed()


def test_users_table_renders_users_api_rows(overview):
    """The Users table lists the users API rows in API order with every figure formatted."""
    cli_analytics, _ = overview
    responses = {}
    cli_analytics.open_section(CLIAnalyticsSection.USERS, responses)
    cli_analytics.should_have_loaded_section(CLIAnalyticsSection.USERS)
    table = responses["users"]
    if not table["rows"]:
        pytest.skip("No CLI users in the default 30-day period")

    assert_that(table["rows"], has_length(min(USERS_PER_PAGE, table["total_count"])))
    expected = [_user_row_text(u) for u in table["rows"]]
    _assert_table(cli_analytics, cli_analytics.users_data_rows, expected)
