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

"""Test data for CLI Analytics API tests (/v1/analytics/cli-analytics/*)."""

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timedelta, timezone
from functools import cache

import pytest
from codemie_sdk.models.llm import CostConfig, LLMModel

from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CT_JSON,
    CT_NDJSON,
    CT_PROTOBUF,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

SEED_MODEL = "claude-sonnet-4-5"

# ── Project gate: discard reasons and the seven ingest endpoint combinations ──

DISABLED = "cli_analytics_disabled"
REQUIRED = "project_context_required"
CONFLICT = "project_context_conflict"


@dataclass(frozen=True)
class Combo:
    id: str
    signal: str
    ct: str


E1 = Combo("E1", "logs", CT_PROTOBUF)
E2 = Combo("E2", "logs", CT_JSON)
E3 = Combo("E3", "metrics", CT_PROTOBUF)
E4 = Combo("E4", "metrics", CT_JSON)
E5 = Combo("E5", "traces", CT_PROTOBUF)
E6 = Combo("E6", "traces", CT_JSON)
E7 = Combo("E7", "event-hooks", CT_NDJSON)
ALL = [E1, E2, E3, E4, E5, E6, E7]
OTLP = [E1, E2, E3, E4, E5, E6]

# Positive wait: how long an accepted session may take to show up in the sessions list.
PRESENCE_TIMEOUT_S = 120
PRESENCE_POLL_S = 5

# Bounded absence window, a TEST HEURISTIC and not an ingestion SLA. It is derived from the
# backend rollup settings: CLI_ANALYTICS_ROLLUP_REFRESH_SECONDS (default 30) + the rollup job
# limit max(60, 4 x refresh) = 120 + one margin refresh = 180 s. It is no upper bound under a
# backlog, and "not observed within the window" is black-box evidence only; row-level proof
# that a discard writes nothing belongs to backend tests. Override per stand with
# CLI_ANALYTICS_ABSENCE_WINDOW_S.
ABSENCE_WINDOW_S = int(
    CredentialsManager.get_parameter("CLI_ANALYTICS_ABSENCE_WINDOW_S", "180")
)
ABSENCE_POLL_S = 10

HOOK_SESSION_EVENTS = 4  # events of one full hook session (see make_batch)
MAX_BODY_BYTES = 5 * 1024 * 1024  # ANALYTICS_INGEST_MAX_BODY_BYTES default

# Base URL (without /v1) of a SEPARATE backend that runs with features:cliAnalytics off. The
# shared flag-on stand's flag is never toggled by the tests.
FLAG_OFF_DOMAIN = (
    CredentialsManager.get_parameter("CODEMIE_API_DOMAIN_FLAG_OFF", "") or ""
)
NO_FLAG_OFF_BACKEND = "no flag-off backend configured (CODEMIE_API_DOMAIN_FLAG_OFF)"

_CT_NAMES = {CT_PROTOBUF: "protobuf", CT_JSON: "json", CT_NDJSON: "ndjson"}


def combo_id(combo: Combo) -> str:
    """Readable pytest id of an endpoint combination, for example logs-protobuf."""
    return f"{combo.signal}-{_CT_NAMES[combo.ct]}"


def malformed_body(combo: Combo) -> bytes:
    """A body the decoder of the combination's content type rejects."""
    return {
        CT_PROTOBUF: b"\xff\xff\xff\xff not protobuf",
        CT_JSON: b"{ this is not json",
        CT_NDJSON: b"this is not an ndjson line\n",
    }[combo.ct]


# Project references: "p_on" / "p_off" (the gate projects), "deleted", "unknown" (a fresh random
# name), "empty" (empty string); an optional ":lower" / ":upper" suffix changes the case.
PROJECT_STATES = [
    pytest.param("p_on", id="enabled-project"),
    pytest.param("p_off", id="disabled-project"),
    pytest.param(None, id="missing-header"),
]
ENABLED_OR_DISABLED = PROJECT_STATES[:2]
AUTH_FAILURES = [
    pytest.param("none", id="no-token"),
    pytest.param("invalid", id="invalid-token"),
]


