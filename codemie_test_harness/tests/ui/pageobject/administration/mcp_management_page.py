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

"""Page object for the MCPs catalog management page (Settings > Administration).

URL: /settings/administration/mcps

Selectors come from the codemie-ui sources (route in src/router.tsx, row menu in
NavigationMore.tsx, columns in MCPManagementPage.tsx) and the MCP clone
change analysis (Clone menu item, "Clone MCP Server" dialog, "Clone Server"
button, "Name is required" message). They have not been checked against a
browser walk.
"""

import re

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

_URL = "/settings/administration/mcps"


class McpManagementPage(BasePage):
    """Page object for Settings -> Administration -> MCPs catalog management."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def add_server_button(self):
        """'Add MCP Server' button in the page header."""
        return self.page.get_by_role("button", name="Add MCP Server")

    def server_name_button(self, name: str):
        """Name cell of the list row for the MCP server called ``name``."""
        return self.page.get_by_role("button", name=name, exact=True)

    def row_actions_button(self, name: str):
        """Row 'More options' button; its accessible name is 'More options <server name>'."""
        return self.page.get_by_role("button", name=f"More options {name}", exact=True)

    @property
    def clone_menu_item(self):
        """'Clone' item of the opened row actions menu."""
        return self.page.get_by_role("menuitem", name="Clone", exact=True)

    @property
    def clone_dialog(self):
        """'Clone MCP Server' dialog."""
        return self.page.get_by_role("dialog", name="Clone MCP Server")

    @property
    def clone_name_input(self):
        """'Name' field of the clone dialog."""
        return self.clone_dialog.get_by_role("textbox", name=re.compile(r"^Name\b"))

    @property
    def clone_documentation_link_input(self):
        """'Link to MCP documentation' field of the clone dialog."""
        return self.clone_dialog.get_by_role(
            "textbox", name=re.compile("Link to MCP documentation")
        )

    @property
    def clone_server_button(self):
        """'Clone Server' submit button of the clone dialog."""
        return self.clone_dialog.get_by_role("button", name="Clone Server")

    @property
    def name_required_error(self):
        """'Name is required' validation message inside the clone dialog."""
        return self.clone_dialog.get_by_text("Name is required")

    @property
    def per_page_100_option(self):
        """'100 items' option of the per-page dropdown."""
        return self.page.get_by_role("option", name="100 items")

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def navigate_to(self):
        """Open the MCPs catalog management page."""
        self.page.goto(_URL)
        expect(self.add_server_button).to_be_visible(timeout=15000)
        return self

    @step
    def open_without_waiting_for_content(self):
        """Open the MCPs page URL without expecting the admin header to render."""
        self.page.goto(_URL)
        return self

    @step
    def should_see_not_found(self):
        """Assert the MCPs page is not available to the current user."""
        expect(self.page.get_by_text("Not found", exact=True)).to_be_visible(
            timeout=15000
        )
        expect(self.add_server_button).to_have_count(0)
        return self

    @step
    def show_100_items_per_page(self):
        """Switch the list to 100 rows per page so a freshly created row is on the page."""
        self.show_per_page_dropdown.click()
        self.per_page_100_option.click()
        return self

    @step
    def open_row_actions_menu(self, server_name: str):
        """Open the actions menu of the ``server_name`` row.

        The row menu closes itself on any ancestor scroll (floating-ui ``useDismiss``).
        Clicking a row below the fold makes Playwright scroll it into view and the
        scroll event closes the menu right after it opens. So the row is scrolled into
        view first and two animation frames are flushed to let the scroll events fire
        before the click.
        """
        actions_button = self.row_actions_button(server_name)
        actions_button.scroll_into_view_if_needed()
        self.page.evaluate(
            "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
        )
        actions_button.click()
        expect(actions_button).to_have_attribute("aria-expanded", "true")
        return self

    @step
    def open_clone_dialog(self, server_name: str):
        """Choose Clone from the actions menu of the ``server_name`` row."""
        self.open_row_actions_menu(server_name)
        self.clone_menu_item.click()
        return self

    @step
    def fill_clone_name(self, name: str):
        """Type ``name`` into the Name field of the clone dialog."""
        self.clone_name_input.fill(name)
        return self

    @step
    def submit_clone(self):
        """Click 'Clone Server'."""
        self.clone_server_button.click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_see_server_in_list(self, name: str):
        """Assert a list row for ``name`` is shown."""
        expect(self.server_name_button(name)).to_be_visible(timeout=15000)
        return self

    @step
    def should_see_server_count_in_list(self, name: str, count: int):
        """Assert exactly ``count`` list rows are called ``name``."""
        expect(self.server_name_button(name)).to_have_count(count)
        return self

    @step
    def should_see_clone_dialog(self):
        """Assert the 'Clone MCP Server' dialog is open."""
        expect(self.clone_dialog).to_be_visible(timeout=10000)
        return self

    @step
    def should_not_see_clone_dialog(self):
        """Assert the 'Clone MCP Server' dialog is closed."""
        expect(self.clone_dialog).to_be_hidden(timeout=10000)
        return self

    @step
    def should_have_empty_clone_name(self):
        """Assert the Name field of the clone dialog is empty."""
        expect(self.clone_name_input).to_have_value("")
        return self

    @step
    def should_have_clone_documentation_link(self, url: str):
        """Assert the documentation link field is pre-filled from the source."""
        expect(self.clone_documentation_link_input).to_have_value(url)
        return self

    @step
    def should_see_name_required_error(self):
        """Assert 'Name is required' is shown in the clone dialog."""
        expect(self.name_required_error).to_be_visible()
        return self

    @step
    def should_see_error_toast(self):
        """Assert an error toast is shown."""
        expect(self.error_toast).to_be_visible(timeout=10000)
        return self

    @step
    def should_see_error_toast_with_text(self, text: str):
        """Assert an error toast is shown and its text contains ``text``."""
        expect(self.error_toast).to_contain_text(text, timeout=10000)
        return self
