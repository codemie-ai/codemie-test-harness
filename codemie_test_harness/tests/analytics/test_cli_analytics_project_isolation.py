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

"""CLI Analytics project filter: a project's results hold that project's sessions only."""

import pytest
from hamcrest import assert_that, close_to, empty, equal_to

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    COST_TOLERANCE,
    FIRST_PROJECT,
    ISOLATED_PROJECTS,
    SECOND_PROJECT,
    SEED_MODEL,
    catalog_cost,
    catalog_cost_by_user,
    day_window,
    get_project_isolation_session_seeds,
    total_tokens,
    totals_by_user,
)


@pytest.fixture(scope="module")
def isolated_projects(cli_analytics_project, create_cli_analytics_project):
    """Names of the two projects that sessions are reported to, keyed by role."""
    return {
        FIRST_PROJECT: cli_analytics_project,
        SECOND_PROJECT: create_cli_analytics_project(),
    }


@pytest.fixture(scope="module")
def project_sessions(isolated_projects, seed_cli_sessions, catalog_priced_model):
    """Sessions of both projects on the same day, keyed by project role. They use a
    catalog-priced model when there is one, so only the money checks need it."""
    model = catalog_priced_model.base_name if catalog_priced_model else SEED_MODEL
    seeds = get_project_isolation_session_seeds(model)
    for project, project_seeds in seeds.items():
        seed_cli_sessions(project_seeds, isolated_projects[project])
    return seeds


@pytest.fixture(scope="module")
def empty_project(create_cli_analytics_project, project_sessions):
    """A project no session was reported to, on an environment that holds the
    sessions of the other two projects for the same day."""
    return create_cli_analytics_project()


def _filters(project_name: str) -> dict:
    return {"projects": project_name, **day_window().params()}


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("project", ISOLATED_PROJECTS)
def test_project_filter_totals_count_only_that_project(
    analytics_utils, isolated_projects, project_sessions, project
):
    """Session count and tokens of a project come from its own sessions; the other
    project's sessions add nothing."""
    expected_sessions = project_sessions[project]

    data = analytics_utils.get_cli_analytics_cost(
        **_filters(isolated_projects[project])
    ).data

    assert_that(data.kpis.total_sessions, equal_to(len(expected_sessions)))
    assert_that(data.kpis.total_tokens, equal_to(total_tokens(expected_sessions)))


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("project", ISOLATED_PROJECTS)
def test_project_filter_cost_counts_only_that_project(
    analytics_utils,
    cli_analytics_users,
    cost_model,
    isolated_projects,
    project_sessions,
    project,
):
    """Cost and the cost rows of a project come from its own sessions; the other
    project's sessions and users add nothing."""
    expected_sessions = project_sessions[project]
    expected_costs = {
        cli_analytics_users[role].email: cost
        for role, cost in catalog_cost_by_user(
            expected_sessions, cost_model.cost
        ).items()
    }

    data = analytics_utils.get_cli_analytics_cost(
        **_filters(isolated_projects[project])
    ).data

    assert_that(
        data.kpis.total_cost_usd,
        close_to(catalog_cost(expected_sessions, cost_model.cost), COST_TOLERANCE),
    )
    assert_that(
        sorted(row.developer_name for row in data.cost_by_user),
        equal_to(sorted(expected_costs)),
    )
    for row in data.cost_by_user:
        assert_that(
            row.cost_usd,
            close_to(expected_costs[row.developer_name], COST_TOLERANCE),
            f"Cost of {row.developer_name}",
        )


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("project", ISOLATED_PROJECTS)
def test_project_filter_lists_only_that_project_sessions(
    analytics_utils, isolated_projects, project_sessions, project
):
    """The session list of a project holds each of its sessions once and no session
    of the other project."""
    expected_ids = sorted(seed.session_id for seed in project_sessions[project])
    other_project_ids = {
        seed.session_id
        for other, seeds in project_sessions.items()
        if other != project
        for seed in seeds
    }

    data = analytics_utils.get_cli_analytics_sessions(
        **_filters(isolated_projects[project])
    ).data
    listed_ids = [session.trace_id for session in data.sessions]

    assert_that(
        sorted(other_project_ids.intersection(listed_ids)),
        empty(),
        "Sessions of the other project in the list",
    )
    assert_that(data.total, equal_to(len(expected_ids)))
    assert_that(sorted(listed_ids), equal_to(expected_ids))


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("project", ISOLATED_PROJECTS)
def test_project_filter_user_rows_hold_only_that_project(
    analytics_utils, cli_analytics_users, isolated_projects, project_sessions, project
):
    """There is a row only for users who reported to the project, holding what
    they reported to it and nothing they reported to the other project."""
    expected_rows = {
        cli_analytics_users[role].email: totals
        for role, totals in totals_by_user(project_sessions[project]).items()
    }

    rows = analytics_utils.get_cli_analytics_users(
        **_filters(isolated_projects[project])
    ).data.rows

    assert_that(
        {
            row.developer_name: (row.session_count, row.input_tokens, row.output_tokens)
            for row in rows
        },
        equal_to(expected_rows),
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_project_without_sessions_has_empty_results(analytics_utils, empty_project):
    """Filtering by a project nobody reported to gives zero totals and no rows: the
    filter does not fall back to the sessions of other projects."""
    filters = _filters(empty_project)

    cost = analytics_utils.get_cli_analytics_cost(**filters).data
    users = analytics_utils.get_cli_analytics_users(**filters).data
    sessions = analytics_utils.get_cli_analytics_sessions(**filters).data

    assert_that(cost.kpis.total_sessions, equal_to(0))
    assert_that(cost.kpis.total_tokens, equal_to(0))
    assert_that(cost.kpis.total_cost_usd, equal_to(0))
    assert_that(cost.kpis.avg_cost_per_session, equal_to(0))
    assert_that(cost.cost_by_user, empty())
    assert_that(users.rows, empty())
    assert_that(sessions.total, equal_to(0))
    assert_that(sessions.sessions, empty())