@dataclass(frozen=True)
class ContextCase:
    """One project-context class of the gate: who sends what, and the expected outcome.

    reason None means the batch must be accepted. Used for the response checks over the
    endpoint combinations and, for the hook endpoint, for the storage scenario.
    """

    id: str
    reason: str | None
    sender: str = "member"  # member | outsider | admin
    header: str | None = "p_on"
    names: tuple = ()
    resource: str | None = None
    combos: tuple = tuple(ALL)


CONTEXT_CASES = [
    ContextCase("missing-header", REQUIRED, header=None),
    ContextCase("empty-string-header", REQUIRED, header="empty", combos=(E1, E2, E7)),
    ContextCase(
        "body-names-project-without-header",
        REQUIRED,
        header=None,
        names=("p_on",),
        combos=(E1, E2, E7),
    ),
    ContextCase("unknown-project", REQUIRED, header="unknown", combos=(E1, E2, E7)),
    ContextCase("deleted-project", REQUIRED, header="deleted", combos=(E7,)),
    ContextCase(
        "project-without-access",
        REQUIRED,
        sender="outsider",
        combos=(E1, E2, E7),
    ),
    ContextCase("header-enabled-body-disabled", CONFLICT, names=("p_off",)),
    ContextCase(
        "header-disabled-body-enabled", CONFLICT, header="p_off", names=("p_on",)
    ),
    ContextCase(
        "mixed-projects-in-one-batch",
        CONFLICT,
        names=("p_on", "p_off"),
        combos=(E1, E2, E7),
    ),
    ContextCase(
        "conflict-in-resource-attribute", CONFLICT, resource="p_off", combos=tuple(OTLP)
    ),
    ContextCase(
        "conflict-in-record-attribute",
        CONFLICT,
        names=("p_off",),
        resource="p_on",
        combos=tuple(OTLP),
    ),
    ContextCase(
        "global-admin-into-disabled-project",
        DISABLED,
        sender="admin",
        header="p_off",
        combos=(E1, E7),
    ),
    ContextCase(
        "plain-member-into-enabled-project",
        None,
        combos=(E1, E7),
    ),
    ContextCase(
        "global-admin-into-enabled-project-without-membership",
        None,
        sender="admin",
        combos=(E1, E7),
    ),
    ContextCase(
        "header-in-upper-case-with-body-name",
        None,
        header="p_on:upper",
        names=("p_on",),
        combos=(E1, E7),
    ),
    ContextCase(
        "header-in-upper-case-without-body-name",
        None,
        header="p_on:upper",
        combos=(E1, E7),
    ),
    ContextCase(
        "body-name-in-other-case-than-header",
        None,
        header="p_on:lower",
        names=("p_on:upper",),
        combos=(E1, E7),
    ),
]
CONTEXT_PARAMS = [
    pytest.param(case, combo, id=f"{case.id}-{combo_id(combo)}")
    for case in CONTEXT_CASES
    for combo in case.combos
]
# The hook endpoint is the one with a read side: its cases drive the storage scenario.
STORAGE_CASES = [case for case in CONTEXT_CASES if E7 in case.combos]

# (combo, sender) of the setting lifecycle; the SDK sender exists for hook events only.
LIFECYCLE_SENDERS = [
    pytest.param(E1, "raw", id="logs-protobuf-raw-sender"),
    pytest.param(E2, "raw", id="logs-json-raw-sender"),
    pytest.param(E7, "raw", id="event-hooks-raw-sender"),
    pytest.param(E7, "sdk", id="event-hooks-sdk-sender"),
]
HOOK_SENDERS = [
    pytest.param("raw", id="raw-sender"),
    pytest.param("sdk", id="sdk-sender"),
]

