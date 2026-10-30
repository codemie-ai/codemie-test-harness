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
UI Tests for Assistant Datasource Attachment Features

Tests cover:
- Attaching Code datasources to assistants
- Attaching Jira datasources to assistants
- Attaching multiple datasources simultaneously
- Removing attached datasources

All tests use API for preconditions (creating assistant and datasources)
and UI for test actions (attaching/removing).
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    AssistantPopUpMessages,
)


@pytest.mark.github
@pytest.mark.gitlab
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_attach_code_datasource_to_assistant(page, assistant, code_datasource):
    """
    Test attaching a Code datasource to an assistant via UI.

    AC: User can select and attach a Code datasource from the Context & Data Sources section.
    """
    test_assistant = assistant()
    test_datasource = code_datasource

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)

    edit_page = assistants_page.click_assistant_edit(test_assistant.name)
    edit_page.should_have_datasource_context()
    edit_page.attach_datasource_from_dropdown(test_datasource.name)
    edit_page.click_save()
    assistants_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )

    view_page = assistants_page.open_assistant_details(test_assistant.name)
    view_page.should_have_datasource_attached(test_datasource.name)


@pytest.mark.github
@pytest.mark.gitlab
@pytest.mark.jira
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_attach_multiple_datasources_to_assistant(
    page, assistant, code_datasource, jira_datasource
):
    """
    Test attaching multiple datasources (Code + Jira) to an assistant via UI.

    AC: User can select and attach multiple datasources simultaneously from the multiselect dropdown.
    """
    test_assistant = assistant()
    code_ds = code_datasource
    jira_ds = jira_datasource

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)

    edit_page = assistants_page.click_assistant_edit(test_assistant.name)
    edit_page.should_have_datasource_context()
    edit_page.attach_datasource_from_dropdown(code_ds.name)
    edit_page.attach_datasource_from_dropdown(jira_ds.name)
    edit_page.click_save()
    assistants_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )

    view_page = assistants_page.open_assistant_details(test_assistant.name)
    view_page.should_have_datasource_attached(code_ds.name)
    view_page.should_have_datasource_attached(jira_ds.name)


@pytest.mark.github
@pytest.mark.gitlab
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_remove_attached_datasource_from_assistant(page, assistant, code_datasource):
    """
    Test removing an attached datasource from an assistant via UI.

    AC: User can remove a previously attached datasource from the assistant configuration.
    """
    test_assistant = assistant()
    test_datasource = code_datasource

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)

    edit_page = assistants_page.click_assistant_edit(test_assistant.name)
    edit_page.attach_datasource_from_dropdown(test_datasource.name)
    edit_page.click_save()
    assistants_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )

    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    edit_page = assistants_page.click_assistant_edit(test_assistant.name)
    edit_page.should_have_datasource_attached(test_datasource.name)
    edit_page.remove_datasource_from_dropdown(test_datasource.name)
    edit_page.click_save()
    assistants_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )

    view_page = assistants_page.open_assistant_details(test_assistant.name)
    view_page.should_see_no_datasources_message()
