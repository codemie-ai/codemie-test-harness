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

"""Assistant chat survives a page reload while the LLM is still replying.

Bug (ticket STR): open a chat, send a message, and reload the page while the
assistant is still generating its reply — the conversation is interrupted/lost
completely instead of the user eventually receiving the reply they asked for.

Verified live (2026-09-23): reloading mid-generation keeps
the user's message and, once the in-flight reply is hydrated/resumed, shows a
non-blank assistant response — matching the ticket's expected result.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage


@pytest.mark.sanity
@pytest.mark.chat
@pytest.mark.conversations
@pytest.mark.ui
@pytest.mark.prod_regression
def test_conversation_survives_reload_during_generation(
    page, slow_response_conversation
):
    """Reloading the page while the assistant is still generating a reply must not
    lose the conversation: the user's message stays visible and the assistant
    eventually renders a non-blank response instead of the turn being dropped."""
    chat_page = ChatPage(page)
    chat_page.navigate_to(slow_response_conversation)
    chat_page.should_have_chat_input_visible()

    message = "Explain the history of the Roman Empire"
    chat_page.send_message(message)
    chat_page.wait_for_generation_to_start()

    # Not networkidle: the resumed reply is delivered over a long-lived
    # GET .../stream connection, so the network never goes idle until the
    # reply finishes — waiting on it here would just race the LLM call.
    page.reload()
    page.wait_for_load_state("domcontentloaded")

    chat_page.should_have_message_sent(message)
    chat_page.should_have_non_blank_assistant_response()
