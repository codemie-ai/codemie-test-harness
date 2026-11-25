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

"""Analytics date filters: a start_date/end_date without a timezone offset is read as UTC."""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.analytics_naive_dates_test_data import (
    DATE_FILTERED_ENDPOINTS,
    NAIVE_DATE_COMPARE_ATTEMPTS,
    NaiveDateCase,
    get_naive_date_cases,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi

NAIVE_DATE_CASES = get_naive_date_cases()


def _read(api: CliAnalyticsApi, endpoint: str, params: dict) -> tuple[dict, dict]:
    """The applied range and the response without its metadata, from a request that must
    succeed. The range is the filter dates the request set, as ``filters_applied``
    reports them; the CLI Analytics views report no ``filters_applied`` but the last day
    of the range as ``data_as_of``."""
    response = api.request("GET", endpoint, params=params)
    assert_that(
        response.status_code,
        equal_to(200),
        f"{endpoint} with {params}: {response.text[:300]}",
    )
    body = response.json()
    metadata = body["metadata"]
    if "filters_applied" in metadata:
        applied = {key: metadata["filters_applied"][key] for key in params}
    else:
        applied = {"data_as_of": metadata["data_as_of"]}
    return applied, {key: value for key, value in body.items() if key != "metadata"}


@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize("endpoint", DATE_FILTERED_ENDPOINTS)
@pytest.mark.parametrize(
    "case", NAIVE_DATE_CASES, ids=[case.name for case in NAIVE_DATE_CASES]
)
def test_naive_dates_are_read_as_utc(
    client, cli_analytics_enabled, endpoint: str, case: NaiveDateCase
):
    """Dates with no UTC offset are answered with 200 and read as UTC: the response
    applies the same range and holds the same data as the request with the dates
    written in UTC."""
    api = CliAnalyticsApi(client)

    for _ in range(NAIVE_DATE_COMPARE_ATTEMPTS):
        aware_range, aware_data = _read(api, endpoint, case.aware)
        naive_range, naive_data = _read(api, endpoint, case.naive)
        if naive_data == aware_data:
            break

    assert_that(  # repro:symptom
        naive_range,
        equal_to(aware_range),
        f"{endpoint}: range applied for {case.naive} (no offset) vs {case.aware}",
    )
    assert_that(  # repro:symptom
        naive_data,
        equal_to(aware_data),
        f"{endpoint}: data for {case.naive} (no offset) vs {case.aware}",
    )
