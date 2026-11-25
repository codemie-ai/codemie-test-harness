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

"""CLI Analytics Session Detail for Copilot hooks-only sessions."""

import pytest
from hamcrest import assert_that, close_to, equal_to, has_entries, none

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    COST_TOLERANCE,
    session_catalog_cost,
)
from codemie_test_harness.tests.test_data.cli_analytics_timeline_test_data import (
    get_hooks_only_timeline_seed,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi


@pytest.mark.cli_analytics
@pytest.mark.api
def test_hooks_only_session_detail_keeps_agent_usage_on_its_timeline_row(
    analytics_utils, cost_model, seed_cli_sessions
):
    """Exercise the deployed ingest → rollup → Session Detail API contract."""
    seed = get_hooks_only_timeline_seed(
        cost_model.deployment_name or cost_model.base_name
    )
    seed = seed_cli_sessions([seed])[seed.key]
    analytics_utils.wait_for_cli_session_end(seed.session_id)
    # The SDK's session-detail model drops dispatches and active_ms.
    response = CliAnalyticsApi(analytics_utils.client).request(
        "GET", f"/v1/analytics/cli-analytics/sessions/{seed.session_id}"
    )
    assert_that(response.status_code, equal_to(200), response.text[:300])
    detail = response.json()["data"]
    dispatches = detail["dispatches"]
    rows = {(row["kind"], row["label"]): row for row in dispatches}

    assert_that(detail["active_ms"], none())
    assert_that(len(dispatches), equal_to(4))
    assert_that(
        set(rows),
        equal_to(
            {
                ("session", "session"),
                ("agent", "agent · file-auditor #1"),
                ("agent", "agent · file-auditor #2"),
                ("skill", "skill · timeline-check"),
            }
        ),
    )

    agent_cost = (
        seed.agent_input_tokens * cost_model.cost.input
        + seed.agent_output_tokens * cost_model.cost.output
    )
    assert_that(
        rows["agent", "agent · file-auditor #1"],
        has_entries(
            input_tokens=seed.agent_input_tokens,
            output_tokens=seed.agent_output_tokens,
            cost_usd=close_to(agent_cost, COST_TOLERANCE),
            start_offset_ms=1000,
            duration_ms=5000,
        ),
    )
    assert_that(
        rows["agent", "agent · file-auditor #2"],
        has_entries(
            input_tokens=none(),
            output_tokens=none(),
            cost_usd=none(),
            start_offset_ms=2000,
            duration_ms=5000,
        ),
    )
    assert_that(
        rows["skill", "skill · timeline-check"],
        has_entries(cost_usd=none(), start_offset_ms=3000, duration_ms=1000),
    )
    assert_that(
        rows["session", "session"],
        has_entries(
            input_tokens=seed.input_tokens + seed.agent_input_tokens,
            output_tokens=seed.output_tokens + seed.agent_output_tokens,
            cost_usd=close_to(
                session_catalog_cost(seed, cost_model.cost) + agent_cost, COST_TOLERANCE
            ),
        ),
    )
