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

import re
from time import sleep
from typing import Union

from hamcrest import assert_that, greater_than
from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.components import (
    WorkflowCard,
    WorkflowSidebar,
)
from codemie_test_harness.tests.ui.pageobject.workflows.create_workflow_page import (
    CreateWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)


class WorkflowsPage(BasePage):
    """Workflows page object with property-based element locators."""

    page_url = "/workflows/"

    def __init__(self, page):
        super().__init__(page)
        self.sidebar = WorkflowSidebar(page)

    # Page elements using @property decorator
    @property
    def page_title(self):
        """Main page title."""
        return self.page.locator("h2:has-text('Workflows')")

    @property
    def page_subtitle(self):
        """Page subtitle."""
        return self.page.locator("text=Browse and run available AI-powered workflows")

    @property
    def search_input(self):
        """Search input field."""
        return self.page.locator('input[placeholder="Search"]')

    @property
    def create_workflow_button(self):
        """Create workflow button."""
        return self.page.locator('button:has-text("Create Workflow")')

    @property
    def clear_all_button(self):
        """Clear all filters button."""
        return self.page.locator('button:has-text("Clear all")')

    @property
    def workflow_cards(self):
        """All workflow cards on the page."""
        return self.page.locator(".bg-surface-specific-card")

    @property
    def pagination_section(self):
        """Pagination section (fixed bottom bar with per-page selector)."""
        return self.page.locator(".fixed.bottom-0")

    @property
    def items_per_page_dropdown(self):
        """Items per page dropdown."""
        return self.page.locator("#per-page")

    @property
    def workflows_nav_link(self):
        """Main workflows navigation link."""
        return self.page.locator('a[href="/workflows/"]')

    @property
    def loading_indicator(self):
        """Loading indicator."""
        return self.page.locator(".loading, .spinner")

    @property
    def empty_state(self):
        """Empty state message."""
        return self.page.locator(".empty-state, .no-results")

    # Navigation methods
    @step
    def navigate_to(self):
        """Navigate to the workflows page."""
        self.page.goto(self.page_url)
        self.wait_for_page_load()
        return self

    # Action methods
    @step
    def search_workflows(self, search_term: str):
        """Search for workflows."""
        self.search_input.fill(search_term)
        self.page.keyboard.press("Enter")
        sleep(2)
        return self

    @step
    def clear_search(self):
        """Clear the search input."""
        self.search_input.clear()
        return self

    @step
    def click_create_workflow(self):
        """Click the create workflow button."""
        self.create_workflow_button.click()
        return CreateWorkflowPage(self.page)

    @step
    def clear_all_filters(self):
        """Clear all applied filters."""
        self.clear_all_button.click()
        return self

    @step
    def change_items_per_page(self, items_count: int):
        """Change the number of items per page."""
        self.items_per_page_dropdown.click()
        self.page.get_by_role("option", name=f"{items_count} items").click()
        sleep(1)
        return self

    # Workflow card methods
    @step
    def get_workflow_card_by_name(self, workflow_name: str):
        """Get WorkflowCard component by workflow name."""
        card_locator = self.page.locator(".bg-surface-specific-card").filter(
            has_text=workflow_name
        )
        return WorkflowCard(self.page, card_locator)

    @step
    def get_workflow_card_by_index(self, index: int):
        """Get WorkflowCard component by index (0-based)."""
        card_locator = self.workflow_cards.nth(index)
        return WorkflowCard(self.page, card_locator)

    @step
    def get_all_workflow_cards(self):
        """Get all WorkflowCard components on the page."""
        cards = self.workflow_cards.all()
        return [WorkflowCard(self.page, card) for card in cards]

    @step
    def run_workflow(self, workflow_name: str):
        """Run a workflow by clicking its run button."""
        workflow_card = self.get_workflow_card_by_name(workflow_name)
        workflow_card.click_run()
        return self

    @step
    def open_workflow_menu(self, workflow_name: str):
        """Open workflow menu by clicking the three dots button."""
        workflow_card = self.get_workflow_card_by_name(workflow_name)
        workflow_card.click_menu()
        return self

    @step
    def click_workflow_card(self, workflow_name: str):
        """Click on a workflow card."""
        workflow_card = self.get_workflow_card_by_name(workflow_name)
        workflow_card.click_card()
        return self

    @step
    def edit_workflow(self, workflow_name: str):
        """Open the edit page for a workflow by clicking Edit in its context menu."""
        workflow_card = self.get_workflow_card_by_name(workflow_name)

        workflow_card.click_edit()
        return EditWorkflowPage(self.page)

    @step
    def hover_workflow_card(self, identifier: Union[str, int]):
        """Hover over a workflow card by name or index."""
        if isinstance(identifier, str):
            workflow_card = self.get_workflow_card_by_name(identifier)
        elif isinstance(identifier, int):
            workflow_card = self.get_workflow_card_by_index(identifier)
        else:
            raise ValueError(
                "Identifier must be either a workflow name (str) or index (int)"
            )

        workflow_card.hover()
        return self

    # Verification methods
    @step
    def should_be_on_workflows_page(self):
        """Verify that we are on the workflows page."""
        # Wait for navigation to workflows page
        self.page.wait_for_url(re.compile(r"/workflows/(my|all)?"), timeout=10000)
        # Wait for page to load
        self.page.wait_for_load_state("networkidle", timeout=10000)
        expect(self.page_title).to_be_visible()
        expect(self.create_workflow_button).to_be_visible()
        return self

    @step
    def should_have_search_input_visible(self):
        """Verify that search input is visible."""
        expect(self.search_input).to_be_visible()
        return self

    @step
    def should_have_create_workflow_button_visible(self):
        """Verify that create workflow button is visible."""
        expect(self.create_workflow_button).to_be_visible()
        return self

    @step
    def should_see_workflow_card(self, workflow_name: str):
        """Verify that a workflow card with the given name is visible."""
        workflow_card = self.get_workflow_card_by_name(workflow_name)
        return workflow_card.is_visible()

    @step
    def should_not_see_workflow_card(self, workflow_name: str):
        """Verify that a workflow card with the given name is not visible."""
        workflow_card = self.get_workflow_card_by_name(workflow_name)
        return not workflow_card.is_visible()

    @step
    def should_see_workflow_with_title(self, workflow_name: str, expected_title: str):
        """Verify workflow card with specific title."""
        workflow_card = self.get_workflow_card_by_name(workflow_name)
        workflow_card.should_have_title(expected_title)
        return self

    @step
    def should_see_workflow_author(self, workflow_name: str, author_name: str):
        """Verify workflow card shows the correct author."""
        workflow_card = self.get_workflow_card_by_name(workflow_name)
        workflow_card.should_have_author(author_name)
        return self

    @step
    def should_see_workflow_description(self, workflow_name: str, description: str):
        """Verify workflow card shows the correct description."""
        workflow_card = self.get_workflow_card_by_name(workflow_name)
        workflow_card.should_have_description(description)
        return self

    @step
    def should_see_shared_workflow(self, workflow_name: str):
        """Verify workflow is marked as shared with project."""
        workflow_card = self.get_workflow_card_by_name(workflow_name)
        workflow_card.should_be_shared_with_project()
        return self

    @step
    def should_see_private_workflow(self, workflow_name: str):
        """Verify workflow is not shared with project."""
        workflow_card = self.get_workflow_card_by_name(workflow_name)
        workflow_card.should_not_be_shared_with_project()
        return self

    @step
    def should_see_workflow_count(self, expected_count: int):
        """Verify the total number of workflow cards displayed."""
        expect(self.workflow_cards).to_have_count(expected_count)
        return self

    @step
    def should_see_workflow_cards(self, minimum_count: int = 0):
        """Verify that search results are displayed."""
        expect(self.workflow_cards.first).to_be_visible(timeout=15000)
        assert_that(self.workflow_cards.count(), greater_than(minimum_count))
        return self

    @step
    def should_see_empty_results(self):
        """Verify that no workflow cards are displayed."""
        expect(self.workflow_cards).to_have_count(0)
        return self

    @step
    def should_see_pagination(self):
        """Verify that pagination controls are visible."""
        expect(self.pagination_section).to_be_visible()
        return self

    @step
    def should_be_on_page(self, page_number: int):
        """Verify the current page number in pagination.

        NOTE: The current UI does not display page number indicators — it only
        shows a per-page count selector (Show: N items). This method verifies
        that the pagination footer is visible as a proxy for page state.
        If explicit page number navigation is restored in the UI, update this
        assertion to use the actual page number element.
        """
        # The current UI has no page number display — verify pagination bar is present
        expect(self.pagination_section).to_be_visible()
        return self

    @step
    def should_have_search_value(self, expected_value: str):
        """Verify the search input contains the expected value."""
        expect(self.search_input).to_have_value(expected_value)
        return self

    @step
    def should_have_empty_search(self):
        """Verify the search input is empty."""
        expect(self.search_input).to_have_value("")
        return self

    @step
    def should_not_see_loading_indicator(self):
        """Verify that loading indicator is not visible."""
        expect(self.loading_indicator).to_be_hidden()
        return self

    @step
    def should_see_empty_state(self):
        """Verify that empty state message is displayed."""
        expect(self.empty_state).to_be_visible()
        return self

    @step
    def should_have_all_main_elements_visible(self):
        """Verify that all main page elements are visible."""
        expect(self.page_title).to_be_visible()
        expect(self.page_subtitle).to_be_visible()
        expect(self.search_input).to_be_visible()
        expect(self.create_workflow_button).to_be_visible()
        self.sidebar.should_be_visible()
        self.sidebar.should_have_categories_section()
        self.sidebar.should_have_filters_section()
        return self
