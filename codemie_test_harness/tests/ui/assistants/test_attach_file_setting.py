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
UI Tests — Admin config to disable the Attach File button.

Covers:
    TC_001  AC-1  Admin config to disable Attach File button exists and is toggleable
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    AssistantPopUpMessages,
)


@pytest.mark.assistant
@pytest.mark.ui
def test_attach_file_setting_toggle_exists_and_persists(page, assistant):
    """
    AC-1: An admin config to disable the Attach File button exists on the
    assistant settings and is toggleable.

    Steps (from cases.json):
      1. Navigate to the assistant settings that expose the file-attachment
         control.
         Expected: a setting to disable the Attach File button is visible
         and reachable.
      2. Toggle the setting off and save.
         Expected: the setting persists as disabled after save/reload.
    """
    test_assistant = assistant()
    assistants_page = AssistantsPage(page)

    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)
    edit_page = assistants_page.click_assistant_edit(test_assistant.name)

    # Step 1 — the setting control is visible and reachable
    edit_page.should_have_attach_file_toggle_visible()

    # Step 2 — toggle it off and save
    edit_page.toggle_attach_file_setting(enabled=False)
    edit_page.should_have_attach_file_setting_disabled()
    edit_page.click_save()
    assistants_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )

    # Reload (re-open the edit page) — the disabled state must persist
    reopened_edit_page = assistants_page.click_assistant_edit(test_assistant.name)
    reopened_edit_page.should_have_attach_file_setting_disabled()
