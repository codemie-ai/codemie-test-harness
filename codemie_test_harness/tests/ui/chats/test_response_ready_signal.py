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
UI Test Suite — response-ready signal for a chat reply that finishes in a hidden tab.

When a reply finishes while the page is hidden, the tab title gets a
'Response ready - ' prefix, a screen-reader live region announces it, and a
'CodeMie' browser notification is raised when permission is already granted.
Returning to the tab clears the signal.

A headless run cannot switch tabs, so the page is reported as hidden through an
init script (document.hidden / visibilitychange) and the Notification constructor
is replaced by a recorder; see ResponseReadyTab. Real tab switching and the OS
notification are covered by manual cases.

Covers:
  TC_001  Hidden-tab reply prefixes the title and announces it; returning clears both
  TC_002  Granted permission: one 'CodeMie' / 'AI response is ready' notification
  TC_003  Visible-tab reply changes nothing
  TC_004  Title prefix works with permission default, denied or the API absent
  TC_005  No signal when the generation is stopped or its request is aborted
  TC_009  Reply that finishes after a mid-generation reload still signals ready
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.pageobject.chats.response_ready_tab import (
    ResponseReadyTab,
)
from codemie_test_harness.tests.ui.test_data.response_ready_test_data import (
    LONG_PROMPT,
    NOTIFICATION_BODY,
    NOTIFICATION_STATES_WITHOUT_GRANT,
    NOTIFICATION_TITLE,
    SHORT_PROMPT,
)


@pytest.fixture
def response_ready_tab(page):
    """Tab-signal page object with the hidden/visible control installed.

    Requested by the test (not used inside a factory) so the init script is in
    place before the test navigates to the chat.
    """
    return ResponseReadyTab(page).install_visibility_control()


@pytest.fixture
def granted_notifications(context, response_ready_tab):
    """Grant the notifications permission on the browser context and record Notification calls.

    The recorder reports 'granted' explicitly: headless Chromium does not reliably
    surface the context grant through Notification.permission, and the app only
    constructs a Notification when it sees 'granted'.
    """
    context.grant_permissions(["notifications"])
    response_ready_tab.record_notifications(permission="granted")


# @case notify-users-llm-response-completed_TC_001
@pytest.mark.chat
@pytest.mark.ui
def test_reply_finished_while_hidden_prefixes_title_and_is_cleared_on_return(
    page, response_ready_tab, slow_response_conversation
):
    """A reply that finishes in a hidden tab prefixes the title and fills the live
    region; marking the page visible restores the plain title and empties it."""
    chat_page = ChatPage(page)
    chat_page.navigate_to(slow_response_conversation)
    chat_page.should_have_chat_input_visible()
    response_ready_tab.remember_plain_title()

    response_ready_tab.mark_page_hidden()
    chat_page.send_message(LONG_PROMPT)
    chat_page.wait_for_generation_to_start()
    response_ready_tab.should_have_plain_title()
    response_ready_tab.should_have_empty_announcer()

    response_ready_tab.should_have_response_ready_title()
    response_ready_tab.should_announce_response_ready()

    response_ready_tab.mark_page_visible()
    response_ready_tab.should_have_plain_title()
    response_ready_tab.should_have_empty_announcer()


# @case notify-users-llm-response-completed_TC_002
@pytest.mark.chat
@pytest.mark.ui
def test_granted_permission_shows_one_notification_when_reply_finishes_hidden(
    page,
    response_ready_tab,
    granted_notifications,
    navigate_to_new_chat_page_with_assistant,
):
    """With permission granted and the page hidden, finishing a reply constructs exactly
    one Notification titled 'CodeMie' with the body 'AI response is ready'."""
    chat_page = navigate_to_new_chat_page_with_assistant(page)
    response_ready_tab.remember_plain_title()
    response_ready_tab.should_see_notification_permission("granted")

    response_ready_tab.mark_page_hidden()
    chat_page.send_message(SHORT_PROMPT)
    chat_page.should_have_message_sent(SHORT_PROMPT)

    response_ready_tab.should_have_response_ready_title()
    response_ready_tab.should_have_constructed_notification(
        NOTIFICATION_TITLE, NOTIFICATION_BODY
    )


