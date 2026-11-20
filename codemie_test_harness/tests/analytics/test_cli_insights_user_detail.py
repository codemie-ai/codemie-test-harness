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

"""CLI Insights user detail: which identifiers get a report and which get a 404
(GET /v1/analytics/cli-insights-user-detail)."""

import pytest
from hamcrest import assert_that, empty, equal_to, instance_of
from requests import HTTPError

from codemie_sdk.models.analytics import AnalyticsDetailResponse
from codemie_test_harness.tests.test_data.cli_insights_user_detail_test_data import (
    KNOWN_USER_QUERIES,
    UNMATCHED_USER_QUERIES,
    USER_DETAIL_TIME_PERIOD,
    USER_NOT_FOUND_HELP,
    get_unmatched_user_query,
    user_not_found_message,
)

NOT_FOUND = 404


@pytest.mark.cli_analytics
@pytest.mark.parametrize("with_user_id", UNMATCHED_USER_QUERIES)
@pytest.mark.api
def test_cli_insights_user_detail_is_not_found_for_unmatched_user(
    analytics_utils, with_user_id
):
    # @case analytics-user-identity-filters_TC_001
    query = get_unmatched_user_query(with_user_id)

    with pytest.raises(HTTPError) as error:
        analytics_utils.get_cli_insights_user_detail(**query.params())

    response = error.value.response
    assert_that(response.status_code, equal_to(NOT_FOUND), response.text)
    body = response.json()["error"]
    assert_that(
        body["message"],
        equal_to(user_not_found_message(query.named_in_error)),
        "the 404 names the identifier that matched nothing",
    )
    assert_that(body["help"], equal_to(USER_NOT_FOUND_HELP))


@pytest.mark.cli_analytics
@pytest.mark.parametrize("known_user_query", KNOWN_USER_QUERIES)
@pytest.mark.api
def test_cli_insights_user_detail_is_a_report_for_known_user_without_activity(
    analytics_utils, platform_user, known_user_query
):
    # @case analytics-user-identity-filters_TC_001
    identifiers = known_user_query(platform_user)

    detail = analytics_utils.get_cli_insights_user_detail(
        time_period=USER_DETAIL_TIME_PERIOD, **identifiers
    )

    assert_that(detail, instance_of(AnalyticsDetailResponse))
    assert_that(
        detail.data["user_name"],
        equal_to(platform_user.email),
        "the report is about the requested user",
    )
    assert_that(
        detail.data["total_sessions"],
        equal_to(0),
        "a fresh user has no CLI sessions in the period",
    )
    assert_that(
        detail.data["repositories"],
        empty(),
        "a fresh user has no repositories in the period",
    )
