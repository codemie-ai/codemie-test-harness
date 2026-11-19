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

"""Creates the folders and chats a sidebar Folders test needs, and removes them again.

The Folders section of the shared test account is also used by other runs, so the
helper only ever deletes what it created itself: a folder that was already registered
before the test touched it is left alone.
"""

import uuid

import pytest

from codemie_test_harness.tests.ui.test_data.cli_agent_folders_test_data import (
    CliAgent,
    agent_history,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.conversation_utils import ConversationUtils


def _key(folder_name: str) -> str:
    """Folder names are compared the way the sidebar compares them: trimmed, any case."""
    return folder_name.strip().lower()


class ChatFolderSetup:
    """Owns the folders and chats created through it for the length of one test."""

    def __init__(self, conversation_utils: ConversationUtils):
        self._utils = conversation_utils
        self._preexisting = {_key(f.folder_name) for f in self._utils.list_folders()}
        self._owned_folders: set[str] = set()
        self._owned_chats: list[str] = []

    def _claim_folder(self, folder_name: str):
        """Remember a folder this test brings into existence, unless it was there before."""
        if _key(folder_name) not in self._preexisting:
            self._owned_folders.add(_key(folder_name))

    def _skip_if_registered(self, folder_name: str):
        """Skip the test when the account already had the folder before the test."""
        if _key(folder_name) in self._preexisting:
            pytest.skip(
                f"Folder '{folder_name}' is already registered on the account; "
                "the test does not touch folders it did not create"
            )

    def register_folder(self, folder_name: str) -> str:
        """Register an empty folder. Skips the test when the account already has it."""
        self._skip_if_registered(folder_name)
        self._owned_folders.add(_key(folder_name))
        self._utils.create_folder(folder_name)
        return folder_name

    def register_random_folder(self) -> str:
        """Register an empty folder with a random, non-agent name."""
        return self.register_folder(get_random_name())

    def create_chat(self, folder_name: str) -> str:
        """Create a regular (non-imported) chat in the folder; returns its id."""
        self._claim_folder(folder_name)
        chat_id = self._utils.create_conversation(folder=folder_name).get("id")
        self._owned_chats.append(chat_id)
        return chat_id

    def import_chat(self, agent: CliAgent, folder_name: str | None = None) -> str:
        """Sync a chat the way the agent's CLI does; returns the chat id.

        The backend sets the chat's import source from the agent's client header and
        registers the folder named in ``folder_name`` (the agent's folder by default).
        Skips the test when the account already had that folder: a real agent folder
        would be listed or offered next to the synced chats and fail the checks for
        reasons unrelated to the product change.
        """
        folder_name = folder_name or agent.folder
        self._skip_if_registered(folder_name)
        self._claim_folder(folder_name)
        chat_id = str(uuid.uuid4())
        self._owned_chats.append(chat_id)
        self._utils.upsert_history_as_cli(
            conversation_id=chat_id,
            history=agent_history(get_random_name()),
            cli_client=agent.client_header,
            folder=folder_name,
        )
        return chat_id

    def cleanup(self):
        """Delete the owned chats, then the owned folders (kept chats are never removed)."""
        for chat_id in self._owned_chats:
            try:
                self._utils.delete_conversation(chat_id)
            except Exception:
                pass
        try:
            registered = self._utils.list_folders()
        except Exception:
            return
        for folder in registered:
            if _key(folder.folder_name) in self._owned_folders:
                try:
                    self._utils.delete_folder(
                        folder.folder_name, remove_conversations=False
                    )
                except Exception:
                    pass
