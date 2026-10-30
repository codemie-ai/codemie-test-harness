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

"""Shared projects, repository groups and people lists: paging, search, scope and the popup of a row."""

import pytest
from hamcrest import (
    assert_that,
    empty,
    equal_to,
    greater_than_or_equal_to,
    has_items,
    is_,
    less_than_or_equal_to,
)

from codemie_test_harness.tests.test_data.usage_attribution_test_data import (
    ALL_LISTS,
    PEOPLE_CASE,
    PEOPLE_FILTERS,
    SCOPED_LISTS,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.usage_attribution_utils import period_params

MAX_PER_PAGE = 200


@pytest.fixture
def list_with_rows(usage_attribution_utils, list_case):
    """The first rows of the list; fails where the environment has no rows to list."""
    page = usage_attribution_utils.list_page(
        list_case, period_params(), per_page=2, **list_case.all_rows
    )
    assert_that(
        page.pagination.total_count,
        greater_than_or_equal_to(1),
        f"the '{list_case.list_method}' list is empty on this environment: "
        "seed data is required for this test",
    )
    return page


@pytest.mark.parametrize("list_case", SCOPED_LISTS)
@pytest.mark.analytics
@pytest.mark.api
def test_threshold_scope_lists_no_more_than_all_scope(
    usage_attribution_utils, list_case
):
    # @case usage-attribution-analytics-who-pays_TC_012
    over_threshold = usage_attribution_utils.list_page(
        list_case, period_params(), scope="threshold", per_page=1
    )
    everything = usage_attribution_utils.list_page(
        list_case, period_params(), scope="all", per_page=1
    )

    assert_that(
        over_threshold.counts["threshold"],
        less_than_or_equal_to(over_threshold.counts["all"]),
        "rows over the threshold are a part of all rows",
    )
    assert_that(
        over_threshold.pagination.total_count,
        equal_to(over_threshold.counts["threshold"]),
        "the threshold scope lists the rows it counts",
    )
    assert_that(
        everything.pagination.total_count,
        equal_to(everything.counts["all"]),
        "the all scope lists the rows it counts",
    )


@pytest.mark.parametrize("people_filter", PEOPLE_FILTERS)
@pytest.mark.analytics
@pytest.mark.api
def test_people_filter_lists_the_people_it_counts(
    usage_attribution_utils, people_filter
):
    # @case usage-attribution-analytics-who-pays_TC_012
    page = usage_attribution_utils.list_page(
        PEOPLE_CASE, period_params(), filter=people_filter, per_page=1
    )

    assert_that(
        page.pagination.total_count,
        equal_to(page.counts[people_filter]),
        f"the {people_filter} filter lists the people it counts",
    )
    assert_that(
        page.counts[people_filter],
        less_than_or_equal_to(page.counts["all"]),
        "a filter narrows the people",
    )


@pytest.mark.parametrize("list_case", ALL_LISTS)
@pytest.mark.analytics
@pytest.mark.api
def test_search_without_a_match_lists_nothing(usage_attribution_utils, list_case):
    # @case usage-attribution-analytics-who-pays_TC_012
    page = usage_attribution_utils.list_page(
        list_case, period_params(), search=get_random_name(), **list_case.all_rows
    )

    assert_that(page.pagination.total_count, equal_to(0))
    assert_that(page.data["rows"], is_(empty()))


@pytest.mark.parametrize("list_case", ALL_LISTS)
@pytest.mark.analytics
@pytest.mark.api
def test_search_by_a_row_name_keeps_that_row(
    usage_attribution_utils, list_case, list_with_rows
):
    # @case usage-attribution-analytics-who-pays_TC_012
    row = list_with_rows.data["rows"][0]

    page = usage_attribution_utils.list_page(
        list_case,
        period_params(),
        search=row["name"],
        per_page=MAX_PER_PAGE,
        **list_case.all_rows,
    )

    assert_that(
        page.pagination.total_count,
        greater_than_or_equal_to(1),
        "the row is found by its name",
    )
    assert_that(
        page.pagination.total_count,
        less_than_or_equal_to(list_with_rows.pagination.total_count),
        "search narrows the rows",
    )
    assert_that(
        [found[list_case.id_field] for found in page.data["rows"]],
        has_items(row[list_case.id_field]),
    )


@pytest.mark.parametrize("list_case", ALL_LISTS)
@pytest.mark.analytics
@pytest.mark.api
def test_first_row_detail_returns_its_sections(
    usage_attribution_utils, list_case, list_with_rows
):
    # @case usage-attribution-analytics-who-pays_TC_012
    row = list_with_rows.data["rows"][0]

    popup = usage_attribution_utils.open_detail(list_case, row, period_params())

    assert_that(
        popup.data["row"][list_case.id_field],
        equal_to(row[list_case.id_field]),
        "the popup opens the row that was asked for",
    )
    assert_that(list(popup.data["detail"]), has_items(*list_case.detail_sections))
