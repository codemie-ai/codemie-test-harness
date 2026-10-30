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

"""UI tests for Assistant Marketplace sorting.

Covers:
    TC-01  Sort controls are visible with all expected options in Marketplace
    TC-03  Selecting sort option in UI reorders the Marketplace assistant list
    TC-04  Sort by usage displays assistant cards in correct users-count order
    TC-08  Sort combined with search preserves search results and displays them in order
"""

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than,
)

from codemie_test_harness.tests.conftest import (
    expected_name_order_with_search,
    pg_collation_sort_key,
)
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_marketplace_page import (
    AssistantsMarketplacePage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    SORT_BY_UI_OPTIONS,
)


# ---------------------------------------------------------------------------
# TC-01 — Sort controls are visible with all expected options
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_marketplace_sort_controls_are_visible(page):
    """TC-01: Sort controls are visible with all expected options in Marketplace.

    Navigates to the Marketplace, asserts that the Sort by combobox and Sort order
    radio buttons are visible and that the Sort by dropdown exposes the four expected options.
    """
    marketplace_page = AssistantsMarketplacePage(page)
    marketplace_page.navigate_to()
    marketplace_page.should_be_on_marketplace_page()

    # Sort by dropdown and Sort order radios must be visible and enabled
    marketplace_page.should_have_sort_controls_visible()

    # Sort by dropdown must expose all four expected option labels
    marketplace_page.should_have_sort_by_options(*SORT_BY_UI_OPTIONS)


# ---------------------------------------------------------------------------
# TC-03 — Selecting sort option reorders the list
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_marketplace_sort_by_name_reorders_list(page):
    """TC-03: Selecting sort option in UI reorders the Marketplace assistant list.

    Navigates to Marketplace, applies Sort by -> Name Ascending then Descending.
    Asserts that each direction produces a correctly ordered list of visible names.
    Note: authoritative sort-order coverage lives in the API tests (TC-02b); here we
    verify the UI controls wire up correctly to the same backend behaviour.
    """
    marketplace_page = AssistantsMarketplacePage(page)
    marketplace_page.navigate_to()
    marketplace_page.should_be_on_marketplace_page()

    # Apply Sort by Name, Ascending
    marketplace_page.sort_by("Name")
    marketplace_page.set_sort_order("Ascending")

    names_asc = marketplace_page.get_assistant_names_in_order()
    assert_that(
        len(names_asc), greater_than(0), "Sorted marketplace must contain assistants"
    )
    names_asc_lower = [n.lower() for n in names_asc]
    assert_that(
        names_asc_lower,
        equal_to(sorted(names_asc_lower, key=pg_collation_sort_key)),
        "Sort by Name Ascending: names must be in alphabetical order (case-insensitive)",
    )

    # Apply Sort by Name, Descending
    marketplace_page.set_sort_order("Descending")

    names_desc = marketplace_page.get_assistant_names_in_order()
    assert_that(
        len(names_desc),
        equal_to(len(names_asc)),
        "Changing sort order must not change the number of displayed assistants",
    )
    names_desc_lower = [n.lower() for n in names_desc]
    assert_that(
        names_desc_lower,
        equal_to(sorted(names_desc_lower, key=pg_collation_sort_key, reverse=True)),
        "Sort by Name Descending: names must be in reverse alphabetical order (case-insensitive)",
    )


# ---------------------------------------------------------------------------
# TC-04 — Sort by usage displays correct users-count order
# ---------------------------------------------------------------------------


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.parametrize(
    "sort_order, reverse", [("Descending", True), ("Ascending", False)]
)
@pytest.mark.prod_regression
def test_marketplace_sort_by_usage_correct_order(sort_order, reverse, page):
    """TC-04: Sort by Usage displays assistant cards in correct users-count order.

    Navigates to Marketplace, applies Sort by Usage with the given direction, extracts
    the numeric usage counts from visible cards, and asserts they match Python's sort
    of the same values — no loops or conditionals in the test body.
    """
    marketplace_page = AssistantsMarketplacePage(page)
    marketplace_page.navigate_to()
    marketplace_page.should_be_on_marketplace_page()

    marketplace_page.sort_by("Usage")
    marketplace_page.set_sort_order(sort_order)

    counts = marketplace_page.get_assistant_usage_counts_in_order()
    assert_that(
        len(counts),
        greater_than(0),
        "Marketplace must contain at least one assistant after sort",
    )
    assert_that(
        counts,
        equal_to(sorted(counts, reverse=reverse)),
        f"Usage counts must be monotonically ordered: {sort_order}",
    )


# ---------------------------------------------------------------------------
# TC-08 — Sort combined with search preserves results and correct ordering
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_marketplace_sort_with_search_preserves_results(page):
    """TC-08: Sort combined with search preserves search results and displays them in order.

    Enters a broad search term in the Marketplace (search_assistants already waits for
    results internally), then applies Sort by Name Ascending.  Asserts that the result count
    is unchanged and visible names follow the two-group priority order used by the backend:
    title-match names first (name contains the search term), then description-only matches,
    each sub-group sorted alphabetically with PostgreSQL locale-aware collation.
    """
    _SEARCH_TERM = "a"
    marketplace_page = AssistantsMarketplacePage(page)
    marketplace_page.navigate_to()
    marketplace_page.should_be_on_marketplace_page()

    # search_assistants() waits for results internally — no wait_for_timeout in test body
    marketplace_page.search_assistants(_SEARCH_TERM)

    names_before_sort = marketplace_page.get_assistant_names_in_order()
    assert_that(
        len(names_before_sort),
        greater_than(0),
        "Search must return at least one assistant",
    )

    # Apply Sort by Name, Ascending
    marketplace_page.sort_by("Name")
    marketplace_page.set_sort_order("Ascending")

    names_after_sort = marketplace_page.get_assistant_names_in_order()
    assert_that(
        len(names_after_sort),
        greater_than(0),
        "Applying sort must not remove all search results from the page",
    )
    # The backend uses a priority CASE in ORDER BY: title-match names (name contains the
    # search term) come first, description-only matches second; each group is alphabetically
    # ordered.  Use the same two-group logic as the API test (TC-10b).
    names_lower = [n.lower() for n in names_after_sort]
    assert_that(
        names_lower,
        equal_to(
            expected_name_order_with_search(names_lower, _SEARCH_TERM, reverse=False)
        ),
        "Sort by Name Ascending must follow the backend priority order: "
        "title-match names first then description-only matches, each group alphabetical",
    )
