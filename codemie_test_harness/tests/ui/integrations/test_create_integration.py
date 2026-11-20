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
from hamcrest import assert_that, has_item, is_not

from codemie_test_harness.tests.ui.pageobject.integrations.create_integration_page import (
    CreateIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integration_form_page import (
    IntegrationFormPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_list_page import (
    IntegrationsListPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_page import (
    IntegrationsPage,
)
from codemie_test_harness.tests.ui.test_data.integration_test_data import (
    IntegrationTestDataFactory,
)
from codemie_test_harness.tests.ui.test_data.unified_integrations_ui_test_data import (
    DIAL,
    DIAL_MEMBER_HINT,
    DIAL_SWITCH_NOTE,
    GOOGLE_OAUTH,
    GOOGLE_OAUTH_SWITCH_NOTE,
    HIDDEN_PROJECT_TOAST,
    NEW_INTEGRATION_FORM_SCOPE_BY_LIST_SCOPE,
    PROJECT_ADMINS_ONLY_REASON,
    PROJECT_CLEARED_NOTE,
    SAME_VIEW_TOAST,
    SAVED_TOAST,
    SCOPE_ALL,
    SCOPE_BADGE_PROJECT_ONLY,
    SCOPE_BADGE_USER_ONLY,
    SCOPE_PROJECT,
    SCOPE_USER,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.user_utils import UserUtils

# Hint on an option bound to the other scope (frontend settingsUIConfig / SettingsForm)
SWITCHES_SCOPE_HINT_PREFIX = "Switches Scope to"
SWITCHES_SCOPE_TO_PROJECT_HINT = f"{SWITCHES_SCOPE_HINT_PREFIX} Project"
SWITCHES_SCOPE_TO_USER_HINT = f"{SWITCHES_SCOPE_HINT_PREFIX} User"


@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
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
    integrations_page.should_see_integration_scope_filter()
    integrations_page.should_see_integrations_table()


@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
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
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
def test_navigate_to_create_integration_from_integrations_page(page):
    """
    Test navigation to create integration page from integrations page ui elements.

    Verifies:
    - Navigation via UI elements works correctly
    - Page Title matches integration type
    """

    list_page = IntegrationsListPage(page)
    create_integration_page = CreateIntegrationPage(page)
    form_page = IntegrationFormPage(page)

    # Scope filter 'User' on the list: the 'New Integration' button opens the form with
    # Scope 'User' already selected (the form is not told which Scope to take)
    list_page.navigate_to()
    list_page.select_scope("User")
    list_page.click_new_integration()
    form_page.wait_until_open()

    # Assert
    create_integration_page.should_be_on_new_integration_form()
    form_page.should_have_scope_selected("User")

    # Scope filter 'Project' on the list: the same form opens with Scope 'Project'
    list_page.navigate_to()
    list_page.select_scope("Project")
    list_page.click_new_integration()
    form_page.wait_until_open()

    # Assert
    create_integration_page.should_be_on_new_integration_form()
    form_page.should_have_scope_selected("Project")


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.parametrize(
    "credential_type",
    [CredentialTypes.GIT, CredentialTypes.JIRA, CredentialTypes.CONFLUENCE],
)
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
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
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
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
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
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
    integrations_page.toast.should_show(SAVED_TOAST)
    integrations_page.should_see_specific_integration(integration_test_data.alias)


@pytest.mark.xfail(
    strict=True,
    reason="The saved toast covers the More options button of the first row and stays "
    "open while the pointer is on it, so the row actions cannot be reached",
)
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
def test_saved_toast_goes_away_while_the_pointer_is_on_the_row_actions(page):
    # Arrange
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    integration_test_data = IntegrationTestDataFactory.git_integration()
    create_integration_page.navigate_to_user_integration_creation()
    create_integration_page.fill_git_integration_form(integration_test_data)
    create_integration_page.create_integration()
    integrations_page.toast.should_show(SAVED_TOAST)

    # Act - the pointer goes to the row actions, which the toast covers
    integrations_page.get_integration_row_by_alias(
        integration_test_data.alias
    ).point_at_menu_button()

    # Assert
    integrations_page.toast.should_disappear(move_cursor_away=False)


@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
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

    integrations_page.toast.should_show(SAVED_TOAST)
    integrations_page.should_see_specific_integration(integration_test_data.alias)


@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
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

    integrations_page.toast.should_show(SAVED_TOAST)
    integrations_page.should_see_specific_integration(integration_test_data.alias)


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
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
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
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
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
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
    if EnvironmentResolver.is_oss_standalone():
        ui_exceptions.extend(["LiteLLM", "Google OAuth"])

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

    # Assert - Scope badge on each scope-bound option; the "Switches Scope to ..." hint appears
    # only when the form's Scope differs from the type's own scope (User form: DIAL has it,
    # Google OAuth does not)
    check_google_oauth = "Google OAuth" not in ui_exceptions
    create_integration_page.should_see_dropdown_option_badge(
        "DIAL", SCOPE_BADGE_PROJECT_ONLY
    ).should_see_dropdown_option_hint("DIAL", SWITCHES_SCOPE_TO_PROJECT_HINT)
    if check_google_oauth:
        create_integration_page.should_see_dropdown_option_badge(
            "Google OAuth", SCOPE_BADGE_USER_ONLY
        ).should_not_see_dropdown_option_hint(
            "Google OAuth", SWITCHES_SCOPE_HINT_PREFIX
        )

    # Project form: the hint moves to Google OAuth, DIAL no longer has it
    create_integration_page.navigate_to_project_integration_creation()
    create_integration_page.credential_type_dropdown_button.click()
    create_integration_page.should_see_dropdown_option_badge(
        "DIAL", SCOPE_BADGE_PROJECT_ONLY
    ).should_not_see_dropdown_option_hint("DIAL", SWITCHES_SCOPE_HINT_PREFIX)
    if check_google_oauth:
        create_integration_page.should_see_dropdown_option_badge(
            "Google OAuth", SCOPE_BADGE_USER_ONLY
        ).should_see_dropdown_option_hint("Google OAuth", SWITCHES_SCOPE_TO_USER_HINT)


# @case unified-integrations-list_TC_013
@pytest.mark.parametrize(
    "list_scope",
    list(NEW_INTEGRATION_FORM_SCOPE_BY_LIST_SCOPE),
    ids=lambda label: f"list_scope_{label.lower()}",
)
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
@pytest.mark.ui_login_as("project_admin")
def test_create_opens_one_form_with_scope_first_taken_from_the_list_scope(
    page, list_scope
):
    list_page = IntegrationsListPage(page)
    form_page = IntegrationFormPage(page)
    list_page.navigate_to()
    list_page.select_scope(list_scope)

    list_page.click_new_integration()

    form_page.wait_until_open()
    form_page.should_show_heading()
    form_page.should_have_scope_first()
    form_page.should_have_scope_selected(
        NEW_INTEGRATION_FORM_SCOPE_BY_LIST_SCOPE[list_scope]
    )


# @case unified-integrations-list_TC_013
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
@pytest.mark.ui_login_as("project_admin")
def test_form_opened_with_scope_in_the_address_preselects_it(page):
    form_page = IntegrationFormPage(page)

    form_page.navigate_to("scope=user")

    form_page.should_have_scope_selected(SCOPE_USER)


# @case unified-integrations-list_TC_016
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.ui_login_as("project_admin")
def test_picking_dial_switches_scope_to_project_and_google_oauth_switches_back(page):
    form_page = IntegrationFormPage(page)
    form_page.navigate_to("scope=user")

    form_page.pick_credential_type(DIAL)

    form_page.should_have_scope_selected(SCOPE_PROJECT)
    form_page.should_show_note(DIAL_SWITCH_NOTE)

    form_page.pick_credential_type(GOOGLE_OAUTH)

    form_page.should_have_scope_selected(SCOPE_USER)
    form_page.should_show_note(GOOGLE_OAUTH_SWITCH_NOTE)


# @case unified-integrations-list_TC_017
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
@pytest.mark.ui_login_as("project_admin")
def test_saved_user_integration_keeps_the_filters_and_is_highlighted(
    page, project_admin_integrations, scoped_integrations
):
    alias = scoped_integrations.track_alias(
        project_admin_integrations, get_random_name()
    )
    list_page = IntegrationsListPage(page)
    form_page = IntegrationFormPage(page)
    list_page.navigate_to()
    list_page.select_scope(SCOPE_USER)
    list_page.click_new_integration()
    form_page.wait_until_open()
    form_page.fill_alias(alias)

    form_page.save()

    list_page.toast.should_show(SAVED_TOAST)
    list_page.toast.should_show(SAME_VIEW_TOAST)
    list_page.should_have_scope_selected(SCOPE_USER)
    list_page.should_show_scope_badge(alias, SCOPE_USER)
    list_page.should_mark_row_as_just_saved(alias)


# @case unified-integrations-list_TC_017
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
@pytest.mark.ui_login_as("project_admin")
def test_saved_project_integration_hidden_by_filters_is_shown_by_the_toast_action(
    page, default_project_member, project_admin_integrations, scoped_integrations
):
    alias = scoped_integrations.track_alias(
        project_admin_integrations, get_random_name()
    )
    list_page = IntegrationsListPage(page)
    form_page = IntegrationFormPage(page)
    list_page.navigate_to()
    list_page.select_scope(SCOPE_USER)
    list_page.click_new_integration()
    form_page.wait_until_open()
    form_page.fill_alias(alias)
    form_page.select_scope(SCOPE_PROJECT)
    form_page.pick_project(default_project_member.project_a)

    form_page.save()

    list_page.toast.should_show(HIDDEN_PROJECT_TOAST)
    list_page.should_offer_show_all_scopes_and_types()
    list_page.should_not_show_row(alias)

    list_page.click_show_all_scopes_and_types()

    list_page.should_have_scope_selected(SCOPE_ALL)
    list_page.should_show_scope_badge(alias, SCOPE_PROJECT)


@pytest.fixture
def administered_projects(fresh_project_admin_client, default_project_member):
    """Projects the signed-in user administers, as their profile lists them.

    The selector at Project scope offers the user's projects that appear in the profile's
    administered list; a personal project is a membership without the admin flag, so it is
    not among them.
    """
    me = UserUtils(fresh_project_admin_client).get_about_me()
    names = [p.name for p in me.projects if p.name in me.applications_admin]
    assert_that(names, has_item(default_project_member.project_a))
    assert_that(names, is_not(has_item(me.email)))
    return names


# @case unified-integrations-list_TC_014
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
@pytest.mark.ui_login_as("project_admin_member_of_project_b")
def test_project_scope_offers_only_administered_projects_and_a_scope_change_clears_the_project(
    page, default_project_member, administered_projects
):
    member_only = default_project_member.project_b
    form_page = IntegrationFormPage(page)
    form_page.navigate_to("scope=user")
    form_page.should_offer_global_switch()
    form_page.pick_project(member_only)
    form_page.switch_global_on()

    form_page.select_scope(SCOPE_PROJECT)

    form_page.should_have_project_cleared(member_only)
    form_page.should_show_note(PROJECT_CLEARED_NOTE)
    form_page.should_not_offer_global_switch()

    form_page.open_project_list()

    form_page.should_offer_exactly_projects(administered_projects)
    form_page.should_not_offer_project(member_only)


# @case unified-integrations-list_TC_015
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.oss_standalone
@pytest.mark.ui_login_as("member")
def test_member_sees_project_scope_and_dial_disabled_on_the_create_form(page):
    form_page = IntegrationFormPage(page)

    form_page.navigate_to()

    form_page.should_have_project_scope_disabled(PROJECT_ADMINS_ONLY_REASON)

    form_page.open_credential_type_list()

    form_page.should_disable_credential_type(DIAL, DIAL_MEMBER_HINT)
