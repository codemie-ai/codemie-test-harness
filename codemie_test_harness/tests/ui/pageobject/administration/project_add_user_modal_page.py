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

"""Page object for the 'Add User to Project' modal on the project Members tab.

Opened by the 'Add User to Project' button above the members table. The user is
chosen through a searchable select (at least two characters are searched).
"""

import re

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ProjectAddUserModalPage(BasePage):
    """'Add User to Project' modal."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def open_button(self):
        """'Add User to Project' button above the members table."""
        return self.page.get_by_role("button", name="Add User to Project")

    @property
    def dialog(self):
        """The 'Add User to Project' dialog."""
        return self.page.get_by_role("dialog", name="Add User to Project")

    @property
    def user_select(self):
        """Searchable 'User' select inside the modal."""
        return self.dialog.get_by_text("Click to search...")

    @property
    def search_input(self):
        """Search box of the opened user select."""
        return self.page.get_by_placeholder("Search for user")

    def user_option(self, email: str):
        """Search result option of the user with the given email."""
        return self.page.get_by_role("option", name=re.compile(re.escape(email)))

    @property
    def add_button(self):
        """'Add' submit button of the modal."""
        return self.dialog.get_by_role("button", name="Add", exact=True)

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def add_user(self, email: str):
        """Open the modal, find the user by email, pick them and submit."""
        self.open_button.click()
        expect(self.dialog).to_be_visible()
        self.user_select.click()
        self.search_input.fill(email)
        self.user_option(email).click()
        expect(self.add_button).to_be_enabled()
        self.add_button.click()
        expect(self.dialog).to_be_hidden()
        return self
