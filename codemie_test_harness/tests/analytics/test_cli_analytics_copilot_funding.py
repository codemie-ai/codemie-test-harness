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

"""CLI Analytics funding of GitHub Copilot CLI sessions.

A codemie-copilot session routed through CodeMie is stored as CodeMie / profile and its cost
counts as API spend on the Overview; a native Copilot session sent without that evidence stays
Unknown and its cost stays out of API spend. Both sessions are sent to the module's project by
one user, so the project's Overview holds exactly these two.

The SDK models of the session detail and the Overview drop the classification and funding
fields, so both are read raw (CliAnalyticsApi).
"""

import pytest
from hamcrest import assert_that, close_to, equal_to, has_entries

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    COST_TOLERANCE,
    PRESENCE_POLL_S,
    PRESENCE_TIMEOUT_S,
    session_catalog_cost,
)
from codemie_test_harness.tests.test_data.cli_copilot_funding_test_data import (
    EXPECTED_CLASSES,
    MANAGED,
    NATIVE,
    get_copilot_funding_seeds,
    managed_copilot_headers,
)
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi


@pytest.fixture(scope="module")
def copilot_sessions(
    analytics_utils,
    cost_model,
    cli_analytics_project,
    cli_analytics_users,
    ingest_cli_sessions,
):
    """A managed and a native Copilot session in the module's project, rolled up."""
    seeds = get_copilot_funding_seeds(
        cost_model.deployment_name or cost_model.base_name
    )
    # The native session is sent the legacy way, which also makes its user a member of the
    # project; the managed session is then sent by the same user with the CLI's evidence.
    ingest_cli_sessions([seeds[NATIVE]])
    managed = seeds[MANAGED]
    cli_analytics_users[managed.user].analytics_utils.ingest_cli_evidence_hooks(
        managed.events(cli_analytics_project),
        cli_analytics_project,
        managed_copilot_headers(managed.session_id),
    )
    for seed in seeds.values():
        analytics_utils.wait_for_cli_session(seed.session_id)
    return seeds


def _read_data(analytics_utils, path: str, **params) -> dict:
    response = CliAnalyticsApi(analytics_utils.client).read(path, **params)
    assert_that(
        response.status_code,
        equal_to(200),
        f"GET {path}: {response.text[:300]}",
    )
    return response.json()["data"]


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("entrypoint", [MANAGED, NATIVE])
def test_copilot_session_is_classified_by_its_route(
    analytics_utils, copilot_sessions, entrypoint
):
    """A codemie-copilot session sent with proof of the CodeMie route is stored with
    subscription type codemie and project origin profile; a native Copilot session is not
    claimed as CodeMie-funded and stays unknown with no origin."""
    seed = copilot_sessions[entrypoint]

    detail = _read_data(analytics_utils, f"/sessions/{seed.session_id}")

    assert_that(  # repro:symptom
        detail,
        has_entries(EXPECTED_CLASSES[entrypoint]),
        f"subscription type and project origin of the {entrypoint} Copilot session",
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_overview_counts_routed_copilot_cost_as_api_spend(
    analytics_utils, cost_model, cli_analytics_project, copilot_sessions
):
    """On the project's Overview the codemie-copilot session is in the api_based funding
    bucket and its cost is API spend; the native session is in the unknown bucket and its
    cost is subscription usage."""
    managed_cost = session_catalog_cost(copilot_sessions[MANAGED], cost_model.cost)
    native_cost = session_catalog_cost(copilot_sessions[NATIVE], cost_model.cost)

    overview = poll_until(
        lambda: _read_data(
            analytics_utils, "/overview", projects=cli_analytics_project
        ),
        lambda data: data["kpis"]["total_sessions"] >= len(copilot_sessions),
        PRESENCE_TIMEOUT_S,
        PRESENCE_POLL_S,
    )

    assert_that(  # repro:symptom
        overview["funding"],
        has_entries(
            api_based=has_entries(
                session_count=1, cost_usd=close_to(managed_cost, COST_TOLERANCE)
            ),
            unknown=has_entries(
                session_count=1, cost_usd=close_to(native_cost, COST_TOLERANCE)
            ),
        ),
        "funding buckets of the project's Copilot sessions",
    )
    assert_that(  # repro:symptom
        overview["kpis"],
        has_entries(
            total_sessions=len(copilot_sessions),
            api_cost_usd=close_to(managed_cost, COST_TOLERANCE),
            subscription_cost_usd=close_to(native_cost, COST_TOLERANCE),
        ),
        "API spend and subscription usage of the project's Copilot sessions",
    )
