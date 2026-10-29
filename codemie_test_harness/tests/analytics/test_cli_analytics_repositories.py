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

"""CLI Analytics repositories: grouping and filtering of sessions reported with and
without a repository."""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    SEED_REPOSITORIES,
    day_window,
    get_repository_session_seeds,
    total_tokens,
)


@pytest.fixture(scope="module")
def repository_sessions(seed_cli_sessions):
    """Sessions reported from two repositories and a session reported without any."""
    return list(seed_cli_sessions(get_repository_session_seeds()).values())


@pytest.mark.cli_analytics
@pytest.mark.api
def test_repository_rows_group_sessions_by_repository(
    analytics_utils, cli_analytics_project, repository_sessions
):
    """There is one row per repository, and sessions without a repository are
    counted in a row of their own instead of being dropped or merged."""
    expected_counts: dict[str | None, int] = {}
    for seed in repository_sessions:
        expected_counts[seed.repository] = expected_counts.get(seed.repository, 0) + 1

    rows = analytics_utils.get_cli_analytics_repositories(
        projects=cli_analytics_project, **day_window().params()
    ).data.rows

    assert_that(len(rows), equal_to(len(expected_counts)))
    assert_that(
        {row.repository: row.session_count for row in rows}, equal_to(expected_counts)
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_unattributed_filter_lists_only_sessions_without_repository(
    analytics_utils, cli_analytics_project, repository_sessions
):
    """The unattributed filter selects exactly the sessions that have no repository."""
    expected_ids = sorted(
        seed.session_id for seed in repository_sessions if seed.repository is None
    )

    data = analytics_utils.get_cli_analytics_sessions(
        projects=cli_analytics_project, is_unattributed=True, **day_window().params()
    ).data

    assert_that(data.total, equal_to(len(expected_ids)))
    assert_that(
        sorted(session.trace_id for session in data.sessions), equal_to(expected_ids)
    )


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("repository", SEED_REPOSITORIES, ids=["first", "other"])
def test_repositories_filter_selects_only_that_repository(
    analytics_utils, cli_analytics_project, repository_sessions, repository
):
    """Filtering by a repository leaves only its sessions in the totals and in the
    session list; another repository and unattributed sessions add nothing."""
    expected_sessions = [
        seed for seed in repository_sessions if seed.repository == repository
    ]
    filters = {
        "projects": cli_analytics_project,
        "repositories": repository,
        **day_window().params(),
    }

    kpis = analytics_utils.get_cli_analytics_cost(**filters).data.kpis
    data = analytics_utils.get_cli_analytics_sessions(**filters).data

    assert_that(kpis.total_sessions, equal_to(len(expected_sessions)))
    assert_that(kpis.total_tokens, equal_to(total_tokens(expected_sessions)))
    assert_that(data.total, equal_to(len(expected_sessions)))
    assert_that(
        sorted(session.trace_id for session in data.sessions),
        equal_to(sorted(seed.session_id for seed in expected_sessions)),
    )