# What each role reads from the CLI analytics GET endpoints, before and after a project is
# disabled. The contract is the existing one, which this change must not widen: every GET sits
# behind the router's `_admin_gate` (user.is_admin or user.is_applications_admin; the same guard
# exists at the pre-change baseline 1d7e4d3d). A maintainer is resolved to is_admin by
# User.resolve_is_admin, so it reads like a global admin; a project admin passes the gate and
# sees only its own admin projects; a plain member, an auditor (whose unrestricted scope applies
# only after the gate) and an unrelated user are refused with 403 before and after.
# The fields of a session row (LocalAnalyticsSessionRow) fixed once the seeded session is listed:
# identity, owner, repository, start and the token counts. Excluded as genuinely volatile
# because the backend derives them in the periodic rollup or from pricing: duration_ms, turns,
# call counts, ctx_per_call, cost_usd, net_lines, bloat_pct, delivery_framework. The project is
# not a row field: it is proven by reading the row with the filter projects=<name>.
STABLE_SESSION_FIELDS = (
    "trace_id",
    "user_email",
    "repository",
    "start_time",
    "model_name",
    "prompt",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
)

HISTORY_READ_ALLOWED = {
    "sessions": 200,
    "overview": 200,
    "repositories": 200,
    "listed": True,
}
HISTORY_READ_DENIED = {
    "sessions": 403,
    "overview": 403,
    "repositories": 403,
    "listed": False,
}
HISTORY_ROLES = [
    pytest.param("admin", HISTORY_READ_ALLOWED, id="global-admin"),
    pytest.param(
        "maintainer", HISTORY_READ_ALLOWED, id="maintainer-reads-as-global-admin"
    ),
    pytest.param(
        "project_admin", HISTORY_READ_ALLOWED, id="project-admin-of-the-project"
    ),
    pytest.param("member", HISTORY_READ_DENIED, id="plain-member-refused"),
    pytest.param("auditor", HISTORY_READ_DENIED, id="auditor-refused"),
    pytest.param("unrelated", HISTORY_READ_DENIED, id="unrelated-user-refused"),
]

OWNER = "owner"
MEMBER = "member"
CLI_ANALYTICS_USERS = (OWNER, MEMBER)

# ── Time ─────────────────────────────────────────────────────────────────────


@cache
def seed_day_start() -> datetime:
    """00:00:00 UTC of the day the seeded sessions are built around: inside raw
    retention and a past day, with a past day on either side.

    Computed once per test process, so seeds and the windows that select them keep
    the same reference day when a run crosses midnight UTC.
    """
    day = datetime.now(timezone.utc).date() - timedelta(days=2)
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


def to_iso(moment: datetime, utc_offset_hours: int = 0) -> str:
    """ISO 8601 text of a moment, written with the given UTC offset."""
    local = moment.astimezone(timezone(timedelta(hours=utc_offset_hours)))
    return local.isoformat(timespec="seconds")


@dataclass(frozen=True)
class Window:
    """A requested time range; both bounds are inclusive."""

    start: datetime
    end: datetime

    def params(self, utc_offset_hours: int = 0) -> dict:
        """start_date/end_date query parameters, written with the given UTC offset."""
        return {
            "start_date": to_iso(self.start, utc_offset_hours),
            "end_date": to_iso(self.end, utc_offset_hours),
        }


def day_window(first_day_offset: int = 0, last_day_offset: int = 0) -> Window:
    """Whole UTC days, as offsets from the seed day: 00:00:00 to 23:59:59."""
    start = seed_day_start() + timedelta(days=first_day_offset)
    end = seed_day_start() + timedelta(days=last_day_offset + 1, seconds=-1)
    return Window(start, end)


SEED_DAY_WINDOW = "seed_day"
PREVIOUS_DAY_WINDOW = "previous_day"
BOTH_DAYS_WINDOW = "both_days"
AGGREGATION_WINDOWS = (SEED_DAY_WINDOW, PREVIOUS_DAY_WINDOW, BOTH_DAYS_WINDOW)


def get_window(name: str) -> Window:
    return {
        SEED_DAY_WINDOW: day_window(),
        PREVIOUS_DAY_WINDOW: day_window(-1, -1),
        BOTH_DAYS_WINDOW: day_window(-1, 0),
    }[name]


# Offsets a window's bounds are written with; every one names the same instants.
WINDOW_UTC_OFFSETS = [0, 2, -5]

# ── Seeded sessions ──────────────────────────────────────────────────────────


