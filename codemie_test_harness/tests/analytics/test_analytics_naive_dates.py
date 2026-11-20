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

"""Analytics date filters: a start_date/end_date without a timezone offset is never a 500."""

import pytest
from hamcrest import assert_that, equal_to, is_in

from codemie_test_harness.tests.test_data.analytics_naive_dates_test_data import (
    DATE_FILTERED_ENDPOINTS,
    NAIVE_DATE_ACCEPTED_STATUSES,
    NaiveDateCase,
    get_naive_date_cases,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi

NAIVE_DATE_CASES = get_naive_date_cases()


@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize("endpoint", DATE_FILTERED_ENDPOINTS)
@pytest.mark.parametrize(
    "case", NAIVE_DATE_CASES, ids=[case.name for case in NAIVE_DATE_CASES]
)
def test_naive_dates_do_not_fail_analytics_endpoint(
    client, cli_analytics_enabled, endpoint: str, case: NaiveDateCase
):
    """Dates with no UTC offset are treated as UTC or rejected as invalid, never a 500,
    while the same dates written with a Z suffix are answered with 200."""
    api = CliAnalyticsApi(client)

    aware = api.request("GET", endpoint, params=case.aware)
    assert_that(  # repro:precondition
        aware.status_code,
        equal_to(200),
        f"{endpoint} with {case.aware} (with offset): {aware.text[:200]}",
    )

    naive = api.request("GET", endpoint, params=case.naive)
    assert_that(  # repro:symptom
        naive.status_code,
        is_in(NAIVE_DATE_ACCEPTED_STATUSES),
        f"{endpoint} with {case.naive} (no offset): {naive.text[:300]}",
    )
