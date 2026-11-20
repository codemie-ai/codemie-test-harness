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
    get_injected_prompt_seeds,
)

# The next rollup refresh (30 s by default) after the typed prompt was counted.
INJECTED_PROMPT_ROLLUP_TIMEOUT = 90


@pytest.fixture(scope="module")
def injected_prompt_sessions(
    ingest_cli_sessions, cli_analytics_users, cli_analytics_project
):
    """One Claude Code session per kind of injected prompt, each with a typed prompt
    and one injected prompt, sent as the owner (hooks and logs, then the spans)."""
    seeds = get_injected_prompt_seeds()
    ingest_cli_sessions(list(seeds.values()))
    for seed in seeds.values():
        cli_analytics_users[OWNER].analytics_utils.ingest_cli_otlp_traces(
            seed.otlp_traces(), project=cli_analytics_project
        )
    return seeds


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "scenario",
    ["subagent-hand-back", "unanswered-task-notification"],
)
def test_session_turns_exclude_injected_prompts(
    analytics_utils, injected_prompt_sessions, scenario
):
    """A session with one typed prompt and one message Claude Code injected itself (a hand-back,
    or an unanswered task notification), whose client summary counts both, has one turn."""
    seed = injected_prompt_sessions[scenario]
    analytics_utils.wait_for_cli_session(seed.session_id)

    typed_prompt_turns = analytics_utils.wait_for_cli_session_turns(
        seed.session_id, lambda turns: turns >= 1
    )
    assert_that(  # repro:precondition
        typed_prompt_turns is not None and typed_prompt_turns >= 1,
        is_(True),
        f"setup: the typed prompt of session {seed.session_id} was not counted "
        f"(turns={typed_prompt_turns!r}), so the session never reached the turn rollup",
    )

    turns = analytics_utils.wait_for_cli_session_turns(
        seed.session_id,
        lambda turns: turns == seed.expected_turns,
        timeout=INJECTED_PROMPT_ROLLUP_TIMEOUT,
    )
    assert_that(  # repro:symptom
        turns,
        equal_to(seed.expected_turns),
        f"turns of a session with one typed prompt and one injected prompt ({scenario})",
    )
