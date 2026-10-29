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
MCP Servers Section Page Object

This page object handles all interactions with the MCP Servers section
in the Create/Edit Assistant page, including:
- MCP Servers accordion
- Browse Catalog and Manual Setup dialogs
- MCP server configuration and tool selection
"""

import re
from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.assistants.assistant_mcp_server import (
    AssistantMCPIntegrationModal,
)


class MCPServersSection(BasePage):
    """
    Page object for MCP Servers section in Create/Edit Assistant page.

    Handles interactions with:
    - MCP Servers accordion
    - Browse Catalog dialog
    - Manual Setup dialog
    - MCP server configuration (Step 1: Configure Server)
    - MCP tool selection (Step 2: Select Tools)
    - Configured MCP servers management
    """

    def __init__(self, page):
        """Initialize the MCP Servers section page object."""
        super().__init__(page)
        self.mcp_modal = AssistantMCPIntegrationModal(page)

    # =============================================================================
    # LOCATORS - MCP Servers Accordion
    # =============================================================================

    @property
    def mcp_servers_accordion(self) -> Locator:
        """MCP Servers accordion header - <a role=button> inside p-accordion-header"""
        return self.page.get_by_role("button", name="MCP Servers")

    @property
    def mcp_servers_accordion_content(self) -> Locator:
        """MCP Servers accordion content section"""
        return (
            self.page.locator("div.p-accordion-tab-active")
            .locator("div.p-accordion-content")
            .filter(has=self.page.locator('h2:has-text("MCP Servers")'))
        )

    @step
    def mcp_browse_catalog_button(self):
        """Browse Catalog button in MCP Servers section"""
        return self.page.locator("button").filter(has_text="Browse Catalog")

    @step
    def mcp_manual_setup_button(self):
        """Manual Setup button in MCP Servers section"""
        return self.page.locator("button").filter(has_text="Manual Setup")

    @step
    def mcp_json_button(self):
        """JSON button in MCP configuration (temporary)"""
        return self.page.get_by_role("button", name="JSON")

    # =============================================================================
    # LOCATORS - Browse Catalog Dialog
    # =============================================================================

    @property
    def mcp_browse_catalog_dialog(self) -> Locator:
        """MCP Browse Catalog dialog.

        Matches both native <dialog> elements and <div role="dialog"> patterns.
        """
        return self.page.locator('dialog, div[role="dialog"]').filter(
            has_text="Browse MCP Servers"
        )

    @property
    def mcp_server_cards_grid(self) -> Locator:
        """Grid containing MCP server cards in browse catalog."""
        return self.mcp_browse_catalog_dialog.locator("div.grid")

    def mcp_server_card(self, server_name: str) -> Locator:
        """
        Get specific MCP server card by name in browse catalog.

        Uses case-insensitive matching to handle variations in capitalization
        between test data and UI display (e.g., "Fetch MCP server" vs "Fetch MCP Server").

        Args:
            server_name: Name of the MCP server (e.g., "filesystem", "brave-search")

        Returns:
            Locator: The MCP server card element
        """
        # Use case-insensitive regex matching for the server name in h3
        # This handles variations like "Fetch MCP server" vs "Fetch MCP Server"

        # Escape special regex characters and create case-insensitive pattern
        escaped_name = re.escape(server_name)
        pattern = f"^{escaped_name}$"

        return self.mcp_server_cards_grid.locator("div.flex.flex-col").filter(
            has=self.page.locator("h3").locator(f"text=/{pattern}/i")
        )

    def mcp_server_add_button(self, server_name: str) -> Locator:
        """
        Get Add button for specific MCP server in browse catalog.

        Args:
            server_name: Name of the MCP server (e.g., "filesystem", "brave-search")

        Returns:
            Locator: The Add button for the specified server
        """
        return (
            self.mcp_server_card(server_name).locator("button").filter(has_text="Add")
        )

    # =============================================================================
    # LOCATORS - MCP Configuration Dialog (Step 1)
    # =============================================================================

    @property
    def mcp_config_dialog(self) -> Locator:
        """MCP Server Configuration dialog (Step 1).

        Matches both native <dialog> elements and <div role="dialog"> patterns.
        """
        return self.page.locator('dialog, div[role="dialog"]').filter(
            has_text="Step 1: Configure MCP Server"
        )

    @property
    def mcp_config_form(self) -> Locator:
        """MCP Server Configuration form (main container for all form fields)."""
        return self.mcp_config_dialog.locator("form.flex.flex-col.gap-4")

    @property
    def mcp_config_name_input(self) -> Locator:
        """Name input field in MCP configuration dialog."""
        return self.mcp_config_form.locator('input[name="name"]')

    @property
    def mcp_config_description_textarea(self) -> Locator:
        """Description textarea in MCP configuration dialog."""
        return self.mcp_config_form.locator('textarea[name="description"]')

    @property
    def mcp_config_tokens_limit_input(self) -> Locator:
        """Tools Tokens Size Limit input in MCP configuration dialog."""
        return self.mcp_config_form.locator('input[name="tokensSizeLimit"]')

    @property
    def mcp_config_json_textarea(self) -> Locator:
        """MCP Configuration JSON textarea."""
        return self.mcp_config_form.locator("textarea#json-config")

    @property
    def mcp_config_connect_url_input(self) -> Locator:
        """MCP-Connect URL input field."""
        return self.mcp_config_form.locator('input[name="connectUrl"]')

    @property
    def mcp_config_env_vars_section(self) -> Locator:
        """Environment Variables section in MCP configuration dialog."""
        return self.mcp_config_form.locator(
            'label:has-text("Environment Variables")'
        ).locator("..")

    def mcp_config_env_var_value_input(self, key_name: str) -> Locator:
        """
        Get environment variable value input by key name.

        Args:
            key_name: The environment variable key name (e.g., "DB_NAME")

        Returns:
            Locator: The value input field for the specified key
        """
        # Find the row that contains the key name, then get the value input
        return (
            self.mcp_config_env_vars_section.locator(f'text="{key_name}"')
            .locator("..")
            .locator("..")
            .locator("textbox")
            .last
        )

    @property
    def global_mode_button(self) -> Locator:
        """Global mode button in the Global/Custom SelectButton toggle (Step 1).

        Returns the 'Global' button from the PrimeReact SelectButton group.
        aria-pressed="true" when Global mode is active.
        """
        return self.mcp_config_form.get_by_role("button", name="Global")

    @property
    def custom_mode_button(self) -> Locator:
        """Custom mode button in the Global/Custom SelectButton toggle (Step 1).

        Returns the 'Custom' button from the PrimeReact SelectButton group.
        aria-pressed="true" when Custom mode is active.
        """
        return self.mcp_config_form.get_by_role("button", name="Custom")

    @property
    def global_config_textarea(self) -> Locator:
        """Read-only config textarea shown when Global mode is active.

        aria-label="Configuration (JSON format) - Global".
        Disabled in Global mode — it mirrors the catalog config.
        """
        return self.mcp_config_form.get_by_label("Configuration (JSON format) - Global")

    @property
    def mcp_config_cancel_button(self) -> Locator:
        """Cancel button in MCP configuration dialog."""
        return self.mcp_config_dialog.locator("button").filter(has_text="Cancel")

    @property
    def mcp_config_test_integration_button(self) -> Locator:
        """Test Integration button in MCP configuration dialog."""
        return self.mcp_config_dialog.locator("button").filter(
            has_text="Test Integration"
        )

    @property
    def mcp_config_next_button(self) -> Locator:
        """Next button in MCP configuration dialog."""
        return self.mcp_config_dialog.locator("button").filter(has_text="Next")

    # =============================================================================
    # LOCATORS - MCP Tools Selection Dialog (Step 2)
    # =============================================================================

    @property
    def mcp_tools_dialog(self) -> Locator:
        """MCP Tools Selection dialog (Step 2).

        Matches both native <dialog> elements and <div role="dialog"> patterns.
        """
        return self.page.locator('dialog, div[role="dialog"]').filter(
            has_text="Step 2: Select Tools"
        )

    @property
    def mcp_tools_save_button(self) -> Locator:
        """Save button in MCP tools selection dialog (Step 2)."""
        # The dialog that contains Save button is the Step 2 dialog
        return (
            self.page.locator('dialog, div[role="dialog"]')
            .locator("button")
            .filter(has_text="Save")
            .first
        )

    @property
    def mcp_tools_add_button(self) -> Locator:
        """Add button in MCP tools selection dialog (Step 2)."""
        # The dialog that contains Add button is the Step 2 dialog
        return (
            self.page.locator('dialog, div[role="dialog"]')
            .locator("button")
            .filter(has_text="Add")
            .first
        )

    @property
    def mcp_tools_use_all_tools_checkbox(self) -> Locator:
        """
        'Use all available tools' checkbox in Step 2 (Select Tools).

        Locates the checkbox by finding text "Use all available tools" within the dialog
        and navigating to the associated checkbox input.
        """
        return (
            self.page.locator('dialog, div[role="dialog"]')
            .get_by_text("Use all available tools")
            .locator("../..")
            .locator('input[type="checkbox"]')
            .first
        )

    @property
    def mcp_tools_back_button(self) -> Locator:
        """Back button in MCP tools selection dialog (Step 2)."""
        return self.mcp_tools_dialog.locator("button").filter(has_text="Back")

    @property
    def mcp_tools_cancel_button(self) -> Locator:
        """Cancel button in MCP tools selection dialog (Step 2)."""
        return self.mcp_tools_dialog.locator("button").filter(has_text="Cancel")

    # =============================================================================
    # LOCATORS - Configured MCP Servers
    # =============================================================================

    def configured_mcp_server_heading(self, server_name: str) -> Locator:
        """
        Get configured MCP server heading (h2) by name.

        This locator finds MCP server headings in the configured servers list.
        The heading text may have different capitalization than the server name
        in the database, so this uses case-insensitive matching.

        Args:
            server_name: Name of the configured MCP server (e.g., "Fetch MCP server")

        Returns:
            Locator: The h2 heading element for the MCP server
        """
        # Use case-insensitive text matching for the heading
        return self.page.locator(f'h2:text-is("{server_name}")').or_(
            self.page.locator("h2").filter(has_text=server_name)
        )

    def configured_mcp_server_container(self, server_name: str) -> Locator:
        """
        Get configured MCP server container by name.

        The container is 2 parent levels up from the h2 heading and contains
        the checkbox and other controls.
        DOM structure: h2 -> div.flex-1.min-w-0 -> div.flex.items-center.p-3 (container)

        Args:
            server_name: Name of the configured MCP server

        Returns:
            Locator: The container element for the configured server
        """
        return (
            self.configured_mcp_server_heading(server_name).locator("..").locator("..")
        )

    def configured_mcp_server_checkbox(self, server_name: str) -> Locator:
        """
        Get checkbox for a configured MCP server.

        Args:
            server_name: Name of the configured MCP server

        Returns:
            Locator: The checkbox for the configured server
        """
        return (
            self.configured_mcp_server_container(server_name)
            .locator('input[type="checkbox"]')
            .first
        )

    def configured_mcp_server_more_options_button(self, server_name: str) -> Locator:
        """
        Get "More options" button for a configured MCP server.

        Args:
            server_name: Name of the configured MCP server

        Returns:
            Locator: The "More options" button for the configured server
        """
        return (
            self.configured_mcp_server_container(server_name)
            .locator('button:has-text("More options")')
            .first
        )

    # =============================================================================
    # LOCATORS - MCP Server Checkboxes in Catalog
    # =============================================================================

    def tool_label_spans_under_toolkit(self, tool: str) -> Locator:
        """
        Get MCP server label element in the MCP catalog.

        Special handling for MCP servers in the accordion.

        Args:
            tool: The MCP server name

        Returns:
            Locator: The label element for the MCP server
        """
        tool_stripped = tool.strip()
        # Special handling for MCP servers
        if "mcp" in tool_stripped.lower():
            return (
                self.page.locator("div.p-accordion-tab-active")
                .filter(has_text="MCP Servers")
                .locator("div.p-accordion-content")
                .get_by_text(tool_stripped, exact=True)
                .first
            )
        # Fallback for other tools
        return (
            self.page.locator("div.p-accordion-tab-active div.p-accordion-content")
            .get_by_text(tool_stripped, exact=True)
            .first
        )

    def tool_checkbox(self, tool_name: str) -> Locator:
        """
        Get checkbox for an MCP server in the catalog.

        The catalog item uses a label element (not span) for the server name text,
        with the PrimeVue p-checkbox component as a sibling inside the same flex container.
        DOM structure: div.flex.items-center.group.gap-x-2 > div.p-checkbox > input[type=checkbox]
                       div.flex.items-center.group.gap-x-2 > label (contains tool_name text)

        Args:
            tool_name: The MCP server name

        Returns:
            Locator: The checkbox element
        """
        return (
            self.page.locator("label")
            .filter(has_text=tool_name)
            .locator("xpath=..")
            .locator("input[type=checkbox]")
        )

    # =============================================================================
    # ACTION METHODS - Accordion
    # =============================================================================

    @step
    def expand_mcp_servers_accordion(self):
        """
        Expand the MCP Servers accordion in Tools & Integrations section.

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_servers_accordion.click()
        return self

    # =============================================================================
    # ACTION METHODS - Browse Catalog
    # =============================================================================

    @step
    def click_mcp_browse_catalog(self):
        """
        Click Browse Catalog button to open MCP server selection dialog.

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_browse_catalog_button().click()
        return self

    @step
    def add_mcp_server_from_catalog(self, server_name: str):
        """
        Click Add button for specific MCP server in browse catalog.

        Args:
            server_name: Name of the MCP server to add (e.g., "filesystem", "brave-search")

        Returns:
            self: Returns the page object for method chaining
        """
        self.page.get_by_placeholder("Search MCP servers...").type(server_name)
        self.mcp_server_add_button(server_name).click()
        return self

    # =============================================================================
    # ACTION METHODS - Manual Setup
    # =============================================================================

    @step
    def click_mcp_manual_setup(self):
        """
        Click Manual Setup button to open MCP server manual configuration dialog.

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_manual_setup_button().click()
        return self

    # =============================================================================
    # ACTION METHODS - Configuration Form (Step 1)
    # =============================================================================

    @step
    def fill_mcp_config_name(self, name: str):
        """
        Fill name field in MCP configuration dialog.

        Args:
            name: MCP server name

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_config_name_input.clear()
        self.mcp_config_name_input.fill(name)
        return self

    @step
    def fill_mcp_config_description(self, description: str):
        """
        Fill description field in MCP configuration dialog.

        Args:
            description: Description text

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_config_description_textarea.clear()
        self.mcp_config_description_textarea.fill(description)
        return self

    @step
    def fill_mcp_config_tokens_limit(self, tokens_limit: int):
        """
        Fill Tools Tokens Size Limit field in MCP configuration dialog.

        Args:
            tokens_limit: Maximum tokens size limit

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_config_tokens_limit_input.clear()
        self.mcp_config_tokens_limit_input.fill(str(tokens_limit))
        return self

    @step
    def fill_mcp_config_json(self, json_config: str):
        """
        Fill MCP Configuration JSON textarea.

        Args:
            json_config: JSON configuration as string

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_config_json_textarea.clear()
        self.mcp_config_json_textarea.fill(json_config)
        return self

    @step
    def fill_mcp_config_connect_url(self, url: str):
        """
        Fill MCP-Connect URL field.

        Args:
            url: MCP-Connect URL

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_config_connect_url_input.clear()
        self.mcp_config_connect_url_input.fill(url)
        return self

    @step
    def fill_mcp_config_env_var(self, key_name: str, value: str):
        """
        Fill MCP configuration environment variable.

        Args:
            key_name: The environment variable key name (e.g., "DB_NAME")
            value: The value to fill

        Returns:
            self: Returns the page object for method chaining
        """
        env_var_input = self.mcp_config_env_var_value_input(key_name)
        env_var_input.clear()
        env_var_input.fill(value)
        return self

    @step
    def configure_mcp_server(
        self,
        description: str = "Test MCP Server",
        tokens_limit: int = None,
        json_config: str = None,
        connect_url: str = None,
    ):
        """
        Configure MCP server with provided values.
        This is a convenience method that fills all fields and clicks Next.

        Args:
            description: Description text (default: "Test MCP Server")
            tokens_limit: Maximum tokens size limit (optional)
            json_config: JSON configuration as string (optional)
            connect_url: MCP-Connect URL (optional)

        Returns:
            self: Returns the page object for method chaining
        """
        # Fill description
        self.fill_mcp_config_description(description)

        # Fill tokens limit if provided
        if tokens_limit is not None:
            self.fill_mcp_config_tokens_limit(tokens_limit)

        # Fill JSON config if provided
        if json_config is not None:
            self.fill_mcp_config_json(json_config)

        # Fill connect URL if provided
        if connect_url is not None:
            self.fill_mcp_config_connect_url(connect_url)

        return self

    @step
    def click_mcp_config_next(self):
        """
        Click Next button in MCP configuration dialog.

        Returns:
            self: Returns the page object for method chaining
        """
        # Ensure button is visible and ready
        self.mcp_config_next_button.wait_for(state="visible", timeout=10000)
        # Force click to avoid interception issues
        self.mcp_config_next_button.click(force=True)
        # Wait longer for Step 2 to load
        self.page.wait_for_timeout(2000)
        return self

    @step
    def click_mcp_config_test_integration(self):
        """
        Click Test Integration button in MCP configuration dialog.

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_config_test_integration_button.click()
        self.page.wait_for_timeout(1000)
        return self

    @step
    def click_mcp_config_cancel(self):
        """
        Click Cancel button in MCP configuration dialog.

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_config_cancel_button.click()
        self.page.wait_for_timeout(500)
        return self

    # =============================================================================
    # ACTION METHODS - Tools Selection (Step 2)
    # =============================================================================

    @step
    def click_mcp_tools_save(self):
        """
        Click Save button in MCP tools selection dialog (Step 2).

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_tools_save_button.click()
        self.page.wait_for_timeout(1000)
        return self

    @step
    def click_mcp_tools_add(self):
        """
        Click Add button in MCP tools selection dialog (Step 2).

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_tools_add_button.click()
        self.page.wait_for_timeout(1000)
        return self

    @step
    def click_mcp_tools_back(self):
        """
        Click Back button in MCP tools selection dialog (Step 2).

        Returns:
            self: Returns the page object for method chaining
        """
        self.mcp_tools_back_button.click()
        self.page.wait_for_timeout(500)
        return self

    @step
    def wait_for_mcp_tools_step(self):
        """
        Wait for Step 2 (Select Tools) to appear by waiting for Save or Add button.

        Returns:
            self: Returns the page object for method chaining
        """
        # Wait for either Save button (catalog flow) or Add button (manual setup flow)
        # Check which button is present in Step 2
        try:
            self.mcp_tools_save_button.wait_for(state="visible", timeout=5000)
        except Exception:
            # If Save button not found, wait for Add button
            self.mcp_tools_add_button.wait_for(state="visible", timeout=5000)
        return self

    @step
    def select_use_all_tools_checkbox(self):
        """
        Ensure 'Use all available tools' checkbox is checked in Step 2.
        By default it should be checked, but this ensures it.

        Returns:
            self: Returns the page object for method chaining
        """
        # Wait for Step 2 dialog to be visible first
        self.wait_for_mcp_tools_step()

        # Wait a bit for the dialog to fully render
        self.page.wait_for_timeout(1000)

        # Wait for the checkbox to be attached to the DOM
        self.mcp_tools_use_all_tools_checkbox.wait_for(state="attached", timeout=10000)

        # Scroll into view if needed
        self.mcp_tools_use_all_tools_checkbox.scroll_into_view_if_needed()

        # Check if checkbox is already checked
        try:
            is_checked = self.mcp_tools_use_all_tools_checkbox.is_checked()
            if not is_checked:
                # Click the checkbox to check it
                self.mcp_tools_use_all_tools_checkbox.click(force=True)
                self.page.wait_for_timeout(500)
        except Exception:
            # If we can't determine the state, just try to click it
            self.mcp_tools_use_all_tools_checkbox.click(force=True)
            self.page.wait_for_timeout(500)

        return self

    # =============================================================================
    # ACTION METHODS - MCP Server Selection/Deselection
    # =============================================================================

    @step
    def select_mcp_server(self, server_name: str):
        """
        Select an MCP server from the MCP Servers accordion (catalog).
        If configuration modal appears, fills the form and submits.

        This method is used to add new MCP servers from the catalog by clicking
        the checkbox. It does not apply to already configured servers.

        Args:
            server_name: Name of the MCP server to select from catalog (e.g., "filesystem")

        Returns:
            self: Returns the page object for method chaining
        """
        # Find and click the server checkbox in the catalog
        server_checkbox = self.tool_checkbox(server_name)
        server_tool = self.tool_label_spans_under_toolkit(server_name)

        if server_checkbox.count() > 0 and not server_checkbox.is_checked():
            # Checkbox exists and is not checked, click to select
            server_tool.click()

            # If configuration popup appears, fill base form
            if self.mcp_modal.is_pop_visible():
                self.mcp_modal.fill_mcp_server_base_form()

        return self

    @step
    def unselect_mcp_server(self, server_name: str):
        """
        Unselect (deselect/uncheck) an MCP server checkbox to remove it.

        This method handles two scenarios:
        1. Configured servers: Unchecks the checkbox to remove from assistant
        2. Catalog servers: Unchecks the checkbox to deselect

        Args:
            server_name: Name of the MCP server to unselect (e.g., "filesystem", "Fetch MCP server")

        Returns:
            self: Returns the page object for method chaining
        """
        # First try to find configured server checkbox
        configured_checkbox = self.configured_mcp_server_checkbox(server_name)

        if configured_checkbox.count() > 0:
            # Configured server found, click checkbox to uncheck (remove)
            if configured_checkbox.is_checked():
                configured_checkbox.click()
                self.page.wait_for_timeout(300)  # Wait for UI to update
        else:
            # Not in configured list, try catalog checkbox
            server_checkbox = self.tool_checkbox(server_name)
            if server_checkbox.count() > 0 and server_checkbox.is_checked():
                # Checkbox exists and is checked, click to uncheck
                server_tool = self.tool_label_spans_under_toolkit(server_name)
                server_tool.click()
                self.page.wait_for_timeout(300)

        return self

    # =============================================================================
    # VERIFICATION METHODS
    # =============================================================================

    @step
    def should_have_mcp_server_checked(self, server_name: str):
        """
        Verify that an MCP server is currently checked/selected or configured.

        This method handles two scenarios:
        1. Unconfigured servers in catalog: Verifies checkbox is checked
        2. Already configured servers: Verifies checkbox in configured list is checked

        Args:
            server_name: Name of the MCP server to verify

        Returns:
            self: Returns the page object for method chaining
        """
        # First try to find configured server (by h4 heading)
        configured_checkbox = self.configured_mcp_server_checkbox(server_name)

        if configured_checkbox.count() > 0:
            # Configured server found, verify its checkbox is checked
            expect(configured_checkbox).to_be_checked()
        else:
            # Not in configured list, try catalog checkbox (span-based)
            server_checkbox = self.tool_checkbox(server_name)
            expect(server_checkbox).to_be_checked()

        return self

    @step
    def should_have_mcp_server_unchecked(self, server_name: str):
        """
        Verify that an MCP server is currently unchecked/not selected or not configured.

        This method handles two scenarios:
        1. Configured servers: Verifies checkbox is unchecked (server being removed)
        2. Catalog servers: Verifies checkbox is unchecked (server not selected)

        Args:
            server_name: Name of the MCP server to verify

        Returns:
            self: Returns the page object for method chaining
        """
        # First try to find configured server checkbox
        configured_checkbox = self.configured_mcp_server_checkbox(server_name)

        if configured_checkbox.count() > 0:
            # Configured server found, verify its checkbox is unchecked
            expect(configured_checkbox).not_to_be_checked()
        else:
            # Not in configured list, try catalog checkbox
            server_checkbox = self.tool_checkbox(server_name)
            if server_checkbox.count() > 0:
                # Catalog checkbox exists, verify it's unchecked
                expect(server_checkbox).not_to_be_checked()
            # If neither exists, that's fine - server is not present at all

        return self

    @step
    def should_have_mcp_servers_accordion_visible(self):
        """
        Verify that MCP Servers accordion is visible.

        Returns:
            self: Returns the page object for method chaining
        """
        expect(self.mcp_servers_accordion).to_be_visible()
        return self

    @step
    def should_have_mcp_setup_buttons_visible(self):
        """
        Verify that Browse Catalog and Manual Setup buttons are visible in MCP Servers section.

        Returns:
            self: Returns the page object for method chaining
        """
        expect(self.mcp_browse_catalog_button()).to_be_visible()
        expect(self.mcp_manual_setup_button()).to_be_visible()
        return self

    # =============================================================================
    # VERIFICATION METHODS - Global/Custom toggle
    # =============================================================================

    @step
    def get_mcp_config_mode(self) -> str:
        """Return the currently active config mode: 'Global' or 'Custom'.

        Reads the aria-pressed attribute on the two SelectButton buttons.

        Returns:
            str: 'Global' if Global button is pressed, 'Custom' otherwise.
        """
        global_pressed = self.global_mode_button.get_attribute("aria-pressed")
        return "Global" if global_pressed == "true" else "Custom"

    @step
    def should_have_global_mode_selected(self):
        """Assert that the Global mode button is pressed and the config textarea is disabled.

        Verifies:
        - Global button has aria-pressed="true"
        - Config textarea is disabled (inheriting catalog config)

        Returns:
            self: Returns the page object for method chaining
        """
        expect(self.global_mode_button).to_have_attribute("aria-pressed", "true")
        expect(self.global_config_textarea).to_be_disabled()
        return self
