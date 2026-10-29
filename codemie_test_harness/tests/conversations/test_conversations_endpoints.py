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

import pytest
from codemie_sdk.models.conversation import Conversation, ConversationDetails
from codemie_sdk.models.assistant import AssistantChatRequest
from hamcrest import (
    assert_that,
    has_length,
    instance_of,
    all_of,
    has_property,
    greater_than_or_equal_to,
    has_item,
    equal_to,
    has_entry,
    has_key,
    contains_string,
)

from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_error_details,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_list_conversations(assistant, assistant_utils, conversation_utils):
    assistant = assistant()
    assistant_utils.ask_assistant(assistant, f"prompt {get_random_name()}")

    conversations = conversation_utils.list_conversations()

    assert_that(conversations, instance_of(list))
    assert_that(conversations, has_length(greater_than_or_equal_to(1)))

    conversation = conversations[0]
    assert_that(
        conversation,
        all_of(
            instance_of(Conversation),
            has_property("id"),
            has_property("name"),
            has_property("folder"),
            has_property("pinned"),
            has_property("date"),
            has_property("assistant_ids", instance_of(list)),
            has_property("initial_assistant_id"),
        ),
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_get_specific_conversation(assistant, assistant_utils, conversation_utils):
    prompt = f"prompt {get_random_name()}"
    assistant = assistant()

    assistant_utils.ask_assistant(assistant, prompt)

    conversations = conversation_utils.list_conversations()

    first_conversation = conversations[0]
    conversation = conversation_utils.get_conversation_by_id(first_conversation.id)
    assert_that(
        conversation,
        all_of(
            instance_of(ConversationDetails),
            has_property("id", first_conversation.id),
            has_property("conversation_name", contains_string(prompt)),
            has_property("initial_assistant_id", assistant.id),
        ),
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_get_conversation_by_assistant_id(
    assistant, assistant_utils, conversation_utils
):
    prompt = f"prompt {get_random_name()}"
    assistant = assistant()

    assistant_utils.ask_assistant(assistant, prompt)
    conversation = conversation_utils.get_conversation_by_assistant_id(assistant.id)
    assert_that(
        conversation[0],
        all_of(
            instance_of(Conversation),
            has_property("id", conversation[0].id),
            has_property("name", contains_string(prompt)),
            has_property("assistant_ids", has_item(assistant.id)),
            has_property("initial_assistant_id", assistant.id),
        ),
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_delete_conversation(assistant, assistant_utils, conversation_utils):
    prompt = f"prompt {get_random_name()}"
    assistant = assistant()

    assistant_utils.ask_assistant(assistant, prompt)
    conversation = conversation_utils.get_conversation_by_assistant_id(assistant.id)

    delete_response = conversation_utils.delete_conversation(conversation[0].id)
    assert_that(
        delete_response["message"],
        equal_to("Specified conversation removed"),
        "Conversation delete response is not as expected.",
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_get_non_existent_conversation(assistant, assistant_utils, conversation_utils):
    invalid_id = get_random_name()
    with pytest.raises(Exception) as exc_info:
        conversation_utils.get_conversation_by_id(invalid_id)

    error_response = exc_info.value.response.json()
    assert_that(
        error_response["error"],
        all_of(
            has_entry("message", "Conversation not found"),
            has_entry(
                "details",
                f"The conversation with ID [{invalid_id}] could not be found in the system.",
            ),
            has_entry(
                "help",
                "Please verify the conversation ID and try again. If you believe this is an error, contact support.",
            ),
        ),
    )


# ==================== Core Conversation Operations Tests ====================


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_create_conversation(assistant, conversation_utils):
    """Test creating a new conversation with initial assistant."""
    assistant_obj = assistant()

    # Create conversation with assistant
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=assistant_obj.id,
    )

    assert_that(created_conv, has_key("id"))
    conversation_id = created_conv["id"]

    # Verify conversation was created correctly
    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(
        conversation,
        all_of(
            has_property("id", conversation_id),
            has_property("initial_assistant_id", assistant_obj.id),
        ),
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_create_conversation_with_folder(assistant, conversation_utils):
    """Test creating a conversation in a specific folder."""
    assistant_obj = assistant()
    folder_name = f"test_folder_{get_random_name()}"

    # Create conversation in folder
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=assistant_obj.id, folder=folder_name
    )

    conversation_id = created_conv["id"]

    # Verify conversation is in the folder
    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation, has_property("folder", folder_name))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_update_conversation_name(assistant, assistant_utils, conversation_utils):
    """Test updating a conversation's name."""
    assistant_obj = assistant()
    initial_prompt = f"prompt {get_random_name()}"
    new_name = f"updated_name_{get_random_name()}"

    # Create conversation
    assistant_utils.ask_assistant(assistant_obj, initial_prompt)
    conversations = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )
    conversation_id = conversations[0].id

    # Update conversation name
    updated_conv = conversation_utils.update_conversation(
        conversation_id, name=new_name
    )

    assert_that(updated_conv, has_property("conversation_name", new_name))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_update_conversation_pin_status(assistant, assistant_utils, conversation_utils):
    """Test pinning and unpinning a conversation."""
    assistant_obj = assistant()
    prompt = f"prompt {get_random_name()}"

    # Create conversation
    assistant_utils.ask_assistant(assistant_obj, prompt)
    conversations = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )
    conversation_id = conversations[0].id

    # Pin conversation
    updated_conv = conversation_utils.update_conversation(conversation_id, pinned=True)
    assert_that(updated_conv, has_property("pinned", True))

    # Unpin conversation
    updated_conv = conversation_utils.update_conversation(conversation_id, pinned=False)
    assert_that(updated_conv, has_property("pinned", False))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_update_conversation_folder(assistant, assistant_utils, conversation_utils):
    """Test moving a conversation to a different folder."""
    assistant_obj = assistant()
    prompt = f"prompt {get_random_name()}"
    folder1 = f"folder1_{get_random_name()}"
    folder2 = f"folder2_{get_random_name()}"

    # Create conversation
    assistant_utils.ask_assistant(assistant_obj, prompt)
    conversations = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )
    conversation_id = conversations[0].id

    # Move to folder1
    updated_conv = conversation_utils.update_conversation(
        conversation_id, folder=folder1
    )
    assert_that(updated_conv, has_property("folder", folder1))

    # Move to folder2
    updated_conv = conversation_utils.update_conversation(
        conversation_id, folder=folder2
    )
    assert_that(updated_conv, has_property("folder", folder2))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_get_conversation_files(assistant, assistant_utils, conversation_utils):
    """Test getting list of files attached to a conversation."""
    assistant_obj = assistant()
    prompt = f"prompt {get_random_name()}"

    # Create conversation
    assistant_utils.ask_assistant(assistant_obj, prompt)
    conversations = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )
    conversation_id = conversations[0].id

    # Get files (should be empty or a list)
    files = conversation_utils.get_conversation_files(conversation_id)
    assert_that(files, instance_of(list))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