@dataclass
class CliSessionSeed:
    """One CLI session to ingest: a session start plus a single model request.

    ``started_at`` is the instant of the session; ``utc_offset_hours`` only changes
    how that instant is written in the events. With ``duration`` the session also
    ends, that long after its start. With ``cost_usd`` the request is reported as
    an OTel ``api_request`` log record, the only form that carries a cost.
    ``model`` is the model the request names; a cost-checking seed needs one priced
    in the platform catalog, since money is tokens × catalog price.
    """

    key: str
    started_at: datetime
    input_tokens: int
    output_tokens: int
    user: str = OWNER
    utc_offset_hours: int = 0
    repository: str | None = None
    duration: timedelta | None = None
    cost_usd: float | None = None
    model: str = SEED_MODEL
    session_id: str = field(
        default_factory=lambda: f"autotest-cli-{uuid.uuid4().hex[:12]}"
    )

    def events(self, project_name: str) -> list[dict]:
        """Hook events for ``POST /v1/analytics/cli-analytics/event-hooks``."""
        envelope = {
            "timestamp": to_iso(self.started_at, self.utc_offset_hours),
            "session_id": self.session_id,
            "schema_version": 2,
            "codemie_project_name": project_name,
        }
        if self.repository:
            envelope["cwd"] = self.repository
        events = [
            {
                **envelope,
                "type": "agent.session.start",
                "event_id": f"start:{self.session_id}",
            }
        ]
        if self.duration is not None:
            events.append(
                {
                    **envelope,
                    "timestamp": to_iso(
                        self.started_at + self.duration, self.utc_offset_hours
                    ),
                    "type": "agent.session.end",
                    "event_id": f"end:{self.session_id}",
                }
            )
        if self.cost_usd is None:
            events.append(self._usage_event(envelope))
        return events

    def _usage_event(self, envelope: dict) -> dict:
        return {
            **envelope,
            "type": "agent.usage.request",
            "event_id": f"usage:{self.session_id}:1:{self.model}",
            "request_id": f"req_{self.session_id}",
            "message_id": f"msg_{self.session_id}",
            "agent_id": "",
            "agent_type": "",
            "scope_kind": "main",
            "scope_name": "",
            "model_raw": self.model,
            "model": self.model,
            "speed": "standard",
            "inference_geo": "not_available",
            "service_tier": "standard",
            "input_tokens": self.input_tokens,
            "cache_creation_5m_tokens": 0,
            "cache_creation_1h_tokens": 0,
            "cache_read_tokens": 0,
            "output_tokens": self.output_tokens,
            "thinking_tokens": 0,
            "web_search_requests": 0,
            "web_fetch_requests": 0,
            "stop_reason": "end_turn",
            "is_api_error": False,
        }

    def otlp_logs(self, user_email: str) -> dict | None:
        """OTLP logs (JSON form) for ``POST /v1/analytics/cli-analytics/logs``: the
        request with its cost, or None for a seed without a cost."""
        if self.cost_usd is None:
            return None
        attributes = {
            "event.name": {"stringValue": "api_request"},
            "session.id": {"stringValue": self.session_id},
            "user.email": {"stringValue": user_email},
            "model": {"stringValue": self.model},
            "request_id": {"stringValue": f"req_{self.session_id}"},
            "cost_usd": {"doubleValue": self.cost_usd},
            "input_tokens": {"intValue": str(self.input_tokens)},
            "output_tokens": {"intValue": str(self.output_tokens)},
            "cache_read_tokens": {"intValue": "0"},
            "cache_creation_tokens": {"intValue": "0"},
        }
        record = {
            "timeUnixNano": str(int(self.started_at.timestamp()) * 10**9),
            "body": {"stringValue": "claude_code.api_request"},
            "attributes": [
                {"key": key, "value": value} for key, value in attributes.items()
            ],
        }
        return {
            "resourceLogs": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": "claude-code"},
                            }
                        ]
                    },
                    "scopeLogs": [{"logRecords": [record]}],
                }
            ]
        }


