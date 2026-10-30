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

"""Period selection of the Usage Attribution totals: named periods, custom dates and the 90-day clamp."""

from datetime import timedelta

import pytest
from hamcrest import (
    assert_that,
    close_to,
    contains_inanyorder,
    equal_to,
    has_items,
    is_,
)

from codemie_test_harness.tests.test_data.usage_attribution_test_data import (
    CLAMPED_RANGE_DAYS,
    MAX_RANGE_DAYS,
    PAYERS,
    PERIOD_LAST_30_DAYS,
    RANGES_WITH_SAME_CATEGORIES,
    TOTALS_FIELDS,
)
from codemie_test_harness.tests.utils.usage_attribution_utils import (
    custom_range_params,
    parse_utc,
    period_params,
    range_params,
)


@pytest.mark.parametrize("range_case", RANGES_WITH_SAME_CATEGORIES)
@pytest.mark.analytics
@pytest.mark.api
def test_totals_have_the_same_categories_for_every_range(
    usage_attribution_utils, range_case
):
    # @case usage-attribution-analytics-who-pays_TC_004
    baseline = usage_attribution_utils.get_totals(period_params(PERIOD_LAST_30_DAYS))

    response = usage_attribution_utils.get_totals(range_params(range_case))

    assert_that(list(response.data), has_items(*TOTALS_FIELDS))
    assert_that(
        list(response.data["web"]),
        contains_inanyorder(*baseline.data["web"]),
        "the Web Platform kinds do not depend on the range",
    )
    assert_that(
        list(response.data["who_pays"]["web"]),
        contains_inanyorder(*PAYERS),
        "Web Platform payer states",
    )
    assert_that(
        list(response.data["who_pays"]["cli"]),
        contains_inanyorder(*PAYERS),
        "CLI payer states",
    )
    assert_that(response.range.clamped, is_(False), "the range is within the maximum")


@pytest.mark.analytics
@pytest.mark.api
def test_range_over_the_maximum_is_clamped_to_90_days(usage_attribution_utils):
    # @case usage-attribution-analytics-who-pays_TC_004
    response = usage_attribution_utils.get_totals(
        custom_range_params(CLAMPED_RANGE_DAYS)
    )

    effective_from, effective_to = (
        parse_utc(response.range.from_),
        parse_utc(response.range.to),
    )
    assert_that(response.range.clamped, is_(True), "120 days is above the maximum")
    assert_that(
        response.range.days, close_to(MAX_RANGE_DAYS, 0.01), "effective length in days"
    )
    assert_that(
        effective_from,
        equal_to(effective_to - timedelta(days=MAX_RANGE_DAYS)),
        "the start moves up so the range ends where requested",
    )
    assert_that(
        parse_utc(response.range.requested_to),
        equal_to(effective_to),
        "the requested end is kept",
    )
    assert_that(
        parse_utc(response.range.requested_from),
        equal_to(effective_to - timedelta(days=CLAMPED_RANGE_DAYS)),
        "the requested start is reported unclamped",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_range_of_exactly_90_days_is_not_clamped(usage_attribution_utils):
    # @case usage-attribution-analytics-who-pays_TC_004
    response = usage_attribution_utils.get_totals(custom_range_params(MAX_RANGE_DAYS))

    assert_that(response.range.clamped, is_(False), "90 days is within the maximum")
    assert_that(
        response.range.days, close_to(MAX_RANGE_DAYS, 0.01), "effective length in days"
    )
    assert_that(
        response.range.from_,
        equal_to(response.range.requested_from),
        "the requested start is used as is",
    )
    assert_that(
        response.range.to,
        equal_to(response.range.requested_to),
        "the requested end is used as is",
    )
