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
UI tests for Test Connection feature.

This test suite covers testing integration connection for JIRA integrations,
including both success and failure scenarios with error message verification.
"""

import pytest
from playwright.sync_api import Page

from codemie_test_harness.tests.ui.pageobject.integrations.create_integration_page import (
    CreateIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_page import (
    IntegrationsPage,
)
from codemie_test_harness.tests.ui.test_data.integration_test_data import (
    IntegrationTestDataFactory,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.mark.jira
@pytest.mark.integration
@pytest.mark.ui
def test_test_connection_success(page: Page):
    """
    Test integration connection with valid credentials (success case).

    AC Coverage:
        - AC#1, AC#2 - Scope Item 3a: Test connection success case

    Prerequisites:
        - User is logged in
        - Valid JIRA credentials are available

    Steps:
        1. Navigate to integrations page
        2. Start creating a JIRA integration
        3. Fill form with valid JIRA credentials
        4. Click Test button
        5. Verify success message appears
        6. Verify Create button remains enabled
    """
    # Arrange
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    # Fill JIRA integration form with valid credentials
    integration_test_data = IntegrationTestDataFactory.jira_integration()

    # Get real JIRA credentials for successful connection test
    jira_url = CredentialsManager.get_parameter("JIRA_URL")
    jira_token = CredentialsManager.get_parameter("JIRA_TOKEN")

    # Update test data with real credentials
    integration_test_data.fields["url"] = jira_url
    integration_test_data.fields["token"] = jira_token

    create_integration_page.fill_jira_integration_form(integration_test_data)

    # Act - Click Test button
    create_integration_page.click_test()

    # Assert - Verify success message
    create_integration_page.should_see_test_connection_success()

    # Verify Create button is still enabled (can proceed with creation)
    create_integration_page.should_have_create_button_enabled()


@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
def test_test_connection_failure_with_error_message(page: Page):
    """
    Test integration connection with invalid credentials (failure case).

    AC Coverage:
        - AC#1, AC#2 - Scope Item 3b: Test connection failure with error message

    Prerequisites:
        - User is logged in

    Steps:
        1. Navigate to integrations page
        2. Start creating a JIRA integration
        3. Fill form with invalid JIRA credentials
        4. Click Test button
        5. Verify error message appears
        6. Verify error message contains connection failure details
    """
    # Arrange
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    # Fill JIRA integration form with invalid credentials
    integration_test_data = IntegrationTestDataFactory.jira_integration()

    # Use invalid credentials to trigger failure
    integration_test_data.fields["url"] = "https://invalid-jira-instance.example.com"
    integration_test_data.fields["token"] = "invalid_token_12345"

    create_integration_page.fill_jira_integration_form(integration_test_data)

    # Act - Click Test button
    create_integration_page.click_test()

    # Assert - Verify error message appears
    create_integration_page.should_see_test_connection_failure()

    # Verify error message contains failure details (AC#2)
    # The exact error message may vary, but it should indicate connection failure
    create_integration_page.should_have_error_message_containing(
        "Integration test failed"
    )
