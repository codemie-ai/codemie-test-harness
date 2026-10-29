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
UI Tests — Attach File button availability driven by the
per-assistant file-attachment setting.

Covers:
    TC_003  AC-2  Attach File button is hidden/inactive when the setting is disabled
    TC_004  AC-2  Attach File button remains visible/active when the setting is enabled (default)
    TC_005  AC-3  No upload initiated via the Attach File button click when disabled

TC_006 (drag-and-drop/paste, AC-3) is manual-for-now — see test-plan.md.
"""

import pytest


@pytest.mark.chat
@pytest.mark.ui
def test_attach_file_button_hidden_when_setting_disabled(
    page, chat_with_attach_file_disabled
):
    """
    AC-2: When the file-attachment setting is disabled, the Attach File
    button is not available to users of the affected assistant.

    Steps (from cases.json):
      1. Open the chat-bot as a user of the affected assistant.
         Expected: chat interface loads.
      2. Inspect the Attach File control area.
         Expected: the button is absent, or present but disabled/non-interactive.
    """
    chat_page = chat_with_attach_file_disabled(page)

    chat_page.should_have_chat_input_visible()
    chat_page.should_have_add_attachment_button_hidden_or_disabled()


@pytest.mark.chat
@pytest.mark.ui
def test_attach_file_button_visible_when_setting_enabled_default(
    page, navigate_to_new_chat_page_with_assistant
):
    """
    AC-2: With the default (enabled) setting, the Attach File button remains
    visible and active — regression guard against the default-enabled path
    breaking.

    Steps (from cases.json):
      1. Open the chat-bot as a user of the assistant with the setting enabled.
         Expected: chat interface loads.
      2. Inspect the Attach File control area.
         Expected: the button is visible and active.
    """
    chat_page = navigate_to_new_chat_page_with_assistant(page)

    chat_page.should_have_chat_input_visible()
    chat_page.should_have_add_attachment_button_visible_and_enabled()


@pytest.mark.chat
@pytest.mark.ui
def test_no_upload_via_button_click_when_setting_disabled(
    page, chat_with_attach_file_disabled
):
    """
    AC-3: Attempting to activate the Attach File control while the setting
    is disabled does not open a file picker or initiate any upload.

    Steps (from cases.json):
      1. Attempt to click/activate the Attach File control with the setting
         disabled.
         Expected: no file picker or upload dialog opens.
      2. Inspect chat state after the attempt.
         Expected: no upload was initiated and no attachment is added to the
         message.
    """
    chat_page = chat_with_attach_file_disabled(page)

    chat_page.should_have_chat_input_visible()
    chat_page.should_not_open_file_picker_when_attach_file_clicked()
    chat_page.should_have_no_attachments_in_composer()
