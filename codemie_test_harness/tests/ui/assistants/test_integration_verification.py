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
UI tests for Missing Integrations validation dialog on Assistant create page.

Tests verify that when a user creates an assistant with a tool requiring
an integration that is not configured, the Missing Integrations validation
dialog is displayed with all expected elements and actions.

"""

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)
from codemie_test_harness.tests.ui.pageobject.components.missing_integrations_validation_dialog import (
    MissingIntegrationsValidationDialog,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import Section
from codemie_test_harness.tests.ui.test_data.integration_verification_test_data import (
    get_integration_verification_assistant_data,
)


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
def test_missing_integrations_dialog_displayed(page):
    """
    Test that Missing Integrations validation dialog is shown when saving an assistant
    with Xray Get Tests tool when Xray integration is not configured.

    Steps:
    1. Open assistant create page
    2. Fill mandatory fields (name, description, system instructions)
    3. Select Quality Assurance -> Xray Get Tests tool
    4. Attempt to save the assistant
    5. Verify Missing Integrations dialog is displayed
    6. Verify dialog contains all expected elements:
       - Title "Missing Integrations"
       - Explanatory message about tools requiring integrations
       - Integration type section (Xray)
       - Required capability item (Quality Assurance)
       - Tool entry (Xray Get Tests)
       - Four action buttons: Add Integration, Cancel, Skip Validation & Save, Validate & Save

    Expected result:
    - Missing Integrations dialog is displayed with all expected elements
    - All four action buttons are visible and enabled
    """
    test_data = get_integration_verification_assistant_data()
    create_page = CreateEditAssistantPage(page)
    validation_dialog = MissingIntegrationsValidationDialog(page)

    create_page.navigate_to()
    create_page.should_be_on_create_assistant_page()

    create_page.fill_name(test_data.name)
    create_page.fill_description(test_data.description)
    create_page.fill_system_prompt(test_data.system_instructions)

    create_page.tools.select_section(Section.AVAILABLE_TOOLS.value)
    create_page.tools.select_toolkit(
        Section.AVAILABLE_TOOLS.value, test_data.toolkit_category
    )
    create_page.tools.select_tool(test_data.tool_name)

    create_page.click_save()

    validation_dialog.should_be_visible()
    validation_dialog.should_have_all_expected_elements()
