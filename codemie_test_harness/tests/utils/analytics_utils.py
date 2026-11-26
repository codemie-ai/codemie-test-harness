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

"""Utility class for analytics operations."""

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from codemie_sdk.models.analytics import (
    AnalyticsDetailResponse,
    AnalyticsQueryParams,
    CliAnalyticsCostResponse,
    CliAnalyticsQueryParams,
    CliAnalyticsRepositoriesResponse,
    CliAnalyticsSessionRow,
    CliAnalyticsSessionsQueryParams,
    CliAnalyticsSessionsResponse,
    CliAnalyticsUsersResponse,
    CliInsightsUserDetailQueryParams,
    PaginatedAnalyticsQueryParams,
    RunAttributesQueryParams,
    SummariesResponse,
    TabularResponse,
    UsersListResponse,
)

from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_test_harness.otlp_builder import build_hook_events
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.assistants_requests_analytics_test_data import (
    CHATS_QUERY_ROW_CAP,
    MAX_PER_PAGE,
    REQUESTS_INDEX_TIMEOUT_S,
    REQUESTS_POLL_INTERVAL_S,
    REQUESTS_TIME_PERIOD,
    REQUESTS_WINDOW_MARGIN_MIN,
)

from .base_utils import BaseUtils, poll_until
from .cli_analytics_api_utils import (
    CT_JSON,
    CliAnalyticsApi,
    IngestClient,
    assert_accepted,
    assert_not_discarded,
    assert_nothing_discarded,
    parse_discard_response,
)

CLI_ANALYTICS_FEATURE_ID = "features:cliAnalytics"
# A newly created project or membership can be visible through /v1/projects before the
# CLI-ingest gate's project context cache catches up on every backend instance.
CLI_PROJECT_CONTEXT_TIMEOUT = 30
# Ingested events reach the session tables on the next rollup refresh (30 s by default).
CLI_SESSION_ROLLUP_TIMEOUT = 180


def requests_window_start() -> str:
    """ISO start of a short window that opens just before a test creates its data.

    Narrowing both assistants endpoints to this window keeps the rows of the shared stand
    out of the result. Pass it as ``start_date``; the end defaults to now.
    """
    start = datetime.now(timezone.utc) - timedelta(minutes=REQUESTS_WINDOW_MARGIN_MIN)
    return start.strftime("%Y-%m-%dT%H:%M:%SZ")


def _period_filters(filters: dict) -> dict:
    """Default to the recent time period unless the caller gave its own start_date.

    The API gives ``time_period`` precedence over ``start_date``, so both must not be sent.
    """
    if "start_date" in filters:
        return filters
    return {"time_period": REQUESTS_TIME_PERIOD, **filters}


@dataclass(frozen=True)
class CLIAnalyticsTestSession:
    """A CLI Analytics session seeded by the test harness."""

    session_id: str
    repository: str
    prompt: str
    project: str


