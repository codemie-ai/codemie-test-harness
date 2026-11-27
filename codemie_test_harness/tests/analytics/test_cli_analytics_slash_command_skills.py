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
    SlashSkillSeed,
    get_foreground_fork_seed,
    get_inline_slash_seed,
    get_skill_call_fork_seed,
    get_slash_fork_seed,
)
from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    COST_TOLERANCE,
    to_iso,
)


def _wait_for_detail(analytics_utils, seed: SlashSkillSeed, ready) -> dict:
    """The session detail ``data`` once ``ready(data)`` holds, or the last one read."""
    detail = analytics_utils.wait_for_cli_session_detail(
        seed.session_id, lambda d: ready(d["data"])
    )
    assert_that(  # repro:precondition
        detail,
        is_(dict),
        f"setup: session {seed.session_id} was never rolled up",
    )
    return detail["data"]


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
    assert_that(  # repro:symptom
        (row["kind"], row["label"]),
        equal_to(("skill", f"skill · {skill}")),
        "kind and label of the skill's Timeline row",
    )
    return row


def _skills_invoked(analytics_utils, project: str, seed: SlashSkillSeed) -> dict:
    """Skills invoked in the module's project from an hour before the seed up to now."""
    return analytics_utils.get_cli_skills_invoked(
        project,
        start_date=to_iso(seed.started_at - timedelta(hours=1)),
        end_date=to_iso(datetime.now(timezone.utc).replace(microsecond=0)),
    )


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
    ingest_cli_sessions,
    cli_analytics_project,
    cost_model,
    build_seed,
):
    """A forked skill, started by a slash command or by the model's Skill
    call, is one skill invocation and no agent. Its fork is not counted again, and the
    Timeline has one row for it with the fork's run, tokens and cost."""
    seed = build_seed(cost_model.base_name)
    ingest_cli_sessions([seed])
    fork = seed.forks[0]
    tokens = seed.tokens_of("fork")

    detail = _wait_for_detail(
        analytics_utils,
        seed,
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
    analytics_utils, ingest_cli_sessions, cost_model
):
    """The Timeline row of an inline skill run as a slash command carries
    the requests the CLI attributed to the skill, from the command to the last of them.
    The prompt's other request and a later prompt's request are not the skill's."""
    seed = get_inline_slash_seed(cost_model.base_name)
    ingest_cli_sessions([seed])
    tokens = seed.tokens_of(*INLINE_SKILL_REQUESTS)

    detail = _wait_for_detail(
        analytics_utils, seed, lambda d: _row_has_tokens(d, tokens)
    )
    _assert_row(
        _skill_row(detail, seed.skill),
        seed.inline_skill_run_ms,
        tokens,
        _catalog_money(cost_model, tokens),
        "inline slash skill row",
    )
    assert_that(detail["skill_count"], is_(1), "skill count")


@pytest.mark.cli_analytics
@pytest.mark.api
def test_foreground_slash_fork_row_takes_its_own_requests(
    analytics_utils, ingest_cli_sessions, cost_model
):
    """A fork a slash command runs in the foreground (Claude Code desktop
    app) is named on none of its requests. Its Timeline row takes the request the CLI sent
    under the fork's agent id: not the main thread's request of the same prompt."""
    seed = get_foreground_fork_seed(cost_model.base_name)
    ingest_cli_sessions([seed])
    fork = seed.forks[0]
    tokens = seed.tokens_of("fork")

    detail = _wait_for_detail(
        analytics_utils, seed, lambda d: _row_has_tokens(d, tokens)
    )
    _assert_row(
        _skill_row(detail, seed.skill),
        fork.run_ms,
        tokens,
        _catalog_money(cost_model, tokens),
        "foreground slash fork row",
    )
