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
Integration card component for individual integration items.
Contains methods for interacting with integration cards in the integrations list.
"""

from playwright.sync_api import expect, Locator
from reportportal_client import step


class IntegrationRow:
    """Integration card component with property-based element locators."""

    def __init__(self, page, card_locator: Locator):
        self.page = page
        self.card = card_locator

    # Card element properties
    @property
    def card_container(self):
        """The main card container."""
        return self.card

    @property
    def integration_name(self):
        """Integration name/title element."""
        return self.card.locator(
            '.integration-name, .card-title, h3, [data-testid="integration-name"]'
        )

    @property
    def integration_type(self):
        """Integration type/category element."""
        return self.card.locator(
            '.integration-type, .card-subtitle, .type-badge, [data-testid="integration-type"]'
        )

    @property
    def integration_icon(self):
        """Integration icon/logo element."""
        return self.card.locator(
            '.integration-icon, .card-icon, img, svg, [data-testid="integration-icon"]'
        )

    @property
    def status_indicator(self):
        """Integration status indicator (active/inactive/error)."""
        return self.card.locator(
            '.status-indicator, .status-badge, [data-testid="status"]'
        )

    @property
    def state_badge(self):
        """State column badge showing 'Enabled'/'Disabled' for a row.

        Confirmed live via playwright-cli against a running Scheduler integration
        row: the badge is rendered with role="status" and an accessible name/text
        of "Enabled" or "Disabled" (shared StatusBadge component: colored dot +
        text). Rows for which the frontend renders no state (e.g. a non-scheduler
        integration, or a Scheduler row whose credential_values entirely omit the
        `is_enabled` key) render an empty cell with no `status` role at all.
        """
        return self.card.get_by_role("status")

    @property
    def description(self):
        """Integration description text."""
        return self.card.locator(
            '.integration-description, .card-description, [data-testid="description"]'
        )

    @property
    def created_date(self):
        """Integration creation date."""
        return self.card.locator(
            '.created-date, .date-created, [data-testid="created-date"]'
        )

    @property
    def last_used_date(self):
        """Last used date."""
        return self.card.locator('.last-used, .date-used, [data-testid="last-used"]')

    @property
    def checkbox(self):
        """Selection checkbox."""
        return self.card.locator(
            'input[type="checkbox"], [data-testid="select-checkbox"]'
        )

    @property
    def menu_button(self):
        """Card menu button (three dots / More options)."""
        return self.card.get_by_role("button", name="More options")

    @property
    def edit_button(self):
        """Edit integration button."""
        return self.card.locator('button:has-text("Edit"), [data-testid="edit-btn"]')

    @property
    def delete_button(self):
        """Delete integration button."""
        return self.card.locator(
            'button:has-text("Delete"), [data-testid="delete-btn"]'
        )

    @property
    def test_connection_button(self):
        """Test connection button."""
        return self.card.locator(
            'button:has-text("Test"), button:has-text("Test Connection"), [data-testid="test-btn"]'
        )

    @property
    def duplicate_button(self):
        """Duplicate integration button."""
        return self.card.locator(
            'button:has-text("Duplicate"), [data-testid="duplicate-btn"]'
        )

    @property
    def view_details_button(self):
        """View details button."""
        return self.card.locator(
            'button:has-text("Details"), button:has-text("View"), [data-testid="details-btn"]'
        )

    @property
    def share_button(self):
        """Share integration button."""
        return self.card.locator('button:has-text("Share"), [data-testid="share-btn"]')

    # Context menu properties
    @property
    def context_menu(self):
        """Context menu that appears when clicking the menu button."""
        return self.page.locator(
            '.p-menu, .p-tieredmenu, .context-menu, .dropdown-menu, [role="menu"]'
        )

    @property
    def context_menu_edit(self):
        """Edit option in context menu."""
        return self.page.get_by_role("menuitem", name="Edit")

    @property
    def context_menu_delete(self):
        """Delete option in context menu."""
        return self.page.get_by_role("menuitem", name="Delete")

    @property
    def context_menu_test(self):
        """Test connection option in context menu."""
        return self.context_menu.locator(
            'button:has-text("Test"), [data-testid="context-test"]'
        )

    @property
    def context_menu_duplicate(self):
        """Duplicate option in context menu."""
        return self.context_menu.locator(
            'button:has-text("Duplicate"), [data-testid="context-duplicate"]'
        )

    # Action methods
    @step
    def click(self):
        """Click on the integration card."""
        self.card_container.click()
        return self

    @step
    def hover(self):
        """Hover over the integration card."""
        self.card_container.hover()
        return self

    @step
    def select(self):
        """Select the integration by checking its checkbox."""
        if self.checkbox.is_visible():
            self.checkbox.check()
        return self

    @step
    def deselect(self):
        """Deselect the integration by unchecking its checkbox."""
        if self.checkbox.is_visible():
            self.checkbox.uncheck()
        return self

    @step
    def click_menu(self):
        """Click the menu button to open context menu."""
        self.menu_button.click()
        # Wait for the menu to appear
        self.context_menu.wait_for(state="visible", timeout=5000)
        return self

    @step
    def click_edit(self):
        """Click the edit button."""
        if self.edit_button.is_visible():
            self.edit_button.click()
        else:
            self.click_menu()
            self.context_menu_edit.click()
        return self

    @step
    def click_delete(self):
        """Click the delete button."""
        if self.delete_button.is_visible():
            self.delete_button.click()
        else:
            self.click_menu()
            self.context_menu_delete.click()
        return self

    @step
    def click_test_connection(self):
        """Click the test connection button."""
        if self.test_connection_button.is_visible():
            self.test_connection_button.click()
        else:
            self.click_menu()
            self.context_menu_test.click()
        return self

    @step
    def click_view_details(self):
        """Click the view details button."""
        self.view_details_button.click()
        return self

    @step
    def click_share(self):
        """Click the share button."""
        self.share_button.click()
        return self

    # Information retrieval methods
    @step
    def get_integration_name(self) -> str:
        """
        Get the integration name.

        Returns:
            str: The integration name
        """
        return self.integration_name.text_content().strip()

    @step
    def get_integration_type(self) -> str:
        """
        Get the integration type.

        Returns:
            str: The integration type
        """
        return self.integration_type.text_content().strip()

    @step
    def is_selected(self) -> bool:
        """
        Check if the integration is selected.

        Returns:
            bool: True if selected, False otherwise
        """
        if self.checkbox.is_visible():
            return self.checkbox.is_checked()
        return False

    # Verification methods
    @step
    def should_be_visible(self):
        """Verify that the integration card is visible."""
        expect(self.card_container).to_be_visible()
        return self

    @step
    def should_be_hidden(self):
        """Verify that the integration card is hidden."""
        expect(self.card_container).to_be_hidden()
        return self

    @step
    def should_have_name(self, expected_name: str):
        """
        Verify the integration name.

        Args:
            expected_name (str): Expected integration name
        """
        expect(self.integration_name).to_contain_text(expected_name)
        return self

    @step
    def should_have_type(self, expected_type: str):
        """
        Verify the integration type.

        Args:
            expected_type (str): Expected integration type
        """
        expect(self.integration_type).to_contain_text(expected_type)
        return self

    @step
    def should_show_state(self, expected_state: str):
        """
        Verify the row's State column badge shows the expected text.

        Args:
            expected_state (str): Expected badge text, e.g. "Enabled" or "Disabled".
        """
        expect(self.state_badge).to_be_visible()
        expect(self.state_badge).to_have_text(expected_state)
        return self

    @step
    def should_not_show_state_badge(self):
        """Verify the row has no State column badge."""
        expect(self.state_badge).to_have_count(0)
        return self
