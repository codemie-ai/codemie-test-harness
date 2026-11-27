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
  Also: a file with a non-Latin name shows its decoded name and downloads under it, a
  sandbox link with an invented token gets no chip, and a chip in a shared conversation
  downloads for a second user

The export runs through the API (an assistant with the opted-in filesystem MCP
server, or the shell one for an xlsx); the tests then open the saved chat in the browser.
The filesystem server writes text only, so a csv file checks its chip, and a shell
MCP server running python3 writes the xlsx.
"""

from datetime import datetime

import pytest
from hamcrest import assert_that, contains_string, empty, is_not
from requests import HTTPError

from codemie_sdk.models.conversation import ConversationCreateRequest, HistoryItem
from codemie_test_harness.tests.enums.tools import McpServerFilesystem
from codemie_test_harness.tests.test_data.mcp_export_files_test_data import (
    CHINESE_NAME_STEM,
    CYRILLIC_NAME_STEM,
    EXPORT_WITHOUT_LINKS_SYSTEM_PROMPT,
    SHELL_MCP_SERVER,
    build_csv_file,
    build_non_latin_csv_file,
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
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.ui.test_data.sandbox_file_link_test_data import (
    build_invented_sandbox_link,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


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


@pytest.fixture
def seeded_reply_chat(client, assistant_factory, conversation_utils):
    """Factory ``(assistant reply text) -> chat id``: a new conversation whose saved
    history holds one user message and the given text as the assistant's answer.

    The answer is written to the history through the API, not produced by a model, so
    the text reaches the chat exactly as given. The conversation is deleted on
    teardown; the assistant is deleted by ``assistant_factory``.
    """
    created_ids = []

    def _seed(reply: str) -> str:
        replier = assistant_factory.create()
        conversation = client.conversations.create(
            ConversationCreateRequest(initial_assistant_id=replier.id, folder="")
        )
        chat_id = conversation.get("id")
        created_ids.append(chat_id)
        conversation_utils.upsert_history(
            conversation_id=chat_id,
            history=[
                HistoryItem(
                    role="User",
                    message="share the report",
                    messageRaw="<p>share the report</p>",
                    historyIndex=0,
                    date=datetime.now(),
                    fileNames=[],
                ),
                HistoryItem(
                    role="Assistant",
                    message=reply,
                    historyIndex=0,
                    date=datetime.now(),
                    fileNames=[],
                ),
            ],
            assistant_id=replier.id,
        )
        return chat_id

    yield _seed

    for chat_id in created_ids:
        try:
            client.conversations.delete(chat_id)
        except HTTPError:
            pass


@pytest.fixture
def reader_chat_page(new_context, platform_user):
    """A ``ChatPage`` of a second, signed-in user in its own browser context, who is not
    the owner of the chats the test creates."""
    page = new_context().new_page()
    user_id = platform_user.user_id
    LoginPage(page).login_suppressing_popups(
        platform_user.email,
        platform_user.password,
        user_id,
        CredentialsManager.get_parameter("FRONTEND_URL", ""),
    )
    return ChatPage(page)


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


# @case unify-sandbox-artifact-link-format_TC_001
@pytest.mark.chat
@pytest.mark.mcp
@pytest.mark.parametrize(
    "name_stem",
    [
        pytest.param(CYRILLIC_NAME_STEM, id="cyrillic"),
        pytest.param(CHINESE_NAME_STEM, id="chinese"),
    ],
)
@pytest.mark.timeout(600)
@pytest.mark.ui
def test_exported_file_with_non_latin_name_shows_decoded_name_and_downloads(
    export_chat, open_chat, name_stem
):
    """A file whose name is Cyrillic or Chinese shows as one chip with its decoded name
    and MIME type, and downloads under that decoded name.

    AC-6: the artifact token of a non-Latin name decodes; AC-3: the chip and the
    download show the decoded name; AC-1: the chip downloads the file.
    """
    exported = build_non_latin_csv_file(name_stem)
    chat_page = open_chat(export_chat(export_prompt(exported)))

    chat_page.generated_files.should_show_file(exported.name, exported.mime_type)

    download = chat_page.generated_files.download_file()
    chat_page.generated_files.should_be_saved_as(
        download, exported.name, exported.content
    )


# @case unify-sandbox-artifact-link-format_TC_002
@pytest.mark.chat
@pytest.mark.mcp
@pytest.mark.timeout(600)
@pytest.mark.ui
def test_sandbox_link_with_invented_token_gets_no_chip(
    export_chat, seeded_reply_chat, open_chat, chat_history
):
    """A sandbox link whose token the back end never issued gets no chip and no sandbox:
    link, while a link to a file the back end did export shows its chip in the same run.

    AC-6: the strict token decoder refuses an invented token.

    The answer is written to the saved history through the API, so no model has to copy
    the link. The history must hold the link and the page must show its label, so a chat
    that lost the link cannot pass. The exported file is the positive control: the same
    chip logic does show a real chip.
    """
    exported = build_csv_file()
    control_page = open_chat(export_chat(export_prompt(exported)))
    control_page.generated_files.should_show_file(exported.name, exported.mime_type)

    invented = build_invented_sandbox_link()
    invented_chat_id = seeded_reply_chat(invented.reply)
    assert_that(
        " ".join(
            item.message for item in _assistant_items(chat_history(invented_chat_id))
        ),
        contains_string(invented.link),
        "The assistant's answer must carry the invented sandbox link",
    )

    chat_page = open_chat(invented_chat_id)
    chat_page.should_show_assistant_text(invented.label)
    chat_page.generated_files.should_not_show_files()
    chat_page.generated_files.should_not_have_undelivered_links()


# @case unify-sandbox-artifact-link-format_TC_003
@pytest.mark.chat
@pytest.mark.mcp
@pytest.mark.timeout(600)
@pytest.mark.ui
def test_exported_file_chip_in_shared_conversation_downloads_for_second_user(
    export_chat, conversation_utils, reader_chat_page
):
    """A second user who opens a shared conversation sees the chip of the exported file
    and downloads it under its name with the bytes the server wrote.

    AC-1: the chip resolves through the share grant and the download uses it.
    """
    exported = build_csv_file()
    share_token = conversation_utils.share_conversation(
        export_chat(export_prompt(exported))
    ).token

    reader_chat_page.navigate_to_shared_conversation(share_token)

    reader_chat_page.generated_files.should_show_file(exported.name, exported.mime_type)
    download = reader_chat_page.generated_files.download_file()
    reader_chat_page.generated_files.should_be_saved_as(
        download, exported.name, exported.content
    )
