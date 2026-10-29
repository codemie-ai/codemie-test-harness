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

"""Assistant-message feedback submission.

Negative (dislike) feedback could not be submitted from the "Submit Feedback
About This Assistant" modal: the frontend posted a payload without the
backend-required `response` field, so POST /v1/feedback always returned a 422
`response: Field required` error and the modal never closed. The fix (already
live in codemie-ui) threads the assistant's response text through the
feedback payload.

Two tests, two different jobs:
- The positive test goes through the SDK and pins the now-working contract:
  a well-formed payload (including `response`) succeeds and round-trips
  through conversation history.
- The negative test intentionally bypasses the SDK for the POST call: the
  SDK's `FeedbackCreateRequest` model requires `response`, so it cannot
  construct the exact broken payload the old frontend sent. A raw request is
  the only way to reproduce the ticket's reported symptom, so it pins that
  exact 422 directly at the wire level.

Evidence:
- codemie/src/codemie/rest_api/models/feedback.py:60 (FeedbackRequest.response, required)
- codemie/src/codemie/rest_api/routers/feedback.py:58 (POST /v1/feedback)
- codemie-ui/src/store/chats.ts:612 (submitFeedback payload, includes `response`)
"""

import pytest
import requests
from codemie_sdk.models.conversation import FeedbackMark
from hamcrest import assert_that, equal_to, is_not, none

from codemie_test_harness.tests.utils.base_utils import assert_response, get_random_name
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_submit_and_delete_negative_feedback_on_assistant_response(
    assistant, assistant_utils, conversation_utils
):
    """Regression: dislike feedback must succeed and clean up."""
    assistant_obj = assistant()
    prompt = f"prompt {get_random_name()}"
    assistant_utils.ask_assistant(assistant_obj, prompt)

    conversation = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )[0]
    conversation_id = conversation.id

    conversation_details = conversation_utils.get_conversation_by_id(conversation_id)
    message_index = len(conversation_details.history) - 1
    assistant_response = conversation_details.history[message_index].message

    result = conversation_utils.submit_feedback(
        conversation_id=conversation_id,
        message_index=message_index,
        assistant_id=assistant_obj.id,
        request=prompt,
        response=assistant_response,
        mark=FeedbackMark.WRONG,
        comments="Not helpful",
        feedback_type="Other",
    )
    assert_that(result.id, is_not(none()))

    updated = conversation_utils.get_conversation_by_id(conversation_id)
    user_mark = updated.history[message_index].userMark
    assert_that(user_mark, is_not(none()))
    assert_that(user_mark.mark, equal_to(FeedbackMark.WRONG))
    assert_that(user_mark.comments, equal_to("Not helpful"))
    assert_that(user_mark.feedback_id, equal_to(result.id))

    conversation_utils.delete_feedback(
        conversation_id=conversation_id,
        feedback_id=result.id,
        message_index=message_index,
        assistant_id=assistant_obj.id,
    )

    cleaned = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(cleaned.history[message_index].userMark, none())


@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_feedback_rejects_payload_missing_response_field(
    assistant, assistant_utils, conversation_utils, client
):
    """Pins the exact 422 at the wire level.

    The SDK's FeedbackCreateRequest model requires `response`, so it can't be
    used to build the broken payload the old frontend sent -- there's no SDK
    way to reproduce this, so the POST here is a raw request instead.
    """
    assistant_obj = assistant()
    prompt = f"prompt {get_random_name()}"
    assistant_utils.ask_assistant(assistant_obj, prompt)

    conversation = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )[0]
    conversation_id = conversation.id
    conversation_details = conversation_utils.get_conversation_by_id(conversation_id)
    message_index = len(conversation_details.history) - 1

    payload = {
        "conversationId": conversation_id,
        "messageIndex": message_index,
        "author": "user",
        "mark": "wrong",
        "comments": "Not helpful",
        "request": prompt,
        # `response` intentionally omitted -- this is the reported defect: the
        # old frontend payload didn't include it either.
        "type": "Other",
        "assistant_id": assistant_obj.id,
    }

    api_domain = CredentialsManager.get_parameter("CODEMIE_API_DOMAIN").rstrip("/")
    verify_ssl = (
        CredentialsManager.get_parameter("VERIFY_SSL", "false").lower() == "true"
    )

    response = requests.post(
        f"{api_domain}/v1/feedback",
        json=payload,
        headers={"Authorization": f"Bearer {client.token}"},
        verify=verify_ssl,
    )

    assert_response(response, 422, "Field required")
