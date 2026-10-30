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

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.assistant_templates_page import (
    AssistantTemplatesPage,
)

_PAGINATION_PAGE_SIZE = 12


@pytest.fixture(scope="function")
def prebuilt_assistant_templates(assistant_utils):
    """Fixture returns the list of prebuilt assistant templates from the API."""
    return assistant_utils.get_prebuilt_assistant()


@pytest.mark.assistant
@pytest.mark.assistant_templates
@pytest.mark.pagination
@pytest.mark.ui
@pytest.mark.prod_regression
def test_assistant_templates_pagination_full_flow(page, prebuilt_assistant_templates):
    """TC-002: Assistant Templates pagination full flow.

    Covers AC-2, AC-3, AC-4, AC-5.

    Steps executed in sequence within a single test (mirrors a manual walkthrough):
      1. Navigate to /assistants/templates.
      2. Template cards visible on page 1 — AC-5.
      3. Pagination controls visible — AC-2.
      5. Previous-page button disabled on page 1 — boundary.
      6. Click next page; verify different card set — AC-3.
      7. Click previous page; verify return to page-1 card set — AC-3.
      8. Conditional: click page 2 directly — AC-3.
      9. Change items-per-page (if control present) — AC-4.
     10. Navigate to last page; next-page button disabled — boundary.
     11. Reload page; page-1 cards still visible — AC-3.

    Precondition: environment has more than _PAGINATION_PAGE_SIZE assistant templates.
    The test is skipped gracefully when this precondition is not met.
    """
    templates = prebuilt_assistant_templates
    total = len(templates)

    at_page = AssistantTemplatesPage(page)
    at_page.navigate_to()

    # Step 2: template cards visible on page 1 — AC-5
    at_page.should_have_templates_visible()

    if total <= _PAGINATION_PAGE_SIZE:
        pytest.skip(
            f"Only {total} assistant templates in the environment; "
            f"need > {_PAGINATION_PAGE_SIZE} to trigger pagination. "
            "Skipping TC-002 pagination flow."
        )

    # Step 3: pagination controls visible — AC-2
    at_page.should_see_pagination()

    # Step 5: previous-page button disabled / absent on page 1
    at_page.should_have_previous_page_disabled()

    # Step 6: click next page, verify a different card set loads — AC-3
    page1_first_title = at_page.get_first_template_title()
    at_page.click_next_page()
    at_page.should_have_templates_visible()
    at_page.should_not_contain_template_text(page1_first_title)

    # Step 7: click previous page, verify return to original card set — AC-3
    at_page.click_previous_page()
    at_page.should_have_templates_visible()
    at_page.should_contain_template_text(page1_first_title)

    # Step 8: direct page-number button navigation (conditional) — AC-3
    page2_btn = at_page.pagination_page_button(2)
    if page2_btn.is_visible():
        at_page.select_page(2)
        at_page.should_see_pagination()
        at_page.should_not_contain_template_text(page1_first_title)

    # Step 9: change items-per-page — AC-4
    if at_page.show_per_page_dropdown.is_visible():
        initial_card_count = at_page.templates_list.count()
        at_page.change_items_per_page(24)
        at_page.should_have_card_count_other_than(initial_card_count)
    # else: per-page dropdown absent — AC-4 skipped gracefully

    # Step 10: navigate to last page, verify next-page button disabled — boundary
    at_page.navigate_to()
    at_page.navigate_to_last_page()
    at_page.should_have_next_page_disabled()

    # Step 11: reload from last page; verify cards still visible after state reset — AC-3
    at_page.refresh_page()
    at_page.should_have_templates_visible()
