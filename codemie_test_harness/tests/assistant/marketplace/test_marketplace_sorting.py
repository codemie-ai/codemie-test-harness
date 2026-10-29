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

"""API tests for Assistant Marketplace sorting.

Covers:
    TC-02   GET marketplace assistants sorted by metric field correctly (parametrized)
    TC-02b  GET marketplace assistants sorted by name correctly (parametrized)
    TC-05   Unsupported sort_by returns 422; missing sort_by returns 200
    TC-07   Sort combined with category filter preserves filtered set and correct ordering
    TC-09   Sort endpoint responds with 200 for an authorised Marketplace user

All tests use existing marketplace data; no fixture assistants are created or modified.
"""

import pytest
from hamcrest import assert_that, equal_to, greater_than, not_none

from codemie_test_harness.tests.conftest import (
    expected_name_order_with_search,
    pg_collation_sort_key,
)
from codemie_test_harness.tests.test_data.marketplace_test_data import (
    SORT_METRIC_PARAMS,
    SORT_NAME_PARAMS,
    SORT_QUERY_METRIC_PARAMS,
    SORT_QUERY_NAME_PARAMS,
)


# ---------------------------------------------------------------------------
# TC-02 — parametrized metric sort correctness (usage / likes / dislikes)
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("sort_by, sort_order, field_name, reverse", SORT_METRIC_PARAMS)
def test_marketplace_assistants_sorted_by_metric_correctly(
    sort_by, sort_order, field_name, reverse, assistant_utils
):
    """TC-02: Marketplace sorted by {sort_by} {sort_order} returns monotonically ordered results.

    Fetches the first 50 marketplace assistants with the requested sort, extracts the
    relevant metric field from each Assistant object (None → 0), and asserts that the
    sequence matches Python's sort of the same values.  No fixture data is created.
    """
    results = assistant_utils.get_assistants(
        scope="marketplace",
        minimal_response=False,
        sort_by=sort_by,
        sort_order=sort_order,
        per_page=50,
    )
    assert_that(
        len(results),
        greater_than(0),
        f"Marketplace must return assistants when sorted by {sort_by} {sort_order}",
    )
    values = [(getattr(a, field_name) or 0) for a in results]
    assert_that(
        values,
        equal_to(sorted(values, reverse=reverse)),
        f"Field '{field_name}' must be monotonically ordered: {sort_by} {sort_order}",
    )


# ---------------------------------------------------------------------------
# TC-02b — parametrized name sort correctness
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("sort_order, reverse", SORT_NAME_PARAMS)
def test_marketplace_assistants_sorted_by_name_correctly(
    sort_order, reverse, assistant_utils
):
    """TC-02b: Marketplace sorted by name returns names in correct alphabetical order.

    The backend uses a case-insensitive collation; we replicate it by lowercasing each
    name and comparing the sequence against Python's default alphabetical sort of the same
    lowercased values.  No fixture data is created.
    """
    results = assistant_utils.get_assistants(
        scope="marketplace",
        minimal_response=False,
        sort_by="name",
        sort_order=sort_order,
        per_page=50,
    )
    assert_that(
        len(results),
        greater_than(0),
        "Marketplace must return assistants when sorted by name",
    )
    names = [a.name.lower() for a in results]
    assert_that(
        names,
        equal_to(sorted(names, key=pg_collation_sort_key, reverse=reverse)),
        f"Names must be in alphabetical order (case-insensitive): {sort_order}",
    )


