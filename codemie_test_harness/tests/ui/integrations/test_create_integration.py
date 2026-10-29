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
UI tests for Create Integration feature - critical paths with best practices.

This test suite covers the essential "Create Integration" workflow focusing on happy path scenarios.
All tests follow the Page Object Model pattern with reusable components abstracted in standalone classes.
"""

import pytest
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.ui.pageobject.integrations.create_integration_page import (
    CreateIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_page import (
    IntegrationsPage,
)
from codemie_test_harness.tests.ui.test_data.integration_test_data import (
    IntegrationTestDataFactory,
)
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


@pytest.mark.integration
@pytest.mark.ui
def test_navigate_to_integrations_via_menu(page):
    """
    Test navigation to create integration page via menu.

    Verifies:
    - User can navigate to integrations page from menu
    - Main UI elements are visible on Integrations page
    """
    # Arrange
    integrations_page = IntegrationsPage(page)

    # Act
    integrations_page.navigate_to_via_menu()

    # Assert
    integrations_page.should_be_on_integrations_page()
    integrations_page.should_see_create_integration_button()
    integrations_page.should_see_integration_type_switcher()
    integrations_page.should_see_integrations_table()


@pytest.mark.integration
@pytest.mark.ui
def test_navigate_to_create_integration_via_direct_url(page):
    """
    Test direct navigation to create integration page via URL.

    Verifies:
    - Direct URL access works correctly
    - Page Title matches integration type
    """

    create_integration_page = CreateIntegrationPage(page)

    # Act
    create_integration_page.navigate_to_user_integration_creation()

    # Assert
    create_integration_page.should_be_on_create_user_integration_page()

    # Act
    create_integration_page.navigate_to_project_integration_creation()

    # Assert
    create_integration_page.should_be_on_create_project_integration_page()


@pytest.mark.integration
@pytest.mark.ui
def test_navigate_to_create_integration_from_integrations_page(page):
    """
    Test navigation to create integration page from integrations page ui elements.

    Verifies:
    - Navigation via UI elements works correctly
    - Page Title matches integration type
    """

    integrations_page = IntegrationsPage(page)

    # Navigate to User Integration creation
    integrations_page.navigate_to().navigate_to_user_integration_creation()

    create_integration_page = CreateIntegrationPage(page)

    # Assert
    create_integration_page.should_be_on_create_user_integration_page()

    # Navigate to Project Integration creation
    integrations_page.navigate_to().navigate_to_project_integration_creation()

    # Assert
    create_integration_page.should_be_on_create_project_integration_page()


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.parametrize(
    "credential_type",
    [CredentialTypes.GIT, CredentialTypes.JIRA, CredentialTypes.CONFLUENCE],
)
def test_create_integration_type_form_fields(page, credential_type):
    """
    Test that all required form fields are displayed for each credential type.

    Verifies:
    - Page navigation and structure validation
    - Action buttons visibility (Back, Cancel, Create, Test for Jira/Confluence)
    - Project selector element presence
    - Global Integration toggle visibility
    - Credential Type field with correct value
    - Alias field with required indicator
    - Authentication section with all fields
    - Help text and information tooltips
    - Form field interactivity validation
    - Create button initial state
    - Credential-specific sections (GitHub App for Git, EPAM section for Confluence)
    """

    create_integration_page = CreateIntegrationPage(page)

    # Act
    create_integration_page.navigate_to_user_integration_creation()
    create_integration_page.select_credential_type(credential_type)

    # Assert - Verify page structure (includes title validation)
    create_integration_page.should_be_on_create_user_integration_page()

    # Assert - Verify UI elements visibility
    (
        create_integration_page.should_have_action_buttons_visible(credential_type)
        .should_have_project_selector_visible()
        .should_have_global_integration_toggle_visible()
        .should_have_credential_type_field_visible()
        .should_have_alias_field_visible()
        .should_have_authentication_section_visible(credential_type)
        .should_have_help_texts_visible()
    )

    # Assert - Verify credential type value
    create_integration_page.should_have_credential_type_selected(credential_type)

    # Assert - Verify form elements are interactive
    create_integration_page.should_have_input_fields_editable()

    # Assert - Verify Create button initial state
    create_integration_page.should_have_create_button_enabled()


@pytest.mark.integration
@pytest.mark.ui
def test_create_git_integration_github_app_authentication(page):
    """
    Test GitHub App authentication option for Git integrations.

    Verifies:
    - Authentication Type dropdown is visible
    - Can switch from Personal Access Token to GitHub Application
    - GitHub App specific fields appear (App ID, Private Key, Installation ID)
    - Personal Access Token fields are hidden when GitHub App is selected
    - GitHub App info section with setup guide link is visible
    """

    create_integration_page = CreateIntegrationPage(page)

    # Act - Navigate and select Git credential type
    create_integration_page.navigate_to_user_integration_creation()
    create_integration_page.select_credential_type(CredentialTypes.GIT)

    # Assert - By default, Personal Access Token is selected
    create_integration_page.should_not_have_github_app_section_visible()

    # Act - Switch to GitHub Application authentication
    create_integration_page.select_authentication_type("GitHub Application")

    # Assert - GitHub App section should now be visible
    create_integration_page.should_have_github_app_section_visible()
    create_integration_page.should_have_github_app_section_editable()


@pytest.mark.integration
@pytest.mark.ui
def test_create_git_integration_complete_workflow(page):
    """
    Test the complete Git integration creation workflow (happy path).

    Verifies the end-to-end workflow for Git integration creation.
    """
    # Arrange
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    integration_test_data = IntegrationTestDataFactory.git_integration()

    # Act - Navigate and create
    create_integration_page.navigate_to_user_integration_creation()
    create_integration_page.fill_git_integration_form(integration_test_data)
    create_integration_page.create_integration()

    # Assert
    integrations_page.should_see_message(
        IntegrationTestDataFactory.success_messages["integration_created"]
    ).should_see_specific_integration(integration_test_data.alias)


@pytest.mark.integration
@pytest.mark.ui
def test_create_jira_integration_complete_workflow(page):
    """
    Test the complete Jira integration creation workflow (happy path).

    Verifies the end-to-end workflow for Jira integration creation including:
    - Navigation to user integration creation page
    - Credential type selection (Jira)
    - Form filling with valid Jira integration data
    - Integration creation and success validation
    - Verification of created integration in integrations list
    """
    # Arrange
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    integration_test_data = IntegrationTestDataFactory.jira_integration()

    # Act - Navigate and create
    create_integration_page.navigate_to_user_integration_creation()
    create_integration_page.fill_jira_integration_form(integration_test_data)
    create_integration_page.create_integration()

    integrations_page.should_see_message(
        IntegrationTestDataFactory.success_messages["integration_created"]
    ).should_see_specific_integration(integration_test_data.alias)


@pytest.mark.integration
@pytest.mark.ui
def test_create_confluence_integration_complete_workflow(page):
    """
    Test the complete Confluence integration creation workflow (happy path).

    Verifies the end-to-end workflow for Confluence integration creation including:
    - Navigation to user integration creation page
    - Credential type selection (Confluence)
    - Form filling with valid Confluence integration data
    - Integration creation and success validation
    - Verification of created integration in integrations list
    """
    # Arrange
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    integration_test_data = IntegrationTestDataFactory.confluence_integration()

    # Act - Navigate and create
    create_integration_page.navigate_to_user_integration_creation()
    create_integration_page.fill_confluence_integration_form(integration_test_data)
    create_integration_page.create_integration()

    integrations_page.should_see_message(
        IntegrationTestDataFactory.success_messages["integration_created"]
    ).should_see_specific_integration(integration_test_data.alias)


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
def test_form_reset_and_cancel_functionality(page):
    """
    Test form reset and cancel functionality.

    Verifies:
    - Cancel button navigates away from form
    - Form data is not saved when cancelled
    - User can safely exit creation process
    """
    # Arrange
    create_integration_page = CreateIntegrationPage(page)
    integrations_page = IntegrationsPage(page)

    # Act
    cancelled_integration_alias = "Test Integration to Cancel"
    create_integration_page.navigate_to_user_integration_creation()
    create_integration_page.fill_alias(cancelled_integration_alias)
    create_integration_page.cancel_creation()

    # Assert - Should navigate back to integrations page
    integrations_page.should_have_page_title("Integrations")

    # Verify the cancelled integration was not created
    integrations_page.should_not_see_integration(cancelled_integration_alias)


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
def test_alias_field_validation_message(page):
    """
    Test validation message when alias field is empty and form is submitted.

    Verifies:
    - Inline validation message appears below alias field
    - Error message states "Alias is required"
    - Validation message is visible and readable
    """
    # Arrange
    create_integration_page = CreateIntegrationPage(page)

    # Act - Navigate to integration creation and try to submit without alias
    create_integration_page.navigate_to_user_integration_creation()
    create_integration_page.select_credential_type(CredentialTypes.GIT)

    # Clean alias field intentionally
    create_integration_page.fill_alias("")
    create_integration_page.create_integration()

    # Assert - Verify inline validation message appears
    create_integration_page.should_see_inline_validation_message(
        field="alias", message="Alias is required"
    )


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
def test_credential_type_dropdown_shows_all_available_options(page):
    """
    Test that credential type dropdown shows all available integration types.

    Verifies that all credential types defined in CredentialTypes enum are
    available in the UI dropdown.
    """
    # Arrange
    create_integration_page = CreateIntegrationPage(page)
    expected_credential_types = [credential.value for credential in CredentialTypes]

    # Credential types not shown in UI dropdown
    ui_exceptions = ["DIAL", "MSTeams"]
    if EnvironmentResolver.is_localhost():
        ui_exceptions.append("LiteLLM")

    # Act
    create_integration_page.navigate_to_user_integration_creation()
    create_integration_page.credential_type_dropdown_button.click()

    # Assert - Verify all credential types are available
    for credential_type in expected_credential_types:
        if credential_type == "Xray":
            credential_type = "X-ray"
        if credential_type == "GoogleOAuth":
            credential_type = "Google OAuth"
        if credential_type == "XWiki":
            credential_type = "xWiki"
        if credential_type == "MSExchange":
            credential_type = "Microsoft Exchange"
        if credential_type in ui_exceptions:
            continue

        create_integration_page.should_see_dropdown_option(credential_type)
