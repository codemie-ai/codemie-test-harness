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

Every test captures the JSON of the request the dashboard itself fired and asserts the
figures on screen against it, formatted as the UI formats them (codemie-ui
``buildOverviewSummaryGroups``, ``SessionsView``, ``UsersView``, ``SessionBody``,
``SessionCostValue`` / ``AmountCost``, ``formatCurrency``, ``formatDuration``,
``describeSessionCount`` / ``describeSessionToolCalls``). Live data changes between any two
requests, so nothing is compared across separate requests. Every check waits for the page to
render the captured figures: React updates the DOM after the response arrives. Safe on
Production: no data is created.

Not covered: Date / Started / Last Active cells (browser-local time) and charts (canvas).
"""

import math
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import parse_qs, urlparse

import pytest
from hamcrest import assert_that, equal_to, greater_than, has_length, is_

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

DASH = "—"  # em dash: a count or caption with no data
ABSENT = "-"  # ABSENT_VALUE_MARKER: an absent amount or line count, never a zero
NOT_REPORTED = "Not reported"
SESSIONS_PER_PAGE = 20
USERS_PER_PAGE = 10
# formatDuration: months are "m", minutes "min"; three units from the largest one filled.
DURATION_UNITS = (
    ("m", 30 * 86400),
    ("w", 7 * 86400),
    ("d", 86400),
    ("h", 3600),
    ("min", 60),
    ("s", 1),
)


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


def _sentence(text: str) -> str:
    """Metric captions render with their first letter upper-cased."""
    return text[:1].upper() + text[1:]


def _currency(v: float) -> str:
    """``formatCurrency``: two decimals, but a positive amount below a cent keeps two
    significant digits; the sign follows the ``$``."""
    if 0 < v < 0.01:
        exact = Decimal(v)
        q = exact.quantize(
            Decimal(1).scaleb(exact.adjusted() - 1), rounding=ROUND_HALF_UP
        )
        return f"${q.normalize():f}"
    sign = "-" if math.copysign(1, v) < 0 else ""
    return f"${sign}{_locale(abs(v), 2)}"


def _spend(v: float | None) -> str:
    """``formatSpend``: an absent amount is not $0.00."""
    return ABSENT if v is None else _currency(v)


def _session_cost(value: float | None, s: dict) -> str:
    """``SessionCostValue``: unknown when nothing was priced; a partial amount stays."""
    unknown = s.get("cost_available") is False
    partial = s.get("cost_incomplete") is True or bool(s.get("unpriced_models"))
    if unknown or (partial and value is None):
        return ABSENT
    return _spend(value)


def _amount_cost(value: float | None, pricing: dict) -> str:
    """``AmountCost`` / ``aggregateCostOverride``: unknown only when the API says so."""
    return ABSENT if pricing.get("cost_unknown") is True else _spend(value)


def _count(n: int | None) -> str:
    """``formatMetricValue`` of an integer: absent stays absent."""
    return ABSENT if n is None else _locale(n)


def _pct(v: float) -> str:
    """``MetricFormat.PERCENTAGE``."""
    return f"{_to_fixed(v, 2)}%"


def _duration(ms: float | None) -> str:
    """``formatDuration``."""
    if ms is None or not math.isfinite(ms) or ms <= 0:
        return DASH
    if ms < 1000:
        return f"{_js_round(ms)}ms"
    remaining = math.floor(ms / 1000)
    first = next(i for i, (_, size) in enumerate(DURATION_UNITS) if remaining >= size)
    parts = []
    for label, size in DURATION_UNITS[first : first + 3]:
        value = remaining // size
        remaining -= value * size
        if value:
            parts.append(f"{value}{label}")
    return " ".join(parts)


def _complete(s: dict, metric: str) -> bool:
    """``isSessionMetricComplete``: the final summary reports the metric."""
    return s.get("summary_state") == "final" and metric in (
        s.get("summary_metrics") or []
    )


def _incomplete_note(s: dict) -> str:
    if s.get("summary_state") == "provisional":
        return "Provisional"
    return "Summary unavailable" if s.get("summary_state") == "none" else "Partial"


def _session_count(n: int | None, s: dict, metric: str) -> tuple[str, str | None]:
    """``describeSessionCount``: (value, note)."""
    if n is None:
        return DASH, NOT_REPORTED
    return _locale(n), None if _complete(s, metric) else _incomplete_note(s)


def _session_tool_calls(s: dict) -> tuple[str, str]:
    """``describeSessionToolCalls``: (value, note); the total comes from the summary."""
    observed = s.get("tool_call_count") or 0
    total = s.get("tool_calls_total")
    complete = total is not None and _complete(s, "tool_calls")
    notes = []
    if total is not None:
        value = _locale(total)
        if not complete:
            notes.append(_incomplete_note(s))
    elif observed > 0:
        value = _locale(observed)
        notes.append("Observed only")
    else:
        return DASH, NOT_REPORTED
    if (
        observed > 0
        and s.get("tool_calls_success") is not None
        and s.get("tool_success_rate") is not None
    ):
        ok = f"{_js_str(s['tool_success_rate'])}% ok"
        same = total is None or (complete and total == observed)
        notes.append(
            ok
            if same
            else f"{_locale(observed)} observed of {_locale(total)} total · {ok}"
        )
    elif total is not None and total > 0 and observed == 0:
        notes.append("No outcomes observed")
    return value, " · ".join(notes)


def _tool_success(rate: float | None, calls: int | None) -> str:
    """``formatToolSuccess``: no calls is no data, not 0%."""
    return DASH if not calls else _pct(rate or 0)


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
    turns, note = _session_count(s["turns"], s, "turns")
    return {
        "Prompt": " ".join((s["prompt"] or DASH).split()),
        "Repository": NOT_REPORTED if s["repository"] is None else s["repository"],
        "Branch": NOT_REPORTED if s["branch"] is None else s["branch"],
        "Framework": s["delivery_framework"] or DASH,
        "Est. Cost": _session_cost(s["cost_usd"], s),
        "Turns": f"{turns}+" if note and s["turns"] is not None else turns,
        "Net Lines": _count(s["net_lines"]),
        "Input Tokens": _locale(s["input_tokens"] or 0),
        "Output Tokens": _locale(s["output_tokens"] or 0),
        "Cache Read Tokens": _locale(s["cache_read_tokens"] or 0),
    }


def _user_row_text(u: dict) -> dict[str, str]:
    return {
        "User": u["developer_name"] or DASH,
        "Sessions": _locale(u["session_count"] or 0),
        "Est. Cost": _amount_cost(u["cost_usd"], u),
        "Turns": _locale(u["turns"] or 0),
        "Tool Calls": _locale(u["tool_calls"] or 0),
        "Tool Success": _tool_success(u["tool_success_rate"], u["tool_calls"]),
        "Net Lines": _count(u["net_lines"]),
        "Top Model": u["top_model"] or DASH,
        "Total Tokens": _locale(_all_tokens(u)),
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
    """Overview cards that need no other request: label -> (value, caption or None)."""
    sessions = k["total_sessions"]
    calls = k["total_tool_calls"]
    return {
        "Est. Cost": (_amount_cost(k["total_cost_usd"], k), "All usage at API rates"),
        "Sessions": (_count(sessions), None),
        "Turns": (
            _count(k["total_turns"]),
            f"{_to_fixed(k['total_turns'] / max(1, sessions), 1)} per session",
        ),
        "Tool Calls": (
            _count(calls),
            f"{_pct(k['tool_call_success_rate'])} succeeded" if calls > 0 else DASH,
        ),
        "Sessions Without Changes": (
            _count(k["dead_sessions"]),
            f"{_pct(k['dead_sessions'] / max(1, sessions) * 100)} of all sessions",
        ),
    }


def _all_kpis(k: dict, user_count: int | None) -> dict[str, tuple[str, str | None]]:
    """Every Overview card; Total Users is the users total when the KPIs carry none."""
    users = k.get("total_users", user_count)
    sessions = k["total_sessions"]
    return {
        **_headline_kpis(k),
        "API Spend": (_spend(k["api_cost_usd"]), "Billed per token"),
        "Subscription Usage": (
            _spend(k["subscription_cost_usd"]),
            "At API rates, not billed",
        ),
        "Cache Re-Read Cost": (
            _spend(k["cache_read_cost_usd"]),
            "Spend on context re-reads",
        ),
        "Bloat %": (_pct(k["bloat_pct"]), "Cache re-read cost / est. cost"),
        "Total Tokens": (_count(k["total_tokens"]), "Input, output and cache"),
        "Input Tokens": (_count(k["total_input_tokens"]), "LLM input tokens"),
        "Output Tokens": (_count(k["total_output_tokens"]), "LLM output tokens"),
        "Cache Read Tokens": (
            _count(k["total_cache_read_tokens"]),
            "Cached input tokens",
        ),
        "Cache Creation Tokens": (
            _count(k["total_cache_creation_tokens"]),
            "Tokens written to cache",
        ),
        "Total Users": (_count(users), "Distinct users"),
        "Sessions": (
            _count(sessions),
            f"{_to_fixed(sessions / users, 1)} per user" if users else None,
        ),
    }


def _assert_kpis(cli_analytics: CLIAnalyticsPage, expected: dict, cards=None):
    """Assert the metric cards of the page, or of ``cards`` (the session dialog)."""
    cards = cards or cli_analytics
    rendered = cli_analytics.rendered_when(
        lambda: _read_kpis(cards, expected), expected
    )
    assert_that(rendered, equal_to(expected))


def _read_kpis(cards, expected: dict) -> dict:
    """Value and caption of each metric card, read from ``cards`` (page or dialog)."""
    return {
        label: (
            cards.metric_value(label).inner_text().strip(),
            None
            if desc is None
            else cards.metric_description(label).inner_text().strip(),
        )
        for label, (_, desc) in expected.items()
    }


@pytest.fixture
def overview(page) -> tuple[CLIAnalyticsPage, dict]:
    """CLI Analytics open on Overview, with the data the Overview rendered.

    ``responses`` also holds ``user_count``: the users total of the Total Users card.
    """
    responses = {}
    cli_analytics = CLIAnalyticsPage(page)
    with cli_analytics.expect_user_count() as user_count:
        cli_analytics.navigate_to(responses)
    cli_analytics.should_have_loaded_section(CLIAnalyticsSection.OVERVIEW)
    assert_that(
        user_count.value.ok,
        is_(True),
        f"user count failed with HTTP {user_count.value.status}",
    )
    responses["user_count"] = user_count.value.json()["data"]["total_count"]
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
    """Every Overview card shows its overview API figure, formatted, with its caption."""
    cli_analytics, responses = overview
    expected = _all_kpis(responses["overview"]["kpis"], responses["user_count"])

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


def _counted(described: tuple[str, str | None], caption: str) -> tuple[str, str]:
    """A count card: its qualifier ("Partial", "Not reported", "... ok") or else its caption."""
    value, note = described
    return value, _sentence(note or caption)


def _session_cards(s: dict) -> dict[str, tuple[str, str]]:
    """The dialog's metric cards (Started is browser-local time): label -> (value, caption)."""
    qualified = (
        s.get("cost_available") is False
        or s.get("cost_incomplete") is True
        or bool(s.get("unpriced_models"))
    )
    cache_cost = s["cache_read_cost_usd"]
    if qualified:
        cache_cost_text = _session_cost(cache_cost, s)
    else:
        cache_cost_text = DASH if cache_cost is None else _spend(cache_cost)
    active = s.get("active_ms")
    return {
        "Est. Cost": (_session_cost(s["cost_usd"], s), "From token usage"),
        "Cache Re-Read Cost": (cache_cost_text, "Spend on context re-reads"),
        "Duration": (_duration(s["duration_ms"]), "Wall-clock"),
        "Active": (DASH if active is None else _duration(active), "Excludes idle"),
        "Total Tokens": (_count(_all_tokens(s)), "Total LLM tokens"),
        "Input Tokens": (_count(s["input_tokens"]), "LLM input tokens"),
        "Output Tokens": (_count(s["output_tokens"]), "LLM output tokens"),
        "Cache Read Tokens": (
            _count(s["cache_read_tokens"] or 0),
            "Cached input tokens",
        ),
        "Cache Creation Tokens": (
            _count(s["cache_creation_tokens"] or 0),
            "Cache creation tokens",
        ),
        "Turns": _counted(_session_count(s["turns"], s, "turns"), "prompts submitted"),
        "Tool Calls": _counted(_session_tool_calls(s), "tools run"),
        "Agents": _counted(
            _session_count(s.get("agent_count"), s, "agents"), "subagents dispatched"
        ),
        "Skills": _counted(
            _session_count(s.get("skill_count"), s, "skills"), "skills invoked"
        ),
    }


def test_session_modal_renders_session_detail_api(sessions_section):
    """The first session's dialog shows its detail API figures and the clicked row's identity."""
    cli_analytics, responses = sessions_section
    row = responses["sessions"]["sessions"][0]

    modal, s = cli_analytics.open_session_at(0, row["trace_id"])
    modal.should_have_session_details()

    _assert_kpis(cli_analytics, _session_cards(s), modal)

    title = " · ".join(
        str(v) for v in (s["developer_name"], s["harness_name"], s["model_name"]) if v
    )
    location = " · ".join(
        str(v) for v in (s["repository"], s["branch"], s["delivery_framework"]) if v
    )
    for line in (title, location):
        assert_that(
            modal.root.get_by_text(line, exact=True).count(),
            equal_to(1),
            f"dialog header line {line!r}",
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