class AnalyticsUtils(BaseUtils):
    """Utility class for analytics operations."""

    def get_summaries(self, **kwargs) -> SummariesResponse:
        """Get overall platform summary metrics.

        Args:
            **kwargs: Query parameters (time_period, start_date, end_date, users, projects)

        Returns:
            SummariesResponse with metrics array
        """
        params = AnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_summaries(params)

    def get_headroom_summary(self, **kwargs) -> SummariesResponse:
        """Get Headroom (context compression) summary metrics.

        Args:
            **kwargs: Query parameters (time_period, start_date, end_date, users, projects);
                ``users`` takes platform user ids, comma-separated

        Returns:
            SummariesResponse with the Headroom savings metrics
        """
        params = AnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_headroom_summary(params)

    def get_headroom_timeseries(self, **kwargs) -> TabularResponse:
        """Get Headroom savings per time bucket.

        Args:
            **kwargs: Query parameters (time_period, start_date, end_date, users, projects)

        Returns:
            TabularResponse with one row per time bucket
        """
        params = AnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_headroom_timeseries(params)

    def get_headroom_by_strategy(self, **kwargs) -> TabularResponse:
        """Get Headroom savings broken down by compression strategy.

        Args:
            **kwargs: Query parameters (time_period, start_date, end_date, users, projects,
                page, per_page)

        Returns:
            TabularResponse with one row per strategy
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_headroom_by_strategy(params)

    def get_cli_summary(self, **kwargs) -> SummariesResponse:
        """Get CLI-specific summary metrics.

        Args:
            **kwargs: Query parameters (time_period, start_date, end_date, users, projects)

        Returns:
            SummariesResponse with CLI metrics
        """
        params = AnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_cli_summary(params)

    def get_assistants_chats(self, **kwargs) -> TabularResponse:
        """Get assistants chats analytics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with assistant performance metrics
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_assistants_chats(params)

    def get_assistants_requests(
        self, assistant_id: str | None = None, **kwargs
    ) -> TabularResponse:
        """Get per-request assistant analytics.

        Args:
            assistant_id: Optional exact assistant id to list the requests of
            **kwargs: Query parameters including pagination and the attributes filter

        Returns:
            TabularResponse with one row per assistant request
        """
        params = RunAttributesQueryParams(assistant_id=assistant_id, **kwargs)
        return self.client.analytics.get_assistants_requests(params)

    def wait_for_assistant_requests(
        self,
        expected_count: int,
        settled: bool = False,
        timeout: float = REQUESTS_INDEX_TIMEOUT_S,
        **filters,
    ) -> TabularResponse:
        """Poll assistants-requests until it lists ``expected_count`` rows.

        Analytics documents reach the index shortly after the chat reply. With
        ``settled`` the poll also waits until every row carries a recorded cost
        (a number, with no ``spend_unavailable`` flag), since the ledger settles later.
        Returns the last response whether or not the condition held; the caller asserts.
        """

        def is_ready(response: TabularResponse) -> bool:
            rows = response.data.rows
            return len(rows) >= expected_count and (
                not settled
                or all(
                    row["money_spent"] is not None and not row["spend_unavailable"]
                    for row in rows
                )
            )

        return poll_until(
            lambda: self.get_assistants_requests(
                per_page=MAX_PER_PAGE, **_period_filters(filters)
            ),
            is_ready,
            timeout=timeout,
            interval=REQUESTS_POLL_INTERVAL_S,
        )

    def wait_for_assistants_chats_row(
        self,
        assistant_name: str,
        assistant_id: str,
        *,
        start_date: str,
        settled: bool = False,
        timeout: float = REQUESTS_INDEX_TIMEOUT_S,
        **filters,
    ) -> dict:
        """Poll assistants-chats until it lists the row of one assistant, and return it.

        assistants-chats groups by assistant id but its rows do not expose the id: each row
        is labelled with the assistant's current name (or with the id itself when the
        assistant no longer exists). The row is therefore found by ``assistant_name``, which
        is unique per test run; ``assistant_id`` only sharpens the failure message.
        ``start_date`` is required: assistants-chats ranks assistants by message count and
        keeps only the first 1000 before paging, so on a long-lived stand a fresh assistant
        is cut off unless the window is narrowed to the test's own data
        (see ``requests_window_start``).
        With ``settled`` the poll also waits for the row's cost to be recorded.

        Raises AssertionError, saying what came back, when the row is not listed or the
        name matches more than one row.
        """

        sent_filters = _period_filters({"start_date": start_date, **filters})

        def fetch() -> tuple[TabularResponse, list[dict]]:
            response = self.get_assistants_chats(per_page=MAX_PER_PAGE, **sent_filters)
            matches = [
                row for row in response.data.rows if row["assistant"] == assistant_name
            ]
            return response, matches

        def is_ready(fetched: tuple[TabularResponse, list[dict]]) -> bool:
            _, matches = fetched
            return len(matches) == 1 and (
                not settled
                or (
                    matches[0]["total_cost_usd"] is not None
                    and not matches[0]["spend_unavailable"]
                )
            )

        response, matches = poll_until(
            fetch,
            is_ready,
            timeout=timeout,
            interval=REQUESTS_POLL_INTERVAL_S,
        )
        assert len(matches) == 1, self._describe_chats_miss(
            response, matches, assistant_id, sent_filters
        )
        return matches[0]

    @staticmethod
    def _describe_chats_miss(
        response: TabularResponse,
        matches: list[dict],
        assistant_id: str,
        filters: dict,
    ) -> str:
        """Say why assistants-chats has no single row for the assistant."""
        rows = response.data.rows
        pagination = response.pagination
        truncated = (
            pagination.has_more
            if pagination is not None
            else len(rows) >= CHATS_QUERY_ROW_CAP
        )
        labelled_by_id = [row for row in rows if row["assistant"] == assistant_id]
        return (
            f"assistants-chats returned {len(rows)} rows for the filters sent, "
            f"{filters}; truncated at the page or query cap: {truncated}; "
            f"rows labelled with the assistant's name: {len(matches)}; "
            f"rows labelled with the assistant's id instead of its name: "
            f"{len(labelled_by_id)}"
        )

    def get_workflows_executions(self, **kwargs) -> TabularResponse:
        """Get per-execution workflow analytics.

        Args:
            **kwargs: Query parameters including pagination and the attributes filter

        Returns:
            TabularResponse with one row per workflow execution
        """
        params = RunAttributesQueryParams(**kwargs)
        return self.client.analytics.get_workflows_executions(params)

    def get_attributes_usage(
        self, attribute_key: str | None = None, **kwargs
    ) -> TabularResponse:
        """Get usage grouped by the values of one run attribute key.

        Args:
            attribute_key: Attribute key to group by; omitted from the request when None
            **kwargs: Query parameters including pagination and the attributes filter

        Returns:
            TabularResponse with one row per attribute value
        """
        params = RunAttributesQueryParams(**kwargs)
        return self.client.analytics.get_attributes_usage(attribute_key, params)

    def get_workflows(self, **kwargs) -> TabularResponse:
        """Get workflows analytics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with workflow execution metrics
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_workflows(params)

    def get_tools_usage(self, **kwargs) -> TabularResponse:
        """Get tool usage analytics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with tool usage metrics
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_tools_usage(params)

    def get_webhooks_invocation(self, **kwargs) -> TabularResponse:
        """Get webhooks invocation statistics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with webhook usage patterns
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_webhooks_invocation(params)

    def get_mcp_servers(self, **kwargs) -> TabularResponse:
        """Get top MCP servers analytics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with MCP server usage distribution
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_mcp_servers(params)

    def get_mcp_servers_by_users(self, **kwargs) -> TabularResponse:
        """Get MCP servers usage by users.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with individual user MCP adoption
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_mcp_servers_by_users(params)

    def get_projects_spending(self, **kwargs) -> TabularResponse:
        """Get money spent by projects.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with project-level spending
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_projects_spending(params)

    def wait_for_projects_with_spend(
        self,
        projects: list[str],
        expected: str,
        user_id: str,
        timeout: float = 600,
        interval: float = 20,
    ) -> set[str]:
        """Names among ``projects`` that show spend of the user in the last hour.

        Waits until ``expected`` shows spend, then one more interval so that a project
        wrongly charged a little later is still seen. Raises TimeoutError if ``expected``
        never shows spend.
        """
        deadline = time.monotonic() + timeout
        while True:
            shown = self._projects_with_spend(projects, user_id)
            if expected in shown:
                time.sleep(interval)
                return self._projects_with_spend(projects, user_id)
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"{expected} shows no spend in the analytics within {timeout}s"
                )
            time.sleep(interval)

    def _projects_with_spend(self, projects: list[str], user_id: str) -> set[str]:
        response = self.get_projects_spending(
            time_period="last_hour",
            projects=",".join(projects),
            users=user_id,
            per_page=len(projects),
        )
        return {
            row["project_name"]
            for row in response.data.rows
            if row["total_cost_usd"] > 0
        }

    def get_llms_usage(self, **kwargs) -> TabularResponse:
        """Get top LLMs usage analytics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with LLM model usage distribution
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_llms_usage(params)

    def get_users_spending(self, **kwargs) -> TabularResponse:
        """Get money spent by users.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with individual user spending
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_users_spending(params)

    def get_budget_soft_limit(self, **kwargs) -> TabularResponse:
        """Get soft budget limit violations.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with users exceeding soft limits
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_budget_soft_limit(params)

    def get_budget_hard_limit(self, **kwargs) -> TabularResponse:
        """Get hard budget limit violations.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with users exceeding hard limits
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_budget_hard_limit(params)

    def get_users_activity(self, **kwargs) -> TabularResponse:
        """Get most active users analytics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with comprehensive user activity metrics
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_users_activity(params)

    def get_projects_activity(self, **kwargs) -> TabularResponse:
        """Get most active projects analytics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with project activity metrics
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_projects_activity(params)

    def get_agents_usage(self, **kwargs) -> TabularResponse:
        """Get top agents usage analytics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with agent usage analytics
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_agents_usage(params)

    def get_cli_agents(self, **kwargs) -> TabularResponse:
        """Get top CLI agents analytics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with CLI agent usage distribution
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_cli_agents(params)

    def get_cli_llms(self, **kwargs) -> TabularResponse:
        """Get top CLI LLMs analytics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with CLI LLM usage distribution
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_cli_llms(params)

    def get_cli_users(self, **kwargs) -> TabularResponse:
        """Get most active CLI users analytics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with CLI user activity
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_cli_users(params)

    def get_cli_errors(self, **kwargs) -> TabularResponse:
        """Get top error codes for CLI.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with most common CLI error codes
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_cli_errors(params)

    def get_cli_repositories(self, **kwargs) -> TabularResponse:
        """Get repository statistics.

        Args:
            **kwargs: Query parameters including pagination

        Returns:
            TabularResponse with repository-level metrics
        """
        params = PaginatedAnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_cli_repositories(params)

    def get_users(self, **kwargs) -> UsersListResponse:
        """Get users list.

        Args:
            **kwargs: Query parameters (time_period, start_date, end_date, users, projects)

        Returns:
            UsersListResponse with list of unique users
        """
        params = AnalyticsQueryParams(**kwargs) if kwargs else None
        return self.client.analytics.get_users(params)

    def get_cli_insights_user_detail(self, **kwargs) -> AnalyticsDetailResponse:
        """Get the CLI Insights drilldown of one user.

        Args:
            **kwargs: user_name (required), user_id, time_period, start_date,
                end_date, users, projects

        Returns:
            AnalyticsDetailResponse with the user's detail payload
        """
        return self.client.analytics.get_cli_insights_user_detail(
            CliInsightsUserDetailQueryParams(**kwargs)
        )

    def get_leaderboard_summary(self, **kwargs) -> dict:
        return self.client.analytics.get_leaderboard_summary(**kwargs)

    def get_leaderboard_scores(self, **kwargs) -> dict:
        return self.client.analytics.get_leaderboard_scores(**kwargs)

    def get_leaderboard_tiers(self, **kwargs) -> dict:
        return self.client.analytics.get_leaderboard_tiers(**kwargs)

    def get_leaderboard_top_performers(self, **kwargs) -> dict:
        return self.client.analytics.get_leaderboard_top_performers(**kwargs)

    def get_leaderboard_dimensions(self, **kwargs) -> dict:
        return self.client.analytics.get_leaderboard_dimensions(**kwargs)

    def get_leaderboard_entries(self, **kwargs) -> dict:
        return self.client.analytics.get_leaderboard_entries(**kwargs)

    def get_leaderboard_seasons(self, **kwargs) -> dict:
        kwargs.setdefault("view", "monthly")
        return self.client.analytics.get_leaderboard_seasons(**kwargs)

    def get_leaderboard_projects(self, **kwargs) -> dict:
        return self.client.analytics.get_leaderboard_projects(**kwargs)

    def get_leaderboard_framework(self, **kwargs) -> dict:
        return self.client.analytics.get_leaderboard_framework(**kwargs)

    def create_cli_session(
        self, timeout: int = 120, project: str = PROJECT
    ) -> CLIAnalyticsTestSession:
        """Seed one CLI Analytics session for the current user and wait until it is listed.

        Every call creates a new session with a unique id. The ingest API has no delete
        endpoint, so seeded data stays until retention; token counts are minimal
        (cost ~ $0) and the repository/branch are marked "autotest" to tell it apart.

        `project` is sent as X-CodeMie-Project and as codemie_project_name on all four
        events. The project must have CLI analytics enabled and the sending user must be
        able to access it; a discarded batch fails here at once (the server answers 200
        with a discard body) instead of timing out after `timeout` seconds.
        """
        user = self.client.users.about_me()
        session_id = f"autotest-cli-{uuid.uuid4().hex[:12]}"
        session = CLIAnalyticsTestSession(
            session_id=session_id,
            repository=f"autotest/{session_id}",
            prompt=f"Autotest CLI Analytics session {session_id}",
            project=project,
        )
        events = build_hook_events(
            session_id, project, user.name, session.repository, session.prompt
        )
        result = self.client.analytics.send_cli_hook_events(events, project=project)
        assert_not_discarded(result, f"CLI analytics batch for project {project!r}")
        self.wait_for_cli_session(session.session_id, timeout=timeout)
        return session

    def get_ai_adoption_feature_adoption(self, **kwargs) -> dict:
        return self.client.analytics.get_ai_adoption_feature_adoption(**kwargs)

    def get_ai_adoption_config(self, **kwargs) -> dict:
        return self.client.analytics.get_ai_adoption_config(**kwargs)

    # ── CLI Analytics: /v1/analytics/cli-analytics/* ─────────────────────────

    def is_cli_analytics_enabled(self) -> bool:
        """Whether the features:cliAnalytics customer-config flag is on."""
        component = next(
            (
                c
                for c in self.client.customer_config.get_config()
                if c.get("id") == CLI_ANALYTICS_FEATURE_ID
            ),
            None,
        )
        return bool(component and component.get("settings", {}).get("enabled"))

    def ingest_cli_event_hooks(
        self, events: list[dict], project: str | None = None
    ) -> None:
        """Send CLI hook events as the client's own user.

        `project` is sent as X-CodeMie-Project: the BE stores the batch only for a project
        with CLI analytics enabled that the sender may use. A newly created project or
        membership may briefly be missing from the ingest gate's cache even after the project
        is readable, so only ``project_context_required`` is retried for the bounded cache
        propagation window. Any other discard fails at once, quoting reason and dropped. The
        whole batch is one request, as in create_cli_session.
        """
        result = poll_until(
            lambda: self.client.analytics.send_cli_hook_events(events, project=project),
            lambda reply: (reply or {}).get("reason") != "project_context_required",
            timeout=CLI_PROJECT_CONTEXT_TIMEOUT,
            interval=2,
        )
        assert_not_discarded(result, f"CLI analytics batch for project {project!r}")

    def ingest_cli_otlp_logs(self, payload: dict, project: str | None = None) -> None:
        """Send OTLP logs (JSON form) as the client's own user (see ingest_cli_event_hooks).

        Posted raw, because the SDK method returns nothing that could show a discard. Like
        the hook events, ``project_context_required`` is retried for the cache propagation
        window; any other discard fails at once, quoting reason and partial_success.
        """
        body = json.dumps(payload).encode()

        def _send():
            """The reply and its parsed discard; no discard for a non-200 reply,
            which assert_accepted then fails on its status."""
            response = IngestClient(self.client).post_signal(
                "logs", body, CT_JSON, project=project
            )
            if response.status_code != 200:
                return response, None
            return response, parse_discard_response(response, "logs", CT_JSON)

        response, discard = poll_until(
            _send,
            lambda reply: reply[1] is None
            or reply[1].reason != "project_context_required",
            timeout=CLI_PROJECT_CONTEXT_TIMEOUT,
            interval=2,
        )
        if discard is None:
            assert_accepted(response, "logs", CT_JSON)
        else:
            assert_nothing_discarded(response, "logs", discard)

    def ingest_cli_otlp_traces(self, payload: dict, project: str | None = None) -> None:
        """Send OTLP traces (JSON form) as the client's own user (see ingest_cli_otlp_logs)."""
        body = json.dumps(payload).encode()

        def _send():
            response = IngestClient(self.client).post_signal(
                "traces", body, CT_JSON, project=project
            )
            if response.status_code != 200:
                return response, None
            return response, parse_discard_response(response, "traces", CT_JSON)

        response, discard = poll_until(
            _send,
            lambda reply: reply[1] is None
            or reply[1].reason != "project_context_required",
            timeout=CLI_PROJECT_CONTEXT_TIMEOUT,
            interval=2,
        )
        if discard is None:
            assert_accepted(response, "traces", CT_JSON)
        else:
            assert_nothing_discarded(response, "traces", discard)

    def get_cli_session_turns(self, trace_id: str) -> int | None:
        """Turns of a session from the raw session detail, or None while the session is
        not rolled up or the detail has no `turns`. The SDK model does not carry the
        field, so the raw JSON is read."""
        response = CliAnalyticsApi(self.client).request(
            "GET", f"/v1/analytics/cli-analytics/sessions/{trace_id}"
        )
        if response.status_code == 404:
            return None
        assert_that(
            response.status_code,
            equal_to(200),
            f"session detail of {trace_id}: {response.text[:200]}",
        )
        return response.json().get("data", {}).get("turns")

    def get_cli_session_unpriced_models(self, trace_id: str) -> list[str] | None:
        """Models of a session the platform catalog has no price for
        (``metadata.unpriced_models`` of the raw session detail), or None while the
        session is not rolled up or the detail has no such field. The SDK model does not
        carry the field, so the raw JSON is read."""
        response = CliAnalyticsApi(self.client).request(
            "GET", f"/v1/analytics/cli-analytics/sessions/{trace_id}"
        )
        if response.status_code == 404:
            return None
        assert_that(
            response.status_code,
            equal_to(200),
            f"session detail of {trace_id}: {response.text[:200]}",
        )
        return response.json().get("metadata", {}).get("unpriced_models")

    def wait_for_cli_session_turns(
        self,
        trace_id: str,
        reached: Callable[[int], bool],
        timeout: float = CLI_SESSION_ROLLUP_TIMEOUT,
    ) -> int | None:
        """Poll the turns of a session until `reached(turns)` holds. Returns the last
        value whether or not it held; the caller asserts."""
        return poll_until(
            lambda: self.get_cli_session_turns(trace_id),
            lambda turns: turns is not None and reached(turns),
            timeout=timeout,
            interval=5,
        )

    def get_cli_analytics_cost(self, **filters) -> CliAnalyticsCostResponse:
        """Totals. filters: start_date, end_date, time_period, users, projects."""
        return self.client.analytics.get_cli_analytics_cost(
            CliAnalyticsQueryParams(**filters)
        )

    def get_cli_analytics_users(self, **filters) -> CliAnalyticsUsersResponse:
        """Per-user rows. filters: start_date, end_date, time_period, users, projects."""
        return self.client.analytics.get_cli_analytics_users(
            CliAnalyticsQueryParams(**filters)
        )

    def get_cli_analytics_sessions(self, **filters) -> CliAnalyticsSessionsResponse:
        """One page of sessions. filters: as for cost, plus page, per_page,
        is_unattributed."""
        return self.client.analytics.get_cli_analytics_sessions(
            CliAnalyticsSessionsQueryParams(**filters)
        )

    def get_cli_analytics_repositories(
        self, **filters
    ) -> CliAnalyticsRepositoriesResponse:
        """Every repository branch. filters: as for cost."""
        return self.client.analytics.get_cli_analytics_repositories(
            CliAnalyticsQueryParams(**filters)
        )

    def find_cli_analytics_session(
        self, trace_id: str
    ) -> CliAnalyticsSessionRow | None:
        """Session detail, or None while the backend answers 404 for it: the
        session is not rolled up yet. Any other error is raised."""
        try:
            return self.client.analytics.get_cli_analytics_session(trace_id).data
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def wait_for_cli_session(
        self, trace_id: str, timeout: float = CLI_SESSION_ROLLUP_TIMEOUT
    ) -> CliAnalyticsSessionRow:
        """Wait until an ingested session is rolled up with its token usage.

        Raises:
            AssertionError: If the session is not available within timeout.
        """
        return self._wait_for_cli_session(
            trace_id, lambda session: session.input_tokens > 0, "usage", timeout
        )

    def wait_for_cli_session_end(
        self, trace_id: str, timeout: float = CLI_SESSION_ROLLUP_TIMEOUT
    ) -> CliAnalyticsSessionRow:
        """Wait until the rollup of a session includes its last real-work event (the
        turn stop at its end).

        Raises:
            AssertionError: If the session has no duration within timeout.
        """
        return self._wait_for_cli_session(
            trace_id, lambda session: session.duration_ms > 0, "its end", timeout
        )

    def _wait_for_cli_session(
        self,
        trace_id: str,
        is_rolled_up: Callable[[CliAnalyticsSessionRow], bool],
        awaited: str,
        timeout: float,
    ) -> CliAnalyticsSessionRow:
        def _ready(session: CliAnalyticsSessionRow | None) -> bool:
            return session is not None and is_rolled_up(session)

        session = poll_until(
            lambda: self.find_cli_analytics_session(trace_id),
            _ready,
            timeout=timeout,
            interval=5,
        )
        if not _ready(session):
            raise AssertionError(
                f"Seeded CLI session '{trace_id}' was not rolled up with {awaited} "
                f"within {timeout}s"
            )
        return session
