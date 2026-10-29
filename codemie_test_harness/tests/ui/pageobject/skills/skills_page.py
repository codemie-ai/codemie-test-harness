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
Skills List Page Object following Page Object Model (POM) best practices.

This class encapsulates all interactions with the Skills list page,
providing a clean interface for test automation.
"""

import re
from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.skills.create_edit_skill_page import (
    CreateEditSkillPage,
)


class SkillsPage(BasePage):
    """Page object for the Skills list page."""

    page_url = "/skills"

    def __init__(self, page):
        """Initialize the Skills page object."""
        super().__init__(page)

    # =============================================================================
    # LOCATORS - Page Elements
    # =============================================================================

    @property
    def page_heading(self) -> Locator:
        """Skills page heading"""
        return self.page.locator('h2:has-text("Skills")')

    @property
    def page_description(self) -> Locator:
        """Page description text"""
        return self.page.locator(
            'p:has-text("Create and manage reusable knowledge for your assistants")'
        )

    @property
    def create_skill_button(self) -> Locator:
        """Create Skill button in header"""
        return self.page.get_by_role("button", name="Create Skill")

    @property
    def skills_tab(self) -> Locator:
        """Skills tab (default view)"""
        return self.page.locator('button:has-text("Skills")').first

    @property
    def project_skills_tab(self) -> Locator:
        """Project Skills tab"""
        return self.page.get_by_role("button", name="Project Skills")

    @property
    def marketplace_tab(self) -> Locator:
        """Marketplace tab"""
        return self.page.get_by_role("button", name="Marketplace")

    @property
    def search_input(self) -> Locator:
        """Search input field"""
        return self.page.get_by_placeholder("Search")

    @property
    def visibility_all_radio(self) -> Locator:
        """Visibility filter - All option (clicks label element)"""
        return self.page.locator('label:has-text("All")').filter(
            has=self.page.locator('input[name="visibility"]')
        )

    @property
    def visibility_private_radio(self) -> Locator:
        """Visibility filter - Private option (clicks label element)"""
        return self.page.locator('label:has-text("Private")').filter(
            has=self.page.locator('input[name="visibility"]')
        )

    @property
    def visibility_project_radio(self) -> Locator:
        """Visibility filter - Project option (clicks label element)"""
        return self.page.locator('label:has-text("Project")').filter(
            has=self.page.locator('input[name="visibility"]')
        )

    @property
    def skills_count_label(self) -> Locator:
        """Skills count label (e.g., '6 SKILLS')"""
        return self.page.locator("text=/\\d+ SKILLS/")

    @property
    def project_selector(self) -> Locator:
        """Project filter dropdown/combobox"""
        return self.page.locator('input[aria-label="Project"]')

    @property
    def categories_selector(self) -> Locator:
        """Categories filter dropdown/combobox"""
        return self.page.locator('input[aria-label="Categories"]')

    @property
    def author_selector(self) -> Locator:
        """Created By (Author) filter dropdown/combobox"""
        return self.page.locator('input[placeholder="Created By"]')

    @property
    def created_by_me_checkbox(self) -> Locator:
        """Created By 'Me' checkbox filter"""
        return self.page.get_by_role("checkbox", name="Me")

    @property
    def project_filter_button(self) -> Locator:
        """PROJECT filter section expand/collapse button"""
        return self.page.get_by_role("button", name="PROJECT", exact=True)

    @property
    def categories_filter_button(self) -> Locator:
        """CATEGORIES filter section expand/collapse button"""
        return self.page.get_by_role("button", name="CATEGORIES", exact=True)

    @property
    def created_by_filter_button(self) -> Locator:
        """CREATED BY filter section expand/collapse button"""
        return self.page.get_by_role("button", name="CREATED BY", exact=True)

    @property
    def visibility_filter_button(self) -> Locator:
        """VISIBILITY filter section expand/collapse button"""
        return self.page.get_by_role("button", name="VISIBILITY", exact=True)

    def skill_card(self, skill_name: str) -> Locator:
        """Get skill card by name - returns the card container"""
        return (
            self.page.locator(f'h3:has-text("{skill_name}")')
            .locator("..")
            .locator("..")
            .locator("..")
            .locator("..")
        )

    def skill_card_by_partial_name(self, partial_name: str) -> Locator:
        """Get skill card by partial name match"""
        return self.page.locator(f'h3:text-matches(".*{partial_name}.*", "i")').locator(
            ".."
        )

    def skill_card_menu_button(self, skill_name: str) -> Locator:
        """Get 3-dot menu button for a skill card"""
        card = self.skill_card(skill_name)
        # The 3-dot menu button is the second button in the card (index 1)
        return card.locator("button").nth(1)

    @property
    def menu_publish_to_marketplace(self) -> Locator:
        """Publish to Marketplace menu item"""
        return self.page.get_by_role("menuitem", name="Publish to Marketplace")

    @property
    def menu_view_details(self) -> Locator:
        """View Details menu item"""
        return self.page.get_by_role("menuitem", name="View Details")

    @property
    def menu_edit(self) -> Locator:
        """Edit menu item"""
        return self.page.get_by_role("menuitem", name="Edit")

    @property
    def menu_delete(self) -> Locator:
        """Delete menu item"""
        return self.page.get_by_role("menuitem", name="Delete")

    @property
    def publish_confirmation_dialog(self) -> Locator:
        """Publish to Marketplace confirmation dialog"""
        return self.page.get_by_role("dialog")

    @property
    def publish_button(self) -> Locator:
        """Publish button in confirmation dialog"""
        return self.page.get_by_role("button", name="Publish")

    @property
    def cancel_button(self) -> Locator:
        """Cancel button in confirmation dialog"""
        return self.page.get_by_role("button", name="Cancel")

    # =============================================================================
    # NAVIGATION METHODS
    # =============================================================================

    @step("Navigate to Skills page")
    def navigate_to(self):
        """Navigate to the Skills page."""
        self.page.goto(self.page_url)
        self.wait_for_page_load()
        return self

    @step("Click Create Skill button")
    def click_create_skill(self):
        """Click the Create Skill button."""
        self.create_skill_button.click()
        self.wait_for_page_load()
        create_page = CreateEditSkillPage(page=self.page)
        # Dismiss the "Generate Skill with AI" dialog if it appears automatically
        if create_page.generate_with_ai_dialog.is_visible():
            create_page.create_manually_button.click()
        return create_page

    @step("Switch to Project Skills tab")
    def switch_to_project_skills_tab(self):
        """Switch to the Project Skills tab."""
        self.project_skills_tab.click()
        # Wait for tab content to load
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @step("Switch to Marketplace tab")
    def switch_to_marketplace_tab(self):
        """Switch to the Marketplace tab."""
        self.marketplace_tab.click()
        # Wait for tab content to load
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @step("Click on skill card")
    def click_skill_card(self, skill_name: str):
        """Click on a skill card by name."""
        self.skill_card(skill_name).click()
        self.wait_for_page_load()
        return self

    @step("Open skill card menu")
    def open_skill_card_menu(self, skill_name: str):
        """Open the 3-dot menu for a skill card."""
        self.skill_card_menu_button(skill_name).click()
        return self

    @step("Close skill card menu")
    def close_skill_card_menu(self):
        """Close the 3-dot menu for a skill card."""
        self.menu_publish_to_marketplace.press("Escape")
        return self

    @step("Open skill details page")
    def open_skill_details(self, skill_name: str):
        """Open the 3-dot menu for the given skill and click View Details.

        Returns a SkillDetailPage for the opened detail view.
        """
        from codemie_test_harness.tests.ui.pageobject.skills.skill_detail_page import (
            SkillDetailPage,
        )

        self.open_skill_card_menu(skill_name)
        self.menu_view_details.click()
        self.page.wait_for_load_state("domcontentloaded")
        return SkillDetailPage(self.page)

    @step("Publish skill to marketplace")
    def publish_skill_to_marketplace(self, skill_name: str):
        """Publish a skill to marketplace from the 3-dot menu.

        Navigates to the Skills page first in case the caller is on a
        different page (e.g., right after creating a skill).
        """
        self.navigate_to()
        self.open_skill_card_menu(skill_name)
        self.menu_publish_to_marketplace.click()
        return self

    @step("Click Edit from skill menu")
    def edit_skill_from_menu(self, skill_name: str):
        """Edit a skill from the 3-dot menu."""
        self.open_skill_card_menu(skill_name)
        self.menu_edit.click()
        self.wait_for_page_load()
        return self

    @step("Click Delete from skill menu")
    def delete_skill_from_menu(self, skill_name: str):
        """Delete a skill from the 3-dot menu."""
        self.open_skill_card_menu(skill_name)
        self.menu_delete.click()
        # Wait for delete dialog/action to appear
        self.page.wait_for_load_state("domcontentloaded")
        return self

    # =============================================================================
    # FILTER METHODS
    # =============================================================================

    @step("Filter by Private visibility")
    def filter_by_private(self):
        """Filter skills by Private visibility."""
        self.visibility_private_radio.click(force=True)
        # Wait for filter to be applied
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @step("Filter by Project visibility")
    def filter_by_project(self):
        """Filter skills by Project visibility."""
        self.visibility_project_radio.click(force=True)
        # Wait for filter to be applied
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @step("Filter by All visibility")
    def filter_by_all(self):
        """Filter skills by All visibility."""
        self.visibility_all_radio.click(force=True)
        # Wait for filter to be applied
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @step("Search for skills")
    def search_skill(self, search_text: str):
        """Search for skills using the search input."""
        self.search_input.fill(search_text)
        # Wait for search to trigger (debounced search)
        self.page.wait_for_load_state("domcontentloaded")
        return self

    # =============================================================================
    # VERIFICATION METHODS
    # =============================================================================

    @step("Verify on Skills page")
    def should_be_on_skills_page(self):
        """Verify that we are on the Skills page."""
        expect(self.page).to_have_url(re.compile(r".*/skills.*"))
        self.should_have_page_heading()
        return self

    @step("Verify Create Skill button is visible")
    def should_have_create_button_visible(self):
        """Verify that the Create Skill button is visible."""
        expect(self.create_skill_button).to_be_visible()
        expect(self.create_skill_button).to_be_enabled()
        return self

    @step("Verify page heading is visible")
    def should_have_page_heading(self):
        """Verify that the page heading is visible."""
        expect(self.page_heading).to_be_visible()
        return self

    @step("Verify page description is visible")
    def should_have_page_description(self):
        """Verify that the page description is visible."""
        expect(self.page_description).to_be_visible()
        return self

    @step("Verify tabs are visible")
    def should_have_tabs_visible(self):
        """Verify that all tabs are visible."""
        expect(self.project_skills_tab).to_be_visible()
        expect(self.marketplace_tab).to_be_visible()
        return self

    @step("Verify skill card is visible")
    def should_see_skill_with_name(self, skill_name: str):
        """Verify that a skill with the given name is visible.

        Navigates to the Skills page first in case the caller is on a
        different page (e.g., right after saving a skill on create/edit page).
        """
        # Ensure we are on the skills list page
        self.navigate_to()

        # First try to find the skill without search
        skill_locator = self.skill_card(skill_name)
        if skill_locator.count() == 0:
            # If not found, use search to filter the list
            self.search_skill(skill_name)
            # Wait for search to complete
            self.page.wait_for_load_state("networkidle")

        expect(self.skill_card(skill_name)).to_be_visible(timeout=10000)
        return self

    @step("Verify skill card is not visible")
    def should_not_see_skill_with_name(self, skill_name: str):
        """Verify that a skill with the given name is NOT visible (doesn't exist)."""
        # Wait for the skills list to load
        self.page.wait_for_load_state("networkidle")

        # The skill card should not exist
        skill_locator = self.skill_card(skill_name)
        expect(skill_locator).not_to_be_visible()
        return self

    @step("Verify filters are visible")
    def should_have_filters_visible(self):
        """Verify that filter controls are visible."""
        # Visibility radio buttons
        expect(self.visibility_all_radio).to_be_visible()
        expect(self.visibility_private_radio).to_be_visible()
        expect(self.visibility_project_radio).to_be_visible()

        # Search input
        expect(self.search_input).to_be_visible()

        # Filter dropdowns/comboboxes
        expect(self.project_selector).to_be_visible()
        expect(self.categories_selector).to_be_visible()
        expect(self.author_selector).to_be_visible()

        # Created By checkbox
        expect(self.created_by_me_checkbox).to_be_visible()

        return self

    @step("Verify publish to marketplace button is visible in menu")
    def should_have_publish_button_in_menu(self, skill_name: str):
        """Verify that Publish to Marketplace option is visible in 3-dot menu."""
        self.open_skill_card_menu(skill_name)
        expect(self.menu_publish_to_marketplace).to_be_visible()
        return self

    @step("Verify publish confirmation dialog is visible")
    def publish_confirm_dialog_should_be_visible(self):
        """Verify that the Publish to Marketplace confirmation dialog is visible."""
        expect(self.publish_confirmation_dialog).to_be_visible()
        return self

    @step("Confirm publish to marketplace")
    def confirm_publish(self):
        """Click the Publish button in the confirmation dialog."""
        self.publish_button.click()
        return self
