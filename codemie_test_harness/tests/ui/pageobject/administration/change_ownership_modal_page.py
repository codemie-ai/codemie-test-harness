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

"""Page object for the Change Ownership popup.

Opened from the 'Change ownership' item of a project row on /settings/administration/projects.
"""

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ChangeOwnershipModalPage(BasePage):
    """Change Ownership popup — current owner line, New owner search select, Confirm."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def modal(self) -> Locator:
        """The popup dialog titled 'Change Ownership'."""
        return self.page.get_by_role("dialog", name="Change Ownership")

    @property
    def confirm_button(self) -> Locator:
        """The 'Confirm' submit button."""
        return self.modal.get_by_role("button", name="Confirm", exact=True)

    @property
    def new_owner_select(self) -> Locator:
        """The 'New owner' searchable single-select (a PrimeReact MultiSelect without a test id)."""
        return self.modal.locator(".p-multiselect")

    @property
    def user_filter_input(self) -> Locator:
        """The 'Search for user' filter input of the open select panel."""
        return self.page.get_by_placeholder("Search for user")

    def _user_option(self, text: str) -> Locator:
        """A search result whose label ('<name> (<email>)') contains the given text."""
        return self.page.get_by_role("option", name=text)

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def select_new_owner(self, email: str):
        """Search the New owner select by email and pick the matching user."""
        self.new_owner_select.click()
        self.user_filter_input.fill(email)
        option = self._user_option(email)
        expect(option).to_be_visible(timeout=15000)
        option.click()
        return self

    @step
    def confirm(self):
        """Click Confirm."""
        self.confirm_button.click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self):
        """Verify the popup is open."""
        expect(self.modal).to_be_visible(timeout=10000)
        return self

    @step
    def should_be_closed(self):
        """Verify the popup is closed."""
        expect(self.modal).to_be_hidden(timeout=15000)
        return self

    @step
    def should_show_current_owner(self, owner_label: str):
        """Verify the 'Current owner: <name (email)>' line."""
        expect(self.modal).to_contain_text(
            f"Current owner: {owner_label}", timeout=15000
        )
        return self

    @step
    def should_have_new_owner_select(self):
        """Verify the 'New owner' select is shown."""
        expect(self.modal.get_by_text("New owner", exact=True)).to_be_visible()
        expect(self.new_owner_select).to_be_visible()
        return self

    @step
    def should_have_confirm_disabled(self):
        """Verify Confirm is disabled (no new owner picked yet)."""
        expect(self.confirm_button).to_be_disabled()
        return self

    @step
    def should_have_confirm_enabled(self):
        """Verify Confirm is enabled (a new owner is picked)."""
        expect(self.confirm_button).to_be_enabled()
        return self
