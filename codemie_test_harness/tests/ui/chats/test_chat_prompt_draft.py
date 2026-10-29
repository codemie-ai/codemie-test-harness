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
UI Test Suite for Chat Prompt Draft Persistence

Verifies the full draft lifecycle: unsubmitted prompt box text is preserved per-chat
when the user switches between conversations; submitting the message clears the draft;
and neither chat history nor the empty prompt state is disrupted by subsequent navigation.

Coverage (merged TC-001 + TC-002):
  type draft in chat A → switch to chat B → switch back to chat A (verify preserved) →
  send the draft → verify cleared + message in history → switch to chat B →
  switch back to chat A → verify history intact and input still empty.

Architecture:
  - Function-based test (no class wrapper) per project conventions.
  - Fixtures injected via pytest parameters.
  - All assertions delegated to ChatPage should_* methods.
  - Cleanup handled exclusively by the `two_conversations` yield fixture.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.test_data.chat_test_data import DRAFT_TEXT


@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.ui
def test_draft_persists_until_sent_across_chat_navigation(page, two_conversations):
    """Comprehensive draft lifecycle test covering AC-1, AC-2, and AC-4.

    Flow:
    1. two_conversations fixture creates chat A and chat B via API.
    2. Navigate to chat A; type DRAFT_TEXT without sending.
    3. Switch to chat B — verify chat B input is empty.
    4. Switch back to chat A — verify draft is still present (AC-1, AC-2).
    5. Send the draft — verify input is empty and message appears in history (AC-4).
    6. Switch to chat B.
    7. Switch back to chat A — verify message still in history and input still empty
       (no ghost-restore of the sent draft; AC-1, AC-4).
    """
    chat_id_a, chat_id_b = two_conversations
    chat_page = ChatPage(page)
    page.set_viewport_size({"width": 1920, "height": 980})

    # Step 2: Navigate to chat A and type the draft
    chat_page.navigate_to(chat_id_a)
    chat_page.should_have_chat_input_visible()
    chat_page.type_message_without_sending(DRAFT_TEXT)

    # Step 3: Switch to chat B — must arrive with an empty input
    chat_page.navigate_to(chat_id_b)
    chat_page.should_have_chat_input_visible()
    chat_page.should_have_empty_chat_input()

    # Step 4: Switch back to chat A — draft must still be there (AC-1, AC-2)
    chat_page.navigate_to(chat_id_a)
    chat_page.should_have_chat_input_visible()
    chat_page.should_have_draft_preserved(DRAFT_TEXT)

    # Step 5: Send the draft — input cleared immediately (editor may briefly
    # unmount while the response generates); message visible in history.
    chat_page.send_message(DRAFT_TEXT)
    chat_page.should_have_draft_cleared_immediately_after_send()
    chat_page.should_have_message_sent(DRAFT_TEXT)

    # Once the response finishes generating, the composer must be empty again.
    chat_page.wait_for_assistant_response()
    chat_page.should_have_empty_chat_input()

    # Step 6: Switch to chat B
    chat_page.navigate_to(chat_id_b)
    chat_page.should_have_chat_input_visible()

    # Step 7: Switch back to chat A — history intact, no ghost draft restored (AC-4)
    chat_page.navigate_to(chat_id_a)
    chat_page.should_have_chat_input_visible()
    chat_page.should_have_message_sent(DRAFT_TEXT)
    chat_page.should_have_empty_chat_input()
