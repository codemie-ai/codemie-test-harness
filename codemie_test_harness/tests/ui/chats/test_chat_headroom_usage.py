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

"""Chat header Usage details shows the tokens Headroom saved.

Needs a stand with features:headroom on, HEADROOM_MODE sdk or sidecar, and the
usage-details chat feature on.
"""

import pytest
from requests import HTTPError

from codemie_sdk.models.conversation import ConversationCreateRequest
from codemie_test_harness.tests.test_data.headroom_test_data import (
    CHAT_HEADROOM_AGGRESSIVE,
    repetitive_log_prompt,
)
from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage

# A reply to a long input takes longer than the default wait.
REPLY_TIMEOUT_MS = 180000


@pytest.fixture
def headroom_conversation_id(client, assistant_factory, default_llm):
    """A new conversation with an assistant that compresses with the aggressive strategy."""
    assistant = assistant_factory.create(
        llm_model_type=default_llm.base_name, headroom_config=CHAT_HEADROOM_AGGRESSIVE
    )
    conversation = client.conversations.create(
        ConversationCreateRequest(initial_assistant_id=assistant.id, folder="")
    )
    yield conversation.get("id")
    try:
        client.conversations.delete(conversation.get("id"))
    except HTTPError:
        pass


# @case headroom-per-assistant-workflow-configuration_TC_013
@pytest.mark.assistant
@pytest.mark.ui
def test_chat_usage_details_show_tokens_saved_by_headroom(
    page, headroom_conversation_id
):
    chat_page = ChatPage(page)
    chat_page.open_conversation(headroom_conversation_id)

    chat_page.send_message_and_wait_for_reply(
        repetitive_log_prompt(), reply_number=1, timeout=REPLY_TIMEOUT_MS
    )
    chat_page.open_usage_details()
    chat_page.should_show_headroom_tokens_saved()
