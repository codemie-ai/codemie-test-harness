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
UI Test Suite — Tool-call confirmation (ASK_FOR_APPROVAL flow)

Covers:
  TC_001  Confirmation dialog appears with correctly styled
                        Allow and Deny buttons (AC-1, AC-2)
  TC_005  Chat resumes on same conversation ID after Allow and
                        Deny — conversation not restarted (AC-5)
  TC_008  Interrupted thought always visible regardless of
                        hideToolOutputs setting (AC-7)
  TC_009  Standard chat (AUTO_APPROVE policy) shows no
                        confirmation dialog (AC-8)
  TC_013  Allow/Deny buttons suppressed in shared-page context
  TC_015  Per-chat policy override (allow_override) persists
                        after navigation and page refresh

          Approval popup shown when several research tools
                        are configured on one assistant (AC-4)

TC_001, TC_005 and TC_009 run once per research tool (Wikipedia, Google
Search, Web Scrapper) regression: the approval popup was
skipped for Google/Web Scrapper under the "Manual" policy.
"""

from __future__ import annotations

import pytest
from hamcrest import assert_that, equal_to
from urllib.parse import urlparse

from codemie_sdk.models.assistant import (
    ToolCallPolicy,
    ToolPermissionsConfig,
)
from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    Toolkit,
)
from codemie_test_harness.tests.enums.tools import ResearchToolName
from codemie_test_harness.tests.ui.test_data.chat_test_data import (
    get_tool_invoking_message,
)
from codemie_test_harness.tests.test_data.tool_call_permissions_test_data import (
    APPROVAL_SYSTEM_PROMPT,
    approval_research_tools,
    get_approval_tool_prompt,
    multi_tool_research_tools,
)
from codemie_test_harness.tests.utils.client_factory import get_client


# Labels rendered by ToolCallPolicyDropdown component.
# Verified against src/components/ToolCallPolicyDropdown/ToolCallPolicyDropdown.tsx,
# POLICY_OPTIONS: ASK_FOR_APPROVAL → label "Manual" (line 41),
#                 AUTO_APPROVE     → label "Auto"   (line 52).
_POLICY_LABEL_MANUAL = "Manual"
_POLICY_LABEL_AUTO = "Auto"


# ---------------------------------------------------------------------------
# Convenience helper
# ---------------------------------------------------------------------------


def _create_ask_for_approval_assistant(assistant_fixture_fn, *tools: ResearchToolName):
    """Create an ASK_FOR_APPROVAL assistant with the given research tools
    (Wikipedia when none are given)."""
    tool_names = tuple(tool.value for tool in tools) or (
        ResearchToolName.WIKIPEDIA.value,
    )
    return assistant_fixture_fn(
        Toolkit.RESEARCH.value,
        tool_names,
        system_prompt=APPROVAL_SYSTEM_PROMPT,
        tool_permissions=ToolPermissionsConfig(
            tool_call_policy=ToolCallPolicy.ASK_FOR_APPROVAL,
            allow_override=True,
        ),
    )


# ---------------------------------------------------------------------------
# TC_001 — Confirmation dialog appears with correctly styled Allow/Deny buttons
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("tool", approval_research_tools)
def test_tool_call_confirmation_dialog_shows_allow_and_deny_buttons(
    page,
    navigate_to_new_chat_page,
    assistant,
    tool,
):
    """
    When an ASK_FOR_APPROVAL assistant invokes a tool, the chat history renders:
      - The interrupted thought 'Tool call is waiting for user approval.'
      - An Allow button (ButtonType.PRIMARY) rendered below the thought
      - A Deny button (ButtonType.DELETE) rendered below the thought

    AC-1: An in-line confirmation overlay appears when a tool call is paused.
    AC-2: Allow uses ButtonType.PRIMARY; Deny uses ButtonType.DELETE.
    """
    chat_page = navigate_to_new_chat_page(page)
    test_assistant = _create_ask_for_approval_assistant(assistant, tool)

    chat_page.send_message(
        message=get_approval_tool_prompt(tool), assistant_name=test_assistant.name
    )

    # All three confirmation elements must be visible
    chat_page.should_have_tool_call_confirmation_visible()


# ---------------------------------------------------------------------------
# Popup shown with several research tools configured
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
def test_confirmation_dialog_shown_for_multi_tool_research_assistant(
    page,
    navigate_to_new_chat_page,
    assistant,
):
    """
    An assistant with Wikipedia, Google Search and Web Scrapper configured
    together under the "Manual" policy must show the approval popup before a
    research tool runs (Exam Helper scenario from the bug report).

    AC-1/AC-4: Manual approval is respected for multi-tool research assistants.
    """
    chat_page = navigate_to_new_chat_page(page)
    test_assistant = _create_ask_for_approval_assistant(
        assistant, *multi_tool_research_tools
    )

    chat_page.send_message(
        message=get_approval_tool_prompt(ResearchToolName.GOOGLE_SEARCH),
        assistant_name=test_assistant.name,
    )

    chat_page.should_have_tool_call_confirmation_visible()


# ---------------------------------------------------------------------------
# TC_005 — Chat resumes on same conversation ID after Allow and after Deny
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("tool", approval_research_tools)
def test_chat_resumes_on_same_conversation_after_allow_then_deny(
    page,
    navigate_to_new_chat_page,
    assistant,
    tool,
):
    """
    Clicking Allow or Deny must NOT create a new conversation.  The page URL
    (which embeds the conversation ID) must stay unchanged after each decision.

    AC-5: resumeToolCall() reuses the same chat.id; no new conversation created.
    """
    chat_page = navigate_to_new_chat_page(page)
    test_assistant = _create_ask_for_approval_assistant(assistant, tool)

    # Capture the URL (contains the conversation ID) before sending the first message
    tool_prompt = get_approval_tool_prompt(tool)
    chat_page.send_message(message=tool_prompt, assistant_name=test_assistant.name)
    url_before_allow = page.url

    # Wait for the confirmation, then click Allow
    chat_page.wait_for_tool_call_confirmation()
    chat_page.click_allow_tool_call()
    chat_page.wait_for_assistant_response()

    url_after_allow = page.url
    assert_that(
        url_after_allow,
        equal_to(url_before_allow),
        f"URL changed after Allow — a new conversation was created.\n"
        f"  Before: {url_before_allow}\n  After:  {url_after_allow}",
    )

    # Trigger a second tool call and Deny it
    chat_page.send_message(message=tool_prompt)
    url_before_deny = page.url

    chat_page.wait_for_tool_call_confirmation()
    chat_page.click_deny_tool_call()
    chat_page.wait_for_assistant_response()

    url_after_deny = page.url
    assert_that(
        url_after_deny,
        equal_to(url_before_deny),
        f"URL changed after Deny — a new conversation was created.\n"
        f"  Before: {url_before_deny}\n  After:  {url_after_deny}",
    )


# ---------------------------------------------------------------------------
# TC_008 — Interrupted thought always visible regardless of hideToolOutputs
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
def test_interrupted_thought_visible_when_hide_tool_outputs_is_active(
    page,
    navigate_to_new_chat_page,
    assistant,
):
    """
    Even when 'Hide tool outputs' is enabled, the interrupted thought and
    Allow/Deny buttons must still render.  The frontend guard
    ``(!hideToolOutputs || thought.interrupted)`` always passes when
    interrupted=True.

    AC-7: The waiting indicator is always visible regardless of hideToolOutputs.
    """
    chat_page = navigate_to_new_chat_page(page)
    test_assistant = _create_ask_for_approval_assistant(assistant)

    # First message to get a response so we can open the config panel
    chat_page.send_message(message="Hello", assistant_name=test_assistant.name)
    chat_page.wait_for_assistant_response()

    # Enable 'Hide tool outputs' BEFORE triggering the tool call
    chat_page.open_configuration()
    config_panel = chat_page.chat_configuration_panel
    config_panel.enable_hide_tool_outputs()
    chat_page.close_configuration()

    # Now trigger the tool call
    tool_message = get_tool_invoking_message()
    chat_page.send_message(message=tool_message.content)

    # The interrupted thought and Allow/Deny buttons must still appear
    chat_page.should_have_tool_call_confirmation_visible()


# ---------------------------------------------------------------------------
# TC_009 — Standard chat (AUTO_APPROVE policy) shows no confirmation dialog
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize("tool", approval_research_tools)
def test_auto_approve_assistant_shows_no_confirmation_dialog(
    page,
    navigate_to_new_chat_page,
    assistant,
    tool,
):
    """
    An assistant using the default AUTO_APPROVE policy must NOT show a
    confirmation dialog — the tool executes automatically and the chat
    completes without pausing.

    AC-8: Standard auto-approve assistants never interrupt for tool approval.
    """
    chat_page = navigate_to_new_chat_page(page)
    # Create a standard assistant with NO tool_permissions override (AUTO_APPROVE)
    standard_assistant = assistant(Toolkit.RESEARCH.value, tool.value)

    chat_page.send_message(
        message=get_approval_tool_prompt(tool), assistant_name=standard_assistant.name
    )
    chat_page.wait_for_assistant_response()

    # No confirmation UI must appear — tool executed automatically
    chat_page.should_not_have_tool_call_confirmation_visible()


# ---------------------------------------------------------------------------
# TC_013 — Allow/Deny buttons suppressed in shared-page context
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
def test_allow_deny_buttons_suppressed_on_shared_page(
    page,
    navigate_to_new_chat_page,
    assistant,
):
    """
    On a shared-page URL (isSharedPage=true) the Allow and Deny buttons must
    NOT be rendered, even when thought.interrupted=True is present.  The
    interrupted thought text ('Tool call is waiting for user approval.') may
    still be visible, but the action controls must be absent.

    Frontend guard: Allow/Deny rendered only when
    ``!currentChat?.isWorkflow && !isSharedPage``.

    Note: The workflow sub-case is manual-for-now because the test harness
    does not have a pre-built tool chain that reliably triggers a second
    interrupt inside a workflow graph.
    """
    chat_page = navigate_to_new_chat_page(page)
    test_assistant = _create_ask_for_approval_assistant(assistant)

    # Trigger the tool call in a regular chat first
    tool_message = get_tool_invoking_message()
    chat_page.send_message(
        message=tool_message.content, assistant_name=test_assistant.name
    )
    chat_page.wait_for_tool_call_confirmation()

    # Navigate to the shared-page view of the same conversation.
    # Derive the URL properly: extract the chat ID from the current /chats/:id
    # path segment, obtain a share token via the API, then construct the URL
    # from the documented frontend router constant (/share/conversations/:token).
    # This avoids string-replacing the live URL, which is fragile if the router
    # path changes or if the substring appears in query params or hash.
    current_url = page.url
    parsed = urlparse(current_url)
    chat_id = parsed.path.rstrip("/").split("/")[-1]

    share_response = get_client().conversations.share_conversation(chat_id)
    shared_url = (
        f"{parsed.scheme}://{parsed.netloc}/share/conversations/{share_response.token}"
    )

    page.goto(shared_url)
    page.wait_for_load_state("networkidle")

    # Precondition: the interrupted thought must be visible so we know the page
    # loaded the correct conversation (prevents a vacuous pass on empty/wrong page).
    chat_page.should_have_interrupted_thought_visible(timeout=10000)

    # On the shared page: Allow and Deny buttons must not exist
    chat_page.should_not_have_allow_deny_buttons(timeout=10000)


# ---------------------------------------------------------------------------
# TC_015 — Per-chat policy override persists after navigation and page refresh
# ---------------------------------------------------------------------------


@pytest.mark.chat
@pytest.mark.ui
def test_per_chat_policy_override_persists_after_navigation_and_reload(
    page,
    two_conversations,
    assistant,
):
    """
    The per-chat policy override is stored per conversation.  After the user
    changes the policy picker in Chat A to 'Auto' and navigates to Chat B,
    then reloads and returns to Chat A, the picker must still show 'Auto'.
    Chat B's picker must remain at the assistant default ('Manual').

    Label constants verified against ToolCallPolicyDropdown.tsx POLICY_OPTIONS:
      ASK_FOR_APPROVAL → "Manual" (line 41), AUTO_APPROVE → "Auto" (line 52).
    """
    chat_id_a, chat_id_b = two_conversations
    ask_assistant = _create_ask_for_approval_assistant(assistant)

    # ── Open Chat A ──────────────────────────────────────────────────────────
    page.set_viewport_size({"width": 1920, "height": 980})
    chat_a = ChatPage(page)
    chat_a.navigate_to(chat_id_a)

    # Connect the ASK_FOR_APPROVAL assistant to Chat A
    chat_a.send_message(message="Hello", assistant_name=ask_assistant.name)
    chat_a.wait_for_assistant_response()

    # Default policy in Chat A must be "Manual" (ASK_FOR_APPROVAL)
    chat_a.should_have_tool_call_policy(_POLICY_LABEL_MANUAL)

    # Change the per-chat override to "Auto" via the policy picker
    chat_a.tool_call_policy_picker.click()
    page.get_by_role("option", name=_POLICY_LABEL_AUTO).click()
    chat_a.should_have_tool_call_policy(_POLICY_LABEL_AUTO)

    # Verify no dialog appears after the override takes effect
    tool_message = get_tool_invoking_message()
    chat_a.send_message(message=tool_message.content)
    chat_a.wait_for_assistant_response()
    chat_a.should_not_have_tool_call_confirmation_visible()

    # ── Open Chat B ──────────────────────────────────────────────────────────
    chat_b = ChatPage(page)
    chat_b.navigate_to(chat_id_b)
    chat_b.send_message(message="Hello", assistant_name=ask_assistant.name)
    chat_b.wait_for_assistant_response()

    # Chat B must still show the assistant default (Manual)
    chat_b.should_have_tool_call_policy(_POLICY_LABEL_MANUAL)

    # ── Reload and return to Chat A ──────────────────────────────────────────
    page.reload()
    page.wait_for_load_state("networkidle")
    chat_a.navigate_to(chat_id_a)

    # Per-chat override must have persisted through navigation and reload
    chat_a.should_have_tool_call_policy(_POLICY_LABEL_AUTO)
