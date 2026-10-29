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

from playwright.sync_api import Locator, Page, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ToolNodeConfigPanel(BasePage):
    """Page object for the Tool Node Configuration Panel in the workflow visual editor."""

    def __init__(self, page: Page):
        super().__init__(page)

    # ==============================================
    # PROPERTIES - UI ELEMENTS
    # ==============================================

    @property
    def config_panel(self) -> Locator:
        """The tool node configuration panel."""
        return self.page.get_by_role("complementary").filter(
            has=self.page.get_by_role("heading", name="Node configuration")
        )

    @property
    def panel_heading(self) -> Locator:
        """Node configuration heading."""
        return self.page.get_by_role("heading", name="Node configuration", level=3)

    @property
    def tool_selector_button(self) -> Locator:
        """Button that opens the tool selection dialog."""
        return self.config_panel.locator("#tool-select-btn")

    @property
    def tools_dialog(self) -> Locator:
        """Tool selection popup (outer — header 'Select Tool')."""
        return self.page.get_by_role("dialog").filter(
            has=self.page.locator("h4", has_text="Select Tool")
        )

    @property
    def available_tools_dialog(self) -> Locator:
        """Available-tools detail modal (inner — header 'Available Tools')."""
        return self.page.get_by_role("dialog").filter(
            has=self.page.locator("h4", has_text="Available Tools")
        )

    @property
    def code_field(self) -> Locator:
        """Code field textbox (role-based, for fill/value assertions)."""
        return self.config_panel.get_by_role("textbox", name="Code")

    @property
    def code_textarea_element(self) -> Locator:
        """Code field as an explicit <textarea> tag (for tag-type assertion)."""
        return self.config_panel.locator('textarea[placeholder="Enter Code"]')

    @property
    def save_button(self) -> Locator:
        """Save button in the config panel footer."""
        return self.config_panel.get_by_role("button", name="Save")

    @property
    def automatic_credentials_lookup_switch(self) -> Locator:
        """Toolkit-level 'Automatic Credentials Lookup' switch (read-only state check).

        The dropdown to manually pick an integration only renders once this switch is off.
        """
        return self.available_tools_dialog.get_by_role(
            "switch", name="Automatic Credentials Lookup"
        )

    @property
    def automatic_credentials_lookup_label(self) -> Locator:
        """Clickable label for the 'Automatic Credentials Lookup' switch.

        The switch input itself is visually covered by a styled overlay that intercepts
        pointer events, so the label text is the reliable click target to toggle it.
        """
        return self.available_tools_dialog.get_by_text(
            "Automatic Credentials Lookup", exact=True
        )

    @property
    def tool_configuration_region(self) -> Locator:
        """The 'Tool Configuration' accordion region holding the bound tool's argument
        fields (e.g. Branch Name for Create Branch / Set Active Branch)."""
        return self.config_panel.get_by_role("region", name="Tool Configuration")

    @property
    def integration_dropdown_trigger(self) -> Locator:
        """Toolkit-level integration dropdown trigger.

        Its accessible name stays 'Select integration' regardless of whether a value is
        already selected.
        """
        return self.available_tools_dialog.get_by_role(
            "button", name="Select integration"
        )

    @property
    def integration_dropdown_label(self) -> Locator:
        """Visible value label of the toolkit-level integration dropdown.

        The dropdown trigger's accessible name never changes (see
        `integration_dropdown_trigger`), so the selected integration's text is only
        available on this PrimeReact value label span, scoped inside the Available Tools
        dialog to avoid also matching the hidden native <select><option> accessibility
        mirror that carries the same text.
        """
        return self.available_tools_dialog.locator("span.p-dropdown-label")

    # ==============================================
    # METHODS - VERIFICATION & ASSERTIONS
    # ==============================================

    @step
    def should_be_visible(self):
        """Verify that the tool node config panel is visible."""
        expect(self.config_panel).to_be_visible()
        expect(self.panel_heading).to_be_visible()
        return self

    @step
    def code_field_should_be_textarea(self):
        """Assert the Code field is rendered as a <textarea> element, not an <input>."""
        expect(self.code_textarea_element).to_be_visible()
        return self

    @step
    def should_have_code_value(self, expected_value: str):
        """Assert the Code field contains the expected value."""
        expect(self.code_field).to_have_value(expected_value)
        return self

    @step
    def should_have_integration_selected(self, integration_alias: str):
        """Assert the toolkit-level integration dropdown shows the given integration.

        Requires the Available Tools detail modal for the relevant toolkit to already be
        open (e.g. via select_tool(toolkit_name, tool_name) without an integration_alias).

        Scoped to the value label span itself (rather than a bare get_by_text() search across
        the whole dialog, and rather than the dropdown trigger, whose accessible name never
        changes) because the PrimeReact dropdown mirrors its selected value in both a hidden
        native <select><option> (for accessibility) and this visible <span> label — a
        dialog-wide text search matches both and raises a strict-mode violation, while the
        trigger button itself carries no text content.
        """
        expect(self.integration_dropdown_label).to_contain_text(integration_alias)
        return self

    # ==============================================
    # METHODS - ACTIONS & INTERACTIONS
    # ==============================================

    @step
    def open_available_tools_panel(self, toolkit_name: str):
        """Navigate (read-only) to a toolkit's panel in the Available Tools modal.

        Unlike select_tool(), this does not click any tool checkbox — it only opens the
        selector dialogs and the toolkit row, leaving the panel open for assertions (e.g.
        should_have_integration_selected()) without mutating the toolkit's saved settings.

        Flow:
          1. Click the 'Select tool' button → 'Select Tool' popup opens
          2. Click 'Configure Available Tools' → full toolkit detail modal opens
          3. Click the toolkit row (by name) in the left panel
        """
        self.tool_selector_button.click()
        self.tools_dialog.wait_for(state="visible")

        configure_btn = self.tools_dialog.get_by_role(
            "button", name="Configure Available Tools"
        )
        configure_btn.wait_for(state="visible")
        configure_btn.click()

        self.available_tools_dialog.wait_for(state="visible")
        self.available_tools_dialog.get_by_text(toolkit_name, exact=True).first.click()
        return self

    @step
    def select_integration(self, integration_alias: str):
        """Select a toolkit-level integration by alias in the currently open toolkit panel.

        Requires the Available Tools detail modal for the relevant toolkit to already be
        open (e.g. via select_tool(toolkit_name, tool_name) reaching its integration step).

        Flow:
          1. Switch off 'Automatic Credentials Lookup' (if on) to reveal the manual
             integration dropdown.
          2. Click the dropdown trigger → the option list opens (rendered at page level).
          3. Click the option matching the given integration alias.
        """
        if self.automatic_credentials_lookup_switch.is_checked():
            self.automatic_credentials_lookup_label.click()

        self.integration_dropdown_trigger.click()
        # The option list is rendered at the page root (portal), not nested in the dialog.
        self.page.get_by_role("option", name=integration_alias).click()
        return self

    @step
    def select_tool(
        self,
        toolkit_name: str,
        tool_name: str,
        integration_alias: str | None = None,
    ):
        """Open the tool selector and choose a tool by toolkit name.

        Flow (compact / chat-config view):
          1. Click the 'Select tool' button → 'Select Tool' popup opens
          2. Click 'Configure Available Tools' → full toolkit detail modal opens
          3. Click the toolkit row (by name) in the left panel
          4. Click the first tool checkbox in the right panel
          5. If integration_alias is given, select that toolkit-level integration
             (only relevant for toolkits with toolkit-level settings, e.g. Git)
          6. Close the detail modal via its Close button
          7. Click 'Save' in the outer 'Select Tool' popup
        """
        # 1. Open the Select Tool popup
        self.tool_selector_button.click()
        self.tools_dialog.wait_for(state="visible")

        # 2. Open the full toolkit selector (compact view has no direct click-to-select)
        configure_btn = self.tools_dialog.get_by_role(
            "button", name="Configure Available Tools"
        )
        configure_btn.wait_for(state="visible")
        configure_btn.click()

        # 3. Wait for the Available Tools detail modal
        self.available_tools_dialog.wait_for(state="visible")

        # 4. Click the toolkit row in the left panel to navigate to it
        self.available_tools_dialog.get_by_text(toolkit_name, exact=True).first.click()

        # 5. Select the tool via checkbox in the right panel
        self.available_tools_dialog.get_by_role("checkbox", name=tool_name).click()

        # 6. Optionally select the toolkit-level integration while the panel is open
        if integration_alias is not None:
            self.select_integration(integration_alias)

        # 7. Close the detail modal
        self.available_tools_dialog.get_by_role("button", name="Close").click()
        self.available_tools_dialog.wait_for(state="hidden")

        # 8. Confirm selection in the outer popup
        self.tools_dialog.get_by_role("button", name="Save").click()
        self.tools_dialog.wait_for(state="hidden")
        return self

    @step
    def fill_required_tool_arguments(self, value: str = "e2e-test-value"):
        """Fill any empty required argument fields for the currently bound tool.

        Some tools (e.g. the Git toolkit's Create Branch / Set Active Branch) expose a
        required design-time argument (e.g. Branch Name) once bound to the node. Leaving
        it empty silently blocks the workflow Save action with no visible error toast, so
        this must be called before saving whenever such a tool is selected.
        """
        # The region can still be rendering right after a tool is bound; .count() below
        # does not auto-wait like Playwright actions do, so wait for it explicitly first
        # to avoid an intermittent zero-count read that would silently skip filling.
        self.tool_configuration_region.wait_for(state="visible")
        # Inputs are not nested inside their <label> (linked via for/id), so match on the
        # input's own aria-required attribute rather than via the label.
        required_fields = self.tool_configuration_region.locator(
            'input[aria-required="true"], textarea[aria-required="true"]'
        )
        for i in range(required_fields.count()):
            field = required_fields.nth(i)
            if field.input_value() == "":
                field.fill(value)
        return self

    @step
    def fill_code(self, code_text: str):
        """Fill the Code textarea with the provided text."""
        self.code_field.click()
        self.code_field.fill(code_text)
        return self

    @step
    def save(self):
        """Click the Save button in the config panel footer."""
        self.save_button.click()
        return self
