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
UI tests for Edit Integration feature.

This test suite covers editing existing integrations through the UI,
including updating credentials and alias.
"""

import pytest
from playwright.sync_api import Page

from codemie_test_harness.tests.ui.pageobject.integrations.create_integration_page import (
    CreateIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.edit_integration_page import (
    EditIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_page import (
    IntegrationsPage,
)
from codemie_test_harness.tests.ui.test_data.integration_test_data import (
    IntegrationTestDataFactory,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
def test_edit_integration_update_credentials(page: Page):
    """
    Test editing an existing integration by updating credentials.

    AC Coverage:
        - AC#1 - Scope Item 1a: Edit existing integration (update credentials)

    Prerequisites:
        - User is logged in
        - At least one Git integration exists

    Steps:
        1. Navigate to integrations page
        2. Create a test Git integration via UI
        3. Open More options menu for the integration
        4. Click Edit
        5. Update token credential
        6. Save changes
        7. Verify success message
        8. Verify integration appears in list
    """
    # Arrange - Create a test integration via UI
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    integration_test_data = IntegrationTestDataFactory.git_integration()

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    create_integration_page.fill_git_integration_form(integration_test_data)
    create_integration_page.create_integration()

    # Wait for integration to be created
    integrations_page.wait_for_page_load()
    integrations_page.should_see_message(
        IntegrationTestDataFactory.success_messages["integration_created"]
    )

    # Act - Edit the integration
    integration_row = integrations_page.get_integration_row_by_alias(
        integration_test_data.alias
    )
    integration_row.click_edit()

    # Update credentials on edit page
    edit_integration_page = EditIntegrationPage(page)
    edit_integration_page.should_be_on_edit_integration_page()

    new_token = f"new-token-{get_random_name()}"
    edit_integration_page.update_token(new_token)
    edit_integration_page.save_changes()

    # Assert - Verify success
    integrations_page.wait_for_page_load()
    integrations_page.should_see_message(
        IntegrationTestDataFactory.success_messages["integration_updated"]
    )
    integrations_page.should_see_specific_integration(integration_test_data.alias)


@pytest.mark.integration
@pytest.mark.ui
def test_edit_integration_update_alias(page: Page):
    """
    Test editing an integration by updating its alias/name.

    AC Coverage:
        - AC#1 - Scope Item 1b: Edit integration name/alias

    Prerequisites:
        - User is logged in
        - At least one Git integration exists

    Steps:
        1. Navigate to integrations page
        2. Create a test Git integration via UI
        3. Open More options menu for the integration
        4. Click Edit
        5. Update alias field with new name
        6. Save changes
        7. Verify success message
        8. Verify integration appears with new alias
    """
    # Arrange - Create a test integration via UI
    integrations_page = IntegrationsPage(page)
    create_integration_page = CreateIntegrationPage(page)
    integration_test_data = IntegrationTestDataFactory.git_integration()

    integrations_page.navigate_to()
    integrations_page.navigate_to_user_integration_creation()

    create_integration_page.fill_git_integration_form(integration_test_data)
    create_integration_page.create_integration()

    # Wait for integration to be created
    integrations_page.wait_for_page_load()
    integrations_page.should_see_message(
        IntegrationTestDataFactory.success_messages["integration_created"]
    )

    # Act - Edit the integration alias
    integration_row = integrations_page.get_integration_row_by_alias(
        integration_test_data.alias
    )
    integration_row.click_edit()

    # Update alias on edit page
    edit_integration_page = EditIntegrationPage(page)
    edit_integration_page.should_be_on_edit_integration_page()

    new_alias = f"Updated Git Integration {get_random_name()}"
    edit_integration_page.update_alias(new_alias)
    edit_integration_page.save_changes()

    # Assert - Verify success with new alias
    integrations_page.wait_for_page_load()
    integrations_page.should_see_message(
        IntegrationTestDataFactory.success_messages["integration_updated"]
    )
    integrations_page.should_see_specific_integration(new_alias)
