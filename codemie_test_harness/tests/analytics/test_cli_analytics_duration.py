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

"""CLI Analytics session duration: from a session's start to its last event."""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    day_window,
    duration_ms,
    get_duration_session_seeds,
)


@pytest.fixture(scope="module")
def duration_sessions(seed_cli_sessions):
    """Sessions of known length, and one that never reported an end."""
    return list(seed_cli_sessions(get_duration_session_seeds()).values())


@pytest.mark.cli_analytics
@pytest.mark.api
def test_session_duration_is_time_from_start_to_end(
    analytics_utils, cli_analytics_project, duration_sessions
):
    """Each session lasts from its start to its end event; a session that reported
    no end lasts 0."""
    sessions = analytics_utils.get_cli_analytics_sessions(
        projects=cli_analytics_project, **day_window().params()
    ).data.sessions

    assert_that(len(sessions), equal_to(len(duration_sessions)))
    assert_that(
        {session.trace_id: session.duration_ms for session in sessions},
        equal_to({seed.session_id: duration_ms(seed) for seed in duration_sessions}),
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_average_session_duration_is_mean_over_window_sessions(
    analytics_utils, cli_analytics_project, duration_sessions
):
    """The average duration is the mean over every session of the window, sessions
    of 0 length included."""
    expected_average = sum(duration_ms(seed) for seed in duration_sessions) // len(
        duration_sessions
    )

    data = analytics_utils.get_cli_analytics_users(
        projects=cli_analytics_project, **day_window().params()
    ).data

    assert_that(data.avg_session_duration_ms, equal_to(expected_average))