def _seeds(*specs: tuple, model: str = SEED_MODEL) -> list[CliSessionSeed]:
    """Seeds from (key, time since the seed day's start, extra fields) specs, all
    naming ``model``. Token counts differ per seed, so a missed or doubled session
    changes every total."""
    return [
        CliSessionSeed(
            key=key,
            started_at=seed_day_start() + since_day_start,
            input_tokens=1000 * 2**index,
            output_tokens=10 * 2**index,
            model=model,
            **extra,
        )
        for index, (key, since_day_start, extra) in enumerate(specs)
    ]


def get_aggregation_session_seeds() -> list[CliSessionSeed]:
    """Two users' sessions on two adjacent UTC days."""
    return _seeds(
        ("owner_day_1", timedelta(hours=10), {}),
        ("owner_day_2", timedelta(hours=11), {}),
        ("member_day", timedelta(hours=12), {"user": MEMBER}),
        ("owner_previous_day", timedelta(hours=-14), {}),
        ("member_previous_day", timedelta(hours=-13), {"user": MEMBER}),
    )


def get_boundary_session_seeds() -> list[CliSessionSeed]:
    """Sessions around both bounds of the seed day window."""
    day = timedelta(days=1)
    second = timedelta(seconds=1)
    return _seeds(
        ("just_before_start", -second, {}),
        ("exactly_at_start", timedelta(0), {}),
        ("just_after_start", second, {}),
        ("just_before_end", day - 2 * second, {}),
        ("exactly_at_end", day - second, {}),
        ("just_after_end", day, {}),
        # Written as 01:30+02:00 of the seed day: 23:30Z of the previous day.
        ("offset_before_start", timedelta(minutes=-30), {"utc_offset_hours": 2}),
        # Written as 22:30-02:00 of the previous day: 00:30Z of the seed day.
        ("offset_after_start", timedelta(minutes=30), {"utc_offset_hours": -2}),
    )


BOUNDARY_SESSION_KEYS = [seed.key for seed in get_boundary_session_seeds()]


def get_replay_session_seeds() -> list[CliSessionSeed]:
    """Sessions whose events are sent twice."""
    return _seeds(
        ("replayed_1", timedelta(hours=10), {}),
        ("replayed_2", timedelta(hours=11), {"user": MEMBER}),
    )


def with_session_end(seed: CliSessionSeed) -> CliSessionSeed:
    """The same session, now ended: its events are those of ``seed`` plus the
    session end."""
    return replace(seed, duration=timedelta(minutes=5))


def get_duration_session_seeds() -> list[CliSessionSeed]:
    """Sessions of known length, and one that never reported an end."""
    return _seeds(
        ("short", timedelta(hours=10), {"duration": timedelta(seconds=90)}),
        ("long", timedelta(hours=11), {"duration": timedelta(hours=1, seconds=1)}),
        (
            "member",
            timedelta(hours=12),
            {"duration": timedelta(minutes=10), "user": MEMBER},
        ),
        ("without_end", timedelta(hours=13), {}),
    )


def get_cost_session_seeds(model: str) -> list[CliSessionSeed]:
    """Two users' sessions of a catalog-priced model. Each request also reports a
    cost far from its catalog price: money must ignore it."""
    return _seeds(
        ("owner_1", timedelta(hours=10), {"cost_usd": 0.25}),
        ("owner_2", timedelta(hours=11), {"cost_usd": 1.5}),
        ("member", timedelta(hours=12), {"cost_usd": 4.0, "user": MEMBER}),
        model=model,
    )


# Reported costs are summed as floating point numbers.
COST_TOLERANCE = 0.000001

SEED_REPOSITORY = "/work/autotest-cli-analytics-repo"
OTHER_SEED_REPOSITORY = "/work/autotest-cli-analytics-other-repo"
SEED_REPOSITORIES = (SEED_REPOSITORY, OTHER_SEED_REPOSITORY)


