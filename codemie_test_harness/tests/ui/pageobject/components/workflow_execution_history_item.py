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

from playwright.sync_api import expect
from reportportal_client import step


class WorkflowExecutionHistoryItem:
    """Component representing a single execution history item in the sidebar."""

    def __init__(self, page, item_locator):
        self.page = page
        self.item = item_locator

    # Item elements
    @property
    def item_container(self):
        """The main interactive button containing execution info."""
        return self.item.locator("button").nth(1)

    @property
    def status_badge(self):
        """Status badge (Succeeded/Failed/Running)."""
        return (
            self.item_container.locator("div")
            .first.locator("div")
            .first.locator("div")
            .first
        )

    @property
    def execution_body(self):
        """Execution number/identifier element (e.g. "01", "002")."""
        return self.item_container.locator("> div").nth(0).locator("> :last-child")

    @property
    def timestamp(self):
        """Execution dates container (Started / Finished / Runtime)."""
        return self.item_container.locator("> div").nth(1)

    @property
    def menu_button(self):
        """Three-dots menu button."""
        return self.item.locator("button").first

    @property
    def menu(self):
        """Context menu opened via menu_button."""
        return self.page.get_by_role("menu", name="Options")

    # Action methods
    @step
    def click(self):
        """Click on the execution item to select it."""
        self.item_container.click()
        return self

    @step
    def click_menu(self):
        """Open the three-dots context menu."""
        self.menu_button.click()
        return self

    # Verification methods
    @step
    def should_be_visible(self):
        """Verify the execution item is visible."""
        expect(self.item_container).to_be_visible()
        return self

    @step
    def should_not_be_visible(self):
        """Verify the execution item is not visible."""
        expect(self.item_container).not_to_be_visible()
        return self

    @step
    def should_have_status(self, expected_status: str):
        """Verify the execution has the expected status text."""
        expect(self.status_badge).to_contain_text(expected_status)
        return self

    @step
    def should_have_succeeded_status(self):
        """Verify status is Succeeded with correct CSS styling."""
        self.should_have_status("Succeeded")
        expect(self.status_badge).to_contain_class("bg-success-secondary")
        expect(self.status_badge).to_contain_class("text-success-primary")
        expect(self.status_badge).to_contain_class("border-success-primary")
        return self

    @step
    def should_have_failed_status(self):
        """Verify status is Failed with correct CSS styling."""
        self.should_have_status("Failed")
        expect(self.status_badge).to_contain_class("bg-error-secondary")
        expect(self.status_badge).to_contain_class("text-error-primary")
        expect(self.status_badge).to_contain_class("border-error-primary")
        return self

    @step
    def should_have_in_progress_status(self):
        """Verify status is In Progress with correct CSS styling."""
        expect(self.status_badge).to_contain_text("In Progress")
        expect(self.status_badge).to_contain_class("bg-in-progress-secondary")
        expect(self.status_badge).to_contain_class("text-in-progress-primary")
        expect(self.status_badge).to_contain_class("border-in-progress-primary")
        return self

    @step
    def should_have_execution_id(self, expected_id: str):
        """Verify the execution sequence number."""
        expect(self.execution_body).to_have_text(expected_id)
        return self

    @step
    def should_have_execution_id_pattern(self, pattern: str):
        """Verify the execution sequence number matches a regex pattern."""
        expect(self.execution_body).to_have_text(re.compile(pattern))
        return self

    @step
    def should_have_timestamp(self, expected_text: str):
        """Verify the timestamp container contains the given text."""
        expect(self.timestamp).to_contain_text(expected_text)
        return self

    @step
    def should_have_timestamp_pattern(self, pattern: str):
        """Verify the timestamp container text matches a regex pattern."""
        expect(self.timestamp).to_contain_text(re.compile(pattern))
        return self

    @step
    def should_be_active(self):
        """Verify the execution item is currently selected (active)."""
        expect(self.item_container).to_contain_class("bg-new-stroke")
        return self

    @step
    def should_not_be_active(self):
        """Verify the execution item is not the active selection."""
        expect(self.item_container).not_to_contain_class("bg-new-stroke")
        return self

    @step
    def should_have_menu_button(self):
        """Verify the three-dots menu button is visible and enabled."""
        expect(self.menu_button).to_be_visible()
        expect(self.menu_button).to_be_enabled()
        return self

    @step
    def should_have_menu_remove_option(self):
        """Verify the context menu contains a 'Remove' menu item."""
        expect(self.menu.get_by_role("menuitem", name="Remove")).to_be_visible()
        return self

    @step
    def should_show_remove_blocked_tooltip(self, expected_text: str):
        """Open the context menu, hover the disabled 'Remove' option, and verify
        the blocking tooltip text (shown while the execution is part of a live
        conversation)."""
        self.click_menu()
        remove_option = self.menu.get_by_role("menuitem", name="Remove")
        expect(remove_option).to_be_disabled()
        remove_option.hover()
        expect(self.page.get_by_role("tooltip")).to_have_text(expected_text)
        return self

    @step
    def should_have_all_elements_visible(self):
        """Verify all main elements are visible."""
        expect(self.item_container).to_be_visible()
        expect(self.status_badge).to_be_visible()
        expect(self.timestamp).to_be_visible()
        expect(self.menu_button).to_be_visible()
        return self

    @step
    def should_be_clickable(self):
        """Verify the execution item button is enabled."""
        expect(self.item_container).to_be_enabled()
        return self

    @step
    def should_have_proper_status_styling(self):
        """Verify status badge has correct visual styling classes."""
        expect(self.status_badge).to_contain_class("uppercase")
        expect(self.status_badge).to_contain_class("font-bold")
        expect(self.status_badge).to_contain_class("rounded-full")
