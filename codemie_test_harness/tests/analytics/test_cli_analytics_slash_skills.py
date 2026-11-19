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
"""

# slash-skill-classification_TC_001 coverage: steps 1-2
# slash-skill-classification_TC_002 coverage: steps 1-2
# slash-skill-classification_TC_003 coverage: steps 1-3
# slash-skill-classification_TC_004 coverage: steps 1-3
# slash-skill-classification_TC_005 coverage: steps 1-4

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
    PLAIN_COMMAND_KEY,
    SKILL_COST_KEY,
    SLASH_SKILL_KEY,
    SLASH_SKILL_REQUEST_DELAY,
    TOOL_SKILL_KEY,
    day_window,
    get_plain_command_session_seed,
    get_slash_skill_cost_session_seed,
    get_slash_skill_session_seeds,
    session_catalog_cost,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi

BASE = "/v1/analytics/cli-analytics"


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
    """A slash-started skill that earned a priced model request."""
    seed = get_slash_skill_cost_session_seed(cost_model.base_name)
    return seed_cli_sessions([seed])[SKILL_COST_KEY]


def _tools(analytics_utils, project: str) -> dict:
    response = CliAnalyticsApi(analytics_utils.client).request(
        "GET",
        f"{BASE}/tools",
        params={**day_window().params(), "projects": project},
    )
    assert_that(response.status_code, equal_to(200))
    return response.json()["data"]


def _session_detail(analytics_utils, seed) -> dict:
    response = CliAnalyticsApi(analytics_utils.client).request(
        "GET", f"{BASE}/sessions/{seed.session_id}"
    )
    assert_that(response.status_code, equal_to(200))
    return response.json()["data"]


def _skill_bars(detail: dict) -> dict[str, str]:
    """Label -> kind of every bar of the Session Detail timeline."""
    return {d["label"]: d["kind"] for d in detail["dispatches"]}


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
    bars = _skill_bars(_session_detail(analytics_utils, seed))

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
    detail = _session_detail(analytics_utils, skill_sessions[case])
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
    Slash Commands (the Skill-tool skill is the control: Skills only)."""
    name = skill_sessions[case].skill_name
    data = _tools(analytics_utils, cli_analytics_project)

    skills = {row["name"]: row["count"] for row in data["skills_invoked"]}
    commands = [row["name"] for row in data["slash_commands"]]

    assert_that(skills, has_entry(name, 1), "Skills Invoked")
    assert_that(commands, is_not(has_item(name)), "Slash Commands")


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_plain_slash_command_stays_a_command(
    analytics_utils, cli_analytics_project, plain_command_session
):
    """@case slash-skill-classification_TC_004
    catches: the skill/command de-duplication swallows a typed slash command that is
    no skill, so it disappears from Slash Commands or is listed as a skill."""
    name = plain_command_session.command_name

    data = _tools(analytics_utils, cli_analytics_project)
    detail = _session_detail(analytics_utils, plain_command_session)

    commands = {row["name"]: row["count"] for row in data["slash_commands"]}
    assert_that(commands, has_entry(name, 1), "Slash Commands")
    assert_that(
        [row["name"] for row in data["skills_invoked"]],
        is_not(has_item(name)),
        "Skills Invoked",
    )
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
    run time its own model request earned (they must stay on its skill bar)."""
    seed = costly_skill_session
    detail = _session_detail(analytics_utils, seed)
    bar = next(
        (d for d in detail["dispatches"] if d["label"] == f"skill · {seed.skill_name}"),
        None,
    )

    assert_that(bar, not_none(), "skill bar of the slash-started skill")
    assert_that(bar["kind"], equal_to("skill"))
    assert_that(bar["input_tokens"], equal_to(seed.input_tokens), "input tokens")
    assert_that(bar["output_tokens"], equal_to(seed.output_tokens), "output tokens")
    assert_that(
        bar["cost_usd"],
        close_to(session_catalog_cost(seed, cost_model.cost), COST_TOLERANCE),
        "cost at the catalog price",
    )
    assert_that(bar["duration_ms"], greater_than(0), "run time of the skill")
    assert_that(
        bar["duration_ms"],
        close_to(SLASH_SKILL_REQUEST_DELAY.total_seconds() * 1000, 1000),
        "run time = dispatch to its last request",
    )
