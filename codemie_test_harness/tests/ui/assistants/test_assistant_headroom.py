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

"""Assistant form 'Context compression (Headroom)' section (needs features:headroom on)."""

import pytest
from hamcrest import assert_that, equal_to

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
from codemie_test_harness.tests.ui.test_data.headroom_test_data import (
    DEFAULT_STRATEGY,
    FORM_HEADROOM_EDITED,
    FORM_HEADROOM_SAVED,
    STRATEGY_AGGRESSIVE,
)


# @case headroom-per-assistant-workflow-configuration_TC_005
@pytest.mark.assistant
@pytest.mark.ui
def test_assistant_form_configures_headroom_for_one_assistant(
    page, assistant_utils, ui_created_assistant_names
):
    test_data = get_minimal_assistant_data()
    ui_created_assistant_names.append(test_data.name)

    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()
    create_page.fill_name(test_data.name)
    create_page.fill_description(test_data.description)
    create_page.fill_system_prompt(test_data.system_prompt)

    headroom = create_page.open_headroom_settings()
    headroom.should_have_enabled(False)
    headroom.should_have_options_disabled()
    headroom.should_have_strategy(DEFAULT_STRATEGY)

    headroom.set_enabled(True)
    headroom.set_compress_user_input(False)
    headroom.select_strategy(STRATEGY_AGGRESSIVE)
    create_page.click_create()

    assistants_page = AssistantsPage(page)
    assistants_page.should_see_assistant_with_name(test_data.name)
    saved = assistant_utils.get_assistant_by_name(test_data.name)
    assert_that(
        assistant_utils.get_assistant_by_id(saved.id).headroom_config,
        equal_to(FORM_HEADROOM_SAVED),
        "Assistant saved from the form does not store the chosen Headroom settings",
    )

    assistants_page.search_assistants(test_data.name)
    edit_page = assistants_page.click_assistant_edit(test_data.name)
    headroom = edit_page.open_headroom_settings()
    headroom.should_have_settings(
        enabled=True,
        compress_user_input=False,
        compress_tool_outputs=True,
        strategy=STRATEGY_AGGRESSIVE,
    )

    # Flip both checkboxes: 'Compress tool outputs' off, 'Compress user input' on.
    headroom.set_compress_tool_outputs(False)
    headroom.set_compress_user_input(True)
    edit_page.click_save()
    assistants_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )
    assert_that(
        assistant_utils.get_assistant_by_id(saved.id).headroom_config,
        equal_to(FORM_HEADROOM_EDITED),
        "Assistant edited in the form does not store the changed Headroom checkboxes",
    )

    assistants_page.navigate_to()
    assistants_page.search_assistants(test_data.name)
    edit_page = assistants_page.click_assistant_edit(test_data.name)
    edit_page.open_headroom_settings().should_have_settings(
        enabled=True,
        compress_user_input=True,
        compress_tool_outputs=False,
        strategy=STRATEGY_AGGRESSIVE,
    )
