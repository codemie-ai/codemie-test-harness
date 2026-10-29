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

import requests
from typing import List, Union, Optional, Dict
from requests import HTTPError
from codemie_sdk.models.conversation import (
    AdminConversationListResponse,
    ConversationCreateRequest,
    ConversationDetails,
    ConversationFinishBulkResponse,
    ConversationFinishResponse,
    UpdateConversationRequest,
    UpdateConversationFolderRequest,
    UpdateHistoryByIndexRequest,
    UpsertHistoryRequest,
    HistoryItem,
    FeedbackCreateRequest,
    FeedbackCreateResponse,
    FeedbackDeleteRequest,
    FeedbackMark,
)
from codemie_sdk.models.assistant import AssistantChatRequest

from codemie_test_harness.tests.utils.base_utils import BaseUtils


class ConversationUtils(BaseUtils):
    def list_conversations(self, is_finished: Optional[bool] = None):
        return self.client.conversations.list(is_finished=is_finished)

    def get_conversation_by_assistant_id(self, assistant_id: str):
        return self.client.conversations.list_by_assistant_id(assistant_id)

    def get_conversation_by_id(self, conversation_id: str) -> requests.Response:
        return self.client.conversations.get_conversation(conversation_id)

    def create_conversation(
        self,
        initial_assistant_id: str = None,
        folder: str = None,
        mcp_server_single_usage: bool = False,
        is_workflow_conversation: bool = None,
    ):
        """Create a new conversation."""
        request = ConversationCreateRequest(
            initial_assistant_id=initial_assistant_id,
            folder=folder,
            mcp_server_single_usage=mcp_server_single_usage,
            is_workflow_conversation=is_workflow_conversation,
        )
        return self.client.conversations.create(request)

    def update_conversation(
        self,
        conversation_id: str,
        name: str = None,
        folder: str = None,
        pinned: bool = None,
    ):
        """Update an existing conversation."""
        request = UpdateConversationRequest(name=name, folder=folder, pinned=pinned)
        return self.client.conversations.update(conversation_id, request)

    def delete_conversation(self, conversation_id: str) -> requests.Response:
        return self.client.conversations.delete(conversation_id)

    def delete_all_conversations(self):
        """Delete all conversations for the current user."""
        return self.client.conversations.delete_all()

    def get_conversation_files(self, conversation_id: str) -> list:
        """Get list of files attached to a conversation."""
        return self.client.conversations.get_files(conversation_id)

    # Folder management methods

    def list_folders(self):
        """Get list of all conversation folders."""
        return self.client.conversations.list_folders()

    def create_folder(self, name: str):
        """Create a new conversation folder."""
        request = UpdateConversationFolderRequest(folder=name)
        return self.client.conversations.create_folder(request)

    def update_folder(self, folder: str, new_name: str):
        """Rename an existing conversation folder."""
        request = UpdateConversationFolderRequest(folder=new_name)
        return self.client.conversations.update_folder(folder, request)

    def delete_folder(self, folder: str, remove_conversations: bool = False):
        """Delete a conversation folder."""
        return self.client.conversations.delete_folder(folder, remove_conversations)

    # History management methods

    def upsert_history(
        self,
        conversation_id: str,
        history: List[HistoryItem],
        assistant_id: str = None,
        folder: str = None,
    ):
        """Create or update conversation with history (idempotent upsert)."""
        request = UpsertHistoryRequest(
            history=history, assistant_id=assistant_id, folder=folder
        )
        return self.client.conversations.upsert_history(conversation_id, request)

    def delete_history(self, conversation_id: str):
        """Clear all history from a conversation."""
        return self.client.conversations.delete_history(conversation_id)

    def delete_history_by_index(self, conversation_id: str, history_index: int):
        """Remove a specific history item by index."""
        return self.client.conversations.delete_history_by_index(
            conversation_id, history_index
        )

    def update_history_by_index(
        self, conversation_id: str, history_index: int, message: str
    ):
        """Update a message in conversation history by index."""
        request = UpdateHistoryByIndexRequest(
            messageIndex=history_index, message=message
        )
        return self.client.conversations.update_history_by_index(
            conversation_id, request
        )

    def chat(
        self,
        conversation_id: str,
        request: AssistantChatRequest,
        headers: Optional[Dict[str, str]] = None,
    ) -> Union[requests.Response, ConversationDetails]:
        """Send a chat message to a conversation.

        This is used for workflow chat mode where the workflow_id is set
        as the initial_assistant_id when creating the conversation.

        Args:
            conversation_id: Conversation ID to send message to
            request: Chat request details
            headers: Optional additional HTTP headers

        Returns:
            ConversationDetails with updated history or streaming response
        """
        return self.client.conversations.chat(conversation_id, request, headers)

    # Share management methods

    def share_conversation(self, conversation_id: str):
        """Create a shareable link for a conversation."""
        return self.client.conversations.share_conversation(conversation_id)

    def get_shared_conversation(self, share_token: str):
        """Get a shared conversation using the share token."""
        return self.client.conversations.get_shared_conversation(share_token)

    # Feedback management methods

    def submit_feedback(
        self,
        conversation_id: str,
        message_index: int,
        assistant_id: str,
        request: str,
        response: str,
        mark: FeedbackMark = FeedbackMark.WRONG,
        comments: Optional[str] = None,
        feedback_type: Optional[str] = None,
    ) -> FeedbackCreateResponse:
        """Submit like/dislike feedback on an assistant message.

        ``response`` must always be provided: the backend requires it and
        rejects the request with a 422 ``response: Field required`` error
        otherwise. Pass an empty string for incomplete,
        failed, or technical-error assistant responses rather than omitting
        the field.
        """
        feedback_request = FeedbackCreateRequest(
            conversation_id=conversation_id,
            message_index=message_index,
            assistant_id=assistant_id,
            request=request,
            response=response,
            mark=mark,
            comments=comments,
            type=feedback_type,
        )
        return self.client.conversations.create_feedback(feedback_request)

    def delete_feedback(
        self,
        conversation_id: str,
        feedback_id: str,
        message_index: int,
        assistant_id: str,
    ):
        """Delete a previously submitted feedback entry."""
        delete_request = FeedbackDeleteRequest(
            conversation_id=conversation_id,
            feedback_id=feedback_id,
            message_index=message_index,
            assistant_id=assistant_id,
        )
        return self.client.conversations.delete_feedback(delete_request)

    # Conversation finishing

    def finish_conversation(self, conversation_id: str) -> ConversationFinishResponse:
        """Mark a conversation as finished (owner-only, not idempotent)."""
        return self.client.conversations.finish(conversation_id)

    def finish_conversation_status_code(self, conversation_id: str) -> int:
        """Return the HTTP status code for a finish_conversation call.

        Useful for permission/error assertions without raising on 4xx.
        """
        try:
            self.finish_conversation(conversation_id)
            return 200
        except HTTPError as e:
            return e.response.status_code

    def finish_conversations_bulk(
        self, conversation_ids: List[str]
    ) -> ConversationFinishBulkResponse:
        """Finish multiple conversations in one request (admin-only)."""
        return self.client.conversations.finish_bulk(conversation_ids)

    def finish_conversations_bulk_status_code(self, conversation_ids: List[str]) -> int:
        """Return the HTTP status code for a finish_conversations_bulk call."""
        try:
            self.finish_conversations_bulk(conversation_ids)
            return 200
        except HTTPError as e:
            return e.response.status_code

    def list_admin_conversations(
        self,
        is_finished: Optional[bool] = None,
        started_after: Optional[str] = None,
        project: Optional[str] = None,
        page: int = 0,
        per_page: int = 20,
    ) -> AdminConversationListResponse:
        """Paginated, cross-user conversation list for admin/scheduler use (admin-only)."""
        return self.client.conversations.list_admin(
            is_finished=is_finished,
            started_after=started_after,
            project=project,
            page=page,
            per_page=per_page,
        )

    def list_admin_conversations_status_code(self, **kwargs) -> int:
        """Return the HTTP status code for a list_admin_conversations call."""
        try:
            self.list_admin_conversations(**kwargs)
            return 200
        except HTTPError as e:
            return e.response.status_code
