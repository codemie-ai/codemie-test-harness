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

"""CLI spend paid from personal budgets, broken down by country and by job title group."""

import pytest
from hamcrest import (
    assert_that,
    close_to,
    empty,
    equal_to,
    greater_than_or_equal_to,
    instance_of,
    is_,
    less_than_or_equal_to,
)

from codemie_test_harness.tests.test_data.usage_attribution_test_data import (
    CATEGORIES,
    MAX_NAMED_BUCKETS,
    OTHER_BUCKET_LABEL,
    TOTAL_TOLERANCE,
)
from codemie_test_harness.tests.utils.usage_attribution_utils import period_params


def _assert_breakdown_contract(data, dimension, category):
    """One breakdown: echoed request, real buckets, largest first, the folded rest last, a matching total."""
    rows = data["rows"]
    named = [row for row in rows if row["label"] != OTHER_BUCKET_LABEL]
    folded = [row for row in rows if row["label"] == OTHER_BUCKET_LABEL]
    spends = [row["spend"] for row in rows]
    named_spends = [row["spend"] for row in named]

    assert_that(data["dimension"], equal_to(dimension))
    assert_that(data["category"], equal_to(category))
    assert_that(rows, instance_of(list), f"{dimension}: rows are a list, maybe empty")
    assert_that(
        [row for row in rows if not row["label"]],
        is_(empty()),
        f"{dimension}: every bucket has a label",
    )
    assert_that(
        [spend for spend in spends if spend <= 0],
        is_(empty()),
        f"{dimension}: every bucket has spend",
    )
    assert_that(
        named_spends,
        equal_to(sorted(named_spends, reverse=True)),
        f"{dimension}: buckets are listed largest first",
    )
    assert_that(
        len(named),
        less_than_or_equal_to(MAX_NAMED_BUCKETS),
        f"{dimension}: at most {MAX_NAMED_BUCKETS} named buckets",
    )
    assert_that(
        len(folded),
        less_than_or_equal_to(1),
        f"{dimension}: the rest is folded into one bucket",
    )
    assert_that(
        rows,
        equal_to(named + folded),
        f"{dimension}: the folded rest comes last",
    )
    assert_that(
        len(named),
        greater_than_or_equal_to(MAX_NAMED_BUCKETS * len(folded)),
        f"{dimension}: a bucket is folded only after {MAX_NAMED_BUCKETS} named ones",
    )
    assert_that(
        sum(spends),
        close_to(data["total"], TOTAL_TOLERANCE),
        f"{dimension}: the total is the sum of its buckets",
    )


@pytest.mark.parametrize("category", CATEGORIES)
@pytest.mark.analytics
@pytest.mark.api
def test_breakdown_buckets_follow_the_contract_for_both_dimensions(
    usage_attribution_utils, user_enrichment_enabled, category
):
    # @case usage-attribution-analytics-who-pays_TC_014
    # The totals of the two dimensions are not compared: the backend drops non-positive labels per dimension.
    by_country = usage_attribution_utils.get_breakdown(
        "country", category, period_params()
    ).data
    by_job = usage_attribution_utils.get_breakdown(
        "job", category, period_params()
    ).data

    _assert_breakdown_contract(by_country, "country", category)
    _assert_breakdown_contract(by_job, "job", category)
