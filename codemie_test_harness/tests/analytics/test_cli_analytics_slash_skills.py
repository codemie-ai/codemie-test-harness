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


"""CLI Analytics: a skill is a skill however it was started (typed slash command or Skill tool).

Session Detail must show kind `skill` and count it once; Tools & Models must list it under
Skills only, not also under Slash Commands.

A session is rolled up in separate batches (hooks, command logs, Skill-tool spans, model
requests), so a rolled-up session does not yet carry everything a test reads. Each test
waits, with a deadline, for the positive data it reads, and a "not listed" check waits for
an ordinary slash command of the same log batch first: an absence must not pass because the
batch is not processed yet.
"""

# slash-skill-classification_TC_001 coverage: steps 1-2
# slash-skill-classification_TC_002 coverage: steps 1-2
# slash-skill-classification_TC_003 coverage: steps 1-3
# slash-skill-classification_TC_004 coverage: steps 1-3
# slash-skill-classification_TC_005 coverage: steps 1-4
# slash-skill-classification_TC_006 coverage: steps 1-2

import pytest
from hamcrest import (
    assert_that,
    close_to,
    equal_to,
    greater_than,
    has_entry,
    has_item,
    is_not,
    not_none,
)

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    COST_TOLERANCE,
    MAIN_REQUEST_DELAY,
    PLAIN_COMMAND_KEY,
    SESSION_DURATION,
    SKILL_COST_KEY,
    SLASH_SKILL_KEY,
    SLASH_SKILL_REQUEST_DELAY,
    TOOL_SKILL_KEY,
    day_window,
    get_plain_command_session_seed,
    get_slash_skill_cost_session_seed,
    get_slash_skill_session_seeds,
    session_catalog_cost,
    with_session_end,
)
from codemie_test_harness.tests.utils.analytics_utils import CLI_SESSION_ROLLUP_TIMEOUT
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi

BASE = "/v1/analytics/cli-analytics"
# The rollup job runs every 30 s by default; the data of one test span a few batches.
READY_TIMEOUT = CLI_SESSION_ROLLUP_TIMEOUT
POLL_INTERVAL = 5
# Answers of a stand that is down or restarting, not of the feature under test.
STAND_UNAVAILABLE = (502, 503, 504)


class StandUnavailable(Exception):
    """The stand answered 502/503/504 until the deadline: nothing was asserted."""


@pytest.fixture(scope="module")
def skill_sessions(seed_cli_sessions):
    """A slash-started and a Skill-tool-started skill session, rolled up; keyed by case."""
    return seed_cli_sessions(get_slash_skill_session_seeds())


@pytest.fixture(scope="module")
def plain_command_session(seed_cli_sessions):
    """A session whose only slash command is no skill."""
    return seed_cli_sessions([get_plain_command_session_seed()])[PLAIN_COMMAND_KEY]


@pytest.fixture(scope="module")
def costly_skill_session(seed_cli_sessions, cost_model):
    """A slash-started skill that earned a priced model request, in a session that also
    did unrelated main-thread work."""
    seed = get_slash_skill_cost_session_seed(cost_model.base_name)
    return seed_cli_sessions([seed])[SKILL_COST_KEY]


def _await(analytics_utils, path, params, ready, awaited, describe):
    """GET ``path`` until ``ready(data)`` holds or READY_TIMEOUT passes; return the data.

    A 502/503/504 is waited out and, when it lasts, raised as StandUnavailable; any other
    status or an unmet condition is an AssertionError that says what was awaited and what
    the last answer held."""
    api = CliAnalyticsApi(analytics_utils.client)

    def read():
        response = api.request("GET", path, params=params)
        data = response.json()["data"] if response.status_code == 200 else None
        return response.status_code, data

    status, data = poll_until(
        read,
        lambda answer: answer[1] is not None and ready(answer[1]),
        timeout=READY_TIMEOUT,
        interval=POLL_INTERVAL,
    )
    if status in STAND_UNAVAILABLE:
        raise StandUnavailable(f"HTTP {status} from {path} for {READY_TIMEOUT}s")
    assert_that(status, equal_to(200), f"status of GET {path}")
    assert_that(
        ready(data),
        equal_to(True),
        f"{awaited} within {READY_TIMEOUT}s; last answer: {describe(data)}",
    )
    return data


def _tools(analytics_utils, project, ready, awaited) -> dict:
    """Tools & Models of the project and day, once ``ready(data)`` holds."""
    return _await(
        analytics_utils,
        f"{BASE}/tools",
        {**day_window().params(), "projects": project},
        ready,
        awaited,
        lambda data: {
            "skills_invoked": data["skills_invoked"],
            "slash_commands": data["slash_commands"],
        },
    )