@pytest.mark.file
def test_get_conversation_files_with_uploaded_file(
    assistant, assistant_utils, conversation_utils
):
    """Test getting list of files when a file is uploaded to conversation."""
    assistant_obj = assistant()
    prompt = f"Analyze this file: {get_random_name()}"

    # Upload a file
    uploaded_file = assistant_utils.upload_file_to_chat(
        FILES_PATH / "test_extended.xlsx"
    )
    file_url = uploaded_file.get("file_url")

    # Send message with the uploaded file
    assistant_utils.ask_assistant(assistant_obj, prompt, file_urls=[file_url])

    # Get conversation
    conversations = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )
    conversation_id = conversations[0].id

    # Get files - should contain the uploaded file
    files = conversation_utils.get_conversation_files(conversation_id)
    assert_that(files, instance_of(list))
    assert_that(files, has_length(greater_than_or_equal_to(1)))
    assert_that(file_url in files)


@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_delete_all_conversations(assistant, assistant_utils, conversation_utils):
    """Test deleting all conversations for the current user."""
    # Create multiple conversations
    assistant1 = assistant()
    assistant2 = assistant()

    assistant_utils.ask_assistant(assistant1, f"prompt1 {get_random_name()}")
    assistant_utils.ask_assistant(assistant2, f"prompt2 {get_random_name()}")

    # Verify conversations exist
    conversations_before = conversation_utils.list_conversations()
    assert_that(conversations_before, has_length(greater_than_or_equal_to(2)))

    # Delete all conversations
    result = conversation_utils.delete_all_conversations()
    assert_that(result, has_property("message"))

    # Verify all conversations are deleted
    conversations_after = conversation_utils.list_conversations()
    assert_that(conversations_after, has_length(0))


