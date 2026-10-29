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

"""Smoke tests for CLI Analytics endpoints (/v1/analytics/cli-analytics/*)."""

import pytest
from hamcrest import assert_that, greater_than_or_equal_to, instance_of

from codemie_sdk.models.analytics import (
    CliAnalyticsCostResponse,
    CliAnalyticsSessionsResponse,
)


@pytest.mark.smoke
@pytest.mark.cli_analytics
@pytest.mark.api
def test_get_cli_analytics_cost(analytics_utils, cli_analytics_enabled):
    """Cost breakdown is returned with its totals."""
    response = analytics_utils.get_cli_analytics_cost()

    assert_that(response, instance_of(CliAnalyticsCostResponse))
    assert_that(response.data.kpis.total_sessions, greater_than_or_equal_to(0))


@pytest.mark.smoke
@pytest.mark.cli_analytics
@pytest.mark.api
def test_get_cli_analytics_sessions(analytics_utils, cli_analytics_enabled):
    """Session list is returned as a page of sessions."""
    response = analytics_utils.get_cli_analytics_sessions()

    assert_that(response, instance_of(CliAnalyticsSessionsResponse))
    assert_that(response.data.total, greater_than_or_equal_to(0))
