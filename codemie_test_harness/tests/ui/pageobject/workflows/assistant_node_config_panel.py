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

from playwright.sync_api import Page, Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class AssistantNodeConfigPanel(BasePage):
    """Page object for Assistant Node Configuration Panel."""

    def __init__(self, page: Page):
        super().__init__(page)

    # ==============================================
    # PROPERTIES - UI ELEMENTS
    # ==============================================

    @property
    def config_panel(self) -> Locator:
        """The assistant node configuration panel."""
        return self.page.get_by_role("complementary").filter(
            has=self.page.get_by_role("heading", name="Node configuration")
        )

    @property
    def panel_heading(self) -> Locator:
        """Node configuration heading."""
        return self.page.get_by_role("heading", name="Node configuration", level=3)

    @property
    def collapse_panel_button(self) -> Locator:
        """Collapse panel button."""
        return self.config_panel.get_by_role("button", name="Collapse panel")

    # Assistant Configuration Section
    @property
    def assistant_config_section(self) -> Locator:
        """Assistant Configuration section heading."""
        return self.page.get_by_role("heading", name="Assistant Configuration", level=3)

    @property
    def system_instructions_textbox(self) -> Locator:
        """System instructions textbox."""
        return self.page.get_by_role(
            "textbox", name="Enter system instructions for the assistant"
        )

    @property
    def llm_model_dropdown(self) -> Locator:
        """LLM model dropdown."""
        return self.page.get_by_role("combobox", name="LLM model:")

    @property
    def temperature_textbox(self) -> Locator:
        """Temperature textbox."""
        return self.page.get_by_role("textbox", name="Temperature:")

    @property
    def skills_label(self) -> Locator:
        """Selected-skills label of the Skills multiselect in the virtual assistant form."""
        return self.config_panel.locator(
            'div.p-multiselect[aria-label="Select skills"] .p-multiselect-label'
        )

    # State Settings Section
    @property
    def state_settings_section(self) -> Locator:
        """State Settings section heading."""
        return self.page.get_by_role("heading", name="State Settings", level=3)

    @property
    def state_id_textbox(self) -> Locator:
        """State ID textbox."""
        return self.page.get_by_role("textbox", name="State ID")

    @property
    def state_id_required_marker(self) -> Locator:
        """State ID required asterisk marker (aria-hidden)."""
        return self.page.locator(
            '//label[contains(text(), "State ID")]/span[@aria-hidden="true" and text()="*"]'
        )

    @property
    def task_textbox(self) -> Locator:
        """Task textbox."""
        return self.page.get_by_role("textbox", name="Describe the task for this node")

    @property
    def output_schema_textbox(self) -> Locator:
        """Output Schema textbox."""
        return self.page.get_by_role(
            "textbox", name="Expected output format (JSON Schema)"
        )

    # Transition Settings Section
    @property
    def transition_settings_accordion(self) -> Locator:
        """Transition Settings accordion button (collapsed or expanded)."""
        return self.config_panel.get_by_role("button", name="Transition Settings")

    @property
    def reset_context_keys_input(self) -> Locator:
        """Reset Context Keys input field (placeholder confirmed via playwright-cli inspection)."""
        return self.config_panel.get_by_placeholder("e.g.: user_data,analysis_result")

    # Footer Buttons
    @property
    def delete_button(self) -> Locator:
        """Delete button."""
        return self.config_panel.get_by_role("button", name="Delete")

    @property
    def duplicate_button(self) -> Locator:
        """Duplicate button."""
        return self.config_panel.get_by_role("button", name="Duplicate")

    @property
    def cancel_button(self) -> Locator:
        """Cancel button."""
        return self.config_panel.get_by_role("button", name="Cancel").last

    @property
    def save_button(self) -> Locator:
        """Save button in config panel."""
        return self.config_panel.get_by_role("button", name="Save")

    # ==============================================
    # METHODS - VERIFICATION & ASSERTIONS
    # ==============================================

    @step
    def should_be_visible(self):
        """Verify that the config panel is visible."""
        expect(self.config_panel).to_be_visible()
        expect(self.panel_heading).to_be_visible()
        return self

    @step
    def should_have_assistant_config_section_visible(self):
        """Verify Assistant Configuration section is visible."""
        expect(self.assistant_config_section).to_be_visible()
        return self

    @step
    def should_show_selected_skill(self, *accepted_labels: str):
        """Verify the Skills field renders the selected skill as one of the accepted
        labels (e.g. name or id) and never as the literal text "null"."""
        pattern = re.compile("|".join(re.escape(label) for label in accepted_labels))
        expect(self.skills_label).to_be_visible()
        expect(self.skills_label).to_have_text(pattern)
        expect(self.skills_label).not_to_contain_text("null")
        return self

    @step
    def should_have_state_settings_section_visible(self):
        """Verify State Settings section is visible."""
        expect(self.state_settings_section).to_be_visible()
        expect(self.state_id_textbox).to_be_visible()
        expect(self.state_id_required_marker).to_be_visible()
        return self

    @step
    def should_have_footer_buttons_visible(self):
        """Verify footer buttons are visible."""
        expect(self.delete_button).to_be_visible()
        expect(self.duplicate_button).to_be_visible()
        expect(self.cancel_button).to_be_visible()
        expect(self.save_button).to_be_visible()
        return self

    # ==============================================
    # METHODS - ACTIONS & INTERACTIONS
    # ==============================================

    @step
    def close_panel(self):
        """Close the configuration panel."""
        self.collapse_panel_button.click()
        self.config_panel.wait_for(state="hidden", timeout=5000)
        return self

    @step
    def fill_task(self, task: str):
        """Fill the Task field (State Settings section)."""
        self.task_textbox.fill(task)
        return self

    @step
    def click_save(self):
        """Click the Save button in the node config panel."""
        self.save_button.click()
        return self

    @step
    def should_have_task_value(self, expected_value: str):
        """Verify the Task field has the expected value."""
        expect(self.task_textbox).to_have_value(expected_value)
        return self

    @step
    def should_not_be_visible(self):
        """Verify the config panel is no longer visible."""
        expect(self.config_panel).not_to_be_visible()
        return self

    # ==============================================
    # METHODS — TRANSITION SETTINGS
    # ==============================================

    @step
    def expand_transition_settings(self):
        """Expand the Transition Settings accordion if not already expanded."""
        btn = self.transition_settings_accordion
        if btn.get_attribute("aria-expanded") != "true":
            btn.click()
            expect(btn).to_have_attribute("aria-expanded", "true")
        return self

    @step
    def fill_reset_context_keys(self, value: str):
        """Fill the Reset Context Keys input without triggering blur/parse."""
        self.reset_context_keys_input.fill(value)
        return self

    @step
    def blur_reset_context_keys(self):
        """Press Tab to move focus away from Reset Context Keys input, triggering onBlur parse."""
        self.reset_context_keys_input.press("Tab")
        return self

    @step
    def should_have_reset_context_keys_value(self, expected: str):
        """Verify the Reset Context Keys input has the expected raw string value."""
        expect(self.reset_context_keys_input).to_have_value(expected)
        return self
