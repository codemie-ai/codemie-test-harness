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

"""CLI Analytics date filtering: sessions on the bounds of the requested window."""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    BOUNDARY_SESSION_KEYS,
    WINDOW_UTC_OFFSETS,
    day_window,
    get_boundary_session_seeds,
    seeds_in_window,
    to_iso,
    total_tokens,
)


@pytest.fixture(scope="module")
def boundary_sessions(seed_cli_sessions):
    """Sessions around both bounds of the seed day; seeds keyed by boundary case."""
    return seed_cli_sessions(get_boundary_session_seeds())


def _listed_session_ids(analytics_utils, project_name: str, **window_params) -> list:
    sessions = analytics_utils.get_cli_analytics_sessions(
        projects=project_name, **window_params
    ).data.sessions
    return sorted(session.trace_id for session in sessions)


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("boundary", BOUNDARY_SESSION_KEYS)
def test_session_is_listed_only_if_it_started_in_window(
    analytics_utils, cli_analytics_project, boundary_sessions, boundary
):
    """A session is listed if and only if it started within the window, bounds
    included, whatever UTC offset its timestamp was reported with."""
    window = day_window()
    seed = boundary_sessions[boundary]

    listed_ids = _listed_session_ids(
        analytics_utils, cli_analytics_project, **window.params()
    )

    assert_that(
        seed.session_id in listed_ids,
        equal_to(window.start <= seed.started_at <= window.end),
        f"Session started at {to_iso(seed.started_at)}, window "
        f"{to_iso(window.start)}..{to_iso(window.end)}",
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_sessions_outside_window_do_not_add_to_totals(
    analytics_utils, cli_analytics_project, boundary_sessions
):
    """Totals of a window come from the sessions that started within it only."""
    window = day_window()
    expected_sessions = seeds_in_window(list(boundary_sessions.values()), window)

    kpis = analytics_utils.get_cli_analytics_cost(
        projects=cli_analytics_project, **window.params()
    ).data.kpis

    assert_that(kpis.total_sessions, equal_to(len(expected_sessions)))
    assert_that(kpis.total_tokens, equal_to(total_tokens(expected_sessions)))


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("utc_offset_hours", WINDOW_UTC_OFFSETS)
def test_window_bounds_with_utc_offset_select_same_sessions(
    analytics_utils, cli_analytics_project, boundary_sessions, utc_offset_hours
):
    """Window bounds written with a UTC offset select by the instants they name."""
    window = day_window()
    expected_sessions = seeds_in_window(list(boundary_sessions.values()), window)

    listed_ids = _listed_session_ids(
        analytics_utils, cli_analytics_project, **window.params(utc_offset_hours)
    )

    assert_that(
        listed_ids, equal_to(sorted(seed.session_id for seed in expected_sessions))
    )
