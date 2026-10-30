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
Assistants Marketplace Page Object following Page Object Model (POM) best practices.

This class encapsulates all interactions with the Assistants Marketplace page.
"""

import re
from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class AssistantsMarketplacePage(BasePage):
    """Page object for the Assistants Marketplace page."""

    page_url = "/assistants/marketplace"

    def __init__(self, page):
        """Initialize the Assistants Marketplace page object."""
        super().__init__(page)

    # =============================================================================
    # LOCATORS - Page Elements
    # =============================================================================

    @property
    def marketplace_heading(self) -> Locator:
        """Marketplace page heading"""
        return self.page.get_by_role("heading", name="Assistants", exact=True, level=2)

    @property
    def assistants_count_label(self) -> Locator:
        """Assistants count label (e.g., '7 ASSISTANTS')"""
        return self.page.locator("text=/\\d+ ASSISTANTS/")

    @property
    def search_input(self) -> Locator:
        """Search input field"""
        return self.page.locator('input[placeholder="Search"]').first

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
    def first_assistant_card(self) -> Locator:
        """Get the first assistant card on the marketplace page"""
        return self.page.locator(".h-card.rounded-xl").first

    @property
    def first_assistant_name(self) -> Locator:
        """Get the name/heading of the first assistant card"""
        return self.page.get_by_role("heading", level=3).first

    @property
    def first_assistant_description(self) -> Locator:
        """Get the description paragraph of the first assistant card"""
        return self.first_assistant_card.locator("p").first

    @property
    def first_assistant_like_button(self) -> Locator:
        """Get the like button of the first assistant card"""
        # Like button is the first button in the actions area
        return self.first_assistant_card.locator("button").first

    @property
    def first_assistant_dislike_button(self) -> Locator:
        """Get the dislike button of the first assistant card"""
        # Dislike button is the second button in the actions area
        return self.first_assistant_card.locator("button").nth(1)

    @property
    def first_assistant_attach_button(self) -> Locator:
        """Get the attach button of the first assistant card"""
        # Attach button is the third button
        return self.first_assistant_card.locator("button").nth(2)

    @property
    def first_assistant_menu_button(self) -> Locator:
        """Get the 3-dot menu button of the first assistant card"""
        # Menu button is the fourth button
        return self.first_assistant_card.locator("button").nth(3)

    @property
    def first_assistant_usage_count(self) -> Locator:
        """Get the usage counter label of the first assistant card"""
        return self.first_assistant_card.get_by_role("status")

    def assistant_card(self, assistant_name: str) -> Locator:
        """Get assistant card by name"""
        return self.page.locator(f'h3:has-text("{assistant_name}")').locator("../..")

    def assistant_card_heading(self, assistant_name: str) -> Locator:
        """Get assistant card heading by name"""
        return self.page.locator(f'h3:has-text("{assistant_name}")')

    def assistant_card_author(self, assistant_name: str) -> Locator:
        """Get assistant card author text"""
        return self.assistant_card(assistant_name).locator("text=/by /").first

    def assistant_card_description(self, assistant_name: str) -> Locator:
        """Get assistant card description"""
        return self.assistant_card(assistant_name).locator("p").first

    def assistant_card_like_button(self, assistant_name: str) -> Locator:
        """Get assistant card like button"""
        return (
            self.assistant_card(assistant_name)
            .locator("button")
            .filter(has_text="0")
            .first
        )

    def assistant_card_usage_count(self, assistant_name: str) -> Locator:
        """Get assistant card usage count label"""
        return self.assistant_card(assistant_name).locator("text=/\\d+ uses/")

    @property
    def first_assistant_clone_count_badge(self) -> Locator:
        """Clone count badge button on the first assistant card.

        The clone count badge is rendered as a button with aria-label
        "Clone {name}, {count}" (confirmed via playwright-cli inspection).
        Selector targets the aria-label prefix to remain stable as count changes.
        """
        return self.first_assistant_card.locator("button[aria-label^='Clone']")

    def assistant_card_clone_count_badge(self, assistant_name: str) -> Locator:
        """Clone count badge button on the named assistant card.

        Uses a direct page-level aria-label selector keyed on the assistant name
        rather than fragile parent-traversal (h3 → ../.. → card → button).
        The button's aria-label is "Clone {name}, {count}" so this is unique per card.
        """
        return self.page.locator(f"button[aria-label^='Clone {assistant_name}']")

    # =============================================================================
    # NAVIGATION METHODS
    # =============================================================================

    @step("Navigate to Assistants Marketplace")
    def navigate_to(self):
        """Navigate to the Assistants Marketplace page."""
        self.page.goto(self.page_url)
        self.wait_for_page_load()
        # Wait for marketplace content to load
        self.page.wait_for_timeout(2000)
        return self

    @step("Click on assistant card")
    def click_assistant_card(self, assistant_name: str):
        """Click on an assistant card by name."""
        self.assistant_card(assistant_name).click()
        self.wait_for_page_load()
        return self

    # =============================================================================
    # SEARCH/FILTER METHODS
    # =============================================================================

    @step("Search for assistants")
    def search_assistants(self, search_text: str):
        """Search for assistants in marketplace."""
        self.search_input.fill(search_text)
        # Wait for search results to update
        self.page.wait_for_timeout(2000)
        return self

    @step("Filter by category")
    def filter_by_category(self, category: str = "Quality Assurance"):
        """Filter marketplace assistants by category."""
        self.categories_dropdown.click(force=True)
        self.page.wait_for_timeout(300)
        self.page.get_by_role("option", name=category).click()
        # Wait for filter results to update
        self.page.wait_for_timeout(2000)
        return self

    @step("Filter by 'Created By Me'")
    def filter_by_created_by_me(self, checked: bool = True):
        """Filter marketplace assistants by 'Me' checkbox."""
        if checked:
            self.created_by_me_checkbox.check()
        else:
            self.created_by_me_checkbox.uncheck()
        self.page.wait_for_timeout(500)
        return self

    @step("Filter by created by user")
    def filter_by_created_by_user(self, username: str):
        """Filter marketplace assistants by Created By dropdown."""
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
        expect(self.page).to_have_url(re.compile(r".*/assistants/marketplace.*"))
        return self

    @step("Verify marketplace page elements are visible")
    def should_have_marketplace_elements_visible(self):
        """Verify that essential marketplace page elements are visible."""
        expect(self.marketplace_heading).to_be_visible()
        expect(self.assistants_count_label).to_be_visible()
        return self

    @step("Verify assistants count label shows number")
    def should_have_assistant_count_number(self, min_count: int = 1):
        """Verify assistants count label shows a number greater than or equal to min_count."""
        expect(self.assistants_count_label).to_have_count(min_count)
        return self

    @step("Verify marketplace displays assistants")
    def should_display_assistants(self):
        # Verify multiple assistant cards are present
        assistant_cards = self.page.locator(".h-card.rounded-xl")
        # Check that we have at least 1 assistant card
        expect(assistant_cards).not_to_have_count(0)
        return self

    @step("Verify assistant card displays metadata")
    def should_assistant_card_display_metadata(self, assistant_name: str):
        """Verify that assistant card displays name, description, and author."""
        expect(self.assistant_card_heading(assistant_name)).to_be_visible()
        expect(self.assistant_card_author(assistant_name)).to_be_visible()
        expect(self.assistant_card_description(assistant_name)).to_be_visible()
        return self

    @step("Verify first assistant card has all elements visible")
    def should_have_assistant_card_elements_visible(self):
        """
        Verify that the first assistant card displays all required elements:
        - Assistant name
        - Assistant description
        - Like/dislike buttons
        - Attach button
        - 3-dot menu button
        - Usage counter label
        """
        # Verify all card elements are visible
        expect(self.first_assistant_name).to_be_visible()
        expect(self.first_assistant_description).to_be_visible()
        expect(self.first_assistant_like_button).to_be_visible()
        expect(self.first_assistant_dislike_button).to_be_visible()
        expect(self.first_assistant_attach_button).to_be_visible()
        expect(self.first_assistant_menu_button).to_be_visible()
        expect(self.first_assistant_usage_count).to_be_visible()
        return self

    @step("Verify assistant is visible in marketplace")
    def should_see_assistant_in_marketplace(self, assistant_name: str):
        """Verify that an assistant is visible in the marketplace."""
        expect(self.assistant_card_heading(assistant_name)).to_be_visible()
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

    @step("Verify ratings and feedback controls are visible")
    def should_have_ratings_and_feedback_visible(self):
        """Verify that like/dislike buttons (ratings) are visible on first assistant card."""
        expect(self.first_assistant_like_button).to_be_visible()
        expect(self.first_assistant_dislike_button).to_be_visible()
        return self

    @step("Verify clone count badge is visible on first assistant card")
    def should_have_clone_count_visible(self):
        """Assert that the clone count badge element is visible on the first assistant card.

        Used by TC-02 to verify the badge was rendered after the frontend MR landed.
        """
        expect(self.first_assistant_clone_count_badge).to_be_visible()
        return self

    @step("Verify clone count badge value on named assistant card")
    def should_have_clone_count_value(self, assistant_name: str, expected: int):
        """Assert that the clone count badge on the named card shows the expected integer.

        Uses exact text match against the button's inner text (e.g. "0", "1", "5").
        For counts that may render in compact form (e.g. "1.2k"), use a regex pattern.
        """
        expect(self.assistant_card_clone_count_badge(assistant_name)).to_have_text(
            re.compile(rf"^\s*{expected}\s*$")
        )
        return self

    @step("Read clone count value from named assistant card")
    def get_clone_count_value(self, assistant_name: str) -> int:
        """Return the current clone count displayed on the named assistant's card badge.

        Reads the button inner text (e.g. "0", "3"). Only safe for values that
        render as plain integers; compact notation (e.g. "1.2k") is not handled.
        """
        badge_text = self.assistant_card_clone_count_badge(assistant_name).inner_text()
        return int(badge_text.strip())

    @step("Clone assistant via 3-dot menu")
    def clone_assistant_via_ui(self, assistant_name: str):
        """Click More options on the named card then select Clone.

        Uses .filter(has_text=) on the card container to avoid fragile parent
        traversal. Navigates to the new assistant creation form, pre-filled with
        clone data. The caller is responsible for submitting the form and
        navigating back.
        """
        card = self.page.locator(".h-card.rounded-xl").filter(has_text=assistant_name)
        card.get_by_role("button", name="More options").click()
        self.page.get_by_role("menuitem", name="Clone").click()
        self.wait_for_page_load()
        return self

    # =============================================================================
    # FAVORITES CARD METRICS
    # The Favorites category (/assistants/favorites) renders the same AssistantCard as
    # the Marketplace, so the card locators below work on both pages. The top-level
    # /favorites/* pages are feature-flagged off on the shared stand, so the Assistants
    # sidebar Favorites category is the reachable Favorites view.
    # =============================================================================

    @property
    def favorites_category_button(self) -> Locator:
        """'Favorites' category button in the Assistants sidebar (route /assistants/favorites)."""
        return self.page.get_by_role("button", name="Favorites", exact=True)

    @property
    def marketplace_category_button(self) -> Locator:
        """'Marketplace' category button in the Assistants sidebar."""
        return self.page.get_by_role("button", name="Marketplace", exact=True)

    def card_by_name(self, assistant_name: str) -> Locator:
        """Assistant card (Marketplace or Favorites) containing the named heading.

        The card is a plain <div> with no role, so it is located structurally: the
        innermost div holding both the card's heading and its favorite toggle. The
        favorite toggle sits outside the card body, so this resolves to the card root
        rather than to an inner wrapper. ``.last`` picks the innermost match, because
        every ancestor of the card contains the same heading and toggle.
        """
        heading = self.page.get_by_role("heading", name=assistant_name, exact=True)
        favorite_toggle = self.page.get_by_role(
            "button", name=re.compile(r"^(Add to|Remove from) favorites$")
        )
        return (
            self.page.locator("div")
            .filter(has=heading)
            .filter(has=favorite_toggle)
            .last
        )

    def card_usage_label(self, assistant_name: str) -> Locator:
        """Usage label of the named card; its aria-label reads '<N> total uses'."""
        return self.card_by_name(assistant_name).get_by_role("status")

    def card_clone_button(self, assistant_name: str, label: str) -> Locator:
        """Clone button of the named card with the exact accessible name *label*."""
        return self.card_by_name(assistant_name).get_by_role(
            "button", name=label, exact=True
        )

    @step("Add assistant to favorites")
    def add_assistant_to_favorites(self, assistant_name: str):
        """Click the star on the named card to mark the assistant as Favorite."""
        self.card_by_name(assistant_name).get_by_role(
            "button", name="Add to favorites"
        ).click()
        return self

    @step("Open Favorites category")
    def open_favorites_category(self):
        """Switch to the Favorites category through the Assistants sidebar."""
        self.favorites_category_button.click()
        self.wait_for_page_load()
        return self

    @step("Switch to Marketplace category")
    def switch_to_marketplace_category(self):
        """Switch to the Marketplace category through the Assistants sidebar."""
        self.marketplace_category_button.click()
        self.wait_for_page_load()
        return self

    @step("Reload the page")
    def reload_page(self):
        """Hard-reload the current page (drops all in-memory UI state)."""
        self.page.reload()
        self.wait_for_page_load()
        return self

    @step("Verify on Favorites category")
    def should_be_on_favorites_category(self):
        """Verify the browser URL is the Assistants Favorites route."""
        expect(self.page).to_have_url(re.compile(r".*/assistants/favorites.*"))
        return self

    @step("Verify card usage label")
    def should_have_usage_label(self, assistant_name: str, expected_label: str):
        """Assert the named card's usage label has the exact aria-label (e.g. '126 total uses')."""
        expect(self.card_usage_label(assistant_name)).to_have_attribute(
            "aria-label", expected_label
        )
        return self

    @step("Verify card clone label")
    def should_have_clone_label(self, assistant_name: str, expected_label: str):
        """Assert the named card shows a clone button named exactly *expected_label*."""
        expect(self.card_clone_button(assistant_name, expected_label)).to_be_visible()
        return self

    @step("Verify assistant is marked as favorite")
    def should_be_favorited(self, assistant_name: str):
        """Assert the named card offers 'Remove from favorites' (i.e. is a favorite)."""
        expect(
            self.card_by_name(assistant_name).get_by_role(
                "button", name="Remove from favorites"
            )
        ).to_be_visible()
        return self

    @step("Verify card shows liked state with dislike control")
    def should_show_liked_state(self, assistant_name: str, likes: int, dislikes: int):
        """Assert the named card shows the assistant as liked by the user.

        The like button reads 'Remove like from <name>, <likes>' once liked and the
        dislike button reads 'Dislike <name>, <dislikes>'.
        """
        card = self.card_by_name(assistant_name)
        expect(
            card.get_by_role(
                "button",
                name=f"Remove like from {assistant_name}, {likes}",
                exact=True,
            )
        ).to_be_visible()
        expect(
            card.get_by_role(
                "button", name=f"Dislike {assistant_name}, {dislikes}", exact=True
            )
        ).to_be_visible()
        return self

    # =============================================================================
    # TEMPLATE-SCOPE SEARCH METHODS
    # =============================================================================

    @property
    def templates_page_url(self) -> str:
        """URL for the Assistant Templates tab."""
        return "/assistants/templates"

    @property
    def assistant_cards(self) -> "Locator":
        """All visible assistant / template cards."""
        return self.page.locator(".h-card.rounded-xl")

    @step("Navigate to Assistant Templates page")
    def navigate_to_templates(self) -> "AssistantsMarketplacePage":
        """Navigate directly to the /assistants/templates page."""
        self.page.goto(self.templates_page_url)
        self.wait_for_page_load()
        return self

    @step("Navigate away to Assistants list")
    def navigate_to_assistants_list(self) -> "AssistantsMarketplacePage":
        """Navigate to /assistants (away from templates) to test state persistence."""
        self.page.goto("/assistants")
        self.wait_for_page_load()
        return self

    @step("Type search query on templates page")
    def type_search_on_templates(self, text: str) -> "AssistantsMarketplacePage":
        """Fill the shared search input and wait for server-side results to update."""
        self.search_input.fill(text)
        self.wait_for_page_load()
        return self

    @step("Clear search on templates page")
    def clear_search_on_templates(self) -> "AssistantsMarketplacePage":
        """Clear the search input and wait for the full template list to be restored."""
        self.search_input.clear()
        self.wait_for_page_load()
        return self

    @step("Get current search filter value")
    def get_filter_value(self) -> str:
        """Return the current value of the search input."""
        return self.search_input.input_value()

    @step("Verify search input is visible on templates page")
    def should_show_search_input_visible(self) -> "AssistantsMarketplacePage":
        """Verify that the search/filter input is visible."""
        expect(self.search_input).to_be_visible()
        return self

    @step("Verify template results count")
    def should_show_template_results_count(
        self, expected_count: int
    ) -> "AssistantsMarketplacePage":
        """Verify the number of visible template cards equals *expected_count*."""
        expect(self.assistant_cards).to_have_count(expected_count)
        return self

    @step("Verify assistant template is shown")
    def should_show_template(self, partial_name: str) -> "AssistantsMarketplacePage":
        """Verify that every visible template card contains *partial_name*."""
        cards = self.assistant_cards
        expect(cards.first).to_be_visible()
        expect(cards.filter(has_not_text=partial_name)).to_have_count(0)
        return self

    @step("Verify assistant template is not shown")
    def should_not_show_template(
        self, partial_name: str
    ) -> "AssistantsMarketplacePage":
        """Verify that no visible template card heading contains *partial_name*."""
        expect(self.page.locator("h3").filter(has_text=partial_name)).to_have_count(0)
        return self

    @step("Verify on Assistant Templates page")
    def should_be_on_templates_page(self) -> "AssistantsMarketplacePage":
        """Verify that the browser URL contains /assistants/templates."""
        expect(self.page).to_have_url(re.compile(r".*/assistants/templates.*"))
        return self

    # =============================================================================
    # SORT CONTROLS — Locators
    # =============================================================================

    @property
    def sort_by_control(self) -> Locator:
        """PrimeReact Dropdown container for the 'Sort by' filter (id='sort_by')."""
        return self.page.locator("#sort_by")

    @property
    def sort_order_descending_radio(self) -> Locator:
        """Clickable label for 'Descending' sort order.

        PrimeReact renders the radio input with opacity:0 (visually hidden).
        The wrapping <label> element has opacity:1 and is the correct click target.
        """
        return (
            self.page.get_by_role("region", name="SORT ORDER")
            .locator("label")
            .filter(has_text="Descending")
        )

    @property
    def sort_order_ascending_radio(self) -> Locator:
        """Clickable label for 'Ascending' sort order.

        PrimeReact renders the radio input with opacity:0 (visually hidden).
        The wrapping <label> element has opacity:1 and is the correct click target.
        """
        return (
            self.page.get_by_role("region", name="SORT ORDER")
            .locator("label")
            .filter(has_text="Ascending")
        )

    # =============================================================================
    # SORT CONTROLS — Action methods
    # =============================================================================

    @step("Select Sort by option")
    def sort_by(self, option: str) -> "AssistantsMarketplacePage":
        """Open the 'Sort by' dropdown and select the named option.

        Args:
            option: Visible label of the sort option (e.g. "Likes", "Name").
        """
        self.sort_by_control.get_by_role("button", name="Sort by").click()
        self.page.wait_for_timeout(900)
        self.page.get_by_role("option", name=option, exact=True).first.click()
        self.page.wait_for_timeout(2500)
        return self

    @step("Set Sort order direction")
    def set_sort_order(self, direction: str) -> "AssistantsMarketplacePage":
        """Click the radio button matching *direction* ("Ascending" or "Descending").

        Args:
            direction: "Ascending" or "Descending".
        """
        if direction == "Ascending":
            self.sort_order_ascending_radio.click()
        else:
            self.sort_order_descending_radio.click()
        self.page.wait_for_timeout(2500)
        return self

    # =============================================================================
    # SORT CONTROLS — Data extraction
    # =============================================================================

    @step("Get assistant names in current DOM order")
    def get_assistant_names_in_order(self) -> list:
        """Return text of all assistant card h3 headings in current DOM order.

        Scoped to .h-card.rounded-xl to avoid capturing unrelated section headings
        inside <main>.
        """
        return self.page.locator(".h-card.rounded-xl h3").all_text_contents()

    @step("Get assistant usage counts in current DOM order")
    def get_assistant_usage_counts_in_order(self) -> list:
        """Parse the usage-count status labels on assistant cards and return ints in DOM order.

        Scoped to .h-card.rounded-xl to avoid capturing unrelated status elements (loading
        indicators, notification banners). Uses re.search to extract only the first contiguous
        number, handling labels such as '1,234 total uses' or '5 uses (3 unique)' correctly.
        Compact notation ('22k', '1.2k', '3M') is expanded to an approximate integer, which
        preserves ordering because the UI's rounding is monotonic.

        Usage count now renders as an <output> element (implicit ARIA role "status", no
        explicit role attribute), so this uses get_by_role() rather than a `[role='status']`
        CSS attribute selector, which only matches an explicit role attribute and would miss it.
        """
        raw = (
            self.page.locator(".h-card.rounded-xl")
            .get_by_role("status")
            .all_text_contents()
        )
        multipliers = {"k": 1_000, "m": 1_000_000}
        counts = []
        for text in raw:
            match = re.search(r"([\d,]+(?:\.\d+)?)\s*([kKmM])?(?![a-zA-Z])", text)
            if not match:
                counts.append(0)
                continue
            number = float(match.group(1).replace(",", ""))
            multiplier = multipliers.get((match.group(2) or "").lower(), 1)
            counts.append(round(number * multiplier))
        return counts

    # =============================================================================
    # SORT CONTROLS — Assertion methods
    # =============================================================================

    @step("Verify sort controls are visible")
    def should_have_sort_controls_visible(self) -> "AssistantsMarketplacePage":
        """Assert that both the Sort by combobox and Sort order radios are visible."""
        expect(self.sort_by_control).to_be_visible()
        expect(self.sort_by_control).to_be_enabled()
        expect(self.sort_order_descending_radio).to_be_visible()
        expect(self.sort_order_ascending_radio).to_be_visible()
        return self

    @step("Verify Sort by dropdown exposes expected options")
    def should_have_sort_by_options(
        self, *expected: str
    ) -> "AssistantsMarketplacePage":
        """Open the Sort by dropdown and assert each expected label is present as a role='option'.

        Args:
            expected: Option labels to verify (e.g. "Usage", "Likes", "Dislikes", "Name").
        """
        self.sort_by_control.get_by_role("button", name="Sort by").click()
        self.page.wait_for_timeout(300)
        for label in expected:
            expect(
                self.page.get_by_role("option", name=label, exact=True).first
            ).to_be_visible()
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(200)
        return self

    @step("Verify assistants are displayed in expected order")
    def should_display_assistants_in_order(
        self, expected_names: list
    ) -> "AssistantsMarketplacePage":
        """Assert that get_assistant_names_in_order() equals expected_names (exact order).

        Args:
            expected_names: Expected list of assistant name strings in order.
        """
        actual = self.get_assistant_names_in_order()
        assert actual == expected_names, (
            f"Expected assistant order {expected_names!r} but got {actual!r}"
        )
        return self