# @case notify-users-llm-response-completed_TC_003
@pytest.mark.chat
@pytest.mark.ui
def test_reply_finished_while_visible_changes_nothing(
    page,
    response_ready_tab,
    granted_notifications,
    navigate_to_new_chat_page_with_assistant,
):
    """A reply that finishes while the tab is visible leaves the title plain, the live
    region empty and constructs no Notification."""
    chat_page = navigate_to_new_chat_page_with_assistant(page)
    response_ready_tab.remember_plain_title()
    response_ready_tab.should_see_notification_permission("granted")

    chat_page.send_message(SHORT_PROMPT)
    chat_page.wait_for_assistant_response()
    chat_page.wait_for_idle_state()

    response_ready_tab.should_have_plain_title()
    response_ready_tab.should_have_empty_announcer()
    response_ready_tab.should_have_constructed_notifications(0)


# @case notify-users-llm-response-completed_TC_004
@pytest.mark.chat
@pytest.mark.ui
@pytest.mark.parametrize(
    "state", NOTIFICATION_STATES_WITHOUT_GRANT, ids=lambda state: state.id
)
def test_title_prefix_is_applied_without_notification_permission(
    page, response_ready_tab, navigate_to_new_chat_page_with_assistant, state
):
    """Without a granted permission (default, denied or the API absent) the title prefix
    still appears when a reply finishes hidden, no Notification is constructed and no
    page error is raised."""
    response_ready_tab.record_notifications(
        permission=state.permission, supported=state.supported
    )
    chat_page = navigate_to_new_chat_page_with_assistant(page)
    response_ready_tab.remember_plain_title()
    response_ready_tab.start_collecting_page_errors()

    response_ready_tab.mark_page_hidden()
    chat_page.send_message(SHORT_PROMPT)
    chat_page.should_have_message_sent(SHORT_PROMPT)

    response_ready_tab.should_have_response_ready_title()
    response_ready_tab.should_have_constructed_notifications(0)
    response_ready_tab.should_have_no_page_errors()


# @case notify-users-llm-response-completed_TC_005
@pytest.mark.chat
@pytest.mark.ui
def test_no_signal_when_generation_is_stopped_while_hidden(
    page, response_ready_tab, granted_notifications, slow_response_conversation
):
    """Stopping a running generation while the page is hidden leaves the title plain
    and constructs no Notification."""
    chat_page = ChatPage(page)
    chat_page.navigate_to(slow_response_conversation)
    chat_page.should_have_chat_input_visible()
    response_ready_tab.remember_plain_title()
    response_ready_tab.should_see_notification_permission("granted")

    response_ready_tab.mark_page_hidden()
    chat_page.send_message(LONG_PROMPT)
    chat_page.wait_for_generation_to_start()
    chat_page.click_stop_generation()
    # An assistant chat has no step to resume after Stop, so "Send" comes back
    # (the "Continue" button exists only in workflow chats).
    chat_page.wait_for_idle_state()
    chat_page.should_have_send_button_visible()
    chat_page.should_not_have_stop_button_visible()

    response_ready_tab.should_have_plain_title()
    response_ready_tab.should_have_constructed_notifications(0)


# @case notify-users-llm-response-completed_TC_005
@pytest.mark.chat
@pytest.mark.ui
def test_no_signal_when_generation_request_is_aborted_while_hidden(
    page, response_ready_tab, granted_notifications, slow_response_conversation
):
    """Aborting the request that starts the generation while the page is hidden leaves
    the title plain and constructs no Notification."""
    chat_page = ChatPage(page)
    chat_page.navigate_to(slow_response_conversation)
    chat_page.should_have_chat_input_visible()
    response_ready_tab.remember_plain_title()

    response_ready_tab.mark_page_hidden()
    response_ready_tab.abort_model_request_during(
        lambda: chat_page.send_message(LONG_PROMPT)
    )
    chat_page.wait_for_idle_state()

    response_ready_tab.should_have_plain_title()
    response_ready_tab.should_have_constructed_notifications(0)


# @case notify-users-llm-response-completed_TC_009
@pytest.mark.chat
@pytest.mark.ui
def test_reply_finished_hidden_after_mid_generation_reload_still_signals_ready(
    page, response_ready_tab, slow_response_conversation
):
    """After a reload during generation, a reply that finishes while the page is hidden
    (observed through polling) prefixes the title."""
    chat_page = ChatPage(page)
    chat_page.navigate_to(slow_response_conversation)
    chat_page.should_have_chat_input_visible()
    response_ready_tab.remember_plain_title()

    chat_page.send_message(LONG_PROMPT)
    chat_page.wait_for_generation_to_start()
    response_ready_tab.reload_page()
    response_ready_tab.should_have_plain_title()

    response_ready_tab.mark_page_hidden()
    response_ready_tab.should_have_response_ready_title()
