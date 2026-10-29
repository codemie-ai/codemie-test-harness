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
UI Test for Sensitive Prompt Variable Functionality

Tests the bug where sensitive prompt variable values
are not saved correctly when is_sensitive=true is set during assistant creation.

Test verifies:
- Creating an assistant with Jira tool via API
- Adding a sensitive prompt variable via UI
- Updating system prompt to reference the variable
- Saving the assistant
- Verifying the assistant uses the real variable value (not "********") at runtime
"""

import pytest

from codemie_test_harness.tests.enums.tools import Toolkit, ProjectManagementTool
from codemie_test_harness.tests.test_data.pm_tools_test_data import (
    RESPONSE_FOR_JIRA_TOOL,
)
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.jira
def test_sensitive_prompt_variable_value_persisted_correctly(
    page,
    assistant,
    jira_integration,
    assistant_utils,
    similarity_check,
    jira_seed_issue,
    seeded,
):
    """
    Test that sensitive prompt variable values are saved and used correctly.

    Verifies the fix where sensitive variable values were being
    replaced with "********" instead of being encrypted and stored properly.

    Steps:
    1. Create assistant with Jira generic tool via API
    2. Open assistant edit page on UI
    3. Add "ticket_id" prompt variable with the seed issue key and mark it as sensitive
    4. Add System Prompt: "Work with Jira ticket {{ticket_id}}"
    5. Save the assistant
    6. Ask assistant via API: "What is the ticket title?"
    7. Assert answer contains expected ticket information (not "********")
    """
    # Step 1: Create assistant with Jira generic tool via API
    test_assistant = assistant(
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.JIRA,
        settings=jira_integration,
    )

    # Step 2: Open assistant edit page on UI
    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    edit_page = assistants_page.click_assistant_edit(test_assistant.name)

    # Step 3: Add "ticket_id" prompt variable with the seed issue key and mark it as sensitive
    edit_page.click_manage_prompt_vars()
    edit_page.add_prompt_variable(
        key="ticket_id",
        default_value=jira_seed_issue.key,
        description="Jira ticket ID for testing sensitive variables",
        is_sensitive=True,
    )
    edit_page.close_manage_prompt_vars_modal()

    # Step 4: Add System Prompt: "Work with Jira ticket {{ticket_id}}"
    edit_page.fill_system_prompt("Work with Jira ticket {{ticket_id}}")

    # Step 5: Save the assistant
    edit_page.click_save()

    # Step 6: Ask assistant via API: "What is the ticket title?"
    response = assistant_utils.ask_assistant(
        test_assistant,
        "What is the ticket title?",
        minimal_response=False,
    )

    # Step 7: Assert answer contains expected ticket information
    # The assistant should use the real ticket ID (the seed issue key) not the mask ("********")
    # Expected behavior: Assistant retrieves the seed issue ticket from Jira and responds with its title
    similarity_check.check_similarity(
        response,
        seeded(RESPONSE_FOR_JIRA_TOOL),
        similarity_rank=80,
        assistant_name=test_assistant.name,
    )
