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

# Copyright 2024 EPAM Systems, Inc.
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
from __future__ import annotations


import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.assistants_marketplace_page import (
    AssistantsMarketplacePage,
)


"""
UI Test — TC-02: Search Assistant Templates by Text (Full Journey)

Feature: Add filters to Workflows and Assistants Templates pages

Coverage:
- AC-2: A search filter is added to the Assistants Templates page
- AC-4: Entering a valid query filters the displayed templates accordingly
- AC-5: Clearing the search query restores the full templates list
- AC-3: The search filter is visually and behaviourally consistent
- AC-6: The search filter works without breaking existing functionality
"""


# ---------------------------------------------------------------------------
# Search query constants — partial names expected to match a subset of
# predefined assistant templates without matching ALL of them.
# ---------------------------------------------------------------------------
_SEARCH_QUERY_1 = "Code"
_SEARCH_QUERY_2 = "Review"


@pytest.mark.assistant
@pytest.mark.ui
def test_assistant_template_search_journey(page):
    """TC-02: Full search journey on the Assistant Templates page.

    Steps:
    1. Navigate to /assistants/templates
    2. Verify the search/filter input is visible
    3. Enter a partial name query matching a subset of assistant templates
    4. Verify filtered results are shown (at least one matching card)
    5. Clear the search input
    6. Verify all templates are restored
    7. Enter a different search query and verify filtered results update
    8. Navigate away to /assistants
    9. Navigate back to /assistants/templates
    10. Verify previous search filter state persists (value + filtered results)
    """
    templates_page = AssistantsMarketplacePage(page)

    # Step 1 — Navigate to assistant templates
    templates_page.navigate_to_templates()

    # Step 2 — Search input must be visible
    templates_page.should_be_on_templates_page()
    templates_page.should_show_search_input_visible()

    # Step 3 — Enter first search query
    templates_page.type_search_on_templates(_SEARCH_QUERY_1)

    # Step 4 — Filtered results shown: every visible card contains the search term
    templates_page.should_show_template(_SEARCH_QUERY_1)

    # Step 5 — Clear search
    templates_page.clear_search_on_templates()

    # Step 6 — All templates restored (count > 0 and no filter active)
    templates_page.should_display_assistants()

    # Step 7 — Enter a different search query
    templates_page.type_search_on_templates(_SEARCH_QUERY_2)
    templates_page.should_show_template(_SEARCH_QUERY_2)

    # Step 8 — Navigate away to /assistants list
    templates_page.navigate_to_assistants_list()

    # Step 9 — Navigate back to /assistants/templates
    templates_page.navigate_to_templates()

    # Step 10 — Verify previous search filter persists
    # (server-side filtering state should survive in-session navigation)
    templates_page.should_be_on_templates_page()
    templates_page.should_show_template(_SEARCH_QUERY_2)
