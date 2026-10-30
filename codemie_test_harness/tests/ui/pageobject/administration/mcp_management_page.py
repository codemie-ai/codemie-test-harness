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
button, "Name is required" message) and from the MCPServerModal / MCPServerDetails
components (Add/Edit MCP Server dialog, environment variable rows, details panel). They
have not been checked against a browser walk.
"""

import re

from hamcrest import assert_that, has_entry
from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.mcp_catalog_test_data import (
    CatalogServerFormData,
)

_URL = "/settings/administration/mcps"


class McpManagementPage(BasePage):
    """Page object for Settings -> Administration -> MCPs catalog management."""

    # PUT request captured by submit_update(); read by should_have_sent_empty_env_vars().
    last_update_request = None

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

    @property
    def edit_menu_item(self):
        """'Edit' item of the opened row actions menu."""
        return self.page.get_by_role("menuitem", name="Edit", exact=True)

    @property
    def add_dialog(self):
        """'Add MCP Server' dialog."""
        return self.page.get_by_role("dialog", name="Add MCP Server")

    @property
    def edit_dialog(self):
        """'Edit MCP Server' dialog."""
        return self.page.get_by_role("dialog", name="Edit MCP Server")

    @property
    def _server_dialog(self):
        """Whichever of the Add / Edit MCP Server dialogs is open."""
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_placeholder("Server Name")
        )

    @property
    def dialog_name_input(self):
        """'Name' field of the Add/Edit MCP Server dialog."""
        return self._server_dialog.get_by_placeholder("Server Name")

    @property
    def dialog_description_input(self):
        """'Description' field of the Add/Edit MCP Server dialog."""
        return self._server_dialog.get_by_placeholder(
            "Describe what this MCP server does"
        )

    @property
    def dialog_documentation_link_input(self):
        """'Link to MCP documentation' field of the Add/Edit MCP Server dialog."""
        return self._server_dialog.get_by_placeholder("https://example.com/docs")

    @property
    def dialog_source_link_input(self):
        """'Link to Source code' field of the Add/Edit MCP Server dialog."""
        return self._server_dialog.get_by_placeholder("https://github.com/user/repo")

    @property
    def dialog_config_json_input(self):
        """'Configuration JSON' field of the Add/Edit MCP Server dialog."""
        return self._server_dialog.get_by_role(
            "textbox", name=re.compile("Configuration JSON")
        )

    @property
    def add_variable_button(self):
        """'Add Variable' button of the Environment Variables section."""
        return self._server_dialog.get_by_role("button", name="Add Variable")

    @property
    def remove_variable_buttons(self):
        """One 'Remove variable' button per environment variable row in the dialog."""
        return self._server_dialog.get_by_role("button", name="Remove variable")

    @property
    def variable_name_inputs(self):
        """'VARIABLE_NAME' field of every environment variable row in the dialog."""
        return self._server_dialog.get_by_placeholder("VARIABLE_NAME")

    @property
    def variable_description_inputs(self):
        """Description field of every environment variable row in the dialog."""
        return self._server_dialog.get_by_placeholder("Description", exact=True)

    @property
    def no_variables_in_dialog_text(self):
        """Empty-state text of the dialog's Environment Variables section."""
        return self._server_dialog.get_by_text("No environment variables defined")

    @property
    def create_server_button(self):
        """'Create Server Configuration' submit button of the Add MCP Server dialog."""
        return self.add_dialog.get_by_role("button", name="Create Server Configuration")

    @property
    def update_server_button(self):
        """'Update Server' submit button of the Edit MCP Server dialog."""
        return self.edit_dialog.get_by_role("button", name="Update Server")

    @property
    def dialog_cancel_button(self):
        """'Cancel' button of the Add/Edit MCP Server dialog."""
        return self._server_dialog.get_by_role("button", name="Cancel")

    @property
    def details_close_button(self):
        """'Close details' button of the details side panel."""
        return self.page.get_by_role("button", name="Close details")

    def details_heading(self, name: str):
        """Server name heading of the details side panel."""
        return self.page.get_by_role("heading", name=name, level=2)

    @property
    def details_variables_heading(self):
        """'Variables (N)' / 'Variables' heading of the details side panel."""
        return self.page.get_by_role("heading", name=re.compile(r"^Variables\b"))

    @property
    def details_no_variables_text(self):
        """'No variables configured' text of the details side panel."""
        return self.page.get_by_text("No variables configured", exact=True)

    @property
    def details_variables_overview_value(self):
        """Overview 'Variables' value of the details panel ('N variables' or 'No variables')."""
        return self.page.get_by_text(re.compile(r"^(\d+ variables|No variables)$"))

    @property
    def details_updated_label(self):
        """'Updated:' label of the details panel's Timestamps section."""
        return self.page.get_by_text("Updated:", exact=True)

    def details_variable_name(self, variable_name: str):
        """Variable card of the details side panel, found by the variable name."""
        return self.page.get_by_text(variable_name, exact=True)

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
    def reload_catalog(self):
        """Reload the page so the list shows what the backend stored, with all rows on one page."""
        self.page.reload()
        expect(self.add_server_button).to_be_visible(timeout=15000)
        self.show_100_items_per_page()
        return self

    @step
    def open_add_server_dialog(self):
        """Click 'Add MCP Server'."""
        self.add_server_button.click()
        return self

    @step
    def fill_server_form(self, server: CatalogServerFormData):
        """Fill the required fields of the Add MCP Server dialog."""
        self.dialog_name_input.fill(server.name)
        self.dialog_description_input.fill(server.description)
        self.dialog_documentation_link_input.fill(server.documentation_url)
        self.dialog_source_link_input.fill(server.source_url)
        self.dialog_config_json_input.fill(server.config_json)
        return self

    @step
    def add_environment_variable(self, name: str, description: str):
        """Add one environment variable row to the open dialog and fill it."""
        self.add_variable_button.click()
        self.variable_name_inputs.last.fill(name)
        self.variable_description_inputs.last.fill(description)
        return self

    @step
    def remove_environment_variable(self):
        """Click 'Remove variable' on the first environment variable row."""
        self.remove_variable_buttons.first.click()
        return self

    @step
    def submit_create(self):
        """Click 'Create Server Configuration'."""
        self.create_server_button.click()
        return self

    @step
    def submit_update(self):
        """Click 'Update Server' and keep the PUT request the page sends."""
        with self.page.expect_request(
            lambda request: request.method == "PUT" and "mcp-configs" in request.url
        ) as request_info:
            self.update_server_button.click()
        self.last_update_request = request_info.value
        return self

    @step
    def open_edit_dialog(self, server_name: str):
        """Choose Edit from the actions menu of the ``server_name`` row."""
        self.open_row_actions_menu(server_name)
        self.edit_menu_item.click()
        return self

    @step
    def open_details(self, server_name: str):
        """Click the name of the ``server_name`` row to open its details side panel."""
        self.server_name_button(server_name).click()
        expect(self.details_heading(server_name)).to_be_visible(timeout=10000)
        return self

    @step
    def close_details(self, server_name: str):
        """Close the details side panel; it overlays the list rows and blocks clicks on them."""
        self.details_close_button.click()
        expect(self.details_heading(server_name)).to_be_hidden(timeout=10000)
        return self

    @step
    def cancel_dialog(self):
        """Click 'Cancel' in the open Add/Edit MCP Server dialog."""
        self.dialog_cancel_button.click()
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
    def should_see_server_dialog_closed(self):
        """Assert neither the Add nor the Edit MCP Server dialog is open."""
        expect(self.add_dialog).to_be_hidden(timeout=15000)
        expect(self.edit_dialog).to_be_hidden(timeout=15000)
        return self

    @step
    def should_see_edit_dialog(self):
        """Assert the 'Edit MCP Server' dialog is open."""
        expect(self.edit_dialog).to_be_visible(timeout=10000)
        return self

    @step
    def should_see_dialog_environment_variable_count(self, count: int):
        """Assert the dialog lists exactly ``count`` environment variable rows."""
        expect(self.remove_variable_buttons).to_have_count(count)
        expect(self.variable_name_inputs).to_have_count(count)
        return self

    @step
    def should_see_dialog_environment_variable(self, name: str):
        """Assert the dialog's first environment variable row carries ``name``."""
        expect(self.variable_name_inputs.first).to_have_value(name)
        return self

    @step
    def should_see_no_environment_variables_in_dialog(self):
        """Assert the dialog shows its 'No environment variables defined' empty state."""
        expect(self.no_variables_in_dialog_text).to_be_visible()
        return self

    @step
    def should_have_sent_empty_env_vars(self):
        """Assert the captured update request body carries ``required_env_vars: []``."""
        assert_that(
            self.last_update_request.post_data_json,
            has_entry("required_env_vars", []),
            "The update request must send an empty required_env_vars list, "
            "not omit the key",
        )
        return self

    @step
    def should_see_details_variable_count(self, count: int):
        """Assert the details panel's Overview shows ``count`` variables."""
        expected = f"{count} variables" if count else "No variables"
        expect(self.details_variables_overview_value).to_have_text(expected)
        return self

    @step
    def should_see_details_variable(self, name: str):
        """Assert the details panel lists the variable ``name``."""
        expect(self.details_variable_name(name)).to_have_count(1)
        return self

    @step
    def should_not_see_details_variable(self, name: str):
        """Assert the details panel does not list the variable ``name``."""
        expect(self.details_variable_name(name)).to_have_count(0)
        return self

    @step
    def should_see_no_variables_in_details(self):
        """Assert the details panel's Variables section shows its empty state."""
        expect(self.details_variables_heading).to_have_text("Variables")
        expect(self.details_no_variables_text).to_be_visible()
        return self

    @step
    def should_see_details_updated_timestamp(self):
        """Assert the details panel shows an 'Updated:' timestamp (only present once the server was updated)."""
        expect(self.details_updated_label).to_be_visible()
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