# ==================== Folder Management Tests ====================


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_create_and_list_folders(conversation_utils):
    """Test creating folders and listing them."""
    folder_name = f"test_folder_{get_random_name()}"

    # Create folder
    result = conversation_utils.create_folder(folder_name)
    assert_that(result, has_property("message", "Folder created"))

    # List folders
    folders = conversation_utils.list_folders()
    assert_that(folders, instance_of(list))

    # Verify folder structure if any folders exist
    first_folder = folders[0]
    assert_that(
        first_folder,
        all_of(
            has_property("id"),
            has_property("folder_name"),
            has_property("user_id"),
            has_property("date"),
        ),
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_update_folder_name(assistant, assistant_utils, conversation_utils):
    """Test renaming a conversation folder."""
    old_folder_name = f"old_folder_{get_random_name()}"
    new_folder_name = f"new_folder_{get_random_name()}"

    # Create a conversation in a folder
    assistant_obj = assistant()
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=assistant_obj.id, folder=old_folder_name
    )
    conversation_id = created_conv["id"]

    # Rename folder
    result = conversation_utils.update_folder(old_folder_name, new_folder_name)
    assert_that(result, has_property("message", "Folder name updated"))

    # Verify conversation is now in new folder
    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation, has_property("folder", new_folder_name))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_delete_folder_without_conversations(
    assistant, assistant_utils, conversation_utils
):
    """Test deleting a folder without deleting conversations in it."""
    folder_name = f"test_folder_{get_random_name()}"

    # Create conversation in folder
    assistant_obj = assistant()
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=assistant_obj.id, folder=folder_name
    )
    conversation_id = created_conv["id"]

    # Delete folder without removing conversations
    result = conversation_utils.delete_folder(folder_name, remove_conversations=False)
    assert_that(result, has_property("message", "Folder removed"))

    # Verify conversation still exists but folder is None or empty
    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation, has_property("folder", ""))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_delete_folder_with_conversations(assistant, conversation_utils):
    """Test deleting a folder and all conversations in it."""
    folder_name = f"test_folder_{get_random_name()}"

    # Create conversation in folder
    assistant_obj = assistant()
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=assistant_obj.id, folder=folder_name
    )
    conversation_id = created_conv["id"]

    # Delete folder and conversations
    result = conversation_utils.delete_folder(folder_name, remove_conversations=True)
    assert_that(result, has_property("message", "Folder removed"))

    # Verify conversation was deleted
    with pytest.raises(Exception) as exec_info:
        conversation_utils.get_conversation_by_id(conversation_id)
    assert_error_details(
        exec_info.value.response,
        404,
        f"The conversation with ID [{conversation_id}] could not be found in the system.",
    )


