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

"""UI tests for the datasource default tools in the assistant form.

A knowledge base datasource adds the Search Knowledge Base tool; the form lists it
under Codebase Tools, checked, and lets the author deselect it. Preconditions are
created through the API; the form is driven through the UI.
"""

import pytest
from hamcrest import assert_that, empty, equal_to

from codemie_test_harness.tests.test_data.default_datasource_tools_test_data import (
    SEARCH_KB,
)
from codemie_test_harness.tests.test_data.file_test_data import file_test_data
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    AssistantPopUpMessages,
    Section,
)
from codemie_test_harness.tests.ui.test_data.default_datasource_tools_ui_test_data import (
    CODEBASE_TOOLS_GROUP,
    DEFAULT_TOOL_NAMES,
    SEARCH_KB_LABEL,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.constants import FILES_PATH


@pytest.fixture
def second_file_datasource(datasource_utils, default_embedding_llm):
    """A second knowledge base datasource, under its own name, removed after the test."""
    file_name = file_test_data[2][0]
    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        description=f"[Autotest] second {file_name} datasource",
        files=[str(FILES_PATH / file_name)],
        embeddings_model=default_embedding_llm.base_name,
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.mark.assistant
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.prod_regression
def test_assistant_form_lists_search_kb_selected_after_attaching_kb_datasource(
    page, assistant, file_datasource
):
    # @case deselect-default-datasource-tools_TC_006
    test_assistant = assistant()

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    edit_page = assistants_page.click_assistant_edit(test_assistant.name)

    edit_page.attach_datasource_from_dropdown(file_datasource.name)
    edit_page.should_have_datasource_attached(file_datasource.name)
    edit_page.tools.select_section(Section.AVAILABLE_TOOLS.value)
    edit_page.tools.open_toolkit(CODEBASE_TOOLS_GROUP)

    edit_page.tools.should_have_tool_checked(SEARCH_KB_LABEL)


@pytest.mark.assistant
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.prod_regression
def test_deselected_search_kb_stays_deselected_after_save_and_new_kb_datasource(
    page,
    assistant_factory,
    assistant_utils,
    kb_context,
    file_datasource,
    second_file_datasource,
):
    # @case deselect-default-datasource-tools_TC_007
    test_assistant = assistant_factory.create(context=[kb_context(file_datasource)])

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    edit_page = assistants_page.click_assistant_edit(test_assistant.name)

    edit_page.tools.select_section(Section.AVAILABLE_TOOLS.value)
    edit_page.tools.open_toolkit(CODEBASE_TOOLS_GROUP)
    edit_page.tools.should_have_tool_checked(SEARCH_KB_LABEL)
    edit_page.tools.deselect_tool(SEARCH_KB_LABEL)
    edit_page.tools.should_have_tool_unchecked(SEARCH_KB_LABEL)
    edit_page.click_save()
    assistants_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )

    saved = assistant_utils.get_assistant_by_id(test_assistant.id)
    assert_that(saved.disabled_context_tools, equal_to([SEARCH_KB]))
    default_tools_in_toolkits = [
        tool.name
        for kit in saved.toolkits
        for tool in kit.tools
        if tool.name in DEFAULT_TOOL_NAMES
    ]
    assert_that(
        default_tools_in_toolkits,
        empty(),
        "Default tools must not be stored in toolkits, only in disabled_context_tools",
    )

    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    edit_page = assistants_page.click_assistant_edit(test_assistant.name)
    edit_page.attach_datasource_from_dropdown(second_file_datasource.name)
    edit_page.tools.select_section(Section.AVAILABLE_TOOLS.value)
    edit_page.tools.open_toolkit(CODEBASE_TOOLS_GROUP)

    edit_page.tools.should_have_tool_unchecked(SEARCH_KB_LABEL)
