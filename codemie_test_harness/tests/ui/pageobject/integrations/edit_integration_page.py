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
Edit Integration Page object for modifying existing integrations.

This page reuses most of the structure from CreateIntegrationPage
but with specific behaviors for editing mode.
"""

import re
from urllib.parse import quote

from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.integrations.create_integration_page import (
    CreateIntegrationPage,
)


class EditIntegrationPage(CreateIntegrationPage):
    """
    Edit Integration Page - extends CreateIntegrationPage.

    Most functionality is inherited from CreateIntegrationPage.
    This class adds edit-specific behavior and overrides where needed.
    """

    def __init__(self, page):
        super().__init__(page)

    # ====================
    # PAGE-SPECIFIC PROPERTIES (Overrides)
    # ====================

    @property
    def page_heading(self) -> Locator:
        """Page heading element - 'Edit Integration' for edit mode."""
        return self.page.get_by_role("heading", name="Edit Integration", level=1)

    @property
    def project_integration_page_heading(self) -> Locator:
        """Page heading of the project-scope edit page - 'Edit Project Integration'."""
        return self.page.get_by_role(
            "heading", name="Edit Project Integration", level=1
        )

    @property
    def project_combobox(self) -> Locator:
        """Project dropdown of the edit form, addressed by its accessible role and name."""
        return self.page.get_by_role("combobox", name="Project", exact=True)

    @property
    def alias_field(self) -> Locator:
        """Alias field - alias for alias_input from parent class."""
        return self.alias_input

    @property
    def url_field(self) -> Locator:
        """URL field - alias for url_input from parent class."""
        return self.url_input

    @property
    def credential_type_dropdown(self) -> Locator:
        """Credential type dropdown - maps to credential_type_input from parent class."""
        return self.credential_type_input

    @property
    def change_project_dialog(self) -> Locator:
        """'Change integration project?' confirmation modal."""
        return self.page.get_by_role("dialog").filter(
            has_text="Change integration project?"
        )

    @property
    def change_project_confirm_button(self) -> Locator:
        """'Change project' confirm button inside the confirmation modal."""
        return self.change_project_dialog.get_by_role("button", name="Change project")

    # ====================
    # NAVIGATION METHODS
    # ====================

    @step
    def navigate_to_edit_integration(
        self, project_name: str, credential_type: str, alias: str
    ):
        """
        Navigate directly to edit integration page via URL.

        Args:
            project_name: Name of the project
            credential_type: Type of credential (e.g., 'Git', 'Jira')
            alias: Integration alias
        """
        # URL format: //integrations/user/edit?project_name=X&credential_type=Y&alias=Z
        url = (
            f"/integrations/user/edit"
            f"?project_name={quote(project_name)}"
            f"&credential_type={quote(credential_type)}"
            f"&alias={quote(alias)}"
        )
        self.page.goto(url)
        self.wait_for_page_load()
        return self

    @step
    def navigate_to_edit_project_integration(
        self, project_name: str, credential_type: str, alias: str
    ):
        """
        Navigate directly to the edit page of a project-scoped integration via URL.

        Args:
            project_name: Name of the project the integration currently belongs to
            credential_type: Type of credential (e.g., 'Git')
            alias: Integration alias
        """
        url = (
            f"/integrations/project/edit"
            f"?project_name={quote(project_name)}"
            f"&credential_type={quote(credential_type)}"
            f"&alias={quote(alias)}"
        )
        self.page.goto(url)
        self.wait_for_page_load()
        return self

    # ====================
    # FORM FIELD UPDATE METHODS
    # ====================

    @step
    def update_alias(self, new_alias: str):
        """
        Update the integration alias.

        Args:
            new_alias: New alias value
        """
        self.fill_alias(new_alias)
        return self

    @step
    def update_url(self, new_url: str):
        """
        Update the integration URL.

        Args:
            new_url: New URL value
        """
        self.fill_url(new_url)
        return self

    @step
    def update_token(self, new_token: str):
        """
        Update the integration token.

        Args:
            new_token: New token value
        """
        self.fill_token(new_token)
        return self

    @step
    def update_token_name(self, new_token_name: str):
        """
        Update the token name.

        Args:
            new_token_name: New token name value
        """
        self.fill_token_name(new_token_name)
        return self

    # ====================
    # VERIFICATION METHODS (Edit-specific)
    # ====================

    @step
    def should_be_on_edit_integration_page(self):
        """Verify that user is on the edit integration page."""
        expect(self.page_heading).to_be_visible(timeout=15000)
        expect(self.page).to_have_url(
            re.compile(r".*integrations/user/edit.*"), timeout=10000
        )
        return self

    @step
    def should_be_on_edit_project_integration_page(self):
        """Verify that user is on the project-scope edit integration page."""
        expect(self.project_integration_page_heading).to_be_visible(timeout=15000)
        expect(self.page).to_have_url(
            re.compile(r".*integrations/project/edit.*"), timeout=10000
        )
        return self

    @step
    def should_have_alias_value(self, expected_alias: str):
        """
        Verify that the alias field contains expected value.

        Args:
            expected_alias: Expected alias value
        """
        expect(self.alias_field).to_have_value(expected_alias)
        return self

    @step
    def should_have_url_value(self, expected_url: str):
        """
        Verify that the URL field contains expected value.

        Args:
            expected_url: Expected URL value
        """
        expect(self.url_field).to_have_value(expected_url)
        return self

    @step
    def should_have_masked_token(self):
        """Verify that the token field shows masked value (asterisks) or is empty."""
        # Token should be masked with asterisks in edit mode or be empty
        # Check that the token field is not displaying plain text credentials
        # We expect either asterisks (masked) or empty value

        # Wait for the field to be visible
        expect(self.token_input).to_be_visible()

        # Get token value and check it's either masked or empty
        # Using page.wait_for_function to ensure condition is met
        self.page.wait_for_function(
            """() => {
                const tokenInput = document.querySelector('input#token[data-testid="validation"]');
                if (!tokenInput) return false;
                const value = tokenInput.value || '';
                // Token should be masked with asterisks or be empty
                return value.includes('*') || value === '';
            }""",
            timeout=5000,
        )
        return self

    @step
    def should_have_credential_type_disabled(self):
        """Verify that credential type dropdown is disabled in edit mode."""
        expect(self.credential_type_dropdown).to_be_disabled()
        return self

    @step
    def should_have_project_selector_disabled(self):
        """Verify that project selector is disabled in edit mode."""
        # Project cannot be changed when editing
        expect(self.project_selector).to_be_disabled()
        return self

    # ====================
    # ACTION METHODS (Overrides and additions)
    # ====================

    @step
    def change_project(self, project_name: str):
        """
        Pick another project in the Project dropdown of the edit form.

        Args:
            project_name: Name of the project to move the integration to
        """
        self.select_project(project_name)
        return self

    @step
    def confirm_project_change(self):
        """Click 'Change project' in the confirmation modal."""
        self.change_project_confirm_button.click()
        return self

    @step
    def should_have_project_selector_enabled(self):
        """Verify that the project selector can be used while editing."""
        expect(self.project_combobox).to_be_visible()
        expect(self.project_combobox).to_be_enabled()
        return self

    @step
    def should_show_project_change_confirmation(self, source_project_name: str):
        """
        Verify the project-change confirmation modal and its warning.

        Args:
            source_project_name: Project the integration is being moved out of
        """
        expect(self.change_project_dialog).to_be_visible()
        expect(self.change_project_dialog).to_contain_text(
            f'"{source_project_name}" that use this integration '
            "will stop working immediately"
        )
        expect(self.change_project_confirm_button).to_be_visible()
        return self

    @step
    def save_changes(self):
        """
        Save the edited integration.

        This is an alias for create_integration() but more semantically appropriate for edit mode.
        """
        self.create_integration()  # In edit mode, this is the Save button
        return self

    @step
    def cancel_editing(self):
        """
        Cancel editing and return to integrations list.

        This is an alias for cancel_creation() but more semantically appropriate for edit mode.
        """
        self.cancel_creation()
        return self

    @step
    def should_show_project_display_name(self, display_name: str):
        """Verify the project selector label shows the human display_name."""
        expect(self.project_selector_label).to_contain_text(display_name)
        return self
