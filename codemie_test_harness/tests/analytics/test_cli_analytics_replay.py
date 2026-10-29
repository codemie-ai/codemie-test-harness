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

"""CLI Analytics ingest replay: events sent twice are counted once."""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    day_window,
    get_replay_session_seeds,
    tokens_by_session,
    total_tokens,
    with_session_end,
)


@pytest.fixture(scope="module")
def replayed_sessions(analytics_utils, seed_cli_sessions, ingest_cli_sessions):
    """Sessions whose events were ingested, rolled up and then sent again unchanged.

    Each replay request also carries the session's end, the one event that is new.
    The backend stores a request in one transaction and recomputes a session from
    all of its stored events, so a rollup that shows the end has also counted
    whatever else that request stored.
    """
    seeds = get_replay_session_seeds()
    seed_cli_sessions(seeds)
    ingest_cli_sessions([with_session_end(seed) for seed in seeds])
    for seed in seeds:
        analytics_utils.wait_for_cli_session_end(seed.session_id)
    return seeds


@pytest.mark.cli_analytics
@pytest.mark.api
def test_replayed_events_do_not_add_to_totals(
    analytics_utils, cli_analytics_project, replayed_sessions
):
    """Session count and token total count every replayed session once."""
    kpis = analytics_utils.get_cli_analytics_cost(
        projects=cli_analytics_project, **day_window().params()
    ).data.kpis

    assert_that(kpis.total_sessions, equal_to(len(replayed_sessions)))
    assert_that(kpis.total_tokens, equal_to(total_tokens(replayed_sessions)))


@pytest.mark.cli_analytics
@pytest.mark.api
def test_replayed_events_do_not_add_to_session_tokens(
    analytics_utils, cli_analytics_project, replayed_sessions
):
    """Each replayed session is listed once, with the tokens of a single send."""
    sessions = analytics_utils.get_cli_analytics_sessions(
        projects=cli_analytics_project, **day_window().params()
    ).data.sessions

    assert_that(len(sessions), equal_to(len(replayed_sessions)))
    assert_that(
        {
            session.trace_id: (session.input_tokens, session.output_tokens)
            for session in sessions
        },
        equal_to(tokens_by_session(replayed_sessions)),
    )
