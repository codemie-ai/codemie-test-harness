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

"""Run attributes sent with a chat or a workflow execution are stored on the run and stay fixed."""

import uuid

import pytest
from hamcrest import assert_that, equal_to, greater_than, has_length
from requests import HTTPError

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.run_attributes_test_data import (
    ACCESS_DENIED_ON_CONVERSATION,
    ATTRIBUTES_IMMUTABLE_MESSAGE,
    CONVERSATION_NOT_FOUND,
    RUN_PROMPT,
    WORKFLOW_TASK,
    get_attributes,
)
from codemie_test_harness.tests.utils.assistant_utils import AssistantUtils
from codemie_test_harness.tests.utils.base_utils import assert_error_details
from codemie_test_harness.tests.utils.run_attributes_utils import (
    assert_error_message,
)


@pytest.mark.analytics
@pytest.mark.conversations
@pytest.mark.api
def test_assistant_chat_attributes_are_stored_on_the_conversation(
    assistant_factory, assistant_utils, conversation_utils
):
    # @case allow-callers-to-associate-custom_TC_001
    created_assistant = assistant_factory.create()
    conversation_id = str(uuid.uuid4())
    attributes = get_attributes(count=2)

    assistant_utils.ask_assistant(
        created_assistant,
        RUN_PROMPT,
        conversation_id=conversation_id,
        attributes=attributes,
    )

    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(
        conversation.attributes,
        equal_to(attributes),
        "the conversation must keep the attributes the chat was sent with",
    )


@pytest.mark.analytics
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_execution_attributes_are_stored_and_kept_after_completion(
    assistant_factory, workflow_with_assistant, workflow_utils
):
    # @case allow-callers-to-associate-custom_TC_002
    workflow = workflow_with_assistant(assistant_factory.create(), WORKFLOW_TASK)
    attributes = get_attributes(count=2)

    # Returns the execution read back after it has finished.
    completed_execution = workflow_utils.create_workflow_execution(
        workflow.id, user_input=RUN_PROMPT, attributes=attributes
    )

    assert_that(
        completed_execution.attributes,
        equal_to(attributes),
        "the execution must keep the attributes it was started with after it finished",
    )


@pytest.mark.analytics
@pytest.mark.conversations
@pytest.mark.api
def test_attributes_of_a_conversation_with_history_cannot_be_changed(
    assistant_factory, assistant_utils, conversation_utils
):
    # @case allow-callers-to-associate-custom_TC_004
    created_assistant = assistant_factory.create()
    conversation_id = str(uuid.uuid4())
    original_attributes = get_attributes()
    assistant_utils.ask_assistant(
        created_assistant,
        RUN_PROMPT,
        conversation_id=conversation_id,
        attributes=original_attributes,
    )

    with pytest.raises(HTTPError) as exc_info:
        assistant_utils.ask_assistant(
            created_assistant,
            RUN_PROMPT,
            conversation_id=conversation_id,
            attributes=get_attributes(),
        )

    assert_error_message(exc_info.value.response, 422, ATTRIBUTES_IMMUTABLE_MESSAGE)
    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(
        conversation.attributes,
        equal_to(original_attributes),
        "the rejected request must leave the attributes of the conversation as they were",
    )


@pytest.mark.analytics
@pytest.mark.conversations
@pytest.mark.api
def test_other_user_cannot_set_attributes_on_an_unreadable_conversation(
    assistant_factory,
    assistant_utils,
    conversation_utils,
    client,
    user_utils,
    non_admin_user,
):
    """The second user's attributes are dropped, but the request is still refused 403.

    The refusal comes from the conversation access check, not from the attributes: the
    same user chats on a conversation of their own with the same assistant, and the chat
    on the owner's conversation is refused with or without attributes.
    """
    # @case allow-callers-to-associate-custom_TC_011
    created_assistant = assistant_factory.create()
    conversation_id = str(uuid.uuid4())
    owner_attributes = get_attributes()
    assistant_utils.ask_assistant(
        created_assistant,
        RUN_PROMPT,
        conversation_id=conversation_id,
        attributes=owner_attributes,
    )
    history_before = conversation_utils.get_conversation_by_id(conversation_id).history
    _, other_user_id, other_client = non_admin_user
    # The other user may chat with the assistant, but has no access to the owner's conversation.
    user_utils.assign_user_to_project(other_user_id, PROJECT)
    client.assistants.share(created_assistant.id, [other_user_id])
    other_assistant_utils = AssistantUtils(other_client)

    other_assistant_utils.ask_assistant(
        created_assistant,
        RUN_PROMPT,
        conversation_id=str(uuid.uuid4()),
        attributes=get_attributes(),
    )
    with pytest.raises(HTTPError) as rejected:
        other_assistant_utils.ask_assistant(
            created_assistant,
            RUN_PROMPT,
            conversation_id=conversation_id,
            attributes=get_attributes(),
        )

    assert_error_details(
        rejected.value.response,
        403,
        ACCESS_DENIED_ON_CONVERSATION.format(conversation_id=conversation_id),
    )
    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(
        conversation.attributes,
        equal_to(owner_attributes),
        "attributes of a user without access must not reach the owner's conversation",
    )
    assert_that(
        conversation.history[: len(history_before)],
        equal_to(history_before),
        "the turns the owner had must stay as they were",
    )


@pytest.mark.analytics
@pytest.mark.conversations
@pytest.mark.api
def test_chat_without_saved_history_stores_no_conversation(
    assistant_factory, assistant_utils, conversation_utils
):
    # @case allow-callers-to-associate-custom_TC_012
    created_assistant = assistant_factory.create()
    conversation_id = str(uuid.uuid4())

    answer = assistant_utils.ask_assistant(
        created_assistant,
        RUN_PROMPT,
        conversation_id=conversation_id,
        attributes=get_attributes(),
        save_history=False,
    )

    assert_that(answer, has_length(greater_than(0)), "the chat must still be answered")
    with pytest.raises(HTTPError) as exc_info:
        conversation_utils.get_conversation_by_id(conversation_id)
    assert_error_details(
        exc_info.value.response,
        404,
        CONVERSATION_NOT_FOUND.format(conversation_id=conversation_id),
    )
