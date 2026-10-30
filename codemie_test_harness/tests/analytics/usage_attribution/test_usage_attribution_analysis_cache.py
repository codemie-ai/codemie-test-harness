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

"""Analysis metadata of the Usage Attribution views and reuse of the cached analysis."""

from datetime import datetime, timedelta, timezone

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than_or_equal_to,
    is_,
    is_in,
    is_not,
    less_than_or_equal_to,
    none,
)

from codemie_test_harness.tests.test_data.usage_attribution_test_data import (
    CACHE_STATES,
    REUSED_CACHE_STATES,
)
from codemie_test_harness.tests.utils.usage_attribution_utils import parse_utc

CLOCK_SKEW = timedelta(minutes=1)


@pytest.mark.analytics
@pytest.mark.api
def test_cli_summary_reports_analysis_metadata(usage_attribution_utils, thirty_days):
    # @case usage-attribution-analytics-who-pays_TC_005
    analysis = usage_attribution_utils.get_cli_summary(thirty_days).analysis

    assert_that(analysis.computed_at, is_not(none()), "when the analysis was computed")
    assert_that(
        parse_utc(analysis.computed_at),
        less_than_or_equal_to(datetime.now(timezone.utc) + CLOCK_SKEW),
        "the analysis was not computed in the future",
    )
    assert_that(analysis.duration_ms, greater_than_or_equal_to(0), "how long it took")
    assert_that(analysis.cache, is_in(CACHE_STATES), "where the analysis came from")


@pytest.mark.analytics
@pytest.mark.api
def test_totals_report_cache_state_and_duration(usage_attribution_utils, thirty_days):
    # @case usage-attribution-analytics-who-pays_TC_005
    data = usage_attribution_utils.get_totals(thirty_days).data

    assert_that(data["cache"], is_in(("hit", "miss")), "fast totals cache state")
    assert_that(
        data["duration_ms"], greater_than_or_equal_to(0), "fast totals duration"
    )


@pytest.mark.analytics
@pytest.mark.api
def test_repeated_requests_reuse_the_cached_analysis(
    usage_attribution_utils, thirty_days
):
    # @case usage-attribution-analytics-who-pays_TC_005
    first = usage_attribution_utils.get_settled_cli_summary(thirty_days)

    second = usage_attribution_utils.get_cli_summary(thirty_days)
    status = usage_attribution_utils.get_status(thirty_days)

    assert_that(
        second.analysis.computed_at,
        equal_to(first.analysis.computed_at),
        "a second request within the cache time reuses the analysis",
    )
    assert_that(second.analysis.cache, is_in(REUSED_CACHE_STATES))
    assert_that(
        status.analysis.computed_at,
        equal_to(first.analysis.computed_at),
        "How It Works describes the same analysis",
    )
    assert_that(status.analysis.cache, is_in(REUSED_CACHE_STATES))
    assert_that(second.analysis.stale, is_(False))
