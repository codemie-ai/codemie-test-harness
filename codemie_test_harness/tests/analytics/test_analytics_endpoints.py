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

"""Tests for analytics endpoints."""

from datetime import datetime, timedelta, timezone

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than_or_equal_to,
    instance_of,
    is_not,
    none,
)

from codemie_sdk.models.analytics import (
    Metric,
    ResponseMetadata,
    SummariesData,
    SummariesResponse,
    TabularData,
    TabularResponse,
    UserListItem,
    UsersListData,
    UsersListResponse,
)


@pytest.mark.analytics
@pytest.mark.api
def test_get_summaries(analytics_utils):
    """Test getting overall platform summary metrics."""
    response = analytics_utils.get_summaries()

    # Validate response structure
    assert_that(response, instance_of(SummariesResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that(response.data, instance_of(SummariesData))

    # Validate metadata
    assert_that(response.metadata.timestamp, is_not(none()))
    assert_that(response.metadata.data_as_of, is_not(none()))
    assert_that(response.metadata.execution_time_ms, greater_than_or_equal_to(0))

    # Validate metrics
    assert_that(response.data.metrics, instance_of(list))
    for metric in response.data.metrics:
        assert_that(metric, instance_of(Metric))
        assert_that(metric.id, is_not(none()))
        assert_that(metric.label, is_not(none()))
        assert_that(metric.type, is_not(none()))


@pytest.mark.analytics
@pytest.mark.api
def test_get_cli_summary(analytics_utils):
    """Test getting CLI-specific summary metrics."""
    response = analytics_utils.get_cli_summary()

    # Validate response structure
    assert_that(response, instance_of(SummariesResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that(response.data, instance_of(SummariesData))

    # Validate metrics
    assert_that(response.data.metrics, instance_of(list))


@pytest.mark.analytics
@pytest.mark.api
def test_get_users(analytics_utils):
    """Test getting users list."""
    response = analytics_utils.get_users()

    assert_that(response, instance_of(UsersListResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that(response.data, instance_of(UsersListData))
    assert_that(response.data.users, instance_of(list))

    # Validate users if present
    for user in response.data.users:
        assert_that(user, instance_of(UserListItem))
        assert_that(user.id, is_not(none()))


@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "endpoint_method",
    [
        "get_assistants_chats",
        "get_workflows",
        "get_tools_usage",
        "get_webhooks_invocation",
        "get_mcp_servers",
        "get_mcp_servers_by_users",
        "get_projects_spending",
        "get_llms_usage",
        "get_users_spending",
        "get_budget_soft_limit",
        "get_budget_hard_limit",
        "get_users_activity",
        "get_projects_activity",
        "get_agents_usage",
        "get_cli_agents",
        "get_cli_llms",
        "get_cli_users",
        "get_cli_errors",
        "get_cli_repositories",
    ],
)
def test_all_tabular_endpoints_baseline(analytics_utils, endpoint_method):
    """Test all 19 tabular endpoints with default parameters."""
    method = getattr(analytics_utils, endpoint_method)
    response = method()

    assert_that(response, instance_of(TabularResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that(response.data, instance_of(TabularData))
    assert_that(response.data.columns, instance_of(list))
    assert_that(response.data.rows, instance_of(list))


# Time Period Parametrized Tests
@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "time_period",
    [
        "last_hour",
        "last_6_hours",
        "last_24_hours",
        "last_7_days",
        "last_30_days",
        "last_60_days",
        "last_year",
    ],
)
def test_summaries_all_time_periods(analytics_utils, time_period):
    """Test summaries endpoint with all valid time periods."""
    response = analytics_utils.get_summaries(time_period=time_period)

    assert_that(response, instance_of(SummariesResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that("time_period" in response.metadata.filters_applied, equal_to(True))


@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "time_period",
    [
        "last_hour",
        "last_6_hours",
        "last_24_hours",
        "last_7_days",
        "last_30_days",
        "last_60_days",
        "last_year",
    ],
)
def test_cli_summary_all_time_periods(analytics_utils, time_period):
    """Test CLI summary endpoint with all valid time periods."""
    response = analytics_utils.get_cli_summary(time_period=time_period)

    assert_that(response, instance_of(SummariesResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that("time_period" in response.metadata.filters_applied, equal_to(True))


@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "time_period",
    [
        "last_7_days",
        "last_30_days",
        "last_60_days",
    ],
)
@pytest.mark.parametrize(
    "endpoint_method",
    [
        "get_assistants_chats",
        "get_workflows",
        "get_tools_usage",
        "get_llms_usage",
        "get_users_activity",
    ],
)
def test_tabular_endpoints_with_time_periods(
    analytics_utils, endpoint_method, time_period
):
    """Test representative tabular endpoints with time periods."""
    method = getattr(analytics_utils, endpoint_method)
    response = method(time_period=time_period)

    assert_that(response, instance_of(TabularResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that(response.data, instance_of(TabularData))
    assert_that("time_period" in response.metadata.filters_applied, equal_to(True))


# Pagination Parametrized Tests


@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "endpoint_method",
    [
        "get_assistants_chats",
        "get_workflows",
        "get_tools_usage",
        "get_llms_usage",
    ],
)
def test_tabular_endpoints_with_pagination(analytics_utils, endpoint_method):
    """Test that pagination works for key tabular endpoints."""
    method = getattr(analytics_utils, endpoint_method)
    response = method(page=1, per_page=10)

    assert_that(response, instance_of(TabularResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))

    if response.pagination:
        assert_that(response.pagination.page, equal_to(1))
        assert_that(response.pagination.per_page, equal_to(10))


# Date Range Parametrized Tests


@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "endpoint_method",
    [
        "get_assistants_chats",
        "get_workflows",
        "get_tools_usage",
    ],
)
def test_endpoints_with_date_range(analytics_utils, endpoint_method):
    """Test endpoints with custom date range (last 90 days)."""
    # Calculate dynamic date range: today - 90 days to today
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=80)

    # Format as ISO 8601
    start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    method = getattr(analytics_utils, endpoint_method)
    response = method(start_date=start_date_str, end_date=end_date_str)

    assert_that(response, instance_of(TabularResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that("start_date" in response.metadata.filters_applied, equal_to(True))
    assert_that("end_date" in response.metadata.filters_applied, equal_to(True))


# Combined Filters Parametrized Tests


@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "endpoint_method",
    [
        "get_assistants_chats",
        "get_workflows",
        "get_tools_usage",
    ],
)
def test_endpoints_time_period_and_pagination(analytics_utils, endpoint_method):
    """Test endpoints with combined time period and pagination filters."""
    method = getattr(analytics_utils, endpoint_method)
    response = method(time_period="last_30_days", page=0, per_page=10)

    assert_that(response, instance_of(TabularResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that("time_period" in response.metadata.filters_applied, equal_to(True))

    if response.pagination:
        assert_that(response.pagination.page, equal_to(0))
        assert_that(response.pagination.per_page, equal_to(10))


# CLI Endpoints Tests


@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "time_period",
    [
        "last_hour",
        "last_6_hours",
        "last_24_hours",
        "last_7_days",
        "last_30_days",
        "last_60_days",
        "last_year",
    ],
)
@pytest.mark.parametrize(
    "endpoint_method",
    [
        "get_cli_agents",
        "get_cli_llms",
        "get_cli_users",
    ],
)
def test_cli_endpoints_with_time_periods(analytics_utils, endpoint_method, time_period):
    """Test CLI endpoints with all valid time periods."""
    method = getattr(analytics_utils, endpoint_method)
    response = method(time_period=time_period)

    assert_that(response, instance_of(TabularResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that(response.data, instance_of(TabularData))


# Users and Projects Filter Tests


@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "endpoint_method",
    [
        "get_assistants_chats",
        "get_workflows",
        "get_tools_usage",
    ],
)
def test_endpoints_with_users_filter(analytics_utils, endpoint_method, client):
    """Test endpoints with users filter parameter."""
    # Get current user ID from client
    user = client.users.about_me()
    user_id = user.user_id

    method = getattr(analytics_utils, endpoint_method)
    response = method(users=user_id)

    assert_that(response, instance_of(TabularResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that("users" in response.metadata.filters_applied, equal_to(True))


@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "endpoint_method",
    [
        "get_assistants_chats",
        "get_workflows",
        "get_tools_usage",
    ],
)
def test_endpoints_with_projects_filter(analytics_utils, endpoint_method):
    """Test endpoints with projects filter parameter."""
    # Use a project name from environment
    from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

    project_name = CredentialsManager.get_parameter("PROJECT_NAME")

    if project_name:
        method = getattr(analytics_utils, endpoint_method)
        response = method(projects=project_name)

        assert_that(response, instance_of(TabularResponse))
        assert_that(response.metadata, instance_of(ResponseMetadata))
        assert_that("projects" in response.metadata.filters_applied, equal_to(True))


@pytest.mark.analytics
@pytest.mark.api
def test_summaries_with_users_and_projects_filters(analytics_utils, client):
    """Test summaries endpoint with both users and projects filters."""
    from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

    user = client.users.about_me()
    user_id = user.user_id
    project_name = CredentialsManager.get_parameter("PROJECT_NAME")

    if project_name:
        response = analytics_utils.get_summaries(users=user_id, projects=project_name)

        assert_that(response, instance_of(SummariesResponse))
        assert_that(response.metadata, instance_of(ResponseMetadata))
        assert_that("users" in response.metadata.filters_applied, equal_to(True))
        assert_that("projects" in response.metadata.filters_applied, equal_to(True))


@pytest.mark.analytics
@pytest.mark.api
def test_endpoints_with_combined_all_filters(analytics_utils):
    """Test endpoint with time_period, pagination, users, and projects combined."""
    from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

    project_name = CredentialsManager.get_parameter("PROJECT_NAME")

    if project_name:
        response = analytics_utils.get_assistants_chats(
            time_period="last_30_days", projects=project_name, page=0, per_page=10
        )

        assert_that(response, instance_of(TabularResponse))
        assert_that(response.metadata, instance_of(ResponseMetadata))
        assert_that("time_period" in response.metadata.filters_applied, equal_to(True))
        assert_that("projects" in response.metadata.filters_applied, equal_to(True))
