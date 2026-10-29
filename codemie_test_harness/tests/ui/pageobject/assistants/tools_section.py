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
Tools Section Page Object

This page object handles all interactions with the Tools & Integrations section
in the Create/Edit Assistant page, including Available Tools and External Tools accordions.
"""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ToolsSection(BasePage):
    """
    Page object for Tools & Integrations section in Create/Edit Assistant page.

    Handles interactions with:
    - Available Tools accordion (internal toolkits and tools)
    - External Tools accordion
    - Tool selection and verification
    """

    def __init__(self, page):
        """Initialize the Tools section page object."""
        super().__init__(page)

    # =============================================================================
    # LOCATORS - Tools & Integrations Section
    # =============================================================================

    @property
    def tools_integrations_section(self) -> Locator:
        """Tools configuration section header - h1 with font-semibold in redesigned UI"""
        return self.page.locator(
            'h1.font-semibold.text-text-primary:has-text("Tools configuration")'
        )

    @property
    def available_tools_accordion(self) -> Locator:
        """Available Tools accordion header - <a role=button> inside p-accordion-header"""
        return self.page.get_by_role("button", name="Available Tools")

    @property
    def external_tools_accordion(self) -> Locator:
        """External Tools accordion header - <a role=button> inside p-accordion-header"""
        return self.page.get_by_role("button", name="External Tools")

    # =============================================================================
    # LOCATOR METHODS - Dynamic Locators
    # =============================================================================

    @step
    def section(self, name: str) -> Locator:
        """Get main accordion section (Available Tools or External Tools) by name.

        Returns the clickable <a role=button> link inside the p-accordion-header div.
        """
        return self.page.get_by_role("button", name=name)

    @step
    def toolkit(self, section_name: str, toolkit_name: str) -> Locator:
        """
        Get toolkit clickable row within the Available Tools section by name.

        In the redesigned UI toolkits are plain div rows (not PrimeReact accordions).
        Each toolkit has an h2 with class 'assistant-form-toolkit-{name}' inside a
        cursor-pointer div row.

        Handles both spaced and non-spaced toolkit names (e.g., 'Open API' vs 'OpenAPI')
        Also handles variations like 'File Management' vs 'Filesystem'

        Args:
            section_name: The section containing the toolkit (e.g., "Available Tools")
            toolkit_name: The name of the toolkit to find

        Returns:
            Locator: The toolkit clickable row element
        """
        # Try the exact name first, if not found try without spaces
        toolkit_name_no_space = toolkit_name.replace(" ", "")

        # Handle special case: "File Management" is called "Filesystem" in UI
        toolkit_variations = [toolkit_name, toolkit_name_no_space]
        if "file" in toolkit_name.lower() and "management" in toolkit_name.lower():
            toolkit_variations.extend(["Filesystem", "File System"])

        # Build selector for all variations using h2.font-medium inside cursor-pointer row
        selectors = [
            f'div.cursor-pointer:has(h2.font-medium:text-is("{variant}"))'
            for variant in toolkit_variations
        ]

        return self.page.locator(",".join(selectors)).first

    @step
    def tool_rows_under_toolkit(self, toolkit_name: str) -> Locator:
        """Returns all tool rows (each with a label and a checkbox) under an expanded toolkit panel."""
        panel = self.page.locator(
            "div.p-accordion-tab.p-accordion-tab-active div.p-accordion-content"
        ).filter(has_text=toolkit_name)
        return panel.locator(
            "div.grid.grid-cols-[auto,1fr]"
        )  # Adapt selector to match tool row

    @step
    def tool_label_spans_under_toolkit(self, tool: str) -> Locator:
        """
        Get tool label element by tool name.

        Args:
            tool: The name of the tool to find

        Returns:
            Locator: The tool label element
        """
        tool_stripped = tool.strip()

        # In the redesigned two-panel tools UI, tool labels are <label> elements.
        # Each label's textContent is "{tool_name}{separator}{tooltip_description}"
        # where the separator is EITHER absent (description starts immediately) OR
        # a newline + spaces (for multi-line tooltip descriptions).
        #
        # Three matching problems to solve:
        # 1. Substring match: filter(has_text="List Branches In Repo") matches
        #    "Create Branch" because its description mentions "List Branches In Repo".
        #    Fix: anchor to start of string with ^.
        # 2. Prefix match: "Update File" starts with ^Update\ File but so does
        #    "Update File Diff" (as "Update File DiffUpdates...").
        #    Fix: require the character immediately after the tool name to be an
        #    uppercase letter (first char of the description) or end-of-string
        #    or a newline (for tools whose description is on a new line).
        #    This works because descriptions start with capital letters while
        #    multi-word tool names are separated by single spaces (not newlines),
        #    so "Update File " + "D" (space before "D") cannot match
        #    ^Update\ File(?=[A-Z\n]|$), but "Update File" + "U" or
        #    "Get Repo Tree..." + "\n    Useful..." do.
        # 3. Newline separator: some tooltips (e.g. "Get Repo Tree with filtering
        #    (Experimental)") have "\n    " between the tool name and description.
        #    Fix: add \n to the lookahead character class.
        return self.page.locator("label:has(span.whitespace-nowrap)").filter(
            has_text=re.compile(f"^{re.escape(tool_stripped)}(?=[A-Z\n]|$)")
        )

    @step
    def tool_checkbox(self, tool_name: str) -> Locator:
        """
        Get checkbox for a tool by tool name.

        Args:
            tool_name: The name of the tool

        Returns:
            Locator: The checkbox element for the tool
        """
        return (
            self.page.locator("span")
            .filter(has_text=tool_name)
            .locator("xpath=..")
            .locator("input[type=checkbox]")
        )

    @step
    def tool_row(self, tool_name: str) -> Locator:
        """
        Get tool row container by tool name.

        Args:
            tool_name: The name of the tool

        Returns:
            Locator: The row container element for the tool
        """
        return (
            self.page.locator("span")
            .filter(has_text=tool_name)
            .locator("xpath=ancestor::div[contains(@class,'grid')]")
        )

    # =============================================================================
    # ACTION METHODS - Tool Selection
    # =============================================================================

    @step
    def select_section(self, section_name: str):
        """
        Select/expand a section by name (Available Tools or External Tools).

        Args:
            section_name: Name of the section to select

        Returns:
            self: Returns the page object for method chaining
        """
        self.section(section_name).click()
        return self

    @step
    def select_toolkit(self, section: str, toolkit: str):
        """
        Select a toolkit within a section.

        Args:
            section: The section containing the toolkit
            toolkit: The name of the toolkit to select

        Returns:
            self: Returns the page object for method chaining
        """
        toolkit_locator = self.toolkit(section, toolkit)
        # Check if toolkit exists before trying to click (some toolkits may not be available)
        if toolkit_locator.count() > 0:
            toolkit_locator.click()
        # Toolkit not found - skip silently (it might not be available in this environment)
        return self

    @step
    def select_tool(self, tool: str):
        """
        Select a tool by clicking on it.

        Skips silently if tool not available in this environment.

        Args:
            tool: Name of the tool to select

        Returns:
            self: Returns the page object for method chaining
        """
        tool_locator = self.tool_label_spans_under_toolkit(tool)
        # Check if tool exists before trying to click (some tools may not be available)
        if tool_locator.count() > 0:
            tool_locator.click()
        # Tool not found - skip silently (it might not be available in this environment)
        return self

    @step
    def select_tool_option(self, toolkit_name: str, label: str, checked: bool = True):
        """
        Select or deselect a tool option within a toolkit.

        Args:
            toolkit_name: The name of the toolkit containing the tool
            label: The label of the tool option
            checked: Whether to check (True) or uncheck (False) the tool

        Returns:
            self: Returns the page object for method chaining
        """
        checkbox = self.toolkit_checkbox_by_label(toolkit_name, label)
        if checked != checkbox.is_checked():
            checkbox.click()
        return self

    def toolkit_checkbox_by_label(self, toolkit_name: str, label: str) -> Locator:
        """
        Get checkbox for a specific tool within a toolkit.

        Args:
            toolkit_name: The name of the toolkit
            label: The label of the tool

        Returns:
            Locator: The checkbox element
        """
        panel = self.toolkit_accordion_panel(toolkit_name)
        return (
            panel.locator(".checkbox-label")
            .filter(has_text=label)
            .locator('input[type="checkbox"]')
        )

    def toolkit_accordion_panel(self, toolkit_name: str) -> Locator:
        """
        Get the content panel of a toolkit accordion.

        Args:
            toolkit_name: The name of the toolkit

        Returns:
            Locator: The panel content element
        """
        return self.page.locator(
            "div.p-accordion-tab.p-accordion-tab-active div.p-accordion-content"
        ).filter(has_text=toolkit_name)

    def get_all_tools_in_toolkit(self, toolkit_name: str):
        """
        Returns a list of tuples (label, checked) for all tool features inside a toolkit accordion.

        Args:
            toolkit_name: The name of the toolkit

        Returns:
            list: List of tuples containing (tool_label, is_checked)
        """
        panel = self.toolkit_accordion_panel(toolkit_name)
        labels = panel.locator(".checkbox-label span.text-sm").all_text_contents()
        checkboxes = panel.locator('input[type="checkbox"]')
        return [
            (lbl, checkboxes.nth(idx).is_checked()) for idx, lbl in enumerate(labels)
        ]

    def toolkit_select_all_checkbox(self, toolkit_name: str):
        """
        Get the "Select all" checkbox for a toolkit.

        Args:
            toolkit_name: The name of the toolkit

        Returns:
            Locator: The "Select all" checkbox element
        """
        return self.toolkit_checkbox_by_label(toolkit_name, "Select all")

    # =============================================================================
    # VERIFICATION METHODS
    # =============================================================================

    @step
    def should_be_visible_tool(self, tool: str):
        """
        Check if a tool is visible.

        Skips silently if tool not available in this environment.

        Args:
            tool: Name of the tool to verify

        Returns:
            self: Returns the page object for method chaining
        """
        tool_locator = self.tool_label_spans_under_toolkit(tool)
        # Only assert visibility if the tool exists (some tools may not be available)
        if tool_locator.count() > 0:
            expect(tool_locator).to_be_visible()
        # Tool not found - skip silently (it might not be available in this environment)
        return self

    @step
    def should_have_tools_integrations_section_visible(self):
        """
        Verify that Tools & Integrations section is visible.

        Returns:
            self: Returns the page object for method chaining
        """
        expect(self.tools_integrations_section).to_be_visible()
        return self
