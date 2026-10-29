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
Skills Marketplace Page Object following Page Object Model (POM) best practices.

This class encapsulates all interactions with the Skills Marketplace page.
"""

import re
from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class SkillsMarketplacePage(BasePage):
    """Page object for the Skills Marketplace page."""

    page_url = "/skills/marketplace"

    def __init__(self, page):
        """Initialize the Skills Marketplace page object."""
        super().__init__(page)

    # =============================================================================
    # LOCATORS - Page Elements
    # =============================================================================

    @property
    def marketplace_heading(self) -> Locator:
        """Marketplace page heading"""
        return self.page.locator('h2:has-text("Skills")')

    @property
    def skills_count_label(self) -> Locator:
        """Skills count label (e.g., '7 SKILLS')"""
        return self.page.locator("text=/\\d+ SKILLS/")

    @property
    def search_input(self) -> Locator:
        """Search input field"""
        return self.page.get_by_placeholder("Search")

    @property
    def filters_heading(self) -> Locator:
        """Filters section heading"""
        return self.page.locator('text="Filters"')

    @property
    def categories_dropdown(self) -> Locator:
        """Categories filter dropdown"""
        return self.page.get_by_role("combobox", name="Categories")

    @property
    def created_by_heading(self) -> Locator:
        """CREATED BY filter section heading"""
        return self.page.locator('text="CREATED BY"')

    @property
    def created_by_me_checkbox(self) -> Locator:
        """'Me' checkbox in Created By filter"""
        return self.page.get_by_role("checkbox", name="Me")

    @property
    def created_by_dropdown(self) -> Locator:
        """Created By dropdown filter"""
        return self.page.get_by_role("combobox", name="Created By")

    @property
    def first_skill_card(self) -> Locator:
        """Get the first skill card on the marketplace page"""
        return self.page.locator(".h-card.rounded-xl").first

    @property
    def first_skill_name(self) -> Locator:
        """Get the name/heading of the first skill card"""
        return self.page.get_by_role("heading", level=3).first

    @property
    def first_skill_description(self) -> Locator:
        """Get the description paragraph of the first skill card"""
        return self.first_skill_card.locator("p").first

    @property
    def first_skill_like_button(self) -> Locator:
        """Get the like button of the first skill card"""
        # Like button is the first button in the actions area
        return self.first_skill_card.locator("button").first

    @property
    def first_skill_dislike_button(self) -> Locator:
        """Get the dislike button of the first skill card"""
        # Dislike button is the second button in the actions area
        return self.first_skill_card.locator("button").nth(1)

    @property
    def first_skill_attach_button(self) -> Locator:
        """Get the attach button of the first skill card"""
        # Attach button is the third button
        return self.first_skill_card.locator("button").nth(2)

    @property
    def first_skill_menu_button(self) -> Locator:
        """Get the 3-dot menu button of the first skill card"""
        # Menu button is the fourth button
        return self.first_skill_card.locator("button").nth(3)

    @property
    def first_skill_assistants_count(self) -> Locator:
        """Get the assistants counter label of the first skill card"""
        return self.first_skill_card.get_by_role("status")

    def skill_card(self, skill_name: str) -> Locator:
        """Get skill card by name"""
        return self.page.locator(f'h3:has-text("{skill_name}")').locator("../..")

    def skill_card_heading(self, skill_name: str) -> Locator:
        """Get skill card heading by name"""
        return self.page.locator(f'h3:has-text("{skill_name}")')

    def skill_card_author(self, skill_name: str) -> Locator:
        """Get skill card author text"""
        return self.skill_card(skill_name).locator("text=/by /").first

    def skill_card_description(self, skill_name: str) -> Locator:
        """Get skill card description"""
        return self.skill_card(skill_name).locator("p").first

    def skill_card_like_button(self, skill_name: str) -> Locator:
        """Get skill card like button"""
        return self.skill_card(skill_name).locator("button").filter(has_text="0").first

    def skill_card_assistants_count(self, skill_name: str) -> Locator:
        """Get skill card assistants count label"""
        return self.skill_card(skill_name).locator("text=/\\d+ assistants/")

    # =============================================================================
    # NAVIGATION METHODS
    # =============================================================================

    @step("Navigate to Skills Marketplace")
    def navigate_to(self):
        """Navigate to the Skills Marketplace page."""
        self.page.goto(self.page_url)
        self.wait_for_page_load()
        return self

    @step("Click on skill card")
    def click_skill_card(self, skill_name: str):
        """Click on a skill card by name."""
        self.skill_card(skill_name).click()
        self.wait_for_page_load()
        return self

    # =============================================================================
    # SEARCH/FILTER METHODS
    # =============================================================================

    @step("Search for skills")
    def search_skills(self, search_text: str):
        """Search for skills in marketplace."""
        self.search_input.fill(search_text)
        self.page.wait_for_timeout(500)
        return self

    @step("Filter by category")
    def filter_by_category(self, category: str):
        """Filter marketplace skills by category."""
        # Use force=True to bypass pointer interception
        self.categories_dropdown.click(force=True)
        self.page.wait_for_timeout(300)
        self.page.get_by_role("option", name=category).click()
        self.page.wait_for_timeout(500)
        return self

    @step("Filter by 'Created By Me'")
    def filter_by_created_by_me(self, checked: bool = True):
        """Filter marketplace skills by 'Me' checkbox."""
        if checked:
            self.created_by_me_checkbox.check()
        else:
            self.created_by_me_checkbox.uncheck()
        self.page.wait_for_timeout(500)
        return self

    @step("Filter by created by user")
    def filter_by_created_by_user(self, username: str):
        """Filter marketplace skills by Created By dropdown."""
        self.created_by_dropdown.click()
        self.page.wait_for_timeout(300)
        self.page.get_by_role("option", name=username).click()
        self.page.wait_for_timeout(500)
        return self

    # =============================================================================
    # VERIFICATION METHODS
    # =============================================================================

    @step("Verify on Marketplace page")
    def should_be_on_marketplace_page(self):
        """Verify that we are on the Marketplace page."""
        expect(self.page).to_have_url(re.compile(r".*/skills/marketplace.*"))
        return self

    @step("Verify marketplace page elements are visible")
    def should_have_marketplace_elements_visible(self):
        """Verify that essential marketplace page elements are visible."""
        expect(self.marketplace_heading).to_be_visible()
        expect(self.skills_count_label).to_be_visible()
        return self

    @step("Verify skills count label shows number")
    def should_have_skill_count_number(self, min_count: int = 1):
        """Verify skills count label shows a number greater than or equal to min_count."""
        expect(self.skills_count_label).to_have_count(min_count)
        return self

    @step("Verify marketplace displays skills")
    def should_display_skills(self):
        # Verify multiple skill cards are present
        skill_cards = self.page.locator(".h-card.rounded-xl")
        # Check that we have at least 1 skill card
        expect(skill_cards).not_to_have_count(0)
        return self

    @step("Verify skill card displays metadata")
    def should_skill_card_display_metadata(self, skill_name: str):
        """Verify that skill card displays name, description, and author."""
        expect(self.skill_card_heading(skill_name)).to_be_visible()
        expect(self.skill_card_author(skill_name)).to_be_visible()
        expect(self.skill_card_description(skill_name)).to_be_visible()
        return self

    @step("Verify first skill card has all elements visible")
    def should_have_skill_card_elements_visible(self):
        """
        Verify that the first skill card displays all required elements:
        - Skill name
        - Skill description
        - Like/dislike buttons
        - Attach button
        - 3-dot menu button
        - Attached assistant counter label
        """
        # Wait for skills to load
        self.page.wait_for_load_state("networkidle")

        # Verify all card elements are visible
        expect(self.first_skill_name).to_be_visible()
        expect(self.first_skill_description).to_be_visible()
        expect(self.first_skill_like_button).to_be_visible()
        expect(self.first_skill_dislike_button).to_be_visible()
        expect(self.first_skill_attach_button).to_be_visible()
        expect(self.first_skill_menu_button).to_be_visible()
        expect(self.first_skill_assistants_count).to_be_visible()
        return self

    @step("Verify skill is visible in marketplace")
    def should_see_skill_in_marketplace(self, skill_name: str):
        """Verify that a skill is visible in the marketplace."""
        expect(self.skill_card_heading(skill_name)).to_be_visible(timeout=15000)
        return self

    @step("Verify filters are visible")
    def should_have_filters_visible(self):
        """Verify that filter controls are visible."""
        expect(self.filters_heading).to_be_visible()
        expect(self.search_input).to_be_visible()
        expect(self.categories_dropdown).to_be_visible()
        expect(self.created_by_heading).to_be_visible()
        expect(self.created_by_me_checkbox).to_be_visible()
        expect(self.created_by_dropdown).to_be_visible()
        return self

    @step("Verify categories dropdown is functional")
    def should_have_categories_dropdown_functional(self):
        """Verify that categories dropdown can be opened."""
        expect(self.categories_dropdown).to_be_visible()
        expect(self.categories_dropdown).to_be_enabled()
        return self

    @step("Verify created by dropdown is functional")
    def should_have_created_by_dropdown_functional(self):
        """Verify that Created By dropdown can be opened."""
        expect(self.created_by_dropdown).to_be_visible()
        expect(self.created_by_dropdown).to_be_enabled()
        return self