def get_repository_session_seeds() -> list[CliSessionSeed]:
    """Sessions reported from two repositories and a session reported without one."""
    return _seeds(
        ("in_repository_1", timedelta(hours=10), {"repository": SEED_REPOSITORY}),
        ("in_repository_2", timedelta(hours=11), {"repository": SEED_REPOSITORY}),
        ("without_repository", timedelta(hours=12), {}),
        (
            "in_other_repository",
            timedelta(hours=13),
            {"repository": OTHER_SEED_REPOSITORY},
        ),
    )


FIRST_PROJECT = "first"
SECOND_PROJECT = "second"
ISOLATED_PROJECTS = (FIRST_PROJECT, SECOND_PROJECT)


def get_project_isolation_session_seeds(
    model: str,
) -> dict[str, list[CliSessionSeed]]:
    """Sessions of two projects on the same day, keyed by project role. The owner
    reports to both projects and the member to the second only; every session has
    its own token counts, so at the catalog price of ``model`` its own cost too, and
    a session counted for the wrong project changes every total."""
    seeds = _seeds(
        ("first_owner_1", timedelta(hours=10), {"cost_usd": 0.25}),
        ("first_owner_2", timedelta(hours=11), {"cost_usd": 0.5}),
        ("second_owner", timedelta(hours=10), {"cost_usd": 1.0}),
        ("second_member", timedelta(hours=11), {"cost_usd": 2.0, "user": MEMBER}),
        model=model,
    )
    return {FIRST_PROJECT: seeds[:2], SECOND_PROJECT: seeds[2:]}


# Small enough to spread the aggregation sessions over several pages.
SESSIONS_PER_PAGE = 2


# ── Expected values ──────────────────────────────────────────────────────────


def seeds_in_window(
    seeds: list[CliSessionSeed], window: Window
) -> list[CliSessionSeed]:
    """Seeds that started inside the window, bounds included."""
    return [seed for seed in seeds if window.start <= seed.started_at <= window.end]


def total_tokens(seeds: list[CliSessionSeed]) -> int:
    return sum(seed.input_tokens + seed.output_tokens for seed in seeds)


def tokens_by_session(seeds: list[CliSessionSeed]) -> dict[str, tuple[int, int]]:
    """(input, output) tokens keyed by session id."""
    return {seed.session_id: (seed.input_tokens, seed.output_tokens) for seed in seeds}


def totals_by_user(seeds: list[CliSessionSeed]) -> dict[str, tuple[int, int, int]]:
    """(session count, input tokens, output tokens) keyed by user role."""
    totals: dict[str, tuple[int, int, int]] = {}
    for seed in seeds:
        count, input_tokens, output_tokens = totals.get(seed.user, (0, 0, 0))
        totals[seed.user] = (
            count + 1,
            input_tokens + seed.input_tokens,
            output_tokens + seed.output_tokens,
        )
    return totals


def duration_ms(seed: CliSessionSeed) -> int:
    """Session length in milliseconds; 0 for a session that reported no end."""
    return int(seed.duration.total_seconds() * 1000) if seed.duration else 0


def priced_model(models: list[LLMModel]) -> LLMModel | None:
    """The enabled, non-router model whose catalog entry prices both input and output
    tokens, first by ``base_name`` so the pick does not depend on catalog order."""
    priced = [
        model
        for model in models
        if model.enabled
        and not model.is_router
        and model.cost
        and model.cost.input > 0
        and model.cost.output > 0
    ]
    return min(priced, key=lambda model: model.base_name, default=None)


def session_catalog_cost(seed: CliSessionSeed, price: CostConfig) -> float:
    """Money of one session: its tokens at the catalog price (seeds carry no cache
    tokens). The cost the session reported plays no part."""
    return seed.input_tokens * price.input + seed.output_tokens * price.output


def catalog_cost(seeds: list[CliSessionSeed], price: CostConfig) -> float:
    """Money of the seeds at the catalog price."""
    return sum(session_catalog_cost(seed, price) for seed in seeds)


def catalog_cost_by_user(
    seeds: list[CliSessionSeed], price: CostConfig
) -> dict[str, float]:
    """Money at the catalog price keyed by user role."""
    costs: dict[str, float] = {}
    for seed in seeds:
        costs[seed.user] = costs.get(seed.user, 0.0) + session_catalog_cost(seed, price)
    return costs
