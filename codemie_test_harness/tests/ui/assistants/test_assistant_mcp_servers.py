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
UI Tests for Assistant MCP Server Configuration

Tests cover:
- Configuring MCP server on assistant
- MCP server configuration panel visibility
- Removing MCP server configuration
"""

import pytest
from hamcrest import assert_that, equal_to, is_not, empty

from codemie_test_harness.tests.test_data.mcp_server_test_data import FETCH_MCP_SERVER
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.mcp
def test_mcp_server_configuration_panel_visibility(page, assistant):
    """
    Test that MCP server configuration panel is visible and accessible.

    AC: MCP Servers accordion is visible in Tools & Integrations section
    and can be expanded to show available MCP servers.
    """
    test_assistant = assistant()

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)

    edit_page = assistants_page.click_assistant_edit(test_assistant.name)
    edit_page.tools.should_have_tools_integrations_section_visible()
    edit_page.mcp_servers.should_have_mcp_servers_accordion_visible()
    edit_page.mcp_servers.expand_mcp_servers_accordion()

    edit_page.mcp_servers.should_have_mcp_setup_buttons_visible()


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.mcp
def test_add_mcp_server_from_browse_catalog(page, assistant):
    """
    Test adding an MCP server from the browse catalog.

    AC: User can browse the MCP catalog, select a server (e.g., sqlite),
    configure its settings, and add it to the assistant.
    """
    test_assistant = assistant()
    mcp_tool = FETCH_MCP_SERVER.name

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)

    edit_page = assistants_page.click_assistant_edit(test_assistant.name)
    edit_page.mcp_servers.should_have_mcp_servers_accordion_visible()
    edit_page.mcp_servers.expand_mcp_servers_accordion()
    edit_page.mcp_servers.click_mcp_browse_catalog()
    edit_page.mcp_servers.add_mcp_server_from_catalog(mcp_tool)

    # Configure the MCP server
    edit_page.mcp_servers.fill_mcp_config_description(FETCH_MCP_SERVER.description)
    edit_page.mcp_servers.click_mcp_config_next()
    edit_page.mcp_servers.select_use_all_tools_checkbox()
    edit_page.mcp_servers.click_mcp_tools_save()
    edit_page.click_save()

    # Verify the MCP server was added
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    view_page = assistants_page.click_assistant_view(test_assistant.name)
    view_page.should_see_toolkit_contains("MCP", mcp_tool)


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.mcp
def test_add_mcp_server_using_manual_setup(page, assistant):
    """
    Test adding an MCP server using manual setup.

    AC: User can manually configure an MCP server by providing
    name, description, and configuration details, then add it to the assistant.
    """
    test_assistant = assistant()

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)

    edit_page = assistants_page.click_assistant_edit(test_assistant.name)
    edit_page.mcp_servers.should_have_mcp_servers_accordion_visible()
    edit_page.mcp_servers.expand_mcp_servers_accordion()

    # Click Manual Setup button
    edit_page.mcp_servers.click_mcp_manual_setup()

    # Configure the MCP server manually - fill basic information
    edit_page.mcp_servers.fill_mcp_config_name(FETCH_MCP_SERVER.name)
    edit_page.mcp_servers.fill_mcp_config_description(FETCH_MCP_SERVER.description)
    edit_page.mcp_servers.fill_mcp_config_json(
        FETCH_MCP_SERVER.config.model_dump_json(indent=2)
    )
    edit_page.mcp_servers.click_mcp_config_next()

    # Step 2: Select Tools - Ensure all tools are selected (default)
    edit_page.mcp_servers.select_use_all_tools_checkbox()

    # Save the MCP server configuration
    edit_page.mcp_servers.click_mcp_tools_add()

    # Save the assistant
    edit_page.click_save()

    # Verify the MCP server was added
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    view_page = assistants_page.click_assistant_view(test_assistant.name)
    view_page.should_see_toolkit_contains("MCP", FETCH_MCP_SERVER.name)


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.mcp
def test_remove_mcp_server_from_assistant(page, assistant):
    """
    Test removing an MCP server from an assistant via UI.

    AC: User can add an MCP server to the assistant, then remove it and save the changes.
    """
    test_assistant = assistant(mcp_server=FETCH_MCP_SERVER)
    mcp_tool = FETCH_MCP_SERVER.name

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)

    # Verify MCP server was added via API
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    edit_page = assistants_page.click_assistant_edit(test_assistant.name)

    edit_page.mcp_servers.should_have_mcp_servers_accordion_visible()
    edit_page.mcp_servers.expand_mcp_servers_accordion()
    edit_page.mcp_servers.should_have_mcp_server_checked(mcp_tool)

    # Remove the MCP server
    edit_page.mcp_servers.unselect_mcp_server(mcp_tool)

    # Save the assistant
    edit_page.click_save()

    # Verify the MCP server was removed
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    view_page = assistants_page.click_assistant_view(test_assistant.name)
    view_page.should_see_tool_not_present("MCP", mcp_tool)


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.mcp
def test_add_global_mcp_from_catalog_preserves_inheritance(page, assistant, client):
    """TC-001: Add global MCP from Browse Catalog in default mode preserves inheritance.

    When a user adds an MCP server from the Browse Catalog, the
    Step 1 dialog must default to Global mode (use_custom_config=False), showing
    the catalog config in a read-only textarea. Saving the assistant must persist
    use_custom_config=False so the assistant inherits the catalog config.

    Uses the existing system catalog entry "EPAM Radar" which is always
    present in the catalog and has been confirmed in the live UI.

    ACs verified:
    - AC1: Configure dialog defaults to Global mode (aria-pressed="true" on Global button)
    - AC2: Config textarea is disabled in Global mode (read-only, inheriting catalog)
    - AC3: After saving, the MCP server entry has use_custom_config=False
    - AC4: The MCP server appears in the assistant's toolkit
    """
    test_assistant = assistant()
    mcp_name = "EPAM Radar"

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)

    edit_page = assistants_page.click_assistant_edit(test_assistant.name)
    edit_page.mcp_servers.should_have_mcp_servers_accordion_visible()
    edit_page.mcp_servers.expand_mcp_servers_accordion()

    # Open Browse Catalog and add the system MCP entry
    edit_page.mcp_servers.click_mcp_browse_catalog()
    edit_page.mcp_servers.add_mcp_server_from_catalog(mcp_name)

    # AC1 + AC2: Step 1 dialog must default to Global mode with disabled textarea
    edit_page.mcp_servers.should_have_global_mode_selected()

    # Proceed through Step 1 (no edits — keep Global mode)
    edit_page.mcp_servers.click_mcp_config_next()

    # Step 2: save without requiring a specific checkbox
    # (some catalog entries like EPAM Radar handle tool selection automatically)
    edit_page.mcp_servers.wait_for_mcp_tools_step()
    edit_page.mcp_servers.click_mcp_tools_save()

    # Save the assistant
    edit_page.click_save()

    # AC4: Verify the MCP server appears in the assistant's toolkit
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    view_page = assistants_page.click_assistant_view(test_assistant.name)
    view_page.should_see_toolkit_contains("MCP", mcp_name)

    # AC3: Verify use_custom_config=False via API (Global mode preserved after save)
    saved_assistant = client.assistants.get(assistant_id=test_assistant.id)
    mcp_entries = [s for s in (saved_assistant.mcp_servers or []) if s.name == mcp_name]
    assert_that(
        mcp_entries,
        is_not(empty()),
        f"MCP server '{mcp_name}' not found in saved assistant",
    )
    assert_that(
        mcp_entries[0].use_custom_config,
        equal_to(False),
        f"Expected use_custom_config=False (Global mode) but got "
        f"use_custom_config={mcp_entries[0].use_custom_config}",
    )
