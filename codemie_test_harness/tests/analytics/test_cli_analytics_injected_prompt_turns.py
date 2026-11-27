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

"""CLI Analytics turns: messages Claude Code injects into a session are not turns."""

import pytest
from hamcrest import assert_that, equal_to, is_

from codemie_test_harness.tests.test_data.cli_analytics_test_data import OWNER
from codemie_test_harness.tests.test_data.cli_analytics_turns_test_data import (
    ClaudeCodeTurnsSeed,
    get_injected_prompt_seeds,
    get_late_hook_seed,
    get_typed_prompts_seed,
)

# The next rollup refresh (30 s by default) after the typed prompt was counted.
INJECTED_PROMPT_ROLLUP_TIMEOUT = 90


@pytest.fixture(scope="module")
def injected_prompt_sessions(ingest_cli_sessions):
    """One Claude Code session per kind of injected prompt, keyed by scenario id: hooks,
    logs and spans, each as the seed's user (the owner)."""
    seeds = get_injected_prompt_seeds()
    ingest_cli_sessions(list(seeds.values()))
    return seeds


def _wait_until_rolled_up(analytics_utils, seed: ClaudeCodeTurnsSeed) -> None:
    """Wait until the session's typed prompt is counted: the turn rollup has run."""
    analytics_utils.wait_for_cli_session(seed.session_id)
    turns = analytics_utils.wait_for_cli_session_turns(
        seed.session_id, lambda turns: turns >= 1
    )
    assert_that(  # repro:precondition
        turns is not None and turns >= 1,
        is_(True),
        f"setup: the typed prompt of session {seed.session_id} was not counted "
        f"(turns={turns!r}), so the session never reached the turn rollup",
    )


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "scenario",
    [
        "subagent-hand-back",
        "unanswered-task-notification",
        "answered-task-notification",
        "parallel-subagent-hand-backs",
    ],
)
def test_session_turns_exclude_injected_prompts(
    analytics_utils, injected_prompt_sessions, scenario
):
    """A session with one typed prompt and messages Claude Code injected itself (subagent
    hand-backs, a task notification answered or not) has one turn. No client summary is
    sent, so the served turns are the ones the backend counted."""
    seed = injected_prompt_sessions[scenario]
    _wait_until_rolled_up(analytics_utils, seed)

    turns = analytics_utils.wait_for_cli_session_turns(
        seed.session_id,
        lambda turns: turns == seed.expected_turns,
        timeout=INJECTED_PROMPT_ROLLUP_TIMEOUT,
    )
    assert_that(  # repro:symptom
        turns,
        equal_to(seed.expected_turns),
        f"turns of a session with one typed prompt and injected prompts ({scenario})",
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_typed_prompt_that_looks_like_a_hand_back_is_a_turn(
    analytics_utils, ingest_cli_sessions
):
    """A prompt the user typed that starts "Another Claude session sent a message:" is a
    turn: only the tag Claude Code injects marks a hand-back. With a real hand-back
    between the two typed prompts, the session has two turns. No client summary is sent,
    so the served turns are the ones the backend counted."""
    seed = get_typed_prompts_seed()
    ingest_cli_sessions([seed])
    _wait_until_rolled_up(analytics_utils, seed)

    turns = analytics_utils.wait_for_cli_session_turns(
        seed.session_id,
        lambda turns: turns == seed.expected_turns,
        timeout=INJECTED_PROMPT_ROLLUP_TIMEOUT,
    )
    assert_that(  # repro:symptom
        turns,
        equal_to(seed.expected_turns),
        "turns of a session with two typed prompts, one starting like a hand-back, "
        "and one subagent hand-back",
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_late_prompt_hook_recounts_the_injected_prompt(
    analytics_utils, ingest_cli_sessions, cli_analytics_users, cli_analytics_project
):
    """When the prompt hook of a subagent hand-back reaches the backend after the session
    was rolled up, the session's turns are counted again and the hand-back stops being a
    turn. No client summary is sent, so the served turns are the ones the backend counted."""
    seed = get_late_hook_seed()
    ingest_cli_sessions([seed])
    analytics_utils.wait_for_cli_session(seed.session_id)

    turns_before = analytics_utils.wait_for_cli_session_turns(
        seed.session_id, lambda turns: turns == seed.turns_before_late_hooks
    )
    assert_that(  # repro:precondition
        turns_before,
        equal_to(seed.turns_before_late_hooks),
        f"setup: before its hook arrived, the answered hand-back of session "
        f"{seed.session_id} was not counted like a typed prompt",
    )

    cli_analytics_users[OWNER].analytics_utils.ingest_cli_event_hooks(
        seed.late_events(cli_analytics_project), project=cli_analytics_project
    )

    turns = analytics_utils.wait_for_cli_session_turns(
        seed.session_id,
        lambda turns: turns == seed.expected_turns,
        timeout=INJECTED_PROMPT_ROLLUP_TIMEOUT,
    )
    assert_that(  # repro:symptom
        turns,
        equal_to(seed.expected_turns),
        "turns of a session after the late prompt hook of its hand-back arrived",
    )
