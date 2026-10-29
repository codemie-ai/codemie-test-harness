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
UI Test Suite — assistant-level "Hide tool outputs from end users" setting.

Covers (assistant form):
    TC_001  Labelled switch with hint, default OFF, extra note only when ON (AC-1, AC-2)
    TC_002  Flag persists after save and reopen (AC-3)

The chat-side behaviour of the flag is covered in
``tests/ui/chats/test_assistant_hide_tool_outputs.py``.

Note on AC-1: the merged UI renders no "Tool Output Visibility" heading (the frontend
integration test asserts it is absent), so the switch label is asserted instead.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    AssistantPopUpMessages,
    get_minimal_assistant_data,
)
from codemie_test_harness.tests.ui.test_data.hide_tool_outputs_test_data import (
    HIDE_TOOL_OUTPUTS_ENABLED_NOTE,
    HIDE_TOOL_OUTPUTS_HINT,
)
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)


@pytest.fixture
def ui_created_assistant_names(assistant_utils):
    """Names of assistants created through the UI form; deleted on teardown."""
    names = []
    yield names
    for name in names:
        try:
            assistant_utils.delete_assistant(
                assistant_utils.get_assistant_by_name(name)
            )
        except Exception as e:
            logger.warning(f"Failed to delete UI-created assistant {name}: {e}")


@pytest.mark.assistant
@pytest.mark.ui
def test_hide_tool_outputs_switch_is_labelled_with_hint_and_off_by_default(page):
    """
    AC-1: the form shows a switch labelled 'Hide tool outputs from end users'.
    AC-2: the hint explains that end users see only the final response; the extra
    'applies to everyone including you' note appears only after the switch is turned ON.
    """
    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()

    # Step 1 — switch is present by role+name and unchecked by default
    create_page.should_have_hide_tool_outputs_switch_visible()
    create_page.should_have_hide_tool_outputs_switch_unchecked()

    # Step 2 — hint text is shown, the ON-only note is not
    create_page.should_have_hide_tool_outputs_hint(HIDE_TOOL_OUTPUTS_HINT)
    create_page.should_not_have_hide_tool_outputs_enabled_note(
        HIDE_TOOL_OUTPUTS_ENABLED_NOTE
    )

    # Step 3 — turning the switch ON reveals the extra note
    create_page.enable_hide_tool_outputs_setting()
    create_page.should_have_hide_tool_outputs_enabled_note(
        HIDE_TOOL_OUTPUTS_ENABLED_NOTE
    )


@pytest.mark.assistant
@pytest.mark.ui
def test_hide_tool_outputs_flag_persists_after_save_and_reopen(
    page, ui_created_assistant_names
):
    """
    AC-3: an assistant created with the switch ON keeps it ON when its edit page
    is opened again. The SDK AssistantCreateRequest has no hide_tool_outputs field,
    so persistence is asserted through the UI round trip.
    """
    test_data = get_minimal_assistant_data()
    ui_created_assistant_names.append(test_data.name)

    # Step 1 — create an assistant with the switch ON and save
    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()
    create_page.fill_name(test_data.name)
    create_page.fill_description(test_data.description)
    create_page.fill_system_prompt(test_data.system_prompt)
    create_page.enable_hide_tool_outputs_setting()
    create_page.click_create()
    create_page.should_see_toast_message(
        AssistantPopUpMessages.ASSISTANT_CREATED_SUCCESS.value
    )

    # Step 2 — reopen the edit page: the switch is still ON
    assistants_page = AssistantsPage(page)
    assistants_page.search_assistants(test_data.name)
    edit_page = assistants_page.click_assistant_edit(test_data.name)
    edit_page.should_have_name_value(test_data.name)
    edit_page.should_have_hide_tool_outputs_switch_checked()
