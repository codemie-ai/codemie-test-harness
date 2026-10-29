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
UI E2E tests for the 'Tools Tokens Size Limit' field in the Assistant configuration.

Feature: Add Tools Tokens Size Limit setting to Assistant configuration

These tests cover:
- TC_001: Default state of the tools_tokens_size_limit field (empty value, correct placeholder)
- TC_010: Value saved via UI is reflected in the API response
"""

import pytest
from playwright.sync_api import expect

from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    AssistantPopUpMessages,
)
from codemie_test_harness.tests.utils.client_factory import get_client


@pytest.mark.assistant
@pytest.mark.ui
def test_tools_tokens_size_limit_field_default_state(page, assistant):
    """
    TC_001 — Verify the default state of the tools_tokens_size_limit field.

    Steps:
    1. Create a fixture assistant via API
    2. Navigate to the Assistants list page
    3. Open the edit page for the fixture assistant
    4. Expand the 'Extra configuration' accordion
    5. Assert the tools_tokens_size_limit input is visible
    6. Assert the input value is empty ("")
    7. Assert the input placeholder is "30000"

    Expected:
    - Input is visible inside the Extra configuration accordion
    - Input value is empty (field has no default value set)
    - Input placeholder text is "30000"
    """
    assistant_page = AssistantsPage(page)
    edit_page = CreateEditAssistantPage(page)
    created_assistant = assistant()

    assistant_page.navigate_to()
    assistant_page.search_assistants(created_assistant.name)
    assistant_page.click_assistant_edit(created_assistant.name)

    edit_page.expand_extra_configuration()

    tools_tokens_input = edit_page.tools_tokens_size_limit_input
    tools_tokens_input.wait_for(state="visible", timeout=5000)

    expect(tools_tokens_input).to_be_visible()
    expect(tools_tokens_input).to_have_value("")
    expect(tools_tokens_input).to_have_attribute("placeholder", "30000")


@pytest.mark.assistant
@pytest.mark.ui
def test_tools_tokens_size_limit_reflected_in_api(page, assistant):
    """
    TC_010 — Verify that a value saved via UI is reflected in the API response.

    Steps:
    1. Create a fixture assistant via API
    2. Navigate to the Assistants list page and open edit page
    3. Fill tools_tokens_size_limit with "30000"
    4. Click Save
    5. Assert success toast message is shown
    6. Fetch the assistant via API using get_client().assistants.get(assistant_id)
    7. Assert the API response contains tools_tokens_size_limit == 30000

    Expected:
    - Success toast "Assistant has been updated successfully!" is displayed
    - API response has tools_tokens_size_limit equal to 30000 (integer)
    """
    assistant_page = AssistantsPage(page)
    edit_page = CreateEditAssistantPage(page)
    created_assistant = assistant()

    assistant_page.navigate_to()
    assistant_page.search_assistants(created_assistant.name)
    assistant_page.click_assistant_edit(created_assistant.name)

    edit_page.fill_tools_tokens_size_limit("30000")
    edit_page.click_save()

    assistant_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )

    client = get_client()
    api_assistant = client.assistants.get(created_assistant.id)

    assert api_assistant.tools_tokens_size_limit == 30000, (
        f"Expected tools_tokens_size_limit == 30000 in API response, "
        f"got: {api_assistant.tools_tokens_size_limit}"
    )
