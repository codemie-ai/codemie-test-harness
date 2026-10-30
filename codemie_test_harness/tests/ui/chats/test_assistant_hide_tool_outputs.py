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
UI Test Suite — assistant-level "Hide tool outputs from end users".

Covers (chat side of the flag; the assistant form is covered in
``tests/ui/assistants/test_hide_tool_outputs_setting.py``):
    TC_003  Flagged assistant shows only the final answer, single and multi tool
    TC_004  Reopened conversation history shows no tool details
    TC_005  Chat configuration does not render the chat-level toggle
    TC_008  Pending tool-call approval stays visible for a flagged assistant
    TC_013  Flipping the flag ON hides existing details, OFF restores them
    TC_016  Shared conversation shows no tool details (JSON export: see
                          test_export_conversation.py)

The chat-level "Hide tool outputs" toggle is left at its default (OFF) everywhere, so a
hidden result can only come from the assistant-level flag. The SDK
AssistantCreateRequest has no hide_tool_outputs field, so the flag is set through the
assistant edit form.

Limitation: while outputs are hidden the UI offers no positive signal that a tool ran, so
"no tool blocks" is asserted together with a non-blank final answer. The matching
"blocks ARE shown" contrast for the same assistant is asserted in TC_013.
"""

import pytest

from codemie_sdk.models.assistant import ToolCallPolicy, ToolPermissionsConfig
from codemie_test_harness.tests.enums.tools import ResearchToolName
from codemie_test_harness.tests.test_data.tool_call_permissions_test_data import (
    APPROVAL_SYSTEM_PROMPT,
    get_approval_tool_prompt,
)
from codemie_test_harness.tests.ui.test_data.assistant_test_data import Toolkit
from codemie_test_harness.tests.ui.test_data.chat_test_data import (
    get_tool_invoking_message,
)
from codemie_test_harness.tests.ui.test_data.hide_tool_outputs_test_data import (
    ToolScenario,
    tool_scenarios,
)

_WIKIPEDIA_ONLY = (ResearchToolName.WIKIPEDIA,)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def research_assistant(assistant):
    """Callable creating an assistant (flag OFF) with the given research tools.

    The assistant is deleted by the shared ``assistant`` fixture teardown.
    """

    def _create(tools=_WIKIPEDIA_ONLY, **kwargs):
        return assistant(
            Toolkit.RESEARCH.value,
            tuple(tool.value for tool in tools),
            system_prompt=APPROVAL_SYSTEM_PROMPT,
            **kwargs,
        )

    return _create


@pytest.fixture
def flagged_assistant(research_assistant, enable_hide_tool_outputs_on_assistant):
    """Callable creating a research-tool assistant with 'Hide tool outputs' turned ON."""

    def _create(tools=_WIKIPEDIA_ONLY, **kwargs):
        created = research_assistant(tools, **kwargs)
        enable_hide_tool_outputs_on_assistant(created.name)
        return created

    return _create


@pytest.fixture
def share_token_for(client):
    """Callable ``(chat_id)`` returning a share token for the conversation."""

    def _share(chat_id: str) -> str:
        return client.conversations.share_conversation(chat_id).token

    return _share


# ---------------------------------------------------------------------------
# TC_003 — flagged assistant: final answer only, single and multi tool
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("scenario", tool_scenarios)
@pytest.mark.prod_regression
def test_flagged_assistant_shows_final_answer_without_tool_details(
    page, navigate_to_new_chat_page, flagged_assistant, scenario: ToolScenario
):
    """
    AC-4/AC-5/AC-6/AC-12: with the assistant flag ON the final response is rendered
    and no tool-call blocks are in the DOM, although the chat-level toggle was left at
    its default (OFF), which on its own would show them.
    """
    test_assistant = flagged_assistant(scenario.tools)
    chat_page = navigate_to_new_chat_page(page)

    chat_page.send_message(message=scenario.prompt, assistant_name=test_assistant.name)
    chat_page.wait_for_assistant_response()

    chat_page.should_have_non_blank_assistant_response()
    chat_page.should_not_have_tool_output_blocks()


# ---------------------------------------------------------------------------
# TC_004 — reopened history
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_reopened_conversation_of_flagged_assistant_shows_no_tool_details(
    page, navigate_to_new_chat_page, flagged_assistant
):
    """
    AC-4: the history served when a finished conversation is loaded again is stripped
    too (a different egress path from the live stream checked in TC_003).
    """
    test_assistant = flagged_assistant()
    chat_page = navigate_to_new_chat_page(page)
    prompt = get_tool_invoking_message().content
    chat_page.send_message(message=prompt, assistant_name=test_assistant.name)
    chat_page.wait_for_assistant_response()

    # Reload and reopen the conversation: everything now comes from stored history
    chat_page.navigate_to(chat_page.chat_id)

    chat_page.should_have_message_sent(prompt)
    chat_page.should_have_non_blank_assistant_response()
    chat_page.should_not_have_tool_output_blocks()


# ---------------------------------------------------------------------------
# TC_005 — chat configuration hides the toggle
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_chat_configuration_hides_toggle_for_flagged_assistant(
    page, navigate_to_new_chat_page, flagged_assistant
):
    """
    AC-7: the 'Hide tool outputs' switch is not rendered at all (not merely disabled)
    in the chat configuration when the active assistant is flagged.
    """
    test_assistant = flagged_assistant()
    chat_page = navigate_to_new_chat_page(page)
    chat_page.send_message(message="Hello", assistant_name=test_assistant.name)
    chat_page.wait_for_assistant_response()

    chat_page.open_configuration()
    config_panel = chat_page.chat_configuration_panel

    # The panel must be rendered, or "toggle absent" would pass on an empty page
    config_panel.should_have_general_section_visible()
    config_panel.should_not_have_hide_tool_outputs_toggle()


# ---------------------------------------------------------------------------
# TC_008 — pending approval stays visible
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_pending_tool_approval_stays_visible_for_flagged_assistant(
    page, navigate_to_new_chat_page, flagged_assistant
):
    """
    A pending tool-call approval is deliberately not hidden: the Allow/Deny dialog and
    the name of the tool awaiting approval stay visible so the user can decide. After
    Allow the final answer is shown and the executed tool blocks are hidden.

    The tool arguments shown in the dialog are not asserted: no grounded selector for
    them exists in the page objects or the change analysis.
    """
    test_assistant = flagged_assistant(
        tool_permissions=ToolPermissionsConfig(
            tool_call_policy=ToolCallPolicy.ASK_FOR_APPROVAL,
            allow_override=True,
        )
    )
    chat_page = navigate_to_new_chat_page(page)

    chat_page.send_message(
        message=get_approval_tool_prompt(ResearchToolName.WIKIPEDIA),
        assistant_name=test_assistant.name,
    )

    chat_page.should_have_tool_call_confirmation_visible()
    chat_page.should_have_pending_tool_call_for(ResearchToolName.WIKIPEDIA.value)

    chat_page.click_allow_tool_call()
    chat_page.wait_for_assistant_response()

    chat_page.should_have_non_blank_assistant_response()
    chat_page.should_not_have_tool_output_blocks()


# ---------------------------------------------------------------------------
# TC_013 — flipping the flag is retroactive and reversible
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_flipping_flag_hides_and_restores_details_of_existing_conversation(
    page,
    navigate_to_new_chat_page,
    research_assistant,
    enable_hide_tool_outputs_on_assistant,
    disable_hide_tool_outputs_on_assistant,
):
    """
    Full thoughts are always stored and stripped on egress, so turning the flag ON hides
    the details of an existing conversation after reload and turning it OFF brings them
    back.
    """
    test_assistant = research_assistant()
    chat_page = navigate_to_new_chat_page(page)
    chat_id = chat_page.chat_id
    prompt = get_tool_invoking_message().content
    chat_page.send_message(message=prompt, assistant_name=test_assistant.name)
    chat_page.wait_for_assistant_response()

    # Step 1 — flag OFF: tool blocks are visible
    chat_page.should_have_tool_output_blocks()

    # Step 2 — flag ON, reload the conversation: blocks gone, final answer present
    enable_hide_tool_outputs_on_assistant(test_assistant.name)
    chat_page.navigate_to(chat_id)
    chat_page.should_have_message_sent(prompt)
    chat_page.should_have_non_blank_assistant_response()
    chat_page.should_not_have_tool_output_blocks()

    # Step 3 — flag OFF again, reload: blocks are back
    disable_hide_tool_outputs_on_assistant(test_assistant.name)
    chat_page.navigate_to(chat_id)
    chat_page.should_have_message_sent(prompt)
    chat_page.should_have_tool_output_blocks()


# ---------------------------------------------------------------------------
# TC_016 — shared conversation
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.prod_regression
def test_shared_conversation_of_flagged_assistant_shows_no_tool_details(
    page, navigate_to_new_chat_page, flagged_assistant, share_token_for
):
    """
    Sharing is a separate egress path that could leak payloads: the shared page shows
    the final answer and no tool blocks. The JSON export path is covered in
    ``test_export_conversation.py`` (it parses the downloaded file).
    """
    test_assistant = flagged_assistant()
    chat_page = navigate_to_new_chat_page(page)
    chat_page.send_message(
        message=get_tool_invoking_message().content,
        assistant_name=test_assistant.name,
    )
    chat_page.wait_for_assistant_response()

    chat_page.navigate_to_shared_conversation(share_token_for(chat_page.chat_id))

    chat_page.should_have_non_blank_assistant_response()
    chat_page.should_not_have_tool_output_blocks()
