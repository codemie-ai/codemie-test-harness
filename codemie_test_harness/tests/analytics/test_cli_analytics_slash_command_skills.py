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

"""CLI Analytics skills started with a slash command: counted once, as a skill, with the
run, tokens and cost of their own requests on the session Timeline."""

from datetime import datetime, timedelta, timezone

import pytest
from hamcrest import (
    assert_that,
    close_to,
    equal_to,
    has_entries,
    has_entry,
    has_length,
    is_,
    is_in,
)

from codemie_test_harness.tests.test_data.cli_analytics_slash_skills_test_data import (
    INLINE_SKILL_REQUESTS,
    INLINE_SKILL_RUN_MS,
    SlashSkillSeed,
    get_foreground_fork_seed,
    get_inline_slash_seed,
    get_skill_call_fork_seed,
    get_slash_fork_seed,
)
from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    COST_TOLERANCE,
    OWNER,
    to_iso,
)
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi

# Session detail counts come from the rollups, refreshed every 30 s by default.
DETAIL_TIMEOUT = 120


@pytest.fixture(scope="module")
def seed_skill_sessions(
    ingest_cli_sessions, cli_analytics_users, cli_analytics_project, analytics_utils
):
    """Factory that sends skill sessions as the owner (hooks and logs, then the spans) and
    waits until each is rolled up with its usage."""

    def _seed(*seeds: SlashSkillSeed) -> None:
        ingest_cli_sessions(list(seeds))
        owner = cli_analytics_users[OWNER].analytics_utils
        for seed in seeds:
            traces = seed.otlp_traces()
            if traces:
                owner.ingest_cli_otlp_traces(traces, project=cli_analytics_project)
        for seed in seeds:
            analytics_utils.wait_for_cli_session(seed.session_id)

    return _seed


def _session_detail(analytics_utils, session_id: str) -> dict | None:
    """The raw session detail (the SDK model has no dispatches), or None before rollup."""
    response = CliAnalyticsApi(analytics_utils.client).read(f"/sessions/{session_id}")
    if response.status_code == 404:
        return None
    assert_that(
        response.status_code,
        equal_to(200),
        f"session detail of {session_id}: {response.text[:200]}",
    )
    return response.json()["data"]


def _wait_for_detail(analytics_utils, session_id: str, ready) -> dict | None:
    """Poll the session detail until ``ready(detail)`` holds; returns the last one
    whether or not it held, for the caller to assert."""
    return poll_until(
        lambda: _session_detail(analytics_utils, session_id),
        lambda detail: detail is not None and ready(detail),
        timeout=DETAIL_TIMEOUT,
        interval=5,
    )


# The kinds a skill's Timeline row may have: "skill", or "command" on builds that
# still label a slash-command run as a command.
SKILL_ROW_KINDS = ("skill", "command")


def _timeline_rows(detail: dict) -> list[dict]:
    """The Timeline rows of a session detail other than the whole-session row."""
    return [row for row in detail["dispatches"] if row["kind"] != "session"]


def _skill_row(detail: dict, skill: str) -> dict:
    """The one Timeline row of the session, which must be the skill's."""
    rows = _timeline_rows(detail)
    assert_that(  # repro:symptom
        [(row["kind"], row["label"]) for row in rows],
        has_length(1),
        f"Timeline rows besides the session: one for the skill {skill}",
    )
    (row,) = rows
    assert_that(row["kind"], is_in(SKILL_ROW_KINDS), f"kind of the row {row}")
    assert_that(row["label"], equal_to(f"{row['kind']} · {skill}"), "row label")
    return row


def _skills_invoked(analytics_utils, project: str, seed: SlashSkillSeed) -> dict:
    """Skills invoked (Tools & Models) in the module's project from an hour before the
    seed up to now (the endpoint refuses a future end), by name."""
    response = CliAnalyticsApi(analytics_utils.client).read(
        "/tools",
        projects=project,
        start_date=to_iso(seed.started_at - timedelta(hours=1)),
        end_date=to_iso(datetime.now(timezone.utc).replace(microsecond=0)),
    )
    assert_that(response.status_code, equal_to(200), response.text[:200])
    return {
        row["name"]: row["count"] for row in response.json()["data"]["skills_invoked"]
    }


