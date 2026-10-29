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
UI Tests for Assistant Lifecycle Operations

Tests cover:
- Deleting assistant with confirmation dialog
- Canceling assistant deletion
- Cloning/duplicating existing assistant
- Cloned assistant inherits configuration (tools and datasources)

All tests use API for preconditions (creating assistants, tools, datasources)
and UI for test actions (delete/clone operations).
"""

import pytest

from codemie_test_harness.tests.enums.tools import (
    Toolkit as ApiToolkit,
    ProjectManagementTool as ApiProjectManagementTool,
)
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    Toolkit as UiToolkit,
    ProjectManagementTool as UiProjectManagementTool,
    get_minimal_assistant_data,
)


@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
def test_delete_assistant_with_confirmation(page):
    """
    Test deleting an assistant with confirmation dialog.

    AC: User can delete an assistant via the actions menu (three-dot menu),
    and a confirmation dialog must appear before deletion is executed.
    """
    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()

    test_data = get_minimal_assistant_data()
    test_name = test_data.name

    # Create regular assistant
    create_page.fill_name(test_name)
    create_page.fill_description(test_data.description)
    create_page.fill_system_prompt(test_data.system_prompt)
    create_page.click_create()

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_name)
    assistants_page.should_see_assistant_with_name(test_name)

    # Delete assistant with confirmation
    assistants_page.delete_assistant_with_confirmation(test_name)

    # Verify assistant is deleted
    assistants_page.search_assistants(test_name)
    assistants_page.should_not_see_assistant_with_name(test_name)


@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
def test_cancel_assistant_deletion(page, assistant):
    """
    Test canceling assistant deletion.

    AC: User can cancel the deletion operation via the confirmation dialog,
    and the assistant should remain in the system.
    """
    test_assistant = assistant()

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    assistants_page.should_see_assistant_with_name(test_assistant.name)

    # Cancel deletion
    assistants_page.cancel_assistant_deletion(test_assistant.name)

    # Verify assistant is still visible
    assistants_page.search_assistants(test_assistant.name)
    assistants_page.should_see_assistant_with_name(test_assistant.name)


@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
def test_clone_existing_assistant(page, assistant):
    """
    Test cloning/duplicating an existing assistant.

    AC: User can clone an assistant via the actions menu (three-dot menu),
    creating a copy with " (Copy)" appended to the name.
    """
    test_assistant = assistant()
    assistant_name = test_assistant.name
    cloned_assistant_name = assistant_name + " CLONED"

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(assistant_name)
    assistants_page.should_see_assistant_with_name(assistant_name)

    # Clone assistant
    create_assistant_page = assistants_page.clone_assistant(assistant_name)
    create_assistant_page.fill_name(cloned_assistant_name)
    create_assistant_page.click_save()

    # Verify original assistant still exists and cloned has appeared
    assistants_page.search_assistants(assistant_name)
    assistants_page.should_see_assistant_with_name(assistant_name)
    assistants_page.should_see_assistant_with_name(cloned_assistant_name)


@pytest.mark.github
@pytest.mark.gitlab
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.jira
def test_cloned_assistant_inherits_configuration(
    page, assistant, jira_integration, code_datasource, client
):
    """
    Test that cloned assistant inherits configuration from original.

    AC: Cloned assistant should have the same tools and datasources as the original.
    """
    test_assistant = assistant(
        ApiToolkit.PROJECT_MANAGEMENT,
        ApiProjectManagementTool.JIRA,
        settings=jira_integration,
    )
    assistant_name = test_assistant.name
    cloned_assistant_name = assistant_name + " CLONED"

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(assistant_name)

    # Clone assistant
    create_assistant_page = assistants_page.clone_assistant(assistant_name)
    create_assistant_page.fill_name(cloned_assistant_name)
    create_assistant_page.click_save()

    assistants_page.search_assistants(assistant_name)

    # Verify original assistant still exists and cloned has appeared
    assistants_page.should_see_assistant_with_name(assistant_name)
    view_page = assistants_page.open_assistant_details(test_assistant.name)
    view_page.should_see_toolkit_tools(
        UiToolkit.PROJECT_MANAGEMENT.value,
        [f"{UiProjectManagementTool.GENERIC_JIRA.value} tool"],
    )

    assistants_page.navigate_to()
    assistants_page.should_see_assistant_with_name(assistant_name)
    view_page = assistants_page.open_assistant_details(cloned_assistant_name)
    view_page.should_see_toolkit_tools(
        UiToolkit.PROJECT_MANAGEMENT.value,
        [f"{UiProjectManagementTool.GENERIC_JIRA.value} tool"],
    )
