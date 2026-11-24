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

"""Fixtures for the conversation tests."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

import pytest
from codemie_sdk.models.conversation import FeedbackMark, HistoryItem

from codemie_test_harness.tests.test_data.feedback_test_data import (
    FeedbackSeed,
    feedback_seed,
)
from codemie_test_harness.tests.utils.conversation_utils import (
    CLI_IMPORT_ASSISTANT_ID,
    ConversationUtils,
)

logger = logging.getLogger(__name__)

# Index of the assistant answer in the history built below: the question is item 0.
ANSWER_MESSAGE_INDEX = 1


@dataclass
class FeedbackConversation:
    """A conversation with one question and one answer, owned by ``owner``.

    ``feedback_id`` is None when the conversation was created without feedback.
    """

    owner: object
    conversation_id: str
    message_index: int
    assistant_id: str
    seed: FeedbackSeed
    feedback_id: str | None = None


@pytest.fixture
def feedback_conversation():
    """Factory: create a conversation owned by a user, optionally with feedback on its answer.

    The conversation is written through the history upsert with the owner's own client, so
    no LLM call is made. Request the owner fixtures before this one: teardown runs in the
    reverse order and uses the owner's client to remove the feedback and the conversation.
    """
    created: list[FeedbackConversation] = []

    def _create(owner, with_feedback: bool = True) -> FeedbackConversation:
        utils = ConversationUtils(owner.client)
        seed = feedback_seed()
        conversation_id = str(uuid.uuid4())
        now = datetime.now()
        history = [
            HistoryItem(
                role="User",
                message=seed.request,
                historyIndex=0,
                date=now,
                fileNames=[],
            ),
            HistoryItem(
                role="Assistant",
                message=seed.response,
                historyIndex=0,
                date=now,
                fileNames=[],
            ),
        ]
        utils.upsert_history(
            conversation_id, history, assistant_id=CLI_IMPORT_ASSISTANT_ID
        )
        item = FeedbackConversation(
            owner=owner,
            conversation_id=conversation_id,
            message_index=ANSWER_MESSAGE_INDEX,
            assistant_id=CLI_IMPORT_ASSISTANT_ID,
            seed=seed,
        )
        created.append(item)
        if with_feedback:
            item.feedback_id = utils.submit_feedback(
                conversation_id=conversation_id,
                message_index=ANSWER_MESSAGE_INDEX,
                assistant_id=CLI_IMPORT_ASSISTANT_ID,
                request=seed.request,
                response=seed.response,
                mark=FeedbackMark.WRONG,
                comments=seed.comments,
                feedback_type="Other",
            ).id
        return item

    yield _create

    for item in created:
        utils = ConversationUtils(item.owner.client)
        try:
            if item.feedback_id:
                utils.delete_feedback(
                    conversation_id=item.conversation_id,
                    feedback_id=item.feedback_id,
                    message_index=item.message_index,
                    assistant_id=item.assistant_id,
                )
        except Exception:
            logger.warning(
                "Cleanup leaked feedback %s on conversation %s",
                item.feedback_id,
                item.conversation_id,
                exc_info=True,
            )
        try:
            utils.delete_conversation(item.conversation_id)
        except Exception:
            logger.warning(
                "Cleanup leaked conversation %s",
                item.conversation_id,
                exc_info=True,
            )
