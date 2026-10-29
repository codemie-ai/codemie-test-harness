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
Regression tests:
Extra configuration — temperature validation for Bedrock and Vertex Claude Sonnet models.

Verifies that when a Claude Sonnet model is selected the temperature field adopts the
0-1 range (placeholder "0-1") and blocks values above 1 with the correct validation
message before any API request is made.
"""

import pytest

from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    AssistantValidationErrors,
)


@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.parametrize(
    "model",
    [
        ModelTypes.CLAUDE_4_6_SONNET,
        ModelTypes.CLAUDE_SONNET_4_6_VERTEX,
    ],
    ids=["bedrock_claude_sonnet_4_6", "vertex_claude_sonnet_4_6"],
)
def test_temperature_validation_blocked_above_one_for_claude_sonnet(
    page, assistant, model
):
    """
    Regression: for Bedrock and Vertex Claude Sonnet models, the temperature field
    must restrict the allowed range to 0-1 and display a validation error when the
    user enters a value greater than 1.

    AC covered:
    - AC 2 / AC 3: Claude Sonnet temperature range is 0-1 for Bedrock and Vertex.
    - AC 4: UI no longer shows 0-2 range for Claude Sonnet models.
    - AC 5 / AC 6: Values > 1 are blocked with a validation message before save.
    """
    assistant_page = AssistantsPage(page)
    created_assistant = assistant()

    assistant_page.navigate_to()
    assistant_page.search_assistants(created_assistant.name)
    edit_page = assistant_page.click_assistant_edit(created_assistant.name)

    # Expand Extra configuration and select the Claude Sonnet model
    edit_page.select_llm_model(model.value)

    # AC 4: placeholder changes to "0-1" for Claude models
    edit_page.should_have_temperature_placeholder("0-1")

    # AC 5 / AC 6: entering 1.5 must be blocked with the Claude-specific error
    edit_page.expand_extra_configuration()
    edit_page.temperature_input.clear()
    edit_page.temperature_input.fill("1.5")
    edit_page.temperature_input.press("Tab")

    edit_page.should_have_temperature_error_textarea(
        AssistantValidationErrors.TEMPERATURE_CLAUDE_NOT_VALID.value
    )

    # Attempt to save — the form must be blocked; no success toast should appear,
    # and the inline error must still be present (confirms the save did not go through).
    edit_page.click_save()
    edit_page.should_have_temperature_error_textarea(
        AssistantValidationErrors.TEMPERATURE_CLAUDE_NOT_VALID.value
    )
    edit_page.should_not_see_success_toast()