# ---------------------------------------------------------------------------
# TC-05 — invalid / missing sort_by
# ---------------------------------------------------------------------------


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_marketplace_sort_invalid_sort_by_returns_422(assistant_utils):
    """TC-05(a): Passing sort_by='invalid_field' to GET /v1/assistants must return HTTP 422."""
    with pytest.raises(Exception) as exc_info:
        assistant_utils.get_assistants(scope="marketplace", sort_by="invalid_field")

    assert_that(
        exc_info.value.response.status_code,
        equal_to(422),
        "Invalid sort_by value must be rejected with HTTP 422",
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_marketplace_no_sort_by_returns_200(assistant_utils):
    """TC-05(b): Calling GET /v1/assistants with no sort_by must return HTTP 200 with a non-empty list."""
    results = assistant_utils.get_assistants(scope="marketplace", per_page=12)
    assert_that(
        len(results),
        greater_than(0),
        "Marketplace must return assistants when no sort_by is provided",
    )


# ---------------------------------------------------------------------------
# TC-07 — sort combined with category filter
# ---------------------------------------------------------------------------


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_marketplace_sort_with_category_filter(assistant_utils):
    """TC-07: Sort combined with a category filter preserves the filtered set.

    Fetches up to 50 marketplace assistants with a category filter (unsorted) and then
    with the same filter plus sort_by=likes desc.  Asserts that:
    1. Both calls return the same number of items (filter count is unchanged by adding sort).
    2. The likes values in the sorted result are monotonically non-increasing.
    No fixture data is created; the test relies on the existing marketplace state.
    """
    category = "quality-assurance"

    baseline = assistant_utils.get_assistants(
        scope="marketplace",
        minimal_response=False,
        filters={"categories": [category]},
        per_page=50,
    )
    assert_that(
        len(baseline),
        greater_than(0),
        f"Category '{category}' must have at least one published assistant in the marketplace",
    )

    sorted_results = assistant_utils.get_assistants(
        scope="marketplace",
        minimal_response=False,
        filters={"categories": [category]},
        sort_by="likes",
        sort_order="desc",
        per_page=50,
    )
    assert_that(
        len(sorted_results),
        equal_to(len(baseline)),
        "Adding sort must not change the count of filtered assistants",
    )
    likes = [(a.unique_likes_count or 0) for a in sorted_results]
    assert_that(
        likes,
        equal_to(sorted(likes, reverse=True)),
        "Likes must be monotonically non-increasing within the category-filtered sort",
    )


# ---------------------------------------------------------------------------
# TC-09 — authorised user gets 200 with sorted results
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_marketplace_sort_authorized_user_returns_200(assistant_utils):
    """TC-09: An authorised user calling the sort endpoint receives HTTP 200 with non-empty results."""
    results = assistant_utils.get_assistants(
        scope="marketplace",
        sort_by="likes",
        sort_order="desc",
        per_page=12,
    )
    assert_that(
        len(results),
        greater_than(0),
        "Authorised user should receive a non-empty sorted marketplace list",
    )
    assert_that(
        results[0].id,
        not_none(),
        "First returned assistant must have a non-None id",
    )


# ---------------------------------------------------------------------------
# TC-10a — sort by metric combined with search query (usage / likes / dislikes)
# ---------------------------------------------------------------------------

_SEARCH_TERM = "ai "


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize(
    "sort_by, sort_order, field_name, reverse", SORT_QUERY_METRIC_PARAMS
)
def test_marketplace_sort_with_search_correct_metric_order(
    sort_by, sort_order, field_name, reverse, assistant_utils
):
    """TC-10a: Sort by metric while search is active preserves the filter and orders results.

    Fetches a baseline (search only, no sort) and a sorted result (search + sort).
    Asserts the result count is unchanged (search filter not dropped by adding sort) and
    the metric field values are monotonically ordered.  Search matches name + description,
    so only the count is compared — not the name text.  No fixture data is created.
    """
    baseline = assistant_utils.get_assistants(
        scope="marketplace",
        minimal_response=False,
        filters={"search": _SEARCH_TERM},
        per_page=50,
    )
    results = assistant_utils.get_assistants(
        scope="marketplace",
        minimal_response=False,
        filters={"search": _SEARCH_TERM},
        sort_by=sort_by,
        sort_order=sort_order,
        per_page=50,
    )
    assert_that(
        len(results),
        equal_to(len(baseline)),
        f"Search filter count must be unchanged when sort_by={sort_by} {sort_order} is added",
    )
    values = [(getattr(a, field_name) or 0) for a in results]
    assert_that(
        values,
        equal_to(sorted(values, reverse=reverse)),
        f"Field '{field_name}' must be monotonically ordered: {sort_by} {sort_order}",
    )


# ---------------------------------------------------------------------------
# TC-10b — sort by name combined with search query
# ---------------------------------------------------------------------------


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("sort_order, reverse", SORT_QUERY_NAME_PARAMS)
def test_marketplace_sort_by_name_with_search_correct_order(
    sort_order, reverse, assistant_utils
):
    """TC-10b: Sort by name while search is active preserves the filter and orders by name.

    Fetches a baseline (search only, no sort) and a name-sorted result (search + sort).
    Asserts the result count is unchanged (search filter not dropped) and the name sequence
    matches the two-group order produced by the backend priority CASE (see
    _expected_name_order_with_search).  No fixture data is created.
    """
    baseline = assistant_utils.get_assistants(
        scope="marketplace",
        minimal_response=False,
        filters={"search": _SEARCH_TERM},
        per_page=50,
    )
    results = assistant_utils.get_assistants(
        scope="marketplace",
        minimal_response=False,
        filters={"search": _SEARCH_TERM},
        sort_by="name",
        sort_order=sort_order,
        per_page=50,
    )
    assert_that(
        len(results),
        equal_to(len(baseline)),
        f"Search filter count must be unchanged when sort_by=name {sort_order} is added",
    )
    names = [a.name.lower() for a in results]
    assert_that(
        names,
        equal_to(expected_name_order_with_search(names, _SEARCH_TERM, reverse)),
        f"Names must follow priority-grouped name order (title matches first, then description-only): {sort_order}",
    )
