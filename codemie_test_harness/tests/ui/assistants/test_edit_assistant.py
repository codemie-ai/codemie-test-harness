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

import pytest

from codemie_test_harness.tests import TEST_USER, PROJECT
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    Section,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    TOOLKIT_TOOLS,
    AssistantPopUpMessages,
    AssistantValidationErrors,
    CodebaseTool,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_assistant_page_elements_visibility(page, assistant):
    """
    Test all main elements are visible on Edit Assistant page—fields, toolkits, checkboxes, etc.
    """
    assistant_page = AssistantsPage(page)
    assistant = assistant()

    assistant_page.navigate_to()
    assistant_page.search_assistants(assistant.name)
    edit_page = assistant_page.click_assistant_edit(assistant.name)

    edit_page.should_have_pinned_title(assistant.name)
    edit_page.should_have_all_form_fields_visible()
    edit_page.should_have_top_p_and_temperature()
    edit_page.should_have_datasource_context()
    edit_page.should_have_sub_assistants_context()
    edit_page.should_have_categories_visible()

    if Section.AVAILABLE_TOOLS in TOOLKIT_TOOLS:
        content = TOOLKIT_TOOLS[Section.AVAILABLE_TOOLS]
        edit_page.tools.select_section(Section.AVAILABLE_TOOLS.value)
        for toolkit, tools in content.items():
            edit_page.tools.select_toolkit(Section.AVAILABLE_TOOLS.value, toolkit.value)
            for tool in tools:
                edit_page.tools.should_be_visible_tool(tool.value)

    if Section.EXTERNAL_TOOLS in TOOLKIT_TOOLS:
        edit_page.tools.select_section(Section.EXTERNAL_TOOLS.value)

    if Section.MCP_SERVERS in TOOLKIT_TOOLS:
        edit_page.mcp_servers.expand_mcp_servers_accordion()
        actions = TOOLKIT_TOOLS[Section.MCP_SERVERS]
        for action in actions:
            edit_page.mcp_servers.should_have_mcp_setup_buttons_visible()


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_assistant_form_field_interactions(page, assistant):
    """
    Test interacting with all editable form fields.
    """
    EDITED = " EDITED"
    assistant_page = AssistantsPage(page)
    assistant = assistant()

    assistant_page.navigate_to()
    assistant_page.search_assistants(assistant.name)
    edit_page = assistant_page.click_assistant_edit(assistant.name)

    edit_page.should_have_pinned_title(assistant.name)
    edit_page.fill_name(assistant.name + EDITED)
    edit_page.should_have_name_value(assistant.name + EDITED)
    edit_page.fill_description(assistant.description + EDITED)
    edit_page.should_have_description_value(assistant.description + EDITED)

    edit_page.toggle_shared_assistant(True)
    edit_page.should_have_shared_checked()
    edit_page.toggle_shared_assistant(False)
    edit_page.should_have_shared_unchecked()

    edit_page.fill_temperature("0.5")
    edit_page.fill_top_p("0.5")
    edit_page.should_have_top_p_and_temperature_value("0.5", "0.5")
    edit_page.click_save()
    assistant_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )
    assistant_page.should_see_assistant_with_name(assistant.name + EDITED)

    view_page = assistant_page.click_assistant_view(assistant.name + EDITED)
    view_page.should_have_pinned_title(assistant.name + EDITED)
    view_page.should_have_all_form_fields_visible(
        name=assistant.name + EDITED,
        author=TEST_USER,
        description=assistant.description + EDITED,
    )
    view_page.should_have_overview_form_fields_visible(
        project=PROJECT, status="Not shared", assistant_id=assistant.id
    )
    view_page.should_have_access_links_form_fields_visible(
        assistant_name=assistant.name
    )
    view_page.should_have_configuration_form_fields_visible(
        temperature="0.5", top_p="0.5"
    )


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_assistant_tools_interactions(
    page, assistant, resolver_runtime_capabilities
):
    """
    Test interacting with all tools in assistant.
    """
    assistant_page = AssistantsPage(page)
    assistant = assistant()

    # Codebase Tools other than Sonar require code indexing; when the capability
    # is missing or disabled, the UI only shows Sonar for that toolkit.
    code_indexing_enabled = bool(
        resolver_runtime_capabilities.get("features:codeIndexing")
    )
    unavailable_tools = (
        set()
        if code_indexing_enabled
        else {
            CodebaseTool.GET_REPOSITORY_FILE_TREE_V2,
            CodebaseTool.SEARCH_CODE_REPO_V2,
            CodebaseTool.READ_FILES_CONTENT,
            CodebaseTool.READ_FILES_CONTENT_SUMMARY,
            CodebaseTool.SEARCH_CODE_REPO_BY_PATH,
        }
    )

    assistant_page.navigate_to()
    assistant_page.search_assistants(assistant.name)
    edit_page = assistant_page.click_assistant_edit(assistant.name)

    for section, content in TOOLKIT_TOOLS.items():
        if section == Section.AVAILABLE_TOOLS:
            edit_page.tools.select_section(section.value)
            for toolkit, tools in content.items():
                edit_page.tools.select_toolkit(section.value, toolkit.value)
                for tool in tools:
                    if tool in unavailable_tools:
                        continue
                    edit_page.tools.select_tool(tool.value)

    edit_page.click_save()
    edit_page.click_save_with_validation_skip()
    assistant_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )

    view_page = assistant_page.click_assistant_view(assistant.name)
    if Section.AVAILABLE_TOOLS in TOOLKIT_TOOLS:
        content = TOOLKIT_TOOLS[Section.AVAILABLE_TOOLS]
        for toolkit, tools in content.items():
            toolkit_label = toolkit.value
            view_page.should_see_toolkit_visible(toolkit_label)
            for tool in tools:
                if tool in unavailable_tools:
                    continue
                view_page.should_see_toolkit_contains(toolkit_label, tool.value)


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_assistant_incorrect_form(page, assistant):
    """
    Test interacting with incorrect data.
    """
    assistant_page = AssistantsPage(page)
    assistant = assistant()

    assistant_page.navigate_to()
    assistant_page.search_assistants(assistant.name)
    edit_page = assistant_page.click_assistant_edit(assistant.name)

    edit_page.fill_name("")
    edit_page.should_have_name_error_textarea(
        AssistantValidationErrors.NAME_REQUIRED.value
    )
    edit_page.fill_name(get_random_name())

    edit_page.fill_icon_url(get_random_name())
    edit_page.should_have_icon_error_textarea(
        AssistantValidationErrors.ICON_URL_NOT_VALID.value
    )
    edit_page.fill_icon_url("")

    edit_page.fill_description("")
    edit_page.should_have_description_error_textarea(
        AssistantValidationErrors.DESCRIPTION_REQUIRED.value
    )
    edit_page.fill_description(get_random_name())

    edit_page.fill_system_prompt("")
    edit_page.should_have_system_prompt_error_textarea(
        AssistantValidationErrors.SYSTEM_PROMPT_REQUIRED.value
    )
    edit_page.fill_system_prompt(get_random_name())

    edit_page.fill_temperature("3")
    edit_page.should_have_temperature_error_textarea(
        AssistantValidationErrors.TEMPERATURE_NOT_VALID.value
    )
    edit_page.fill_temperature("1")

    edit_page.fill_top_p("2")
    edit_page.should_have_top_p_error_textarea(
        AssistantValidationErrors.TOP_P_NOT_VALID.value
    )
    edit_page.fill_top_p("1")

    edit_page.click_save()
    assistant_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )
