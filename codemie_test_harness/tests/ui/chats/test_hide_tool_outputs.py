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
UI Test Suite — Hide tool outputs toggle

Covers:
  TC-01  Toggle is visible and correctly labeled in the config panel (AC1, AC4)
  TC-02  Enabling toggle hides tool outputs; state persists within session (AC1, AC2, AC3)
  TC-03  Disabling toggle restores tool output visibility in response (AC2)

Note: TC-01 originally had a "tools=false" variant expecting the toggle to be absent.
Removed after confirming that assistantFeatures.tools is always true on this deployment —
the toggle renders unconditionally. TC-01 therefore only verifies the happy path.
"""

import pytest

from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    Toolkit,
    ResearchTool,
)
from codemie_test_harness.tests.ui.test_data.chat_test_data import (
    get_tool_invoking_message,
)


# ---------------------------------------------------------------------------
# TC-01 — toggle IS visible and correctly labeled in the config panel
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_hide_tool_outputs_toggle_visible_and_labeled(
    page, navigate_to_new_chat_page, assistant
):
    """
    TC-01: The 'Hide tool outputs' toggle is visible, unchecked by default,
    and correctly labeled in the configuration panel.

    AC1: Users can enable/disable display of technical tool outputs.
    AC4: Option is accessible and clearly labeled for end users.
    """
    chat_page = navigate_to_new_chat_page(page)
    test_assistant = assistant(Toolkit.RESEARCH.value, ResearchTool.WIKIPEDIA.value)

    # Use the tools-enabled assistant in the chat to make the feature active
    chat_page.send_message(message="Hello", assistant_name=test_assistant.name)
    chat_page.wait_for_assistant_response()

    chat_page.open_configuration()
    config_panel = chat_page.chat_configuration_panel

    # Toggle must be visible and unchecked by default
    config_panel.should_have_hide_tool_outputs_toggle_visible()
    config_panel.should_have_hide_tool_outputs_label_visible()
    config_panel.should_have_hide_tool_outputs_toggle_unchecked()

    # General section heading must be visible (feature sits inside the config panel)
    config_panel.should_have_general_section_visible()


# ---------------------------------------------------------------------------
# TC-02 — Enabling toggle hides tool outputs; state persists within session
# ---------------------------------------------------------------------------


@pytest.mark.not_for_parallel_run
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_hide_tool_outputs_toggle_hides_tool_blocks_and_persists(
    page, navigate_to_new_chat_page, assistant
):
    """
    TC-02: Enabling the 'Hide tool outputs' toggle removes ThoughtsBlock from the
    DOM (count=0, not just hidden). Closing and re-opening the config panel confirms
    the toggle state persists within the same session.

    AC1: Users can enable/disable display of technical tool outputs.
    AC2: When disabled, only the final answer is shown in the response.
    AC3: The setting is persistent for the session.
    """
    chat_page = navigate_to_new_chat_page(page)
    test_assistant = assistant(Toolkit.RESEARCH.value, ResearchTool.WIKIPEDIA.value)

    # Step 1 — open config and enable the toggle before sending a message
    chat_page.send_message(message="Hello", assistant_name=test_assistant.name)
    chat_page.wait_for_assistant_response()

    chat_page.open_configuration()
    config_panel = chat_page.chat_configuration_panel
    config_panel.enable_hide_tool_outputs()
    chat_page.close_configuration()

    # Step 2 — send a tool-triggering message
    tool_message = get_tool_invoking_message()
    chat_page.send_message(
        message=tool_message.content, assistant_name=test_assistant.name
    )
    chat_page.wait_for_assistant_response()

    # Step 3 — tool output blocks must be absent from the DOM
    chat_page.should_not_have_tool_output_blocks()

    # Step 4 — re-open config panel; toggle must still be ON (persists in session)
    chat_page.open_configuration()
    config_panel.should_have_hide_tool_outputs_toggle_checked()


# ---------------------------------------------------------------------------
# TC-03 — Disabling toggle restores tool output visibility
# ---------------------------------------------------------------------------


@pytest.mark.not_for_parallel_run
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_hide_tool_outputs_toggle_restore_visibility_after_disable(
    page, navigate_to_new_chat_page, assistant
):
    """
    TC-03: After enabling the toggle (tool outputs hidden) and then disabling it,
    a subsequent tool-triggering message must show the ThoughtsBlock again.

    AC2: When disabled, only the final answer is shown; re-enabling shows them again.
    """
    chat_page = navigate_to_new_chat_page(page)
    test_assistant = assistant(Toolkit.RESEARCH.value, ResearchTool.WIKIPEDIA.value)

    # Step 1 — connect assistant and enable the hide toggle
    chat_page.send_message(message="Hello", assistant_name=test_assistant.name)
    chat_page.wait_for_assistant_response()

    chat_page.open_configuration()
    config_panel = chat_page.chat_configuration_panel
    config_panel.enable_hide_tool_outputs()
    chat_page.close_configuration()

    # Step 2 — send tool message; outputs must be hidden (toggle is ON)
    tool_message = get_tool_invoking_message()
    chat_page.send_message(
        message=tool_message.content, assistant_name=test_assistant.name
    )
    chat_page.wait_for_assistant_response()
    chat_page.should_not_have_tool_output_blocks()

    # Step 3 — disable the toggle
    chat_page.open_configuration()
    config_panel.disable_hide_tool_outputs()
    chat_page.close_configuration()

    # Step 4 — send a second tool message; outputs must now be visible
    chat_page.send_message(
        message=tool_message.content, assistant_name=test_assistant.name
    )
    chat_page.wait_for_assistant_response()
    chat_page.should_have_tool_output_blocks()
