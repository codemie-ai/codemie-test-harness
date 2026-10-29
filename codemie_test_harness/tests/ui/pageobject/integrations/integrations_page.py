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

"""
Integrations page object for managing integrations.
Contains methods for navigating to integrations, viewing integration lists, and interacting with integrations.
"""

from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.components.integration_row import (
    IntegrationRow,
)

page_url = "/integrations"


# noinspection PyArgumentList
class IntegrationsPage(BasePage):
    """Integrations page with property-based element locators and comprehensive functionality."""

    def __init__(self, page):
        super().__init__(page)

    # Page-specific properties
    @property
    def page_title(self):
        """Page title element."""
        return self.page.get_by_role("heading", name="Integrations", level=2)

    @property
    def create_button(self):
        """Create Integration button."""
        return self.page.locator('[data-pc-name="splitbutton"]').get_by_role(
            "button", name="Create"
        )

    @property
    def user_type_button(self):
        """Integration type User button."""
        return self.page.locator(".p-button").filter(has_text="User")

    @property
    def project_type_button(self):
        """Integration type Project button."""
        return self.page.locator(".p-button").filter(has_text="Project")

    @property
    def create_user_integration_menu_item(self):
        """Create User Integration menu item in the tiered menu."""
        return self.page.get_by_role("link", name="Create User Integration")

    @property
    def create_project_integration_menu_item(self):
        """Create Project Integration menu item in the tiered menu."""
        return self.page.get_by_role("link", name="Create Project Integration")

    @property
    def tiered_menu_overlay(self):
        """Tiered menu overlay containing integration creation options."""
        return self.page.locator("#null_overlay_list, .p-tieredmenu-root-list")

    @property
    def search_input(self):
        """Search input field for filtering integrations."""
        return self.page.locator(
            'input[placeholder*="Search"], input[data-testid="search-input"]'
        )

    @property
    def filter_dropdown(self):
        """Filter dropdown for integration types."""
        return self.page.locator(
            '.filter-dropdown, select[data-testid="filter-select"]'
        )

    @property
    def integrations_table(self):
        """All integration rows on the page."""
        return self.page.locator("table.w-full")

    @property
    def no_integrations_message(self):
        """Message displayed when no integrations are found."""
        return self.page.locator(
            '.no-results, .empty-state, [data-testid="no-integrations"]'
        )

    @property
    def toast_message(self) -> Locator:
        """Toast message after operation."""
        return self.page.locator(".codemie-toast-info")

    @property
    def pagination_container(self):
        """Pagination controls container."""
        return self.page.locator('.pagination, [data-testid="pagination"]')

    @property
    def items_per_page_selector(self):
        """Items per page selector."""
        return self.page.locator(
            '.items-per-page, select[data-testid="items-per-page"]'
        )

    # Navigation and initialization methods
    @step
    def navigate_to(self):
        """Navigate to the integrations page."""
        self.page.goto(page_url)
        self.wait_for_page_load()
        return self

    @step
    def navigate_to_via_menu(self):
        """Navigate to integrations page using header navigation."""
        self.go_to_integrations_page()
        self.wait_for_page_load()
        return self

    @step
    def switch_to_user_tab(self):
        """Switch the integrations list to the User tab."""
        self.user_type_button.click()
        self.wait_for_page_load()
        return self

    @step
    def switch_to_project_tab(self):
        """Switch the integrations list to the Project tab."""
        self.project_type_button.click()
        self.wait_for_page_load()
        return self

    # Integration management actions
    @step
    def click_create_integration(self):
        """Click the Create Integration button to start creating a new integration."""
        self.create_button.click()
        return self

    @step
    def navigate_to_user_integration_creation(self):
        """
        Navigate to the User Integration creation page.

        This method clicks the Create button to open the tiered menu,
        then selects "Create User Integration" from the dropdown menu.

        Returns:
            self: For method chaining
        """
        # Click the Create button to open the tiered menu
        self.create_button.click()

        # Wait for the tiered menu to appear
        self.tiered_menu_overlay.wait_for(state="visible", timeout=5000)

        # Click on "Create User Integration" menu item
        self.create_user_integration_menu_item.click()

        # Wait for navigation to complete
        self.wait_for_page_load()

        return self

    @step
    def navigate_to_project_integration_creation(self):
        """
        Navigate to the Project Integration creation page.

        This method clicks the Create button to open the tiered menu,
        then selects "Create Project Integration" from the dropdown menu.

        Returns:
            self: For method chaining
        """
        # Click the Create button to open the tiered menu
        self.create_button.click()

        # Wait for the tiered menu to appear
        self.tiered_menu_overlay.wait_for(state="visible", timeout=5000)

        # Click on "Create Project Integration" menu item
        self.create_project_integration_menu_item.click()

        # Wait for navigation to complete
        self.wait_for_page_load()

        return self

    @step
    def search_integrations(self, search_term: str):
        """
        Search for integrations using the search input.

        Args:
            search_term (str): The term to search for
        """
        self.search_input.clear()
        self.search_input.fill(search_term)
        self.search_input.press("Enter")
        self.wait_for_page_load()
        return self

    @step
    def clear_search(self):
        """Clear the search input."""
        self.search_input.clear()
        self.search_input.press("Enter")
        self.wait_for_page_load()
        return self

    @step
    def select_filter(self, filter_type: str):
        """
        Select a filter type from the filter dropdown.

        Args:
            filter_type (str): The integration type to filter by (e.g., "AWS", "JIRA", "GIT")
        """
        self.filter_dropdown.click()
        self.page.locator(
            f'option[value="{filter_type}"], .filter-option:has-text("{filter_type}")'
        ).click()
        self.wait_for_page_load()
        return self

    @step
    def clear_filters(self):
        """Clear all applied filters."""
        clear_filters_btn = self.page.locator(
            'button:has-text("Clear Filters"), [data-testid="clear-filters"]'
        )
        if clear_filters_btn.is_visible():
            clear_filters_btn.click()
            self.wait_for_page_load()
        return self

    # Integration card interactions
    @step
    def get_integration_card_by_name(self, integration_name: str) -> IntegrationRow:
        """
        Get an integration card by its name.

        Args:
            integration_name (str): The name of the integration

        Returns:
            IntegrationRow: The integration card component
        """
        card_locator = self.integrations_table.filter(has_text=integration_name).first
        return IntegrationRow(self.page, card_locator)

    @step
    def get_integration_row_by_alias(self, alias: str) -> IntegrationRow:
        """
        Get an integration row by its alias.

        Args:
            alias (str): The alias of the integration

        Returns:
            IntegrationRow: The integration row component
        """
        # Find the row containing the alias text
        row_locator = self.integrations_table.locator("tbody tr").filter(has_text=alias)
        return IntegrationRow(self.page, row_locator)

    @step
    def get_all_integration_cards(self) -> list[IntegrationRow]:
        """
        Get all visible integration cards.

        Returns:
            list[IntegrationRow]: List of all integration card components
        """
        cards = []
        count = self.integrations_table.count()
        for i in range(count):
            card_locator = self.integrations_table.nth(i)
            cards.append(IntegrationRow(self.page, card_locator))
        return cards

    # Pagination methods
    @step
    def navigate_to_page(self, page_number: int):
        """
        Navigate to a specific page in pagination.

        Args:
            page_number (int): The page number to navigate to
        """
        page_btn = self.pagination_container.locator(
            f'button:has-text("{page_number}"), a:has-text("{page_number}")'
        )
        page_btn.click()
        self.wait_for_page_load()
        return self

    @step
    def go_to_next_page(self):
        """Navigate to the next page."""
        next_btn = self.pagination_container.locator(
            'button:has-text("Next"), [data-testid="next-page"]'
        )
        if next_btn.is_enabled():
            next_btn.click()
            self.wait_for_page_load()
        return self

    @step
    def go_to_previous_page(self):
        """Navigate to the previous page."""
        prev_btn = self.pagination_container.locator(
            'button:has-text("Previous"), [data-testid="prev-page"]'
        )
        if prev_btn.is_enabled():
            prev_btn.click()
            self.wait_for_page_load()
        return self

    @step
    def change_items_per_page(self, items_count: int):
        """
        Change the number of items displayed per page.

        Args:
            items_count (int): Number of items to display per page
        """
        self.items_per_page_selector.select_option(value=str(items_count))
        self.wait_for_page_load()
        return self

    # Utility methods
    @step
    def get_integrations_count(self) -> int:
        """
        Get the total number of visible integration cards.

        Returns:
            int: Number of integration cards
        """
        return self.integrations_table.count()

    @step
    def get_current_page_number(self) -> int:
        """
        Get the current page number from pagination.

        Returns:
            int: Current page number
        """
        current_page = self.pagination_container.locator(
            '.active, .current-page, [aria-current="page"]'
        )
        if current_page.is_visible():
            return int(current_page.text_content())
        return 1

    @step
    def integration_exists(self, integration_name: str) -> bool:
        """
        Check if an integration with the given name exists.

        Args:
            integration_name (str): The name of the integration to check

        Returns:
            bool: True if integration exists, False otherwise
        """
        return self.integrations_table.filter(has_text=integration_name).count() > 0

    # Verification methods
    @step
    def should_be_on_integrations_page(self):
        """Verify that the user is on the integrations page."""
        expect(self.page).to_have_url(page_url)
        return self

    @step
    def should_have_page_title(self, expected_title: str = "Integrations"):
        """Verify the page title."""
        expect(self.page_title).to_contain_text(expected_title)
        return self

    @step
    def should_see_create_integration_button(self):
        """Verify that the Create Integration button is visible."""
        expect(self.create_button).to_be_visible()
        return self

    @step
    def should_see_integration_type_switcher(self):
        """Verify that the Integration type selectors are visible."""
        expect(self.user_type_button).to_be_visible()
        expect(self.project_type_button).to_be_visible()
        return self

    @step
    def should_see_search_input(self):
        """Verify that the search input is visible."""
        expect(self.search_input).to_be_visible()
        return self

    @step
    def should_see_integrations_table(self):
        """Verify that integration table is visible."""
        expect(self.integrations_table).to_be_visible()
        return self

    @step
    def should_see_specific_integration(self, integration_name: str):
        """
        Verify that a specific integration is visible.

        Args:
            integration_name (str): The name of the integration to verify
        """
        integration_card = self.get_integration_card_by_name(integration_name)
        integration_card.should_be_visible()
        return self

    @step
    def should_not_see_integration(self, integration_name: str):
        """
        Verify that a specific integration is not visible.

        Args:
            integration_name (str): The name of the integration that should not be visible
        """
        expect(self.integrations_table.filter(has_text=integration_name)).to_have_count(
            0
        )
        return self

    @step
    def should_see_no_integrations_message(self):
        """Verify that the no integrations message is displayed."""
        expect(self.no_integrations_message).to_be_visible()
        return self

    @step
    def should_have_pagination(self):
        """Verify that pagination controls are visible."""
        expect(self.pagination_container).to_be_visible()
        return self

    @step
    def should_see_message(self, message: str):
        """
        Verify that a message is displayed.

        Args:
            message (str, optional): Specific message to verify
        """
        expect(self.toast_message).to_be_visible()
        if message:
            expect(self.toast_message).to_contain_text(message)
        return self

    @step
    def should_not_see_message(self):
        """
        Verify that a toast message is not displayed.
        """
        self.page.mouse.move(0, 0)
        expect(self.toast_message).to_be_hidden()
        return self

    def _integration_row_by_alias(self, alias: str):
        """A specific integration table row identified by its alias."""
        return self.integrations_table.locator("tbody tr").filter(has_text=alias)

    @step
    def should_show_project_display_name_in_table_row(
        self, alias: str, display_name: str
    ):
        """Verify the integration row for the given alias shows display_name as project hover tooltip."""
        row = self._integration_row_by_alias(alias)
        trigger = row.locator('[data-tooltip-id="react-tooltip"]').first
        trigger.hover()
        self.page.wait_for_timeout(300)
        expect(self.page.locator('[role="tooltip"]')).to_contain_text(display_name)
        return self
