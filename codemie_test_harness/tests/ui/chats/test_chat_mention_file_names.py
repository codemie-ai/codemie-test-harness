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

"""UI tests: the `@` mention list shows the decoded names of the files of a chat.

The files are uploaded and sent through the API; the test then opens the saved chat in
the browser. The list offers a file only once it is part of a sent message, so the
files are sent with a message before the chat is opened.
"""

import pytest
from requests import HTTPError

from codemie_sdk.models.conversation import ConversationCreateRequest
from codemie_test_harness.tests.test_data.mcp_export_files_test_data import (
    CHINESE_NAME_STEM,
    CYRILLIC_NAME_STEM,
)
from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.test_data.sandbox_file_link_test_data import (
    FILE_BODY,
    build_mention_file_names,
)


@pytest.fixture
def chat_with_sent_files(client, assistant, assistant_utils, tmp_path):
    """Factory ``(file names) -> chat id``: a new conversation in which one message
    carries the uploaded files, one per name.

    The conversation is deleted on teardown, also when a step fails.
    """
    created_ids = []

    def _create(names: tuple) -> str:
        chatter = assistant()
        file_urls = []
        for name in names:
            path = tmp_path / name
            path.write_text(FILE_BODY, encoding="utf-8")
            file_urls.append(assistant_utils.upload_file_to_chat(path).get("file_url"))
        conversation = client.conversations.create(
            ConversationCreateRequest(initial_assistant_id=chatter.id, folder="")
        )
        chat_id = conversation.get("id")
        created_ids.append(chat_id)
        assistant_utils.ask_assistant(
            chatter,
            "Reply with the single word OK.",
            file_urls=file_urls,
            conversation_id=chat_id,
        )
        return chat_id

    yield _create

    for chat_id in created_ids:
        try:
            client.conversations.delete(chat_id)
        except HTTPError:
            pass


@pytest.fixture
def open_chat(page):
    """Factory ``(chat id) -> ChatPage``: the chat opened on a desktop-sized viewport,
    with the assistant's answer shown."""

    def _open(chat_id: str) -> ChatPage:
        chat_page = ChatPage(page)
        page.set_viewport_size({"width": 1920, "height": 980})
        chat_page.navigate_to(chat_id)
        chat_page.should_have_non_blank_assistant_response(timeout=30000)
        return chat_page

    return _open


# @case unify-sandbox-artifact-link-format_TC_004
@pytest.mark.chat
@pytest.mark.parametrize(
    "non_latin_stem",
    [
        pytest.param(CYRILLIC_NAME_STEM, id="cyrillic"),
        pytest.param(CHINESE_NAME_STEM, id="chinese"),
    ],
)
@pytest.mark.timeout(300)
@pytest.mark.ui
def test_mention_list_shows_decoded_names_of_sent_files(
    chat_with_sent_files, open_chat, non_latin_stem
):
    """After one ASCII-named and one non-Latin-named file were sent in a chat, typing
    `@` lists both files, each by its decoded name.

    AC-3: the editor's mention list decodes the file name; AC-6: the upload token is
    accepted whatever characters it holds.
    """
    names = build_mention_file_names(non_latin_stem)
    chat_page = open_chat(chat_with_sent_files(names))

    chat_page.open_file_mention_list()

    chat_page.should_list_mention_files(names)
