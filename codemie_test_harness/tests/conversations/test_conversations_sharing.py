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

import re

import pytest
from codemie_sdk.models.assistant import AssistantChatRequest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_item,
    has_property,
)

from codemie_test_harness.tests import TEST_USER
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_error_details,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.constants import FILES_PATH
from codemie_test_harness.tests.utils.conversation_utils import ConversationUtils
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_share_conversation_basic(assistant, assistant_utils, conversation_utils):
    """Test basic conversation sharing - create share link for a conversation."""
    # Create an assistant and have a conversation
    assistant = assistant()
    prompt = f"Hello, this is a test message {get_random_name()}"

    # Create conversation with some history
    assistant_utils.ask_assistant(assistant, prompt)

    # Get the conversation
    conversations = conversation_utils.get_conversation_by_assistant_id(assistant.id)
    conversation_id = conversations[0].id

    # Share the conversation
    share_response = conversation_utils.share_conversation(conversation_id)

    # Verify share response structure
    assert_that(share_response, has_property("token"))
    assert_that(share_response, has_property("share_id"))
    assert_that(share_response.share_id, equal_to(f"share_{conversation_id}"))

    # Get shared conversation
    shared_conversation = conversation_utils.get_shared_conversation(
        share_response.token
    )

    # Verify shared conversation details
    assert_that(shared_conversation.conversation.id, equal_to(conversation_id))
    assert_that(
        shared_conversation.conversation.history[0].message, contains_string(prompt)
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_share_conversation_with_multiple_messages(
    assistant, assistant_utils, conversation_utils
):
    """Test sharing a conversation with multiple back-and-forth messages."""

    # Create an assistant and have multiple conversations
    assistant = assistant()
    message1 = f"First message {get_random_name()}"
    message2 = f"Second message {get_random_name()}"
    message3 = f"Third message {get_random_name()}"

    # Send first message
    assistant_utils.ask_assistant(assistant, message1)

    # Get conversation ID
    conversations = conversation_utils.get_conversation_by_assistant_id(assistant.id)
    conversation_id = conversations[0].id

    # Send additional messages in the same conversation
    chat_request2 = AssistantChatRequest(text=message2, conversation_id=conversation_id)
    assistant_utils.send_chat_request(assistant, chat_request2)

    chat_request3 = AssistantChatRequest(text=message3, conversation_id=conversation_id)
    assistant_utils.send_chat_request(assistant, chat_request3)

    # Share the conversation
    share_response = conversation_utils.share_conversation(conversation_id)

    # Get shared conversation
    shared_conversation = conversation_utils.get_shared_conversation(
        share_response.token
    )

    # Verify shared conversation details
    assert_that(shared_conversation.conversation.id, equal_to(conversation_id))
    assert_that(
        shared_conversation.conversation.history[0].message, contains_string(message1)
    )
    assert_that(shared_conversation.conversation.history[2].message, equal_to(message2))
    assert_that(shared_conversation.conversation.history[4].message, equal_to(message3))


@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
@pytest.mark.skipif(
    not EnvironmentResolver.is_preview(),
    reason="Default test user created only on preview environment",
)
def test_share_conversation_different_user_access(
    assistant, assistant_utils, conversation_utils
):
    """Test that a different user can access a shared conversation via token."""
    # User 1: Create and share conversation
    assistant = assistant()
    prompt = f"Hello, this is a test message {get_random_name()}"
    assistant_utils.ask_assistant(assistant, prompt)

    conversations = conversation_utils.get_conversation_by_assistant_id(assistant.id)
    conversation_id = conversations[0].id

    # User 1 shares the conversation
    share_response = conversation_utils.share_conversation(conversation_id)
    share_token = share_response.token

    # User 2: Create a different client with different credentials
    user2_client = get_client(
        username=CredentialsManager.get_parameter("AUTH_USERNAME_DEFAULT"),
        password=CredentialsManager.get_parameter("AUTH_PASSWORD_DEFAULT"),
    )
    user2_conversation_utils = ConversationUtils(user2_client)

    # User 2 accesses the shared conversation
    shared_conversation = user2_conversation_utils.get_shared_conversation(share_token)

    # Verify shared conversation details
    assert_that(shared_conversation.conversation.id, equal_to(conversation_id))
    assert_that(
        shared_conversation.conversation.history[0].message, contains_string(prompt)
    )
    assert_that(shared_conversation.conversation.user_name, equal_to(TEST_USER))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_access_conversation_multiple_times(
    assistant, assistant_utils, conversation_utils
):
    """Test sharing the same conversation multiple times with the same tokens."""
    # Create an assistant and have a conversation
    assistant = assistant()
    prompt = f"Hello, this is a test message {get_random_name()}"

    # Create conversation with some history
    assistant_utils.ask_assistant(assistant, prompt)

    # Get the conversation
    conversations = conversation_utils.get_conversation_by_assistant_id(assistant.id)
    conversation_id = conversations[0].id

    # Share the conversation
    share_response = conversation_utils.share_conversation(conversation_id)

    # Verify access count from response
    assert_that(share_response.access_count, equal_to(0))

    # Get shared conversation
    for _ in range(3):
        conversation_utils.get_shared_conversation(share_response.token)

    # Get access count from the response
    share_response = conversation_utils.share_conversation(conversation_id)

    # Verify share response structure
    assert_that(share_response.access_count, equal_to(3))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_share_conversation_with_file_attachment(
    assistant, assistant_utils, conversation_utils
):
    """Test sharing a conversation that contains file attachments."""

    assistant = assistant()
    prompt = f"Analyze this file {get_random_name()}"

    # Upload a file
    uploaded_file = assistant_utils.upload_file_to_chat(FILES_PATH / "test.txt")
    file_url = uploaded_file.get("file_url")

    # Send message with file attachment
    assistant_utils.ask_assistant(assistant, prompt, file_urls=[file_url])

    # Get conversation
    conversations = conversation_utils.get_conversation_by_assistant_id(assistant.id)
    conversation_id = conversations[0].id

    # Share the conversation
    share_response = conversation_utils.share_conversation(conversation_id)

    # Access shared conversation
    shared_conversation = conversation_utils.get_shared_conversation(
        share_response.token
    )

    # Verify shared conversation details
    assert_that(shared_conversation.conversation.id, equal_to(conversation_id))
    assert_that(
        shared_conversation.conversation.history[0].message, contains_string(prompt)
    )
    assert_that(
        shared_conversation.conversation.history[0].fileNames, has_item(file_url)
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_share_conversation_updated_after_sharing(
    assistant, assistant_utils, conversation_utils
):
    """Test that updates to conversation after sharing are reflected in shared view."""
    # Create an assistant and have a conversation
    assistant = assistant()
    prompt = f"Hello, this is a test message {get_random_name()}"

    # Create conversation with some history
    assistant_utils.ask_assistant(assistant, prompt)

    # Get the conversation
    conversations = conversation_utils.get_conversation_by_assistant_id(assistant.id)
    conversation_id = conversations[0].id

    # Share the conversation
    share_response = conversation_utils.share_conversation(conversation_id)
    share_token = share_response.token

    # Get shared conversation
    shared_conversation = conversation_utils.get_shared_conversation(share_token)

    # Verify shared conversation details
    assert_that(shared_conversation.conversation.id, equal_to(conversation_id))
    assert_that(
        shared_conversation.conversation.history[0].message, contains_string(prompt)
    )

    # Add more messages after sharing
    additional_message = f"Message after sharing {get_random_name()}"
    chat_request = AssistantChatRequest(
        text=additional_message, conversation_id=conversation_id
    )
    assistant_utils.send_chat_request(assistant, chat_request)

    # Access shared conversation again
    shared_conversation = conversation_utils.get_shared_conversation(share_token)

    # Verify all messages are visible in the shared view
    assert_that(shared_conversation.conversation.id, equal_to(conversation_id))
    assert_that(
        shared_conversation.conversation.history[0].message, contains_string(prompt)
    )
    assert_that(
        shared_conversation.conversation.history[2].message,
        equal_to(additional_message),
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.conversations
@pytest.mark.api
def test_share_workflow_conversation(
    conversation_utils,
    workflow_with_virtual_assistant,
    workflow_utils,
):
    """Test workflow conversation sharing - create share link for a conversation."""
    # Create workflow with virtual assistant
    assistant_and_state_name = get_random_name()

    created_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        system_prompt="You are the math expert. Do not format output as markdown",
    )

    # Create workflow conversation
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    # Send chat message via workflow execution
    user_message = "Solve it, only answer: 2+2*2"
    workflow_utils.create_workflow_execution(
        workflow_id=created_workflow.id,
        user_input=user_message,
        conversation_id=conversation_id,
    )

    # Share the conversation
    share_response = conversation_utils.share_conversation(conversation_id)

    # Get shared conversation
    shared_conversation = conversation_utils.get_shared_conversation(
        share_response.token
    )

    # Verify shared conversation details
    assert_that(shared_conversation.conversation.id, equal_to(conversation_id))
    assert_that(
        shared_conversation.conversation.history[0].message,
        contains_string(user_message),
    )
    assert_that(
        re.sub(
            r"\D", "", shared_conversation.conversation.history[1].thoughts[0].message
        ),
        equal_to("6"),
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_share_nonexistent_conversation(conversation_utils):
    """Test sharing a conversation that doesn't exist returns appropriate error."""
    invalid_conversation_id = f"invalid_{get_random_name()}"

    # Attempt to share non-existent conversation
    with pytest.raises(Exception) as exec_info:
        conversation_utils.share_conversation(invalid_conversation_id)

    # Verify error response
    assert_error_details(
        exec_info.value.response,
        404,
        f"The conversation with ID [{invalid_conversation_id}] could not be found in the system.",
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_access_shared_conversation_invalid_token(conversation_utils):
    """Test accessing a shared conversation with invalid token returns error."""
    invalid_token = f"invalid_token_{get_random_name()}"

    # Attempt to access with invalid token
    with pytest.raises(Exception) as exec_info:
        conversation_utils.get_shared_conversation(invalid_token)

    # Verify error response
    assert_error_details(
        exec_info.value.response,
        404,
        "The shared conversation you're trying to access doesn't exist or has been removed.",
    )
