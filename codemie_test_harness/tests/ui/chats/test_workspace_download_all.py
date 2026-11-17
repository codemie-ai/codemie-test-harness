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
UI tests: "Download all" in the agent workspace popup of a chat.

Covers:
  TC_001  Download all is disabled on an empty workspace; the archive then holds the
          generated Python script and the uploaded file under their own names
  TC_002  Archive entries are byte-identical to the uploaded binary and text files
  TC_003  The archive of one chat does not include the files of another chat

Gates of the flow: the chat header shows "Browse files" only after the first message,
and an uploaded file reaches the workspace only when the message carrying it is sent.
"""

import pytest

from codemie_test_harness.tests.ui.test_data.workspace_download_test_data import (
    BINARY_SAMPLE_FILE,
    GENERATE_SCRIPT_PROMPT,
    GENERATED_SCRIPT_NAME,
    NO_FILE_PROMPT,
    OTHER_TEXT_SAMPLE_FILE,
    TEXT_SAMPLE_FILE,
    UPLOAD_ACK_PROMPT,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH


# @case enable-download-of-all-files_TC_001
@pytest.mark.chat
@pytest.mark.timeout(600)
@pytest.mark.ui
def test_download_all_archives_generated_script_and_uploaded_file(open_workspace_chat):
    chat_page = open_workspace_chat()

    chat_page.send_message_and_wait_for_reply(NO_FILE_PROMPT, 1)
    empty_popup = chat_page.open_workspace_browser()
    empty_popup.should_have_no_files()
    empty_popup.should_have_download_all_disabled()
    empty_popup.close()

    chat_page.send_message_and_wait_for_reply(GENERATE_SCRIPT_PROMPT, 2)
    chat_page.attach_file_to_composer(str(FILES_PATH / TEXT_SAMPLE_FILE))
    chat_page.should_have_file_attached(TEXT_SAMPLE_FILE)
    chat_page.send_message_and_wait_for_reply(UPLOAD_ACK_PROMPT, 3)

    popup = chat_page.open_workspace_browser()
    popup.should_list_file(GENERATED_SCRIPT_NAME)
    popup.should_list_file(TEXT_SAMPLE_FILE)
    popup.should_have_download_all_enabled()

    archive = popup.download_all()

    popup.should_have_archive_named(archive)
    popup.should_have_archive_entry(archive, GENERATED_SCRIPT_NAME)
    popup.should_have_archive_entry(archive, TEXT_SAMPLE_FILE)


# @case enable-download-of-all-files_TC_002
@pytest.mark.chat
@pytest.mark.ui
def test_download_all_archive_entries_are_identical_to_uploaded_files(
    open_workspace_chat,
):
    binary_file = FILES_PATH / BINARY_SAMPLE_FILE
    text_file = FILES_PATH / TEXT_SAMPLE_FILE
    chat_page = open_workspace_chat()

    chat_page.attach_multiple_files([str(binary_file), str(text_file)])
    chat_page.should_have_file_attached(BINARY_SAMPLE_FILE)
    chat_page.should_have_file_attached(TEXT_SAMPLE_FILE)
    chat_page.send_message_and_wait_for_reply(UPLOAD_ACK_PROMPT, 1)

    popup = chat_page.open_workspace_browser()
    popup.should_list_file(BINARY_SAMPLE_FILE)
    popup.should_list_file(TEXT_SAMPLE_FILE)

    archive = popup.download_all()

    popup.should_have_archive_named(archive)
    popup.should_have_archive_entry_equal_to_file(
        archive, BINARY_SAMPLE_FILE, binary_file
    )
    popup.should_have_archive_entry_equal_to_file(archive, TEXT_SAMPLE_FILE, text_file)


# @case enable-download-of-all-files_TC_003
@pytest.mark.chat
@pytest.mark.timeout(600)
@pytest.mark.ui
def test_download_all_archive_excludes_files_of_another_chat(open_workspace_chat):
    first_chat = open_workspace_chat()
    first_chat.attach_file(str(FILES_PATH / OTHER_TEXT_SAMPLE_FILE))
    first_chat.should_have_file_attached(OTHER_TEXT_SAMPLE_FILE)
    first_chat.send_message_and_wait_for_reply(UPLOAD_ACK_PROMPT, 1)

    first_popup = first_chat.open_workspace_browser()
    first_popup.should_list_file(OTHER_TEXT_SAMPLE_FILE)
    first_popup.close()

    second_chat = open_workspace_chat()
    second_chat.attach_file(str(FILES_PATH / TEXT_SAMPLE_FILE))
    second_chat.should_have_file_attached(TEXT_SAMPLE_FILE)
    second_chat.send_message_and_wait_for_reply(UPLOAD_ACK_PROMPT, 1)

    popup = second_chat.open_workspace_browser()
    popup.should_list_file(TEXT_SAMPLE_FILE)

    archive = popup.download_all()

    popup.should_have_archive_named(archive)
    popup.should_have_archive_entry(archive, TEXT_SAMPLE_FILE)
    popup.should_not_have_archive_entry(archive, OTHER_TEXT_SAMPLE_FILE)
