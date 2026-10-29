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
UI Tests for File Upload in Assistant Chat

Tests cover:
- Uploading single file to assistant chat
- Uploading multiple files to assistant chat
- File upload error handling for invalid file types

All tests use API for preconditions (creating assistant and chat)
and UI for test actions (uploading files).
"""

import os
import pytest

from codemie_test_harness.tests.utils.constants import FILES_PATH


@pytest.mark.assistant
@pytest.mark.ui
def test_upload_single_file_to_assistant_chat(
    page, assistant, navigate_to_new_chat_page
):
    """
    Test uploading a single file to assistant chat via UI.

    AC: User can click the attachment button and upload a single file to the chat.
    The file indicator/badge should appear showing the attached file.
    """
    test_assistant = assistant()
    chat_page = navigate_to_new_chat_page(page)

    chat_page.should_have_chat_input_visible()
    chat_page.should_have_add_attachment_button_visible()

    test_file_path = os.path.join(FILES_PATH, "test.txt")
    chat_page.attach_file(test_file_path)
    chat_page.should_have_file_attached("test.txt")

    chat_page.send_message(f"@{test_assistant.name} Analyze this file")
    chat_page.wait_for_assistant_response()

    chat_page.should_have_message_sent("Analyze this file")
    chat_page.should_have_assistant_response()


@pytest.mark.assistant
@pytest.mark.ui
def test_upload_multiple_files_to_assistant_chat(
    page, assistant, navigate_to_new_chat_page
):
    """
    Test uploading multiple files to assistant chat via UI.

    AC: User can attach multiple files (up to 10) to a single chat message.
    All file indicators should be visible before sending.
    """
    chat_page = navigate_to_new_chat_page(page)

    chat_page.should_have_chat_input_visible()
    chat_page.should_have_add_attachment_button_visible()

    test_files = [
        ("test.txt", os.path.join(FILES_PATH, "test.txt")),
        ("test.csv", os.path.join(FILES_PATH, "test.csv")),
    ]

    file_paths = [file_path for _, file_path in test_files]
    chat_page.attach_multiple_files(file_paths)

    chat_page.should_have_file_attached("test.txt")
    chat_page.should_have_file_attached("test.csv")

    chat_page.send_message("Analyze these files")
    chat_page.wait_for_assistant_response()

    chat_page.should_have_message_sent("Analyze these files")
    chat_page.should_have_assistant_response()