# ==================== History Management Tests ====================


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_delete_conversation_history(assistant, assistant_utils, conversation_utils):
    """Test clearing all history from a conversation."""
    assistant_obj = assistant()
    prompt = f"prompt {get_random_name()}"

    # Create conversation with history
    assistant_utils.ask_assistant(assistant_obj, prompt)
    conversations = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )
    conversation_id = conversations[0].id

    # Verify history exists
    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation.history, has_length(greater_than_or_equal_to(1)))

    # Clear history
    updated_conv = conversation_utils.delete_history(conversation_id)
    assert_that(updated_conv.history, has_length(0))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_delete_history_by_index(assistant, assistant_utils, conversation_utils):
    """Test deleting a specific history item by index."""
    assistant_obj = assistant()

    # Create conversation with multiple messages
    assistant_utils.ask_assistant(assistant_obj, f"message1 {get_random_name()}")

    # Get conversation_id from first message
    conversations = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )
    conversation_id = conversations[0].id

    # Send second message using send_chat_request with same conversation_id
    chat_request = AssistantChatRequest(
        text=f"message2 {get_random_name()}", conversation_id=conversation_id
    )
    assistant_utils.send_chat_request(assistant_obj, chat_request)

    # Get initial history length
    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    initial_length = len(conversation.history)
    # Since each message has 2 History Items
    assert_that(initial_length, greater_than_or_equal_to(4))

    # Delete first history item
    updated_conv = conversation_utils.delete_history_by_index(conversation_id, 0)
    assert_that(updated_conv.history, has_length(initial_length - 2))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_update_history_by_index(assistant, assistant_utils, conversation_utils):
    """Test updating an Assistant response in conversation history."""
    assistant_obj = assistant()
    prompt = f"prompt {get_random_name()}"
    updated_response = f"updated_response_{get_random_name()}"

    # Create conversation
    assistant_utils.ask_assistant(assistant_obj, prompt)
    conversations = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )
    conversation_id = conversations[0].id

    # Update response from Assistant
    updated_conv = conversation_utils.update_history_by_index(
        conversation_id, 0, updated_response
    )

    # Verify the message was updated
    assert_that(updated_conv.history[3].message, equal_to(updated_response))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_upsert_history_conversation(assistant, conversation_utils, default_llm):
    """Test creating a new conversation via history upsert."""
    from datetime import datetime
    from codemie_sdk.models.conversation import HistoryItem

    assistant_obj = assistant()
    conversation_id = f"test_conv_{get_random_name()}"

    # Create history items
    history = [
        HistoryItem(
            role="User",
            message="Hello",
            historyIndex=0,
            date=datetime.now(),
            fileNames=[],
        ),
        HistoryItem(
            role="Assistant",
            message="Hi there!",
            historyIndex=0,
            date=datetime.now(),
            fileNames=[],
        ),
    ]

    # Upsert history (should create new conversation)
    result = conversation_utils.upsert_history(
        conversation_id, history, assistant_id=assistant_obj.id
    )

    assert_that(
        result,
        all_of(
            has_property("conversation_id", conversation_id),
            has_property("new_messages", 2),
            has_property("total_messages", 2),
            has_property("created", True),
        ),
    )

    # Verify conversation was created with history
    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation.history, has_length(2))

    # Update existing history (same roles and historyIndex)
    result = conversation_utils.upsert_history(
        conversation_id, history, assistant_id=assistant_obj.id
    )

    assert_that(
        result,
        all_of(
            has_property("conversation_id", conversation_id),
            has_property("new_messages", 2),
            has_property("total_messages", 2),
            has_property("created", False),
        ),
    )

    # Verify conversation history length remains the same
    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation.history, has_length(2))

    # Upsert new history items
    history[0].historyIndex = 1
    history[1].historyIndex = 1

    result = conversation_utils.upsert_history(
        conversation_id, history, assistant_id=assistant_obj.id
    )

    assert_that(
        result,
        all_of(
            has_property("conversation_id", conversation_id),
            has_property("new_messages", 2),
            has_property("total_messages", 4),
            has_property("created", False),
        ),
    )

    # Verify conversation history length updated
    conversation = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation.history, has_length(4))
