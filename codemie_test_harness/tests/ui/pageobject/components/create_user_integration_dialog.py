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

from playwright.sync_api import Locator, Page, expect
from reportportal_client import step


class CreateUserIntegrationDialog:
    """Component for the 'Create User Integration' dialog opened from a datasource
    creation page when no integration exists yet for the selected datasource type."""

    def __init__(self, page: Page):
        self.page = page

    # ====================
    # PROPERTIES
    # ====================

    @property
    def dialog(self) -> Locator:
        """Main dialog container."""
        return self.page.locator(
            '[role="dialog"]:has(h4:text-is("Create User Integration"))'
        )

    @property
    def heading(self) -> Locator:
        """Dialog heading 'Create User Integration'."""
        return self.dialog.get_by_role(
            "heading", name="Create User Integration", level=4
        )

    @property
    def project_selector(self) -> Locator:
        """Project selector, pre-filled and locked to the current project."""
        return self.dialog.get_by_role("combobox", name="Project")

    @property
    def global_integration_switch(self) -> Locator:
        """'Global Integration' switch."""
        return self.dialog.get_by_role("switch", name="Global Integration")

    @property
    def credential_type_selector(self) -> Locator:
        """Credential Type selector, locked to 'Google OAuth' for this flow."""
        return self.dialog.get_by_role("combobox", name="Credential Type")

    @property
    def alias_input(self) -> Locator:
        """Alias input, pre-filled with a generated value."""
        return self.dialog.get_by_role("textbox", name="Alias")

    @property
    def sign_in_with_google_button(self) -> Locator:
        """'Sign in with Google' button."""
        return self.dialog.get_by_role("button", name="Sign in with Google")

    @property
    def cancel_button(self) -> Locator:
        """'Cancel' button."""
        return self.dialog.get_by_role("button", name="Cancel")

    @property
    def save_button(self) -> Locator:
        """'Save' button."""
        return self.dialog.get_by_role("button", name="Save")

    # ====================
    # ACTION METHODS
    # ====================

    @step
    def click_sign_in_with_google_and_get_popup(self) -> Page:
        """Click 'Sign in with Google' and return the new tab it opens."""
        with self.page.expect_popup() as popup_info:
            self.sign_in_with_google_button.click()
        return popup_info.value

    # ====================
    # VERIFICATION METHODS
    # ====================

    @step
    def should_be_visible(self):
        """Verify that the Create User Integration dialog is visible."""
        expect(self.dialog).to_be_visible(timeout=10000)
        expect(self.heading).to_be_visible()
        return self

    @step
    def should_have_project_selector_disabled(self):
        """Verify that the Project selector is visible and locked."""
        expect(self.project_selector).to_be_visible()
        expect(self.project_selector).to_be_disabled()
        return self

    @step
    def should_have_global_integration_switch(self):
        """Verify that the Global Integration switch is visible."""
        expect(self.global_integration_switch).to_be_visible()
        return self

    @step
    def should_have_credential_type_locked_to_google_oauth(self):
        """Verify that Credential Type is locked and pre-selected to Google OAuth."""
        expect(self.credential_type_selector).to_be_visible()
        expect(self.credential_type_selector).to_be_disabled()
        expect(self.credential_type_selector).to_have_value("Google OAuth")
        return self

    @step
    def should_have_alias_input_populated(self):
        """Verify that the Alias input is visible and pre-filled."""
        expect(self.alias_input).to_be_visible()
        expect(self.alias_input).not_to_have_value("")
        return self

    @step
    def should_have_sign_in_with_google_button(self):
        """Verify that the 'Sign in with Google' button is visible."""
        expect(self.sign_in_with_google_button).to_be_visible()
        return self

    @step
    def should_have_all_expected_elements(self):
        """Verify that all expected dialog elements are visible."""
        self.should_have_project_selector_disabled()
        self.should_have_global_integration_switch()
        self.should_have_credential_type_locked_to_google_oauth()
        self.should_have_alias_input_populated()
        self.should_have_sign_in_with_google_button()
        return self
