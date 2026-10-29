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
Chats Sidebar Page Object for CodeMie UI Testing

This module implements the Chats Sidebar page object following the established POM patterns
in the CodeMie test harness. It provides comprehensive support for chat sidebar functionality
including assistants management, chat navigation, and folder organization.

Following the same architecture as other page objects in the framework:
- Property-based element locators with multiple fallbacks
- Comprehensive verification methods
- Integration with ReportPortal via @step decorators
- Method chaining support for fluent API
- Robust error handling and graceful degradation
"""

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from playwright.sync_api import expect, Locator
from reportportal_client import step


class ChatsSidebar(BasePage):
    """
    Chats Sidebar page object with comprehensive sidebar functionality support.

    This class encapsulates all chat sidebar-related UI interactions including:
    - Assistants section management
    - Chat history navigation
    - Folder management
    - Sidebar navigation and actions

    Follows established POM patterns with property-based locators and method chaining.
    """

    def __init__(self, page):
        super().__init__(page)

    # ==================== MAIN SIDEBAR CONTAINER ====================

    @property
    def sidebar_container(self) -> Locator:
        """Main sidebar container — the resizable chat-sidebar panel.

        The chat sidebar is now a `react-resizable-panels` Panel (id="chat-sidebar-panel")
        whose <aside> fills the panel (`w-full`); the old fixed `w-sidebar` /
        `max-w-sidebar` classes no longer exist here. The panel is visible when
        expanded and shrinks to zero width when collapsed."""
        return self.page.locator('div[data-panel="true"]#chat-sidebar-panel')

    # ==================== ASSISTANTS SECTION ====================

    @property
    def assistants_accordion(self) -> Locator:
        """Assistants accordion section."""
        return self.sidebar_container.locator('[data-pc-name="accordion"]').first

    @property
    def assistants_header(self) -> Locator:
        """Assistants accordion header."""
        return self.assistants_accordion.locator(".p-accordion-header")

    @property
    def assistants_header_action(self) -> Locator:
        """Assistants accordion header action button."""
        return self.assistants_header.locator(".p-accordion-header-action")

    @property
    def assistants_header_icon(self) -> Locator:
        """Assistants accordion chevron icon."""
        return self.assistants_header.locator("svg")

    @property
    def assistants_header_title(self) -> Locator:
        """Assistants accordion header title text."""
        return self.assistants_header.locator(".p-accordion-header-text")

    @property
    def assistants_content(self) -> Locator:
        """Assistants accordion content area."""
        return self.assistants_accordion.locator(".p-accordion-content")

    # ==================== ASSISTANT ITEMS ====================

    @property
    def assistant_item_container(self) -> Locator:
        """Individual assistant item container."""
        return self.assistants_content.locator(
            ".flex.justify-between.items-center.h-8.mb-2.ml-6.mr-4"
        )

    @property
    def assistant_avatar(self) -> Locator:
        """Assistant avatar image."""
        return self.assistant_item_container.locator('img[alt="assistant icon"]')

    @property
    def assistant_name(self) -> Locator:
        """Assistant name text."""
        return self.assistant_item_container.locator(
            "span.block.w-full.truncate.text-text-main.text-sm.font-normal"
        )

    @property
    def assistant_menu_button(self) -> Locator:
        """Assistant menu/options button (three dots)."""
        return self.assistant_item_container.locator("button.button.tertiary.medium")

    def get_assistant_by_name(self, assistant_name: str) -> Locator:
        """Get specific assistant item by name."""
        return self.assistant_item_container.locator(
            f'span[title*="{assistant_name}"]'
        ).locator("..")

    # ==================== EXPLORE ASSISTANTS ====================

    @property
    def explore_assistants_button(self) -> Locator:
        """Explore Assistants navigation button."""
        return self.sidebar_container.locator("button#navigate")

    @property
    def explore_assistants_icon(self) -> Locator:
        """Explore Assistants button icon."""
        return self.explore_assistants_button.locator("svg")

    # ==================== DIVIDER ====================

    @property
    def section_divider(self) -> Locator:
        """Divider between assistants and chats sections."""
        return self.sidebar_container.locator(".p-divider")

    # ==================== CHATS SECTION ====================

    @property
    def chats_section_button(self) -> Locator:
        """Chats section toggle button."""
        return (
            self.sidebar_container.locator(
                "div.flex.items-center.gap-2.text-text-heading"
            )
            .filter(has_text="Chats")
            .first
        )

    @property
    def chats_section_icon(self) -> Locator:
        """Chats section chevron icon."""
        return self.chats_section_button.locator("svg.rotate-90")

    @property
    def chats_section_title(self) -> Locator:
        """Chats section title text."""
        return self.chats_section_button.locator("span").first

    # ==================== CHAT HISTORY LIST ====================

    @property
    def chat_history_container(self) -> Locator:
        """Chat history list container."""
        return self.sidebar_container.locator("ul")

    @property
    def chat_items(self) -> Locator:
        """All chat items in the history list."""
        return self.chat_history_container.locator("li")

    @property
    def active_chat_item(self) -> Locator:
        """Currently active/selected chat item."""
        return self.page.locator("li.bg-surface-specific-dropdown-hover")

    def get_chat_item_by_index(self, index: int) -> Locator:
        """Get specific chat item by index (0-based)."""
        return self.chat_items.nth(index)

    def get_chat_item_by_text(self, chat_text: str) -> Locator:
        """Get specific chat item by partial text content."""
        return self.chat_items.filter(has_text=chat_text)

    # ==================== CHAT ITEM ELEMENTS ====================

    @property
    def chat_item_link(self) -> Locator:
        """Chat item button element."""
        return self.chat_items.locator("button")

    @property
    def chat_item_name_input(self) -> Locator:
        """Chat item name edit input (when editing)."""
        return self.chat_items.locator("input.edit-name")

    @property
    def chat_item_menu_button(self) -> Locator:
        """Chat item menu/options button (three dots)."""
        return self.chat_items.locator("button.button.tertiary.medium")

    # ==================== FOLDERS SECTION ====================

    @property
    def folders_section_button(self) -> Locator:
        """Folders section toggle button."""
        return (
            self.sidebar_container.locator(
                "div.flex.items-center.gap-2.text-text-heading"
            )
            .filter(has_text="Folders")
            .first
        )

    @property
    def folders_section_icon(self) -> Locator:
        """Folders section chevron icon."""
        return self.folders_section_button.locator("svg").first

    @property
    def folders_section_title(self) -> Locator:
        """Folders section title text."""
        return self.folders_section_button.locator("span").first

    @property
    def create_folder_button(self) -> Locator:
        """Create new folder button."""
        return self.folders_section_button.locator('button[title="Create Folder"]')

    @property
    def create_folder_icon(self) -> Locator:
        """Create folder button icon."""
        return self.create_folder_button.locator("svg")

    # ==================== SIDEBAR TOGGLE ====================

    @property
    def hide_sidebar_button(self) -> Locator:
        """Sidebar toggle button, labelled 'Hide Sidebar' while the sidebar is expanded."""
        return self.page.get_by_role("button", name="Hide Sidebar")

    @property
    def open_sidebar_button(self) -> Locator:
        """Sidebar toggle button, labelled 'Open Sidebar' while the sidebar is collapsed."""
        return self.page.get_by_role("button", name="Open Sidebar")

    @property
    def sidebar_toggle_tooltip(self) -> Locator:
        """Global react-tooltip bubble (single shared instance, id='react-tooltip',
        role='tooltip') rendered when hovering the sidebar toggle button."""
        return self.page.get_by_role("tooltip")

    # ==================== INTERACTION METHODS ====================

    @step
    def toggle_assistants_section(self):
        """Toggle the assistants accordion section."""
        self.assistants_header_action.click()
        return self

    @step
    def click_explore_assistants(self):
        """Click the Explore Assistants button."""
        self.explore_assistants_button.click()
        return self

    @step
    def click_assistant_by_name(self, assistant_name: str):
        """Click on a specific assistant by name."""
        assistant = self.get_assistant_by_name(assistant_name)
        assistant.click()
        return self

    @step
    def click_assistant_menu(self, assistant_name: str = None):
        """Click the menu button for a specific assistant or the first one."""
        if assistant_name:
            assistant = self.get_assistant_by_name(assistant_name)
            assistant.locator("button.button.tertiary.medium").click()
        else:
            self.assistant_menu_button.first.click()
        return self

    @step
    def toggle_chats_section(self):
        """Toggle the chats section."""
        self.chats_section_button.click()
        return self

    @step
    def click_chat_item(self, index: int = 0):
        """Click on a specific chat item by index."""
        chat_item = self.get_chat_item_by_index(index)
        chat_item.click()
        return self

    @step
    def click_chat_by_text(self, chat_text: str):
        """Click on a specific chat item by text content."""
        chat_item = self.get_chat_item_by_text(chat_text)
        chat_item.click()
        return self

    @step
    def click_chat_menu(self, index: int = 0):
        """Click the menu button for a specific chat item."""
        chat_item = self.get_chat_item_by_index(index)
        menu_button = chat_item.locator("button.button.tertiary.medium")
        menu_button.click()
        return self

    @step
    def toggle_folders_section(self):
        """Toggle the folders section."""
        self.folders_section_button.click()
        return self

    @step
    def click_create_folder(self):
        """Click the create folder button."""
        self.create_folder_button.click()
        return self

    @step
    def hover_sidebar_toggle_button(self):
        """Hover-and-hold over the sidebar toggle button (Hide Sidebar) to trigger its tooltip."""
        self.hide_sidebar_button.hover()
        return self

    @step
    def move_mouse_away_from_sidebar_toggle_button(self):
        """Move the mouse away from the sidebar toggle button to dismiss its tooltip."""
        self.page.mouse.move(0, 0)
        return self

    @step
    def click_hide_sidebar(self):
        """Click the Hide Sidebar button to collapse the sidebar."""
        self.hide_sidebar_button.click()
        return self

    @step
    def click_open_sidebar(self):
        """Click the Open Sidebar button to expand the sidebar."""
        self.open_sidebar_button.click()
        return self

    @step
    def edit_chat_name(self, index: int, new_name: str):
        """Edit the name of a specific chat item."""
        chat_item = self.get_chat_item_by_index(index)
        # This would trigger edit mode - implementation depends on actual UI behavior
        # For now, assuming double-click or specific action triggers edit
        chat_item.dblclick()

        name_input = chat_item.locator("input.edit-name")
        if name_input.is_visible():
            name_input.fill(new_name)
            name_input.press("Enter")
        return self

    # ==================== VERIFICATION METHODS ====================

    @step
    def should_have_sidebar_visible(self):
        """Verify that the main sidebar container is visible."""
        expect(self.sidebar_container).to_be_visible()
        return self

    @step
    def should_have_tooltip_visible(self, text: str):
        """Verify that the sidebar toggle tooltip bubble is visible with the given text."""
        expect(self.sidebar_toggle_tooltip).to_be_visible()
        expect(self.sidebar_toggle_tooltip).to_have_text(text)
        return self

    @step
    def should_have_tooltip_hidden(self):
        """Verify that the sidebar toggle tooltip bubble is hidden."""
        expect(self.sidebar_toggle_tooltip).to_be_hidden()
        return self

    @step
    def should_have_sidebar_collapsed(self):
        """Verify that the sidebar is collapsed.

        Assert on the resizable panel (`#chat-sidebar-panel`), not the inner <aside>.
        When collapsed the panel width is 0, so Playwright treats it as hidden.
        The <aside> keeps a 1px-wide box (its `border-r`) even at zero content
        width, so `to_be_hidden()` on the aside would never pass."""
        expect(self.sidebar_container).to_be_hidden()
        expect(self.open_sidebar_button).to_be_visible()
        return self

    @step
    def should_have_assistants_section_visible(self):
        """Verify that the assistants section is visible."""
        expect(self.assistants_accordion).to_be_visible()
        expect(self.assistants_header).to_be_visible()
        expect(self.assistants_header_title).to_have_text("Recent Assistants")
        return self

    @step
    def should_have_assistants_section_expanded(self):
        """Verify that the assistants section is expanded."""
        expect(self.assistants_accordion).to_have_attribute("data-p-active", "true")
        expect(self.assistants_content).to_be_visible()
        return self

    @step
    def should_have_assistants_section_collapsed(self):
        """Verify that the assistants section is collapsed."""
        expect(self.assistants_accordion).to_have_attribute("data-p-active", "false")
        expect(self.assistants_content).to_be_hidden()
        return self

    @step
    def should_have_assistant_visible(self, assistant_name: str):
        """Verify that a specific assistant is visible."""
        assistant = self.get_assistant_by_name(assistant_name)
        expect(assistant).to_be_visible()
        return self

    @step
    def should_have_assistant_avatar_visible(self):
        """Verify that assistant avatar is visible."""
        expect(self.assistant_avatar).to_be_visible()
        return self

    @step
    def should_have_explore_assistants_button_visible(self):
        """Verify that the Explore Assistants button is visible."""
        expect(self.explore_assistants_button).to_be_visible()
        expect(self.explore_assistants_button).to_contain_text("Explore Assistants")
        return self

    @step
    def should_have_section_divider_visible(self):
        """Verify that the section divider is visible."""
        expect(self.section_divider).to_be_visible()
        return self

    @step
    def should_have_chats_section_visible(self):
        """Verify that the chats section is visible."""
        expect(self.chats_section_button).to_be_visible()
        expect(self.chats_section_button).to_contain_text("Chats")
        return self

    @step
    def should_have_chat_history_visible(self):
        """Verify that the chat history container is visible."""
        expect(self.chat_history_container).to_be_visible()
        return self

    @step
    def should_have_chat_items(self, expected_count: int = None):
        """Verify that chat items are present, optionally checking count."""
        expect(self.chat_items.first).to_be_visible()
        if expected_count is not None:
            expect(self.chat_items).to_have_count(expected_count)
        return self

    @step
    def should_have_active_chat_item(self):
        """Verify that there is an active/selected chat item."""
        expect(self.active_chat_item).to_be_visible()
        return self

    @step
    def should_have_chat_item_with_text(self, chat_text: str):
        """Verify that a chat item with specific text exists."""
        chat_item = self.get_chat_item_by_text(chat_text)
        expect(chat_item).to_be_visible()
        return self

    @step
    def should_have_folders_section_visible(self):
        """Verify that the folders section is visible."""
        expect(self.folders_section_button).to_be_visible()
        expect(self.folders_section_button).to_contain_text("Folders")
        return self

    @step
    def should_have_create_folder_button_visible(self):
        """Verify that the create folder button is visible."""
        expect(self.create_folder_button).to_be_visible()
        return self

    @step
    def should_have_assistant_menu_button_visible(self):
        """Verify that assistant menu buttons are visible."""
        expect(self.assistant_menu_button.first).to_be_visible()
        return self

    @step
    def should_have_chat_menu_buttons_visible(self):
        """Verify that chat item menu buttons are visible."""
        expect(self.chat_item_menu_button.first).to_be_visible()
        return self

    # ==================== UTILITY METHODS ====================

    @step
    def get_chat_items_count(self) -> int:
        """Get the total number of chat items."""
        return self.chat_items.count()

    @step
    def get_active_chat_title(self) -> str:
        """Get the text of the currently active chat item."""
        return self.active_chat_item.locator("button.text-inherit").inner_text()

    @step
    def get_assistant_names(self) -> list:
        """Get a list of all visible assistant names."""
        names = []
        count = self.assistant_name.count()
        for i in range(count):
            names.append(self.assistant_name.nth(i).inner_text())
        return names

    @step
    def get_chat_texts(self) -> list:
        """Get a list of all chat item texts."""
        texts = []
        count = self.chat_items.count()
        for i in range(count):
            chat_button = self.chat_items.nth(i).locator("button")
            if chat_button.is_visible():
                texts.append(chat_button.inner_text())
        return texts

    @step
    def wait_for_sidebar_load(self, timeout: int = 10000):
        """Wait for the sidebar to fully load."""
        self.sidebar_container.wait_for(state="visible", timeout=timeout)
        return self

    @step
    def scroll_chat_history_to_top(self):
        """Scroll the chat history to the top."""
        self.chat_history_container.evaluate("element => element.scrollTop = 0")
        return self

    @step
    def scroll_chat_history_to_bottom(self):
        """Scroll the chat history to the bottom."""
        self.chat_history_container.evaluate(
            "element => element.scrollTop = element.scrollHeight"
        )
        return self

    # ==================== COMPREHENSIVE VERIFICATION METHODS ====================

    @step
    def verify_all_sidebar_sections_visibility(self):
        """Comprehensive verification of all sidebar sections."""
        self.should_have_sidebar_visible()
        self.should_have_assistants_section_visible()
        self.should_have_chats_section_visible()
        self.should_have_chat_history_visible()
        self.should_have_active_chat_item()
        self.should_have_folders_section_visible()
        return self

    @step
    def verify_assistants_section(self):
        """Verify assistants section functionality."""
        self.should_have_assistants_section_visible()
        self.should_have_assistants_section_expanded()
        self.should_have_assistant_avatar_visible()
        self.should_have_assistant_menu_button_visible()
        return self