def _catalog_money(model, tokens: tuple[int, int]) -> float:
    """Tokens × the model's catalog price: the money CLI Analytics serves."""
    input_tokens, output_tokens = tokens
    return input_tokens * model.cost.input + output_tokens * model.cost.output


def _assert_row(row: dict, run_ms: int, tokens: tuple[int, int], money: float, what):
    assert_that(  # repro:symptom
        row,
        has_entries(
            duration_ms=run_ms,
            input_tokens=tokens[0],
            output_tokens=tokens[1],
        ),
        f"{what}: run and tokens of its own requests",
    )
    assert_that(  # repro:symptom
        row["cost_usd"],
        close_to(money, COST_TOLERANCE),
        f"{what}: cost of its own requests at the catalog price",
    )


def _row_has_tokens(detail: dict, tokens: tuple[int, int]) -> bool:
    """Whether the session's only Timeline row carries ``tokens``: the rollup has the
    session's requests."""
    rows = _timeline_rows(detail)
    return (
        len(rows) == 1 and (rows[0]["input_tokens"], rows[0]["output_tokens"]) == tokens
    )


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "build_seed",
    [get_slash_fork_seed, get_skill_call_fork_seed],
    ids=["slash-command", "skill-tool"],
)
def test_forked_skill_counts_once_as_a_skill(
    analytics_utils,
    seed_skill_sessions,
    cli_analytics_project,
    cost_model,
    build_seed,
):
    """A forked skill, started by a slash command or by the model's Skill
    call, is one skill invocation and no agent. Its fork is not counted again, and the
    Timeline has one row for it with the fork's run, tokens and cost."""
    seed = build_seed(cost_model.base_name)
    seed_skill_sessions(seed)
    fork = seed.forks[0]
    tokens = seed.tokens_of("fork")

    detail = _wait_for_detail(
        analytics_utils,
        seed.session_id,
        lambda d: d["skill_count"] == 1 and _row_has_tokens(d, tokens),
    )
    assert_that(  # repro:symptom
        (detail["skill_count"], detail["agent_count"]),
        is_in([(1, None), (1, 0)]),
        "skill and agent counts of a session that ran one forked skill",
    )
    assert_that(  # repro:symptom
        _skills_invoked(analytics_utils, cli_analytics_project, seed),
        has_entry(seed.skill, 1),
        "Tools & Models > Skills invoked: the seed's skill once (the module's other "
        "sessions run skills of their own names)",
    )
    _assert_row(
        _skill_row(detail, seed.skill),
        fork.run_ms,
        tokens,
        _catalog_money(cost_model, tokens),
        f"forked skill row ({seed.key})",
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_inline_slash_skill_row_has_its_own_run_tokens_and_cost(
    analytics_utils, seed_skill_sessions, cost_model
):
    """The Timeline row of an inline skill run as a slash command carries
    the requests the CLI attributed to the skill, from the command to the last of them.
    The prompt's other request and a later prompt's request are not the skill's."""
    seed = get_inline_slash_seed(cost_model.base_name)
    seed_skill_sessions(seed)
    tokens = seed.tokens_of(*INLINE_SKILL_REQUESTS)

    detail = _wait_for_detail(
        analytics_utils, seed.session_id, lambda d: _row_has_tokens(d, tokens)
    )
    _assert_row(
        _skill_row(detail, seed.skill),
        INLINE_SKILL_RUN_MS,
        tokens,
        _catalog_money(cost_model, tokens),
        "inline slash skill row",
    )
    assert_that(detail["skill_count"], is_(1), "skill count")


@pytest.mark.cli_analytics
@pytest.mark.api
def test_foreground_slash_fork_row_takes_its_own_requests(
    analytics_utils, seed_skill_sessions, cost_model
):
    """A fork a slash command runs in the foreground (Claude Code desktop
    app) is named on none of its requests. Its Timeline row takes the request the CLI sent
    under the fork's agent id: not the main thread's request of the same prompt."""
    seed = get_foreground_fork_seed(cost_model.base_name)
    seed_skill_sessions(seed)
    fork = seed.forks[0]
    tokens = seed.tokens_of("fork")

    detail = _wait_for_detail(
        analytics_utils, seed.session_id, lambda d: _row_has_tokens(d, tokens)
    )
    _assert_row(
        _skill_row(detail, seed.skill),
        fork.run_ms,
        tokens,
        _catalog_money(cost_model, tokens),
        "foreground slash fork row",
    )
