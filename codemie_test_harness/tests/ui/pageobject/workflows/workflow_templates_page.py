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

from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from playwright.sync_api import Page, expect

from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)


class WorkflowTemplatesPage(BasePage):
    """Page object for the Workflow Templates page."""

    page_url = "/workflows/templates"

    def __init__(self, page: Page):
        super().__init__(page)

    # ==================== PROPERTIES ====================

    @property
    def templates_list(self):
        return self.page.locator(".body.h-card")

    @property
    def templates_create_list(self):
        return self.templates_list.get_by_label("Create Workflow")

    # ==================== NAVIGATION METHODS ====================
    @step
    def navigate_to(self):
        """Navigate to the workflow templates page."""
        self.page.goto(self.page_url)

    @step
    def click_create_workflow_from_template(self, index: int):
        """Verify that user on workflow templates page can create new workflow template."""
        self.templates_create_list.nth(index).click()

    # ==================== INTERACTION METHODS ====================
    @step
    def template_details_click(self, index: int):
        """Verify that user on workflow templates page can click on template page."""
        self.templates_list.nth(index).click()

    @step
    def click_create_workflow_from_specific_template(self, template_name: str):
        """Verify that user on workflow templates page can create new workflow template."""
        self.page.locator(
            f"//div[text()='{template_name}']/following::button[@type='button'][1]"
        ).click()

    # ==================== VERIFICATION METHODS ====================
    @step
    def should_have_templates(self, count):
        """Verify that workflow templates page have predefined workflows."""
        expect(self.templates_list).to_have_count(count)
        return self

    @step
    def should_have_title_description(
        self, index: int, title: str, description: str, tooltip_description: str
    ):
        """Verify that workflow templates have titles."""
        workflow_page = WorkflowsPage(self.page)
        workflow_card = workflow_page.get_workflow_card_by_index(index)
        expect(workflow_card.title).to_have_text(title)
        expect(workflow_card.description).to_contain_text(description)
        workflow_page.hover_workflow_card(index)
        if workflow_card.description_tooltip.is_visible():
            expect(workflow_card.description_tooltip).to_contain_text(
                tooltip_description
            )
        return self

    @step
    def should_have_templates_visible(self):
        """Verify that at least one template card is visible on the current page."""
        expect(self.templates_list.first).to_be_visible()
        return self

    @step
    def should_see_pagination(self):
        """Verify that pagination controls (page-number buttons) are visible."""
        expect(self.pagination_block).to_be_visible()
        return self

    @step
    def should_not_see_pagination(self):
        """Verify that no pagination controls are visible."""
        expect(self.pagination_block).not_to_be_visible()
        return self

    @step
    def should_have_previous_page_disabled(self):
        """Verify that the previous-page button is disabled or absent on page 1.

        Some Pagination implementations hide the button on the first page; both
        hidden and disabled states are accepted as valid boundary behaviour.
        """
        prev_btn = self.pagination_previous_button
        if prev_btn.is_visible():
            expect(prev_btn).to_be_disabled()
        return self

    @step
    def should_have_next_page_disabled(self):
        """Verify that the next-page button is disabled or absent on the last page."""
        next_btn = self.pagination_next_button
        if next_btn.is_visible():
            expect(next_btn).to_be_disabled()
        return self

    @step
    def get_templates_page_text(self) -> list:
        """Return the inner-text of every visible template card for page comparison."""
        return self.templates_list.all_inner_texts()

    def get_first_template_title(self) -> str:
        """Return the title (first text line) of the first visible template card.

        Uses only the first non-empty line of inner_text so the value is short
        and unambiguous — suitable as a ``has_text`` filter argument.
        """
        raw = self.templates_list.first.inner_text()
        return next(line.strip() for line in raw.splitlines() if line.strip())

    @step
    def should_not_contain_template_text(self, text: str) -> "WorkflowTemplatesPage":
        """Verify no template card on the current page contains the given text.

        Used to confirm navigation to the next page (a specific page-1 title must
        not appear on page 2).
        """
        expect(self.templates_list.filter(has_text=text)).to_have_count(0)
        return self

    @step
    def should_contain_template_text(self, text: str) -> "WorkflowTemplatesPage":
        """Verify at least one template card on the current page contains the given text.

        Used to confirm navigation back to page 1 (a previously captured title
        must be visible again).
        """
        expect(self.templates_list.filter(has_text=text)).not_to_have_count(0)
        return self

    @step
    def should_have_card_count_other_than(self, count: int) -> "WorkflowTemplatesPage":
        """Verify the number of template cards on the page differs from the given count.

        Used after changing items-per-page: the new card count must differ from
        the count observed before the change, confirming AC-4 (card list reloaded).
        """
        expect(self.templates_list).not_to_have_count(count)
        return self

    @step
    def click_next_page(self):
        """Click the next-page button and wait for template list to reload.

        Overrides BasePage.click_next_page with a networkidle wait so the
        async `workflowsStore.indexWorkflowTemplates()` call has time to finish
        before assertions are made on the new page content.
        """
        self.pagination_next_button.click()
        self.page.wait_for_load_state("networkidle", timeout=15000)

    @step
    def click_previous_page(self):
        """Click the previous-page button and wait for template list to reload."""
        self.pagination_previous_button.click()
        self.page.wait_for_load_state("networkidle", timeout=15000)

    @step
    def select_page(self, page_number: int):
        """Click a specific page-number button and wait for template list to reload.

        Overrides BasePage.select_page with a networkidle wait consistent with
        click_next_page / click_previous_page to avoid flakiness on async reloads.
        """
        self.pagination_page_button(page_number).click()
        self.page.wait_for_load_state("networkidle", timeout=15000)

    @step
    def change_items_per_page(self, count: int):
        """Change items-per-page via the per-page PrimeReact Dropdown (no-op if not rendered).

        The `#per-page` element is a PrimeReact Dropdown (``<div>``), not a native
        ``<select>``.  Interaction requires: click to open → click the target option.

        Args:
            count: the desired page size value to select.
        """
        dropdown = self.show_per_page_dropdown
        if not dropdown.is_visible():
            return
        dropdown.click()
        self.page.wait_for_timeout(400)
        # PrimeReact renders options as <li class="p-dropdown-item">
        target = self.page.locator(
            f'li.p-dropdown-item[data-p-value="{count}"], '
            f'li.p-dropdown-item:has-text("{count}")'
        )
        if target.first.is_visible(timeout=2000):
            target.first.click()
        else:
            # Requested count not in list — pick first available option as fallback
            fallback = self.page.locator("li.p-dropdown-item").first
            if fallback.is_visible(timeout=2000):
                fallback.click()
            else:
                self.page.keyboard.press("Escape")
        self.page.wait_for_load_state("networkidle", timeout=15000)

    @step
    def navigate_to_last_page(self):
        """Navigate to the last available page by clicking Next until it is disabled."""
        for _ in range(50):
            next_btn = self.pagination_next_button
            if not next_btn.is_visible():
                break
            if next_btn.is_disabled():
                break
            next_btn.click()
            self.page.wait_for_load_state("networkidle", timeout=15000)

    # ==================== SEARCH / FILTER METHODS ====================

    @property
    def search_input(self):
        """Search / name filter input on the Workflow Templates page."""
        return self.page.get_by_placeholder("Search")

    @step
    def type_search(self, text: str) -> "WorkflowTemplatesPage":
        """Fill the search input with *text* and wait for client-side filtering."""
        self.search_input.fill(text)
        self.page.wait_for_timeout(600)
        return self

    @step
    def clear_search(self) -> "WorkflowTemplatesPage":
        """Clear the search input and wait for the full list to be restored."""
        self.search_input.clear()
        self.page.wait_for_timeout(600)
        return self

    @step
    def get_filter_value(self) -> str:
        """Return the current value of the search input."""
        return self.search_input.input_value()

    @step
    def should_show_search_input_visible(self) -> "WorkflowTemplatesPage":
        """Verify that the search/filter input is visible on the page."""
        expect(self.search_input).to_be_visible()
        return self

    @step
    def should_show_results_count(self, expected_count: int) -> "WorkflowTemplatesPage":
        """Verify the number of visible template cards equals *expected_count*."""
        expect(self.templates_list).to_have_count(expected_count)
        return self

    @step
    def should_show_template(self, partial_name: str) -> "WorkflowTemplatesPage":
        """Verify that every visible template card contains *partial_name*."""
        cards = self.page.locator(".body.h-card")
        expect(cards.first).to_be_visible()
        expect(cards.filter(has_not_text=partial_name)).to_have_count(0)
        return self

    @step
    def should_not_show_template(self, partial_name: str) -> "WorkflowTemplatesPage":
        """Verify that no visible template card contains *partial_name*."""
        expect(
            self.page.locator(".body.h-card").filter(has_text=partial_name)
        ).to_have_count(0)
        return self
