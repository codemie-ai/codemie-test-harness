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
UI tests for Delete Integration feature.

This test suite covers deleting integrations with confirmation dialog.
"""

import pytest
from playwright.sync_api import Page

from codemie_test_harness.tests.ui.pageobject.integrations.create_integration_page import (
    CreateIntegrationPage,
)
from codemie_test_harness.tests.ui.pageobject.integrations.integrations_page import (
    IntegrationsPage,
)
from codemie_test_harness.tests.ui.pageobject.components.delete_confirmation_dialog import (
    DeleteConfirmationDialog,
)
from codemie_test_harness.tests.ui.test_data.integration_test_data import (
    IntegrationTestDataFactory,
)


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.integration
@pytest.mark.ui
@pytest.mark.prod_regression
def test_delete_integration_with_confirmation(page: Page):
    """
    Test deleting an integration with confirmation dialog.

    AC Coverage:
        - AC#1 - Scope Item 2: Delete integration with confirmation

    Prerequisites:
        - User is logged in
        - At least one Git integration exists

    Steps:
        1. Navigate to integrations page
        2. Create a test Git integration via UI
        3. Open More options menu for the integration
        4. Click Delete
        5. Verify confirmation dialog appears
        6. Confirm deletion by clicking Yes
        7. Verify success message
        8. Verify integration is removed from list
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
    integrations_page.should_not_see_message()

    # Act - Delete the integration
    integration_row = integrations_page.get_integration_row_by_alias(
        integration_test_data.alias
    )
    integration_row.click_delete()

    # Verify and confirm deletion dialog
    delete_dialog = DeleteConfirmationDialog(page)
    delete_dialog.should_be_visible()
    delete_dialog.should_have_both_buttons()
    delete_dialog.click_confirm()

    # Assert - Verify deletion success
    integrations_page.wait_for_page_load()
    integrations_page.should_see_message(
        IntegrationTestDataFactory.success_messages["integration_deleted"]
    )

    # Verify integration is no longer in the list
    integrations_page.should_not_see_integration(integration_test_data.alias)
