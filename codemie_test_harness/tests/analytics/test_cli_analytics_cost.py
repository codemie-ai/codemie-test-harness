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

"""CLI Analytics cost: reported request cost rolled up to session, user and total."""

import pytest
from hamcrest import assert_that, close_to, equal_to

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    COST_TOLERANCE,
    catalog_cost,
    catalog_cost_by_user,
    day_window,
    get_cost_session_seeds,
    session_catalog_cost,
)


@pytest.fixture(scope="module")
def cost_sessions(seed_cli_sessions, cost_model):
    """Two users' sessions of a priced model, each also reporting a cost."""
    return list(
        seed_cli_sessions(get_cost_session_seeds(cost_model.base_name)).values()
    )


def _filters(project_name: str) -> dict:
    return {"projects": project_name, **day_window().params()}


@pytest.mark.cli_analytics
@pytest.mark.api
def test_total_cost_is_tokens_priced_at_catalog(
    analytics_utils, cli_analytics_project, cost_model, cost_sessions
):
    """Total cost is the sessions' tokens at the catalog price, not the cost they
    reported, and the average is per session."""
    expected_total = catalog_cost(cost_sessions, cost_model.cost)

    kpis = analytics_utils.get_cli_analytics_cost(
        **_filters(cli_analytics_project)
    ).data.kpis

    assert_that(kpis.total_sessions, equal_to(len(cost_sessions)))
    assert_that(kpis.total_cost_usd, close_to(expected_total, COST_TOLERANCE))
    assert_that(
        kpis.avg_cost_per_session,
        close_to(expected_total / len(cost_sessions), COST_TOLERANCE),
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_cost_by_user_is_each_users_tokens_priced_at_catalog(
    analytics_utils,
    cli_analytics_project,
    cli_analytics_users,
    cost_model,
    cost_sessions,
):
    """There is one cost row per user, holding that user's own tokens at the
    catalog price."""
    expected_costs = {
        cli_analytics_users[role].email: cost
        for role, cost in catalog_cost_by_user(cost_sessions, cost_model.cost).items()
    }

    rows = analytics_utils.get_cli_analytics_cost(
        **_filters(cli_analytics_project)
    ).data.cost_by_user

    assert_that(len(rows), equal_to(len(expected_costs)))
    assert_that(
        sorted(row.developer_name for row in rows), equal_to(sorted(expected_costs))
    )
    for row in rows:
        assert_that(
            row.cost_usd,
            close_to(expected_costs[row.developer_name], COST_TOLERANCE),
            f"Cost of {row.developer_name}",
        )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_session_cost_is_its_tokens_priced_at_catalog(
    analytics_utils, cli_analytics_project, cost_model, cost_sessions
):
    """Each session is listed once and costs its tokens at the catalog price, not
    what its request reported."""
    expected_costs = {
        seed.session_id: session_catalog_cost(seed, cost_model.cost)
        for seed in cost_sessions
    }

    sessions = analytics_utils.get_cli_analytics_sessions(
        **_filters(cli_analytics_project)
    ).data.sessions

    assert_that(len(sessions), equal_to(len(expected_costs)))
    assert_that(
        sorted(session.trace_id for session in sessions),
        equal_to(sorted(expected_costs)),
    )
    for session in sessions:
        assert_that(
            session.cost_usd,
            close_to(expected_costs[session.trace_id], COST_TOLERANCE),
            f"Cost of session {session.trace_id}",
        )
