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

"""Workflow Configuration Panel component page object."""

import re

import yaml
from playwright.sync_api import Locator, Page, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.workflows.workflow_version_history_popup import (
    WorkflowVersionHistoryPopup,
)


class WorkflowConfigPanel:
    """Component representing the workflow configuration panel on the right side."""

    def __init__(self, page: Page):
        """
        Initialize workflow config panel component.

        Args:
            page: Playwright page object
        """
        self.page = page

    # ==============================================
    # PROPERTIES - UI ELEMENTS
    # ==============================================

    @property
    def config_panel(self) -> Locator:
        """Right side configuration panel."""
        return self.page.get_by_role("complementary").filter(
            has=self.page.get_by_text("Workflow configuration")
        )

    @property
    def config_panel_close_button(self) -> Locator:
        """Close button for config panel."""
        return self.page.get_by_role("button", name="Collapse panel")

    # ------ Tab Elements ------
    @property
    def yaml_tab(self) -> Locator:
        """YAML tab in config panel."""
        return self.page.get_by_role("tab", name="YAML")

    @property
    def basic_tab(self) -> Locator:
        """Basic tab in config panel."""
        return self.page.get_by_role("tab", name="Basic")

    @property
    def advanced_tab(self) -> Locator:
        """Advanced tab in config panel."""
        return self.page.get_by_role("tab", name="Advanced")

    # ------ Project Selection Elements (in Basic Tab) ------
    @property
    def project_dropdown(self) -> Locator:
        """Project selection dropdown in config panel."""
        return self.page.get_by_role("combobox", name="Project name")

    @property
    def project_label(self) -> Locator:
        """Selected project value display."""
        return self.project_dropdown

    # ------ Shared Switch Elements (in Basic Tab) ------
    @property
    def shared_switch_label(self) -> Locator:
        """Shared with Project Team checkbox/label."""
        return self.page.get_by_text("Shared with Project Team")

    @property
    def shared_switch_checkbox(self) -> Locator:
        """Hidden checkbox input for the shared switch (uses Tailwind 'peer' pattern)."""
        # The checkbox uses class "sr-only peer" (screen-reader-only, accessible but visually hidden)
        return self.page.locator('input[type="checkbox"]#shared')

    # ------ Name Field Elements (in Basic Tab) ------
    @property
    def name_input(self) -> Locator:
        """Name input field."""
        return self.page.get_by_role("textbox", name="Name")

    # ------ Description Field Elements (in Basic Tab) ------
    @property
    def description_textarea(self) -> Locator:
        """Description textarea field."""
        return self.page.get_by_role("textbox", name="Description")

    # ------ Icon URL Field Elements (in Basic Tab) ------
    @property
    def icon_url_input(self) -> Locator:
        """Icon URL input field."""
        return self.page.get_by_role("textbox", name="Icon URL")

    # ------ Categories Field Elements (in Basic Tab) ------
    @property
    def categories_dropdown(self) -> Locator:
        """Categories multiselect (below Icon URL) in config panel."""
        return self.config_panel.locator('div.p-multiselect[aria-label="Categories"]')

    @property
    def categories_listbox(self) -> Locator:
        """Options list of the opened Categories multiselect (rendered in a portal)."""
        return self.page.get_by_role("listbox")

    def category_option(self, name: str) -> Locator:
        """Option for the given category; options also contain a description text."""
        return self.categories_listbox.get_by_role("option").filter(
            has=self.page.get_by_text(name, exact=True)
        )

    @property
    def max_categories_error(self) -> Locator:
        """Error shown when more than 3 categories are selected."""
        return self.page.get_by_role("alert").filter(
            has_text="You can select maximum 3 categories"
        )

    # ------ YAML Configuration Elements (in YAML Tab) ------
    @property
    def yaml_config_header(self) -> Locator:
        """YAML Configuration section header."""
        return self.page.get_by_text("YAML Configuration").first

    @property
    def yaml_documentation_link(self) -> Locator:
        """Documentation link in YAML tab."""
        return self.page.get_by_role("link", name="Documentation")

    @property
    def yaml_editor_text_layer(self):
        """YAML Configuration text layer - contains all text content"""
        return self.page.locator(".ace_text-layer")

    @property
    def yaml_editor_text_input(self):
        """YAML Configuration text input"""
        return self.page.locator(".ace_text-input")

    # ------ Version History Header Button (new popup-based UI) ------
    @property
    def version_history_button(self) -> Locator:
        """'Version History' button in the YAML editor header actions.

        Clicking this button opens WorkflowVersionHistoryPopup.
        aria-label = 'Version History'  (WorkflowYamlHeaderActions.tsx:55).
        Use exact=True to avoid matching 'Version History (visual editor)'.
        """
        return self.page.get_by_role("button", name="Version History", exact=True)

    @property
    def version_history_yaml_button(self) -> Locator:
        """'Version History (YAML)' button in the YamlPanel header.

        Present when the visual editor's YAML panel is open.  Opens the
        *text* diff WorkflowVersionHistoryPopup (Previous Version /
        Current Version comparison buttons).
        aria-label = 'Version History (YAML)' (YamlPanel.tsx:166).

        NOTE: this button used to carry the aria-label
        'Version History (visual editor)'; that label now belongs to the
        editor-toolbar button which opens the *graph* diff popup instead.
        """
        return self.page.get_by_role(
            "button", name="Version History (YAML)", exact=True
        )

    @property
    def version_history_visual_editor_button(self) -> Locator:
        """'Version History (visual editor)' button in the editor toolbar.

        Opens WorkflowVisualVersionHistoryPopup — the ReactFlow graph diff
        (Added / Modified / Removed legend), which has no
        Previous Version / Current Version comparison buttons
        (EditorActions.tsx:134).
        """
        return self.page.get_by_role(
            "button", name="Version History (visual editor)", exact=True
        )

    # ------ YAML Editor Tabs ------
    @property
    def edit_current_version_tab(self) -> Locator:
        """Edit mode tab in YAML editor (previously named 'Edit Current Version')."""
        return self.page.get_by_role("tab", name="Edit mode")

    # ------ Footer Buttons (in Config Panel) ------
    @property
    def save_button(self) -> Locator:
        """Save button at the bottom of config panel."""
        return self.config_panel.get_by_role("button", name="Save")

    @property
    def cancel_button(self) -> Locator:
        """Cancel button at the bottom of config panel."""
        return self.config_panel.get_by_role("button", name="Cancel")

    # ==============================================
    # METHODS - ACTIONS & INTERACTIONS
    # ==============================================

    @step
    def is_visible(self) -> bool:
        """Check if the configuration panel is currently visible."""
        return self.config_panel.is_visible()

    @step
    def close(self):
        """Close the workflow config panel if open."""
        if self.is_visible():
            self.config_panel_close_button.click()
            expect(self.config_panel).not_to_be_visible()

    @step
    def switch_to_yaml_tab(self):
        """Switch to YAML tab in config panel."""
        self.yaml_tab.focus()
        self.yaml_tab.press("Enter")

    @step
    def switch_to_basic_tab(self):
        """Switch to Basic tab in config panel."""
        self.basic_tab.focus()
        self.basic_tab.press("Enter")

    @step
    def switch_to_advanced_tab(self):
        """Switch to Advanced tab in config panel."""
        self.advanced_tab.focus()
        self.advanced_tab.press("Enter")

    @step
    def open_yaml_panel(self, yaml_button: Locator):
        """
        Open YAML config panel.

        Args:
            yaml_button: YAML button locator from parent page
        """
        yaml_button.click()
        self.wait_for_opened()

    @step
    def save_yaml_config(self):
        """Click Save button in YAML editor panel to save the configuration."""
        yaml_panel_save_button = self.page.get_by_role("tabpanel").get_by_role(
            "button", name="Save"
        )
        yaml_panel_save_button.click(force=True)
        self.wait_for_closed()

    @step
    def wait_for_closed(self):
        """Wait for the config panel to close."""
        self.config_panel.wait_for(state="hidden", timeout=5000)

    @step
    def wait_for_opened(self):
        """Wait for the config panel to open."""
        self.config_panel.wait_for(state="visible", timeout=5000)
        self.page.wait_for_selector(".ace_text-layer", state="visible", timeout=5000)

    # ------ Project Selection Actions ------
    @step
    def select_project(self, project_name: str):
        """Select a project from the dropdown."""
        # Focus and open the dropdown with keyboard (to bypass overlapping elements)
        self.project_dropdown.focus()
        self.project_dropdown.press("Enter")
        self.page.get_by_role("listbox").wait_for(state="visible")
        self.page.keyboard.type(project_name)
        self.page.get_by_role("option").filter(has_text=project_name).first.wait_for(
            state="visible"
        )
        self.page.get_by_role("option").filter(has_text=project_name).first.click()

    # ------ Shared Switch Actions ------
    @step
    def toggle_shared_switch(self):
        """Toggle the 'Shared with Project Team' switch."""
        self.shared_switch_label.click()

    # ------ Form Field Actions ------
    @step
    def fill_name(self, name: str):
        """Fill the workflow name field."""
        self.name_input.fill(name)

    @step
    def clear_name(self):
        """Clear the workflow name field."""
        self.name_input.clear()

    @step
    def get_name_value(self) -> str:
        """Get the current value of the workflow name field."""
        return self.name_input.input_value()

    @step
    def fill_description(self, description: str):
        """Fill the workflow description field."""
        self.description_textarea.fill(description)

    @step
    def fill_icon_url(self, icon_url: str):
        """Fill the icon URL field."""
        self.icon_url_input.fill(icon_url)

    # ------ Categories Actions ------
    @step
    def select_categories(self, names: list[str]):
        """Open the Categories multiselect, click each named option and close it."""
        self.categories_dropdown.click()
        self.categories_listbox.wait_for(state="visible")
        for name in names:
            self.category_option(name).click()
        self.page.keyboard.press("Escape")
        self.categories_listbox.wait_for(state="hidden")

    # ------ YAML Configuration Actions ------
    @step
    def fill_yaml_config(self, yaml_content: str):
        """
        Fill YAML configuration in the ACE editor.

        Uses the ACE editor JavaScript API (``editor.setValue()``) to set
        content reliably.  The ACE editor stores its content internally and
        does not reflect it in the hidden textarea's ``.value`` property, so
        Playwright's ``.fill()`` on the textarea does not propagate changes to
        the editor model.  Using the JS API is the only reliable approach.
        """
        # Wait for the editor to be visible before setting content
        expect(self.yaml_editor_text_layer).to_be_visible()

        # Use the ACE editor JavaScript API to set content
        self.page.evaluate(
            """(content) => {
                const aceEditors = document.querySelectorAll('.ace_editor');
                for (const editor of aceEditors) {
                    if (editor.env && editor.env.editor && !editor.env.editor.getReadOnly()) {
                        editor.env.editor.setValue(content, -1);
                        return;
                    }
                }
            }""",
            yaml_content,
        )
        self.page.wait_for_function(
            """(content) => {
                const aceEditors = document.querySelectorAll('.ace_editor');
                for (const editor of aceEditors) {
                    if (editor.env && editor.env.editor && !editor.env.editor.getReadOnly()) {
                        return editor.env.editor.getValue() === content;
                    }
                }
                return false;
            }""",
            arg=yaml_content,
        )

    @step
    def get_yaml_content(self) -> str:
        """
        Get the YAML content from the editor.

        Uses the ACE editor JavaScript API (``editor.getValue()``) to retrieve
        the full and correctly-formatted YAML content.  This is more reliable than
        reading ``inner_text()`` from the DOM text layer, which can drop indentation
        or truncate nested structures when the editor content is not fully scrolled
        into view.

        Returns:
            str: The cleaned YAML content (with meta_states section removed)
        """
        # Wait for YAML editor to be visible
        expect(self.yaml_editor_text_layer).to_be_visible()

        # Use the ACE editor JavaScript API to get the full, properly-formatted content.
        # The ACE editor stores its content in a session object accessible via the
        # DOM element's ``env.editor`` property.  This avoids the indentation/truncation
        # issues that arise when reading the rendered text layer with inner_text().
        yaml_content = self.page.evaluate("""() => {
            const aceEditors = document.querySelectorAll('.ace_editor');
            for (const editor of aceEditors) {
                if (editor.env && editor.env.editor && !editor.env.editor.getReadOnly()) {
                    return editor.env.editor.getValue();
                }
            }
            // Fallback: return content of the first ace editor found
            if (aceEditors.length > 0) {
                const first = aceEditors[0];
                if (first.env && first.env.editor) {
                    return first.env.editor.getValue();
                }
            }
            return '';
        }""")

        # Remove meta_states section from actual content (added by visual editor)
        yaml_content_cleaned = re.sub(
            r"(\n|^)meta_states:.*", "", yaml_content, flags=re.DOTALL
        )

        # The visual editor also computes graph reachability from the entry state
        # and buckets any state with no incoming transition into a separate
        # top-level orphaned_states list (so it can gray them out / warn about
        # them on the canvas), instead of leaving them inline in states.  This is
        # a real, valid state — not dropped content — so merge it back into
        # states rather than discarding it, to compare equal against the raw
        # template yaml_config (which has no such bucketing). Unlike meta_states,
        # orphaned_states is not guaranteed to be the last top-level key, so a
        # simple regex would swallow unrelated keys after it — parse instead.
        try:
            parsed = yaml.safe_load(yaml_content_cleaned)
        except yaml.YAMLError:
            parsed = None
        if isinstance(parsed, dict) and "orphaned_states" in parsed:
            orphaned = parsed.pop("orphaned_states") or []
            parsed.setdefault("states", []).extend(orphaned)
            yaml_content_cleaned = yaml.dump(
                parsed, sort_keys=False, default_flow_style=False
            )

        return yaml_content_cleaned.strip()

    # ------ YAML Editor Tab Actions ------
    @step
    def click_edit_current_version_tab(self):
        """Click the Edit Current Version tab in YAML editor."""
        self.edit_current_version_tab.click()

    @step
    def open_version_history_popup(self) -> WorkflowVersionHistoryPopup:
        """Click the 'Version History' button and return the popup component.

        Clicks the header-actions 'Version History' button in the YAML editor,
        waits for the popup to be visible, and returns a
        :class:`WorkflowVersionHistoryPopup` instance for further interaction.

        Returns:
            WorkflowVersionHistoryPopup: The popup component instance.
        """
        # Two buttons open the *text* diff popup: 'Version History' (standalone YAML
        # editor, default aria-label) and 'Version History (YAML)' (visual editor's
        # YAML panel).  Click whichever is visible in the current context.
        # Deliberately NOT 'Version History (visual editor)' since
        # that toolbar button opens the graph diff popup, which has no
        # Previous/Current Version comparison buttons.
        btn = self.version_history_button.or_(self.version_history_yaml_button)
        btn.first.click()
        popup = WorkflowVersionHistoryPopup(self.page)
        popup.wait_for_visible()
        return popup

    # ------ Footer Button Actions ------
    @step
    def click_save(self):
        """Click the Save button in config panel."""
        self.save_button.click()

    @step
    def click_cancel(self):
        """Click the Cancel button in config panel."""
        self.cancel_button.click()

    # ==============================================
    # METHODS - VERIFICATION & ASSERTIONS
    # ==============================================

    # ------ Project Selection Verifications ------
    @step
    def should_see_project_selected(self, project_name: str):
        """Verify the currently selected project name."""
        expect(self.project_dropdown).to_have_value(project_name)

    @step
    def should_have_project_dropdown_visible(self):
        """Verify that the project dropdown is visible."""
        expect(self.project_dropdown).to_be_visible()

    @step
    def should_have_project_selected(self, project_name: str):
        """Verify that the specified project is selected."""
        expect(self.project_label).to_have_text(project_name)

    # ------ Shared Switch Verifications ------
    @step
    def should_have_shared_switch_checked(self):
        """Verify that the shared switch is checked."""
        # Check the hidden checkbox's checked state
        expect(self.shared_switch_checkbox).to_be_checked()

    @step
    def should_have_shared_switch_unchecked(self):
        """Verify that the shared switch is unchecked."""
        # Check the hidden checkbox's checked state
        expect(self.shared_switch_checkbox).not_to_be_checked()

    # ------ Form Field Verifications ------
    @step
    def should_have_name_field_value(self, expected_value: str):
        """Verify that the name field has the expected value."""
        expect(self.name_input).to_have_value(expected_value)

    @step
    def should_have_empty_name_field(self):
        """Verify that the name field is empty."""
        expect(self.name_input).to_have_value("")

    @step
    def should_have_description_field_value(self, expected_value: str):
        """Verify that the description field has the expected value."""
        expect(self.description_textarea).to_have_value(expected_value)

    @step
    def should_have_empty_description_field(self):
        """Verify that the description field is empty."""
        expect(self.description_textarea).to_have_value("")

    @step
    def should_have_icon_url_field_value(self, expected_value: str):
        """Verify that the icon URL field has the expected value."""
        expect(self.icon_url_input).to_have_value(expected_value)

    @step
    def should_have_empty_icon_url_field(self):
        """Verify that the icon URL field is empty."""
        expect(self.icon_url_input).to_have_value("")

    @step
    def should_have_name_is_required_message(self):
        """Verify that 'Name is required' validation message is displayed."""
        validation_message = self.page.get_by_text("Name is required")
        expect(validation_message).to_be_visible()

    @step
    def should_have_valid_icon_url_is_required_message(self):
        """Verify that 'Icon URL must be a valid URL' validation message is displayed."""
        validation_message = self.page.get_by_text("Icon URL must be a valid URL")
        expect(validation_message).to_be_visible()

    # ------ Categories Verifications ------
    @step
    def should_have_categories_below_icon_url(self):
        """Verify that the Categories field is displayed below the Icon URL field."""
        expect(self.icon_url_input).to_be_visible()
        expect(self.categories_dropdown).to_be_visible()
        self.page.wait_for_function(
            "([categories, icon]) => categories.getBoundingClientRect().top"
            " > icon.getBoundingClientRect().bottom - 1",
            arg=[
                self.categories_dropdown.element_handle(),
                self.icon_url_input.element_handle(),
            ],
        )

    @step
    def should_have_categories_selected(self, names: list[str]):
        """Verify that exactly the given categories are selected in the multiselect."""
        self.categories_dropdown.click()
        expect(self.categories_listbox).to_be_visible()
        expect(
            self.categories_listbox.get_by_role("option", selected=True)
        ).to_have_count(len(names))
        for name in names:
            expect(self.category_option(name)).to_have_attribute(
                "aria-selected", "true"
            )
        self.page.keyboard.press("Escape")
        expect(self.categories_listbox).to_be_hidden()

    @step
    def should_see_max_categories_error(self):
        """Verify that the 'You can select maximum 3 categories' error is displayed."""
        expect(self.max_categories_error).to_be_visible()

    # ------ YAML Configuration Verifications ------
    @step
    def should_have_yaml_editor_visible(self):
        """Verify that the YAML editor is visible."""
        expect(self.yaml_config_header).to_be_visible()
        expect(self.yaml_editor_text_layer).to_be_visible()

    @step
    def should_have_yaml_editor_with_content(self, expected_config):
        """Verify that the YAML editor has content."""
        yaml_content_cleaned = self.get_yaml_content()

        # Normalize whitespace for comparison
        expected_lines = [
            line.strip() for line in expected_config.strip().split("\n") if line.strip()
        ]
        actual_lines = [
            line.strip()
            for line in yaml_content_cleaned.strip().split("\n")
            if line.strip()
        ]

        assert expected_lines == actual_lines, (
            f"YAML content mismatch.\nExpected:\n{expected_config}\n\nActual:\n{yaml_content_cleaned}"
        )

    # ------ Config Panel Verifications ------
    @step
    def should_be_visible(self):
        """Verify that config panel is visible."""
        expect(self.config_panel).to_be_visible()

    @step
    def should_be_hidden(self):
        """Verify that config panel is hidden."""
        expect(self.config_panel).not_to_be_visible()

    # ------ Footer Button Verifications ------
    @step
    def should_have_save_button_visible(self):
        """Verify that Save button is visible."""
        expect(self.save_button).to_be_visible()

    @step
    def should_have_save_button_enabled(self):
        """Verify that Save button is enabled."""
        expect(self.save_button).to_be_enabled()

    @step
    def should_have_save_button_disabled(self):
        """Verify that Save button is disabled."""
        expect(self.save_button).to_be_disabled()

    @step
    def should_have_cancel_button_visible(self):
        """Verify that Cancel button is visible."""
        expect(self.cancel_button).to_be_visible()

    # ------ YAML Editor Tab Verifications ------
    @step
    def should_have_yaml_tabs_visible(self):
        """Verify that YAML editor header controls are visible.

        The old tab-based UI (Edit mode / Version History tabs) was replaced by a
        popup.  This method now checks for the Version History
        button (either 'Version History' in the standalone YAML editor or
        'Version History (YAML)' in the visual editor's YAML panel).
        """
        expect(
            self.version_history_button.or_(self.version_history_yaml_button).first
        ).to_be_visible()
        return self

    @step
    def should_have_current_version_tab_active(self):
        """Verify that Edit Current Version tab is active."""
        # Active tabs have bold font and primary border color
        # They also have cursor-default instead of cursor-pointer
        expect(self.edit_current_version_tab).to_have_css("font-weight", "600")
        expect(self.edit_current_version_tab).to_have_css("cursor", "default")
        return self
