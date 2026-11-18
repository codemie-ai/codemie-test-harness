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
Page object for the "Folders" section of the chat sidebar and the "Move to folder" popup.

A folder entry is identified by its ``data-folder`` key: ``custom:<name>`` for a folder
the user created, ``import:<kind>`` for the group of chats synced by a CLI agent and
``legacy-import:<label>`` for the older import groups. Because the shared test account
changes under parallel runs, every check targets an entry or chat the test owns.
"""

import re
from urllib.parse import quote

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


def custom_folder_key(folder_name: str) -> str:
    """``data-folder`` key of a folder the user created."""
    return f"custom:{folder_name}"


class ChatFoldersSection(BasePage):
    """The sidebar Folders accordion, its entries and the chat Move popup."""

    # ==================== FOLDERS SECTION ====================

    @property
    def folders_header(self) -> Locator:
        """Folders accordion header; collapsed (aria-expanded=false) by default."""
        return self.page.get_by_role("treeitem", name="Folders Create Folder")

    @property
    def folders_header_label(self) -> Locator:
        """The "Folders" label inside the accordion header, the click target that toggles it."""
        return self.folders_header.get_by_text("Folders", exact=True)

    # ==================== FOLDER ENTRIES ====================

    @property
    def folder_entries(self) -> Locator:
        """Every folder entry header in the Folders section."""
        return self.page.locator('a[role="treeitem"][data-folder]')

    def folder_entry(self, key: str) -> Locator:
        """Folder entry header with the given data-folder key (case-insensitive)."""
        return self.page.locator(f'a[role="treeitem"][data-folder="{key}" i]')

    def entries_labelled(self, label: str) -> Locator:
        """Folder entry headers whose visible name is exactly ``label``."""
        name = self.page.locator(
            'p[id^="folder-name-"]', has_text=re.compile(rf"^{re.escape(label)}$")
        )
        return self.folder_entries.filter(has=name)

    def chats_group(self, key: str) -> Locator:
        """Chat list of a folder entry; its children exist only while the entry is expanded."""
        group_id = f"chat-tree-folder-group-{quote(key, safe='')}"
        return self.page.locator(f'ul[id="{group_id}" i]')

    def chat_item(self, chat_id: str) -> Locator:
        """Chat item with the given chat id."""
        return self.page.locator(f'li[role="treeitem"][data-chat-id="{chat_id}"]')

    # ==================== CHAT MENU AND MOVE POPUP ====================

    def chat_menu_button(self, chat_id: str) -> Locator:
        """The More options button of a chat item."""
        return self.chat_item(chat_id).locator(
            'button[aria-haspopup="menu"][id^="nav-more-btn-"]'
        )

    @property
    def move_chat_menu_item(self) -> Locator:
        """Chat menu item that opens the Move to folder popup."""
        return self.page.locator(
            '[role="menu"] button[role="menuitem"][aria-label="Add to folder..."]'
        )

    @property
    def move_popup(self) -> Locator:
        """Move to folder dialog."""
        return self.page.locator('[role="dialog"][data-pc-name="dialog"]').filter(
            has=self.page.locator("h4", has_text="Move to folder")
        )

    @property
    def move_popup_folder_input(self) -> Locator:
        """Folder picker input of the Move popup."""
        return self.move_popup.locator(
            'input[role="combobox"][placeholder="Select folder"]'
        )

    @property
    def move_popup_add_button(self) -> Locator:
        """Add button that commits the move."""
        return self.move_popup.get_by_role("button", name="Add", exact=True)

    @property
    def folder_options(self) -> Locator:
        """Folder suggestions of the Move popup picker."""
        return self.page.locator('.p-autocomplete-panel [role="option"]')

    def folder_option(self, folder_name: str) -> Locator:
        """Folder suggestion whose text is exactly ``folder_name`` (case-insensitive)."""
        return self.folder_options.filter(
            has_text=re.compile(rf"^\s*{re.escape(folder_name)}\s*$", re.IGNORECASE)
        )

    # ==================== NAVIGATION ====================

    @step
    def open_chat(self, chat_id: str):
        """Open a chat; the sidebar renders on every chat page."""
        self.page.goto(f"/chats/{chat_id}")
        expect(self.folders_header).to_be_visible()
        return self

    @step
    def open_folders_section(self):
        """Expand the Folders accordion."""
        expect(self.folders_header).to_be_visible()
        if self.folders_header.get_attribute("aria-expanded") != "true":
            self.folders_header_label.click()
        expect(self.folders_header).to_have_attribute("aria-expanded", "true")
        return self

    @step
    def expand_folder(self, key: str):
        """Expand a folder entry so its chats render."""
        entry = self.folder_entry(key)
        expect(entry).to_be_visible()
        if entry.get_attribute("aria-expanded") != "true":
            entry.click()
        expect(entry).to_have_attribute("aria-expanded", "true")
        return self

    # ==================== ACTIONS ====================

    @step
    def open_move_chat_popup(self, group_key: str, chat_id: str):
        """Open the Move to folder popup of a chat listed in the given folder entry."""
        self.expand_folder(group_key)
        chat = self.chat_item(chat_id)
        expect(chat).to_be_visible()
        chat.hover()
        self.chat_menu_button(chat_id).click()
        self.move_chat_menu_item.click()
        expect(self.move_popup).to_be_visible()
        return self

    @step
    def search_move_popup_folder(self, folder_name: str):
        """Type a folder name into the picker so the matching suggestions render."""
        self.move_popup_folder_input.fill(folder_name)
        return self

    @step
    def move_chat_to_folder(self, group_key: str, chat_id: str, folder_name: str):
        """Move a chat into a custom folder through the Move to folder popup."""
        self.open_move_chat_popup(group_key, chat_id)
        self.search_move_popup_folder(folder_name)
        self.folder_option(folder_name).click()
        self.move_popup_add_button.click()
        expect(self.move_popup).to_be_hidden()
        return self

    # ==================== VERIFICATIONS ====================

    @step
    def should_list_folder(self, key: str):
        """Verify the sidebar lists the folder entry with this key."""
        expect(self.folder_entry(key)).to_have_count(1)
        return self

    @step
    def should_not_list_folder(self, key: str):
        """Verify the sidebar has no folder entry with this key.

        Only meaningful once the list has rendered; check an entry the test owns
        first (``should_list_folder``).
        """
        expect(self.folder_entry(key)).to_have_count(0)
        return self

    @step
    def should_list_single_entry(self, label: str, key: str):
        """Verify exactly one entry is labelled ``label`` and it is the ``key`` group."""
        entries = self.entries_labelled(label)
        expect(entries).to_have_count(1)
        expect(entries).to_have_attribute(
            "data-folder", re.compile(rf"^{re.escape(key)}$", re.IGNORECASE)
        )
        return self

    @step
    def should_contain_chat(self, key: str, chat_id: str):
        """Verify the folder entry lists the chat."""
        self.expand_folder(key)
        expect(
            self.chats_group(key).locator(f'li[data-chat-id="{chat_id}"]')
        ).to_have_count(1)
        return self

    @step
    def should_not_contain_chat(self, key: str, chat_id: str):
        """Verify the folder entry, when it exists, does not list the chat."""
        if self.folder_entry(key).count():
            self.expand_folder(key)
        expect(
            self.chats_group(key).locator(f'li[data-chat-id="{chat_id}"]')
        ).to_have_count(0)
        return self

    @step
    def should_offer_move_target(self, folder_name: str):
        """Verify the Move popup suggests the folder."""
        expect(self.folder_option(folder_name)).to_have_count(1)
        return self

    @step
    def should_not_offer_move_target(self, folder_name: str):
        """Verify the Move popup does not suggest the folder."""
        expect(self.folder_option(folder_name)).to_have_count(0)
        return self
