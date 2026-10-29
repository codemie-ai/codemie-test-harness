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

"""CLI Analytics aggregation: seeded sessions rolled up to session, user and total."""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    AGGREGATION_WINDOWS,
    BOTH_DAYS_WINDOW,
    CLI_ANALYTICS_USERS,
    SESSIONS_PER_PAGE,
    get_aggregation_session_seeds,
    get_window,
    seeds_in_window,
    tokens_by_session,
    total_tokens,
    totals_by_user,
)


@pytest.fixture(scope="module")
def aggregation_sessions(seed_cli_sessions):
    """Two users' sessions over two adjacent UTC days."""
    return list(seed_cli_sessions(get_aggregation_session_seeds()).values())


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("window_name", AGGREGATION_WINDOWS)
def test_totals_match_seeded_sessions(
    analytics_utils, cli_analytics_project, aggregation_sessions, window_name
):
    """Session count and token total are the sums over the window's sessions."""
    window = get_window(window_name)
    expected_sessions = seeds_in_window(aggregation_sessions, window)

    kpis = analytics_utils.get_cli_analytics_cost(
        projects=cli_analytics_project, **window.params()
    ).data.kpis

    assert_that(kpis.total_sessions, equal_to(len(expected_sessions)))
    assert_that(kpis.total_tokens, equal_to(total_tokens(expected_sessions)))


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("window_name", AGGREGATION_WINDOWS)
def test_user_rows_match_each_users_sessions(
    analytics_utils,
    cli_analytics_project,
    cli_analytics_users,
    aggregation_sessions,
    window_name,
):
    """There is one row per user, holding that user's own sessions and tokens."""
    window = get_window(window_name)
    expected_rows = {
        cli_analytics_users[role].email: totals
        for role, totals in totals_by_user(
            seeds_in_window(aggregation_sessions, window)
        ).items()
    }

    rows = analytics_utils.get_cli_analytics_users(
        projects=cli_analytics_project, **window.params()
    ).data.rows

    assert_that(len(rows), equal_to(len(expected_rows)))
    assert_that(
        {
            row.developer_name: (row.session_count, row.input_tokens, row.output_tokens)
            for row in rows
        },
        equal_to(expected_rows),
    )


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("window_name", AGGREGATION_WINDOWS)
def test_session_list_matches_seeded_sessions(
    analytics_utils, cli_analytics_project, aggregation_sessions, window_name
):
    """Each of the window's sessions is listed once, with its own tokens."""
    window = get_window(window_name)
    expected_sessions = seeds_in_window(aggregation_sessions, window)

    data = analytics_utils.get_cli_analytics_sessions(
        projects=cli_analytics_project, **window.params()
    ).data

    assert_that(data.total, equal_to(len(expected_sessions)))
    assert_that(len(data.sessions), equal_to(len(expected_sessions)))
    assert_that(
        {
            session.trace_id: (session.input_tokens, session.output_tokens)
            for session in data.sessions
        },
        equal_to(tokens_by_session(expected_sessions)),
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_session_pages_together_hold_every_session_once(
    analytics_utils, cli_analytics_project, aggregation_sessions
):
    """Read page by page, the session list reports the full count on every page and
    gives each session on exactly one page."""
    window = get_window(BOTH_DAYS_WINDOW)
    expected_ids = sorted(
        seed.session_id for seed in seeds_in_window(aggregation_sessions, window)
    )
    page_count = -(-len(expected_ids) // SESSIONS_PER_PAGE)

    listed_ids = []
    for page in range(page_count):
        data = analytics_utils.get_cli_analytics_sessions(
            projects=cli_analytics_project,
            page=page,
            per_page=SESSIONS_PER_PAGE,
            **window.params(),
        ).data
        assert_that(data.total, equal_to(len(expected_ids)), f"Total on page {page}")
        assert_that(
            len(data.sessions),
            equal_to(min(SESSIONS_PER_PAGE, len(expected_ids) - len(listed_ids))),
            f"Sessions on page {page}",
        )
        listed_ids += [session.trace_id for session in data.sessions]

    assert_that(sorted(listed_ids), equal_to(expected_ids))


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("identifier", ["email", "user_id"])
@pytest.mark.parametrize("user", CLI_ANALYTICS_USERS)
def test_users_filter_selects_only_that_users_sessions(
    analytics_utils,
    cli_analytics_project,
    cli_analytics_users,
    aggregation_sessions,
    user,
    identifier,
):
    """Filtering by a user, given by email or by user id, leaves only that user's
    sessions in the totals and in the session list."""
    window = get_window(BOTH_DAYS_WINDOW)
    expected_sessions = [
        seed
        for seed in seeds_in_window(aggregation_sessions, window)
        if seed.user == user
    ]
    filters = {
        "projects": cli_analytics_project,
        "users": getattr(cli_analytics_users[user], identifier),
        **window.params(),
    }

    kpis = analytics_utils.get_cli_analytics_cost(**filters).data.kpis
    sessions = analytics_utils.get_cli_analytics_sessions(**filters).data.sessions

    assert_that(kpis.total_sessions, equal_to(len(expected_sessions)))
    assert_that(kpis.total_tokens, equal_to(total_tokens(expected_sessions)))
    assert_that(len(sessions), equal_to(len(expected_sessions)))
    assert_that(
        {
            session.trace_id: (session.input_tokens, session.output_tokens)
            for session in sessions
        },
        equal_to(tokens_by_session(expected_sessions)),
    )
