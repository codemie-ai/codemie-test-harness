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
UI tests for how the chat sidebar "Folders" section shows CLI agents.

A CLI agent's chats appear in one entry per agent (``import:<kind>``); a registered folder
named after the agent must not add a second, empty entry. Folders and chats are created
through the API (imported chats with the agent's ``X-CodeMie-Client`` header), every name
besides the agent folder names is random, and everything is removed in fixture teardown.

The agent folder names are fixed by the contract under test and the account is shared, so
all tests of this module run on one xdist worker (``--dist=loadgroup``).
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.chats.chat_folders_section import (
    ChatFoldersSection,
    custom_folder_key,
)
from codemie_test_harness.tests.ui.test_data.cli_agent_folders_test_data import (
    AGENT_NAMED_CUSTOM_FOLDERS,
    CLAUDE,
    COPILOT_CLI,
    COPILOT_FOLDER_NAMES,
    EMPTY_AGENT_FOLDER_NAMES,
    GEMINI,
    MOVE_AGENTS,
    SYNCED_AGENTS,
)
from codemie_test_harness.tests.ui.utils.chat_folder_setup import ChatFolderSetup


@pytest.fixture
def folder_setup(conversation_utils):
    """Creates folders and chats for one test and deletes them afterwards."""
    setup = ChatFolderSetup(conversation_utils)
    yield setup
    setup.cleanup()


@pytest.mark.chat
@pytest.mark.xdist_group("cli_agent_folders")
@pytest.mark.parametrize("folder_name", EMPTY_AGENT_FOLDER_NAMES)
@pytest.mark.ui
def test_empty_agent_named_folder_is_not_listed(
    page, folder_setup, create_new_conversation, folder_name
):
    # @case show-each-cli-agent-once_TC_001
    control_folder = folder_setup.register_random_folder()
    folder_setup.register_folder(folder_name)

    folders = ChatFoldersSection(page)
    folders.open_chat(create_new_conversation.get("id"))
    folders.open_folders_section()

    # The empty control folder proves the registered folders have rendered.
    folders.should_list_folder(custom_folder_key(control_folder))
    folders.should_not_list_folder(custom_folder_key(folder_name))


@pytest.mark.chat
@pytest.mark.xdist_group("cli_agent_folders")
@pytest.mark.ui
def test_empty_custom_folder_with_non_agent_name_stays_listed(
    page, folder_setup, create_new_conversation
):
    # @case show-each-cli-agent-once_TC_002
    folder_name = folder_setup.register_random_folder()

    folders = ChatFoldersSection(page)
    folders.open_chat(create_new_conversation.get("id"))
    folders.open_folders_section()

    folders.should_list_folder(custom_folder_key(folder_name))


@pytest.mark.chat
@pytest.mark.xdist_group("cli_agent_folders")
@pytest.mark.ui
def test_regular_chat_stays_in_its_custom_folder(page, folder_setup):
    # @case show-each-cli-agent-once_TC_003
    folder_name = folder_setup.register_random_folder()
    chat_id = folder_setup.create_chat(folder_name)

    folders = ChatFoldersSection(page)
    folders.open_chat(chat_id)
    folders.open_folders_section()

    folders.should_contain_chat(custom_folder_key(folder_name), chat_id)


@pytest.mark.chat
@pytest.mark.xdist_group("cli_agent_folders")
@pytest.mark.parametrize("folder_name, agent_group_key", AGENT_NAMED_CUSTOM_FOLDERS)
@pytest.mark.ui
def test_regular_chat_stays_in_agent_named_custom_folder(
    page, folder_setup, folder_name, agent_group_key
):
    # @case show-each-cli-agent-once_TC_003
    folder_setup.register_folder(folder_name)
    chat_id = folder_setup.create_chat(folder_name)

    folders = ChatFoldersSection(page)
    folders.open_chat(chat_id)
    folders.open_folders_section()

    folders.should_contain_chat(custom_folder_key(folder_name), chat_id)
    folders.should_not_contain_chat(agent_group_key, chat_id)


@pytest.mark.chat
@pytest.mark.xdist_group("cli_agent_folders")
@pytest.mark.ui
def test_synced_gemini_chats_appear_in_one_gemini_entry(page, folder_setup):
    # @case show-each-cli-agent-once_TC_004
    first_chat_id = folder_setup.import_chat(GEMINI)
    second_chat_id = folder_setup.import_chat(GEMINI)

    folders = ChatFoldersSection(page)
    folders.open_chat(first_chat_id)
    folders.open_folders_section()

    folders.should_list_single_entry(GEMINI.label, GEMINI.group_key)
    folders.should_contain_chat(GEMINI.group_key, first_chat_id)
    folders.should_contain_chat(GEMINI.group_key, second_chat_id)
    folders.should_not_list_folder(custom_folder_key(GEMINI.folder))


@pytest.mark.chat
@pytest.mark.xdist_group("cli_agent_folders")
@pytest.mark.parametrize("agent", SYNCED_AGENTS)
@pytest.mark.ui
def test_synced_agent_chat_appears_in_one_entry(page, folder_setup, agent):
    # @case show-each-cli-agent-once_TC_005
    chat_id = folder_setup.import_chat(agent)

    folders = ChatFoldersSection(page)
    folders.open_chat(chat_id)
    folders.open_folders_section()

    folders.should_list_single_entry(agent.label, agent.group_key)
    folders.should_contain_chat(agent.group_key, chat_id)
    folders.should_not_list_folder(custom_folder_key(agent.folder))


@pytest.mark.chat
@pytest.mark.xdist_group("cli_agent_folders")
@pytest.mark.ui
def test_synced_claude_chat_appears_in_claude_cli_entry(page, folder_setup):
    # @case show-each-cli-agent-once_TC_006
    chat_id = folder_setup.import_chat(CLAUDE)

    folders = ChatFoldersSection(page)
    folders.open_chat(chat_id)
    folders.open_folders_section()

    folders.should_list_single_entry(CLAUDE.label, CLAUDE.group_key)
    folders.should_contain_chat(CLAUDE.group_key, chat_id)
    folders.should_not_list_folder(custom_folder_key(CLAUDE.folder))


@pytest.mark.chat
@pytest.mark.xdist_group("cli_agent_folders")
@pytest.mark.parametrize("folder_name", COPILOT_FOLDER_NAMES)
@pytest.mark.ui
def test_synced_copilot_chat_appears_in_one_entry_for_any_folder_spelling(
    page, folder_setup, folder_name
):
    # @case show-each-cli-agent-once_TC_007
    chat_id = folder_setup.import_chat(COPILOT_CLI, folder_name=folder_name)

    folders = ChatFoldersSection(page)
    folders.open_chat(chat_id)
    folders.open_folders_section()

    folders.should_list_single_entry(COPILOT_CLI.label, COPILOT_CLI.group_key)
    folders.should_contain_chat(COPILOT_CLI.group_key, chat_id)
    folders.should_not_list_folder(custom_folder_key(folder_name))


@pytest.mark.chat
@pytest.mark.xdist_group("cli_agent_folders")
@pytest.mark.parametrize("agent", MOVE_AGENTS)
@pytest.mark.ui
def test_imported_chat_has_no_folder_action_and_stays_in_agent_entry(
    page, folder_setup, agent
):
    # @case show-each-cli-agent-once_TC_008
    custom_folder = folder_setup.register_random_folder()
    chat_id = folder_setup.import_chat(agent)

    folders = ChatFoldersSection(page)
    folders.open_chat(chat_id)
    folders.open_folders_section()

    folders.open_chat_menu(agent.group_key, chat_id)
    # The other items prove the menu has rendered before the folder item's absence counts.
    folders.should_offer_chat_menu_items("Pin", "Rename", "Delete")
    folders.should_not_offer_move_to_folder_item()
    folders.close_chat_menu()

    folders.should_list_single_entry(agent.label, agent.group_key)
    folders.should_contain_chat(agent.group_key, chat_id)
    folders.should_not_list_folder(custom_folder_key(agent.folder))
    folders.should_not_contain_chat(custom_folder_key(custom_folder), chat_id)


@pytest.mark.chat
@pytest.mark.xdist_group("cli_agent_folders")
@pytest.mark.parametrize("agent", MOVE_AGENTS)
@pytest.mark.ui
def test_move_chat_popup_does_not_offer_agent_folder_of_imported_chats(
    page, folder_setup, agent
):
    # @case show-each-cli-agent-once_TC_010
    chat_folder = folder_setup.register_random_folder()
    control_folder = folder_setup.register_random_folder()
    regular_chat_id = folder_setup.create_chat(chat_folder)
    folder_setup.import_chat(agent)

    folders = ChatFoldersSection(page)
    folders.open_chat(regular_chat_id)
    folders.open_folders_section()
    folders.open_move_chat_popup(custom_folder_key(chat_folder), regular_chat_id)

    # The control folder proves the popup lists folders at all.
    folders.search_move_popup_folder(control_folder)
    folders.should_offer_move_target(control_folder)
    folders.search_move_popup_folder(agent.folder)
    # The control folder drops out once the new search ran; only then does absence count.
    folders.should_have_refreshed_move_suggestions(control_folder)
    folders.should_not_offer_move_target(agent.folder)
