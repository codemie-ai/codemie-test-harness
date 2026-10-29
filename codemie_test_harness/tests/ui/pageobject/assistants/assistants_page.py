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

from codemie_test_harness.tests.ui.pageobject.assistants.assistant_view_page import (
    AssistantViewPage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_marketplace_page import (
    AssistantsMarketplacePage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect
from reportportal_client import step


class AssistantsPage(BasePage):
    """Assistants page object with property-based element locators."""

    page_url = "/assistants"

    def __init__(self, page):
        super().__init__(page)
        self.page.goto(self.page_url)

    # Page elements using @property decorator
    @property
    def page_title(self):
        """Main page title."""
        return self.page.get_by_role("heading", name="Assistants", exact=True)

    @property
    def page_subtitle(self):
        """Page subtitle or description."""
        return self.page.locator("text=Browse and create AI assistants")

    @property
    def create_assistant_button(self):
        """Create new assistant button."""
        return self.page.locator("button").filter(has_text="Create Assistant")

    @property
    def search_input(self):
        """Search input field."""
        return self.page.locator('input[placeholder="Search"]').first

    @property
    def assistant_cards(self):
        """All assistant cards on the page."""
        return self.page.locator(".assistant-card, .bg-assistant-card-fill")

    @property
    def sidebar(self):
        """Sidebar navigation."""
        return self.page.locator("aside.bg-sidebar")

    @property
    def my_assistants_link(self):
        """My Assistants navigation link."""
        return self.page.locator('a[href="/assistants/my"]')

    @property
    def all_assistants_link(self):
        """All Assistants navigation link."""
        return self.page.locator('a[href="/assistants/all"]')

    @property
    def templates_link(self):
        """Templates navigation link."""
        return self.page.locator('a[href="/assistants/templates"]')

    @property
    def marketplace_tab(self):
        """Marketplace tab."""
        return self.page.locator("aside").get_by_role("button", name="Marketplace")

    @property
    def loading_indicator(self):
        """Loading spinner or indicator."""
        return self.page.locator(".loading, .spinner")

    @property
    def empty_state(self):
        """Empty state message when no assistants are found."""
        return self.page.locator(".empty-state, .no-results")

    @property
    def filters_section(self):
        """Filters section."""
        return self.page.locator('span:has-text("Filters")')

    @property
    def clear_filters_button(self):
        """Clear all filters button."""
        return self.page.locator('button:has-text("Clear all")')

    @property
    def action_view_details(self):
        """Dropdown 'View Details' button."""
        return self.page.locator("button").filter(has_text="View Details")

    @property
    def action_copy_link(self):
        """Dropdown 'Copy Link' button."""
        return self.page.locator("button").filter(has_text="Copy Link")

    @property
    def action_edit(self):
        """Dropdown 'Edit' button."""
        return self.page.locator("button").filter(has_text="Edit")

    @property
    def action_clone(self):
        """Dropdown 'Clone' button."""
        return self.page.locator("button").filter(has_text="Clone")

    @property
    def action_delete(self):
        """Dropdown 'Delete' button."""
        return self.page.locator("button").filter(has_text="Delete")

    @property
    def action_publish_to_marketplace(self):
        """Dropdown 'Publish to Marketplace' button."""
        return self.page.locator("button").filter(has_text="Publish to Marketplace")

    @property
    def publish_confirmation_dialog(self):
        """Publish to Marketplace confirmation dialog."""
        return self.page.get_by_role("dialog")

    @property
    def publish_button(self):
        """Publish button in confirmation dialog."""
        return self.page.get_by_role("button", name="Publish")

    @property
    def publish_anyway_button(self):
        """Publish Anyway button in confirmation dialog."""
        return self.page.get_by_role("button", name="Publish Anyway")

    @property
    def validation_message(self):
        """Validation message that appears during assistant configuration validation."""
        return self.page.locator(
            'p.text-sm.text-text-quaternary:has-text("Validating your Assistant configuration")'
        )

    @property
    def publish_dialog_categories_dropdown(self):
        """Categories dropdown in publish to marketplace dialog."""
        return self.publish_confirmation_dialog.locator("#assistant-categories")

    @property
    def publish_dialog_sub_assistants_heading(self):
        """'Sub-Assistants' section heading, rendered only after validation finishes."""
        return self.publish_confirmation_dialog.get_by_role(
            "heading", name="Sub-Assistants", level=3
        )

    @property
    def publish_dialog_published_sub_assistants_info(self):
        """Info line listing sub-assistants that are already on Marketplace."""
        return self.publish_confirmation_dialog.get_by_text(
            "Already on Marketplace, no action needed"
        )

    @property
    def updating_successful_popup(self):
        """Updating successful popup."""
        return self.page.locator(".codemie-toast .codemie-toast-header")

    # Navigation methods
    @step
    def navigate_to(self):
        """Navigate to the assistants page."""
        self.page.goto(self.page_url)
        return self

    # Action methods
    @step
    def click_create_assistant(self):
        """Click the create assistant button."""
        self.create_assistant_button.click()
        return CreateEditAssistantPage(self.page)

    @step
    def search_assistants(self, search_term: str):
        """Search for assistants using the search input."""
        self.search_input.fill(search_term)
        self.page.keyboard.press("Enter")
        return self

    @step
    def navigate_to_my_assistants(self):
        """Navigate to My Assistants section."""
        self.my_assistants_link.click()
        return self

    @step
    def navigate_to_all_assistants(self):
        """Navigate to All Assistants section."""
        self.all_assistants_link.click()
        return self

    @step
    def navigate_to_templates(self):
        """Navigate to Templates section."""
        self.templates_link.click()
        return self

    @step
    def switch_to_marketplace_tab(self):
        """Switch to the Marketplace tab."""
        self.marketplace_tab.click()
        # Wait for tab content to load
        self.page.wait_for_load_state("domcontentloaded")
        return AssistantsMarketplacePage(self.page)

    @step
    def clear_all_filters(self):
        """Clear all applied filters."""
        self.clear_filters_button.click()
        return self

    @step
    def get_assistant_card_by_index(self, index: int):
        """Get assistant card by its index."""
        return self.assistant_cards.nth(index)

    @step
    def get_assistant_card_by_name(self, name: str):
        """Get assistant card by its name."""
        return self.page.locator(".body.h-card").filter(
            has=self.page.get_by_text(name, exact=True)
        )

    @step
    def click_assistant_card(self, name: str):
        """Click on an assistant card by name."""
        self.get_assistant_card_by_name(name).click()
        return self

    @step
    def action_dropdown_panel(self, name: str):
        """Three dot menu."""
        return self.get_assistant_card_by_name(name).locator(
            "div.flex.items-center.relative"
        )

    def open_action_menu(self, name: str, menu_item):
        """Open the card's three-dot menu and wait for a menu item to appear.

        A list refetch (e.g. right after typing in the search filter) can
        re-render the card and unmount a freshly opened menu, swallowing the
        first click. Retry the click until the menu item is visible.
        """
        for _ in range(3):
            self.action_dropdown_panel(name).click()
            try:
                menu_item.wait_for(state="visible", timeout=3000)
                return self
            except PlaywrightTimeoutError:
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(300)
        self.action_dropdown_panel(name).click()
        menu_item.wait_for(state="visible", timeout=5000)
        return self

    @step
    def publish_dialog_sub_assistant_title(self, name: str):
        """Title of a selectable sub-assistant in the publish dialog."""
        return self.publish_confirmation_dialog.get_by_role(
            "heading", name=name, exact=True, level=4
        )

    @step
    def publish_dialog_sub_assistant_item(self, name: str):
        """Card of a selectable sub-assistant (checkbox, title and categories)."""
        # Every ancestor containing both headings matches; the innermost is last.
        return (
            self.publish_confirmation_dialog.locator("div")
            .filter(
                has=self.page.get_by_role("heading", name=name, exact=True, level=4)
            )
            .filter(
                has=self.page.get_by_role("heading", name="Categories", level=5),
            )
            .last
        )

    @step
    def publish_dialog_sub_assistant_checkbox(self, name: str):
        """Selection checkbox of a sub-assistant in the publish dialog."""
        return self.publish_dialog_sub_assistant_item(name).get_by_role("checkbox")

    @step
    def publish_dialog_sub_assistant_categories(self, name: str):
        """Per-sub-assistant 'Categories' heading (collapsed until it is ticked)."""
        return self.publish_dialog_sub_assistant_item(name).get_by_role(
            "heading", name="Categories", level=5
        )

    @step
    def click_assistant_view(self, name: str):
        """Click on an assistant view by name."""
        self.open_action_menu(name, self.action_view_details)
        self.action_view_details.click()
        return AssistantViewPage(self.page)

    @step
    def click_assistant_edit(self, name: str):
        """Click on an assistant edit by name."""
        self.close_new_release_popup()
        self.open_action_menu(name, self.action_edit)
        self.action_edit.click()
        return CreateEditAssistantPage(self.page)

    @step
    def open_assistant_details(self, name: str):
        """Open assistant details page by clicking on the assistant card and return the view page."""
        self.click_assistant_card(name)
        return AssistantViewPage(self.page)

    @step
    def publish_assistant_to_marketplace(self, name: str):
        """Publish an assistant to marketplace from the 3-dot menu."""
        self.open_action_menu(name, self.action_publish_to_marketplace)
        self.action_publish_to_marketplace.click()
        return self

    # Verification methods
    @step
    def should_be_on_assistants_page(self):
        """Verify that we are on the assistants page."""
        expect(self.page_title).to_be_visible(timeout=15000)
        return self

    @step
    def should_see_create_assistant_button(self):
        """Verify that create assistant button is visible."""
        expect(self.create_assistant_button).to_be_visible()
        return self

    @step
    def should_see_search_input(self):
        """Verify that search input is visible."""
        expect(self.search_input).to_be_visible()
        return self

    @step
    def should_see_assistant_count(self, expected_count: int):
        """Verify the exact number of assistant cards."""
        expect(self.assistant_cards).to_have_count(expected_count)
        return self

    @step
    def should_see_empty_state(self):
        """Verify that empty state is displayed."""
        expect(self.empty_state).to_be_visible()
        return self

    @step
    def should_not_see_loading_indicator(self):
        """Verify that loading indicator is not visible."""
        expect(self.loading_indicator).to_be_hidden()
        return self

    @step
    def should_see_assistant_with_name(self, name: str):
        """Verify that an assistant with specific name is visible."""
        expect(self.get_assistant_card_by_name(name)).to_be_visible(timeout=15000)
        return self

    @step
    def should_not_see_assistant_with_name(self, name: str):
        """Verify that an assistant with specific name is not visible."""
        expect(self.get_assistant_card_by_name(name)).to_be_hidden()
        return self

    @step
    def should_see_updating_popup(self, text: str):
        """Verify that an update popup is visible."""
        expect(self.updating_successful_popup).to_be_visible()
        expect(self.updating_successful_popup).to_have_text(text)
        return self

    @step
    def publish_confirm_dialog_should_be_visible(self):
        """Verify that the Publish to Marketplace confirmation dialog is visible."""
        expect(self.publish_confirmation_dialog).to_be_visible()
        return self

    @step
    def publish_dialog_should_finish_validation(self):
        """Wait until the dialog finished validating and rendered the Sub-Assistants section."""
        expect(self.publish_dialog_sub_assistants_heading).to_be_visible(timeout=60000)
        expect(self.validation_message).to_be_hidden()
        return self

    @step
    def publish_dialog_should_show_published_sub_assistants_info(
        self, names: list[str]
    ):
        """Verify the info line names the sub-assistants that are already on Marketplace."""
        info = self.publish_dialog_published_sub_assistants_info
        expect(info).to_be_visible()
        for name in names:
            expect(info).to_contain_text(name)
        return self

    @step
    def publish_dialog_should_list_unpublished_sub_assistant(self, name: str):
        """Verify an unpublished sub-assistant is listed as a selectable publish candidate."""
        expect(self.publish_dialog_sub_assistant_title(name)).to_be_visible()
        return self

    @step
    def publish_dialog_should_not_list_sub_assistant(self, name: str):
        """Verify a sub-assistant is not listed as a selectable publish candidate."""
        expect(self.publish_dialog_sub_assistant_title(name)).to_have_count(0)
        return self

    @step
    def publish_dialog_sub_assistant_should_be_unchecked(self, name: str):
        """Verify a sub-assistant is not preselected for publishing."""
        expect(self.publish_dialog_sub_assistant_checkbox(name)).not_to_be_checked()
        return self

    @step
    def publish_dialog_should_not_request_categories_for_sub_assistant(self, name: str):
        """Verify the sub-assistant's Categories selector is not shown until it is ticked."""
        # The selector stays in the DOM in a collapsed container, so check the viewport.
        expect(
            self.publish_dialog_sub_assistant_categories(name)
        ).not_to_be_in_viewport()
        return self

    @step
    def publish_dialog_should_request_categories_once_sub_assistant_selected(
        self, name: str
    ):
        """Tick the sub-assistant and verify its Categories selector appears (positive control)."""
        self.publish_dialog_sub_assistant_checkbox(name).check()
        expect(self.publish_dialog_sub_assistant_categories(name)).to_be_in_viewport()
        return self

    @step
    def select_category_in_publish_dialog(self, category: str = "Quality Assurance"):
        """Select category in the publish to marketplace dialog."""
        self.publish_dialog_categories_dropdown.click()
        self.page.get_by_role("option", name=category).click()
        self.publish_confirmation_dialog.click()
        return self

    @step
    def confirm_and_wait_for_publish(self):
        """
        Click the Publish button and handle validation flow.

        Waits for validation to complete and handles both success and failure scenarios.
        If validation fails and "Publish Anyway" appears, clicks it and waits again.
        """
        # Click Publish button
        self.publish_button.click()

        # Wait for validation to start and complete
        # The validation message may appear briefly or not at all depending on speed
        self.page.wait_for_timeout(3000)

        # Wait for either "Publish Anyway" button (validation failed) or dialog to close (validation succeeded)
        # Check if "Publish Anyway" button appeared (validation warning/error)
        try:
            # Try to wait for Publish Anyway button with reasonable timeout
            self.publish_anyway_button.wait_for(state="visible", timeout=60000)

            # If we get here, validation failed - click Publish Anyway to force publish
            self.publish_anyway_button.click()

            # Wait for the second validation round to complete
            self.page.wait_for_timeout(3000)

        except TimeoutError:
            # Publish Anyway button didn't appear - validation succeeded
            pass

        # Wait for publish process to fully complete and backend to index the assistant
        self.page.wait_for_timeout(5000)
        return self

    @step
    def delete_assistant_with_confirmation(self, assistant_name: str):
        """Delete an assistant and confirm the deletion dialog."""
        delete_action = self.action_delete
        self.open_action_menu(assistant_name, delete_action)
        delete_action.click()

        confirmation_dialog = (
            self.page.get_by_role("dialog")
            .filter(has_text="Delete")
            .or_(self.page.locator('div[role="dialog"]').filter(has_text="confirm"))
            .or_(self.page.locator('div[role="dialog"]').filter(has_text="sure"))
        )
        expect(confirmation_dialog.first).to_be_visible()

        confirm_button = confirmation_dialog.locator(
            'button:has-text("Delete"), button:has-text("Confirm"), button:has-text("Yes")'
        ).first
        expect(confirm_button).to_be_visible()
        confirm_button.click()
        return self

    @step
    def cancel_assistant_deletion(self, assistant_name: str):
        """Start assistant deletion but cancel it."""
        delete_action = self.action_delete
        self.open_action_menu(assistant_name, delete_action)
        delete_action.click()

        confirmation_dialog = (
            self.page.get_by_role("dialog")
            .filter(has_text="Delete")
            .or_(self.page.locator('div[role="dialog"]').filter(has_text="confirm"))
        )
        expect(confirmation_dialog.first).to_be_visible()

        cancel_button = confirmation_dialog.locator(
            'button:has-text("Cancel"), button:has-text("No"), button:has-text("Close")'
        ).first
        expect(cancel_button).to_be_visible()
        cancel_button.click()
        return self

    @step
    def clone_assistant(self, assistant_name: str):
        """Clone an assistant via the action menu."""
        clone_action = self.action_clone
        self.open_action_menu(assistant_name, clone_action)
        clone_action.click()
        return CreateEditAssistantPage(self.page)
