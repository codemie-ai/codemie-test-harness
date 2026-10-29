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


class MissingIntegrationsValidationDialog:
    """Component for the Missing Integrations validation dialog on Assistant create/edit page."""

    def __init__(self, page: Page):
        self.page = page

    # ====================
    # PROPERTIES
    # ====================

    @property
    def dialog(self) -> Locator:
        """Main dialog container."""
        return (
            self.page.get_by_role("dialog")
            .filter(has_text="Missing Integrations")
            .or_(
                self.page.get_by_role("alertdialog").filter(
                    has_text="Missing Integrations"
                )
            )
        )

    @property
    def heading(self) -> Locator:
        """Dialog heading 'Missing Integrations'."""
        return self.dialog.get_by_role("heading", name="Missing Integrations", level=4)

    @property
    def message(self) -> Locator:
        """Dialog message explaining missing integrations."""
        return self.dialog.locator("p").first

    @property
    def integration_type_section(self) -> Locator:
        """Integration type section (e.g., Xray)."""
        return self.dialog.locator("text=/Integration Type:/i")

    @property
    def required_capability_item(self) -> Locator:
        """Required capability item (e.g., Quality Assurance)."""
        return self.dialog.locator("text=/Quality Assurance/i")

    @property
    def tool_entry(self) -> Locator:
        """Tool entry that requires the integration."""
        return self.dialog.locator("text=/Xray Get Tests/i")

    @property
    def add_integration_button(self) -> Locator:
        """'Add Integration' button."""
        return self.dialog.get_by_role("button", name="Add Integration")

    @property
    def cancel_button(self) -> Locator:
        """'Cancel' button."""
        return self.dialog.get_by_role("button", name="Cancel")

    @property
    def skip_validation_save_button(self) -> Locator:
        """'Skip Validation & Save' button."""
        return self.dialog.get_by_role("button", name="Skip Validation & Save")

    @property
    def validate_save_button(self) -> Locator:
        """'Validate & Save' button."""
        return self.dialog.get_by_role("button", name="Validate & Save")

    # ====================
    # ACTION METHODS
    # ====================

    @step
    def click_add_integration(self):
        """Click the 'Add Integration' button."""
        self.add_integration_button.click()
        return self

    @step
    def click_cancel(self):
        """Click the 'Cancel' button."""
        self.cancel_button.click()
        return self

    @step
    def click_skip_validation_save(self):
        """Click the 'Skip Validation & Save' button."""
        self.skip_validation_save_button.click()
        return self

    @step
    def click_validate_save(self):
        """Click the 'Validate & Save' button."""
        self.validate_save_button.click()
        return self

    # ====================
    # VERIFICATION METHODS
    # ====================

    @step
    def should_be_visible(self):
        """Verify that the missing integrations validation dialog is visible."""
        expect(self.dialog).to_be_visible(timeout=10000)
        expect(self.heading).to_be_visible()
        return self

    @step
    def should_not_be_visible(self):
        """Verify that the missing integrations validation dialog is not visible."""
        expect(self.dialog).not_to_be_visible()
        return self

    @step
    def should_have_explanatory_message(self):
        """Verify that the dialog displays an explanatory message."""
        expect(self.message).to_be_visible()
        expect(self.message).to_contain_text(
            "require integrations that are not configured"
        )
        return self

    @step
    def should_display_integration_type(self):
        """Verify that the dialog displays the integration type."""
        expect(self.integration_type_section).to_be_visible()
        return self

    @step
    def should_display_required_capability(self):
        """Verify that the dialog displays the required capability."""
        expect(self.required_capability_item).to_be_visible()
        return self

    @step
    def should_display_tool_entry(self):
        """Verify that the dialog displays the tool entry."""
        expect(self.tool_entry).to_be_visible()
        return self

    @step
    def should_have_add_integration_button(self):
        """Verify that the 'Add Integration' button is visible."""
        expect(self.add_integration_button).to_be_visible()
        return self

    @step
    def should_have_cancel_button(self):
        """Verify that the 'Cancel' button is visible."""
        expect(self.cancel_button).to_be_visible()
        return self

    @step
    def should_have_skip_validation_save_button(self):
        """Verify that the 'Skip Validation & Save' button is visible."""
        expect(self.skip_validation_save_button).to_be_visible()
        return self

    @step
    def should_have_validate_save_button(self):
        """Verify that the 'Validate & Save' button is visible."""
        expect(self.validate_save_button).to_be_visible()
        return self

    @step
    def should_have_all_action_buttons(self):
        """Verify that all four action buttons are visible."""
        self.should_have_add_integration_button()
        self.should_have_cancel_button()
        self.should_have_skip_validation_save_button()
        self.should_have_validate_save_button()
        return self

    @step
    def should_have_all_expected_elements(self):
        """Verify that all expected dialog elements are visible."""
        self.should_have_explanatory_message()
        self.should_display_integration_type()
        self.should_display_required_capability()
        self.should_display_tool_entry()
        self.should_have_all_action_buttons()
        return self