def _skills(data: dict) -> dict[str, int]:
    return {row["name"]: row["count"] for row in data["skills_invoked"]}


def _commands(data: dict) -> dict[str, int]:
    return {row["name"]: row["count"] for row in data["slash_commands"]}


def _session_detail(analytics_utils, seed, ready, awaited) -> dict:
    """Session Detail of the seed's session, once ``ready(detail)`` holds."""
    return _await(
        analytics_utils,
        f"{BASE}/sessions/{seed.session_id}",
        None,
        ready,
        awaited,
        lambda data: {
            "skill_count": data.get("skill_count"),
            "dispatches": data["dispatches"],
        },
    )


def _bar(detail: dict, name: str) -> dict | None:
    """The timeline bar of the skill or command ``name``, whatever kind it was given."""
    return next(
        (d for d in detail["dispatches"] if d["label"].endswith(f" · {name}")), None
    )


def _skill_bars(detail: dict) -> dict[str, str]:
    """Label -> kind of every bar of the Session Detail timeline."""
    return {d["label"]: d["kind"] for d in detail["dispatches"]}


def _has_bar(name: str):
    return lambda detail: _bar(detail, name) is not None


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.parametrize("case", [SLASH_SKILL_KEY, TOOL_SKILL_KEY])
@pytest.mark.api
def test_session_detail_shows_started_skill_as_skill_bar(
    analytics_utils, skill_sessions, case
):
    """@case slash-skill-classification_TC_001
    catches: a skill typed as a slash command is shown as "command · name" with kind
    `command` in Session Detail while the same skill started through the Skill tool is
    a `skill` bar."""
    seed = skill_sessions[case]
    detail = _session_detail(
        analytics_utils,
        seed,
        _has_bar(seed.skill_name),
        f"a timeline bar for {seed.skill_name}",
    )
    bars = _skill_bars(detail)

    assert_that(
        bars,
        has_entry(f"skill · {seed.skill_name}", "skill"),
        f"timeline labels and kinds: {bars}",
    )


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.parametrize("case", [SLASH_SKILL_KEY, TOOL_SKILL_KEY])
@pytest.mark.api
def test_session_detail_skill_count_matches_skill_bars(
    analytics_utils, skill_sessions, case
):
    """@case slash-skill-classification_TC_002
    catches: Session Detail Skills count says 1 while the timeline has no skill bar
    for a slash-started skill."""
    seed = skill_sessions[case]
    detail = _session_detail(
        analytics_utils,
        seed,
        lambda d: _bar(d, seed.skill_name) is not None and d["skill_count"] is not None,
        f"a timeline bar for {seed.skill_name} and a Skills count",
    )
    skill_bars = [d for d in detail["dispatches"] if d["kind"] == "skill"]

    assert_that(detail["skill_count"], equal_to(1), "Skills count of the session")
    assert_that(len(skill_bars), equal_to(1), "skill bars of the timeline")


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.parametrize("case", [SLASH_SKILL_KEY, TOOL_SKILL_KEY])
@pytest.mark.api
def test_tools_and_models_lists_started_skill_under_skills_only(
    analytics_utils, cli_analytics_project, skill_sessions, case
):
    """@case slash-skill-classification_TC_003
    catches: Tools & Models counts a slash-started skill under Skills and again under
    Slash Commands (the Skill-tool skill is the control: Skills only).

    The session's ordinary slash command, sent in the same log batch, is the control that
    the commands were processed: it is awaited first and must stay a command."""
    seed = skill_sessions[case]
    data = _tools(
        analytics_utils,
        cli_analytics_project,
        lambda d: seed.skill_name in _skills(d) and seed.command_name in _commands(d),
        f"{seed.skill_name} under Skills and the control command {seed.command_name} "
        "under Slash Commands",
    )

    assert_that(_skills(data), has_entry(seed.skill_name, 1), "Skills Invoked")
    assert_that(_commands(data), has_entry(seed.command_name, 1), "control command")
    assert_that(
        list(_commands(data)), is_not(has_item(seed.skill_name)), "Slash Commands"
    )
    assert_that(
        list(_skills(data)), is_not(has_item(seed.command_name)), "Skills Invoked"
    )


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_plain_slash_command_stays_a_command(
    analytics_utils, cli_analytics_project, plain_command_session
):
    """@case slash-skill-classification_TC_004
    catches: the skill/command de-duplication swallows a typed slash command that is
    no skill, so it disappears from Slash Commands or is listed as a skill."""
    seed = plain_command_session
    name = seed.command_name

    data = _tools(
        analytics_utils,
        cli_analytics_project,
        lambda d: name in _commands(d),
        f"{name} under Slash Commands",
    )
    detail = _session_detail(
        analytics_utils, seed, lambda d: True, "the session detail"
    )

    assert_that(_commands(data), has_entry(name, 1), "Slash Commands")
    assert_that(list(_skills(data)), is_not(has_item(name)), "Skills Invoked")
    assert_that(
        [d["label"] for d in detail["dispatches"] if d["kind"] == "skill"],
        equal_to([]),
        "skill bars of the session",
    )
    assert_that(detail["skill_count"] or 0, equal_to(0), "Skills count")


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_slash_started_skill_keeps_its_cost_tokens_and_duration(
    analytics_utils, cost_model, costly_skill_session
):
    """@case slash-skill-classification_TC_005
    catches: classifying a slash-started skill as a skill drops the cost, tokens or
    run time its own model request earned, or hands it those of the whole session. The
    session also did main-thread work under another prompt, so its totals and length
    differ from the skill's."""
    seed = costly_skill_session
    main = seed.main_request
    skill_cost = session_catalog_cost(seed, cost_model.cost)
    main_cost = main.input_tokens * cost_model.cost.input + (
        main.output_tokens * cost_model.cost.output
    )
    total_input = seed.input_tokens + main.input_tokens
    total_output = seed.output_tokens + main.output_tokens
    session_floor_ms = MAIN_REQUEST_DELAY.total_seconds() * 1000

    def counted(detail):
        bar = _bar(detail, seed.skill_name)
        return (
            bar is not None
            and detail["input_tokens"] == total_input
            and detail["output_tokens"] == total_output
            and detail["duration_ms"] > session_floor_ms
        )

    detail = _session_detail(
        analytics_utils,
        seed,
        counted,
        f"the skill bar with its values, session totals {total_input}/{total_output} "
        f"and a session run time past {session_floor_ms:.0f} ms",
    )
    bar = _bar(detail, seed.skill_name)

    assert_that(bar, not_none(), "skill bar of the slash-started skill")
    assert_that(bar["kind"], equal_to("skill"))
    assert_that(bar["input_tokens"], equal_to(seed.input_tokens), "skill input tokens")
    assert_that(
        bar["output_tokens"], equal_to(seed.output_tokens), "skill output tokens"
    )
    assert_that(
        bar["cost_usd"],
        close_to(skill_cost, COST_TOLERANCE),
        "skill cost, catalog price",
    )
    assert_that(
        bar["duration_ms"],
        close_to(SLASH_SKILL_REQUEST_DELAY.total_seconds() * 1000, 1000),
        "skill run time = dispatch to its own last request",
    )
    # The session is demonstrably larger than the skill: the skill must not own it.
    assert_that(
        detail["cost_usd"],
        close_to(skill_cost + main_cost, COST_TOLERANCE),
        "session cost, catalog price",
    )
    assert_that(
        detail["duration_ms"],
        greater_than(session_floor_ms),
        "session run time reaches past the skill",
    )


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_resent_skill_tool_seed_is_counted_once(
    analytics_utils, ingest_cli_sessions, cli_analytics_users, skill_sessions
):
    """@case slash-skill-classification_TC_006
    catches: a seed sent again (as the seed fixture does for a send that failed part-way)
    builds new span ids and the backend counts the Skill-tool call twice.

    The resend also carries the session end, which is new and is the only thing that moves
    the session's run time to the end's: once that shows, the request has been stored
    together with the spans and logs it was sent with. The timeline bars are
    read from the stored spans, so they show a duplicate at once; the Skills count is a
    rollup that may not yet reflect the resent spans, so it cannot prove an absence on its
    own. The test adds the end to the module's shared Skill-tool session and runs after
    the tests that read it (no other test reads that session's duration)."""
    seed = skill_sessions[TOOL_SKILL_KEY]
    email = cli_analytics_users[seed.user].email
    assert_that(
        seed.otlp_traces(email), equal_to(seed.otlp_traces(email)), "same spans"
    )

    ingest_cli_sessions([with_session_end(seed)])
    end_ms = SESSION_DURATION.total_seconds() * 1000
    detail = _session_detail(
        analytics_utils,
        seed,
        lambda d: d["duration_ms"] >= end_ms and d["skill_count"] is not None,
        f"the session end of the resend (run time of {end_ms:.0f} ms) and a Skills count",
    )
    skill_bars = [d for d in detail["dispatches"] if d["kind"] == "skill"]
    assert_that(detail["skill_count"], equal_to(1), "Skills count after the resend")
    assert_that(len(skill_bars), equal_to(1), "skill bars after the resend")
