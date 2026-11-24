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

"""UI tests: files an MCP server exports show as downloadable chips in the chat.

Covers:
  TC_002  An exported file shows as a chip with its name and MIME type, downloads
          under its name, and is listed again after a reload
  TC_004  A file that is missing or empty produces no chip and no filesystem link

The export runs through the API (an assistant with the opted-in filesystem MCP
server, or the shell one for an xlsx); the tests then open the saved chat in the browser.
The filesystem server writes text only, so a csv file checks its chip, and a shell
MCP server running python3 writes the xlsx.
"""

import pytest
from hamcrest import assert_that, empty, is_not
from requests import HTTPError

from codemie_sdk.models.conversation import ConversationCreateRequest
from codemie_test_harness.tests.enums.tools import McpServerFilesystem
from codemie_test_harness.tests.test_data.mcp_export_files_test_data import (
    EXPORT_WITHOUT_LINKS_SYSTEM_PROMPT,
    SHELL_MCP_SERVER,
    build_csv_file,
    build_xlsx_file,
    export_empty_file_prompt,
    export_missing_file_prompt,
    export_prompt,
    shell_export_prompt,
)
from codemie_test_harness.tests.test_data.mcp_server_test_data import (
    FILESYSTEM_MCP_SERVER,
)
from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage


@pytest.fixture
def export_chat(client, assistant, assistant_utils):
    """Factory ``(*prompts, mcp_server=filesystem) -> chat id``: a new conversation with
    an assistant that has an opted-in MCP server, in which each prompt is asked through
    the API.

    The conversation is deleted on teardown, also when a prompt fails.
    """
    created_ids = []

    def _ask(*prompts: str, mcp_server=FILESYSTEM_MCP_SERVER) -> str:
        exporter = assistant(
            mcp_server=mcp_server,
            system_prompt=EXPORT_WITHOUT_LINKS_SYSTEM_PROMPT,
        )
        conversation = client.conversations.create(
            ConversationCreateRequest(initial_assistant_id=exporter.id, folder="")
        )
        chat_id = conversation.get("id")
        created_ids.append(chat_id)
        for prompt in prompts:
            assistant_utils.ask_assistant(exporter, prompt, conversation_id=chat_id)
        return chat_id

    yield _ask

    for chat_id in created_ids:
        try:
            client.conversations.delete(chat_id)
        except HTTPError:
            pass


def _assistant_items(history) -> list:
    return [item for item in history if item.role.lower() == "assistant"]


def _filesystem_tool_calls(history) -> list:
    """Names of the filesystem MCP server tools the assistant turns called, failed
    calls included. A tool card is named after its tool, e.g. "Write File"."""
    tool_names = {tool.value.replace("_", " ") for tool in McpServerFilesystem}
    return [
        thought.author_name
        for item in _assistant_items(history)
        for thought in item.thoughts or []
        if thought.author_name.lower() in tool_names
    ]


@pytest.fixture
def chat_history(conversation_utils):
    """Factory ``(chat id) -> history items`` of the saved conversation."""

    def _history(chat_id: str) -> list:
        return conversation_utils.get_conversation_by_id(chat_id).history

    return _history


@pytest.fixture
def open_chat(page):
    """Factory ``(chat id) -> ChatPage``: the chat opened on a desktop-sized viewport."""

    def _open(chat_id: str) -> ChatPage:
        chat_page = ChatPage(page)
        page.set_viewport_size({"width": 1920, "height": 980})
        chat_page.navigate_to(chat_id)
        chat_page.should_have_non_blank_assistant_response(timeout=30000)
        return chat_page

    return _open


# @case downloadable-chat-artifacts-mcp-files_TC_002
@pytest.mark.chat
@pytest.mark.mcp
@pytest.mark.timeout(600)
@pytest.mark.ui
def test_exported_file_chip_shows_name_type_and_downloads(export_chat, open_chat):
    """A file the MCP server exported shows as one chip with its name and MIME type,
    downloads under its name with the bytes the server wrote, and is listed again
    after a reload.

    AC-2: the chip shows the name and the MIME type; AC-3: the chip downloads the file.
    """
    exported = build_csv_file()
    chat_page = open_chat(export_chat(export_prompt(exported)))

    chat_page.generated_files.should_show_file(exported.name, exported.mime_type)

    download = chat_page.generated_files.download_file()
    chat_page.generated_files.should_be_saved_as(
        download, exported.name, exported.content
    )

    chat_page.refresh_page()
    chat_page.generated_files.should_show_file(exported.name, exported.mime_type)


# @case downloadable-chat-artifacts-mcp-files_TC_002
@pytest.mark.chat
@pytest.mark.mcp
@pytest.mark.timeout(600)
@pytest.mark.ui
def test_exported_xlsx_chip_shows_name_type_and_downloads(export_chat, open_chat):
    """An xlsx file the shell MCP server exported shows as one chip with its name and
    the xlsx MIME type, downloads under its name as a zip container holding the
    workbook, and is listed again after a reload.

    AC-2: the chip shows the name and the MIME type; AC-3: the chip downloads the file.
    """
    exported = build_xlsx_file()
    chat_page = open_chat(
        export_chat(shell_export_prompt(exported), mcp_server=SHELL_MCP_SERVER)
    )

    chat_page.generated_files.should_show_file(exported.name, exported.mime_type)

    download = chat_page.generated_files.download_file()
    chat_page.generated_files.should_be_saved_as_archive(
        download, exported.name, exported.zip_members
    )

    chat_page.refresh_page()
    chat_page.generated_files.should_show_file(exported.name, exported.mime_type)


# @case downloadable-chat-artifacts-mcp-files_TC_004
@pytest.mark.chat
@pytest.mark.mcp
@pytest.mark.timeout(600)
@pytest.mark.ui
def test_missing_and_empty_export_files_show_no_chip_or_filesystem_link(
    export_chat, open_chat, chat_history
):
    """Exporting a file that does not exist and then an empty file leaves the chat
    without a generated-files block and without a filesystem:, file: or sandbox: link.

    AC-4: a file that cannot be delivered is not shown as downloadable.

    Before looking at the chat, the saved history must show that the MCP server's tools
    ran and that no assistant message lists a file, so a server that never started
    cannot pass. The history does not show the export tool call itself (it is an
    argument of another tool call), so this check does not prove the export was tried.
    """
    chat_id = export_chat(export_missing_file_prompt(), export_empty_file_prompt())

    history = chat_history(chat_id)
    assert_that(
        _filesystem_tool_calls(history),
        is_not(empty()),
        "The MCP server must have been called, or the empty result below proves nothing",
    )
    assert_that(
        [name for item in _assistant_items(history) for name in item.fileNames],
        empty(),
        "No exported file may be listed on the assistant messages",
    )

    chat_page = open_chat(chat_id)
    chat_page.generated_files.should_not_show_files()
    chat_page.generated_files.should_not_have_undelivered_links()
