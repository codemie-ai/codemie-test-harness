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

"""Page object for the State Settings of any node configuration panel.

The Tool, Sub-workflow, Custom, Assistant and Transform panels share the same
State Settings block (State ID, Task, Output Schema, four switches). Which of its
fields are rendered depends on the node type; this class asserts that.
"""

from typing import Optional

from playwright.sync_api import Locator, Page, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

CUSTOM_NODE_TYPE_PLACEHOLDER = "Select a custom node type"
REQUIRED_FIELD_ERROR = "Field is required"


class NodeStateSettingsPanel(BasePage):
    """Node configuration side panel, focused on its State Settings fields."""

    def __init__(self, page: Page):
        super().__init__(page)

    # ==============================================
    # PROPERTIES - UI ELEMENTS
    # ==============================================

    @property
    def config_panel(self) -> Locator:
        """The node configuration side panel."""
        return self.page.get_by_role("complementary").filter(
            has=self.page.get_by_role("heading", name="Node configuration")
        )

    @property
    def state_id_input(self) -> Locator:
        """State ID input of State Settings."""
        return self.config_panel.get_by_placeholder("e.g., analyze_code", exact=True)

    @property
    def task_textarea(self) -> Locator:
        """Task textarea of State Settings."""
        return self.config_panel.get_by_placeholder(
            "Describe the task for this node", exact=True
        )

    @property
    def output_schema_textarea(self) -> Locator:
        """Output Schema textarea of State Settings."""
        return self.config_panel.get_by_placeholder(
            "Expected output format (JSON Schema)", exact=True
        )

    @property
    def other_state_settings_switches(self) -> list[Locator]:
        """The four State Settings switches that follow Task and Output Schema:
        Interrupt Before, Finish Iteration, Resolve Dynamic Values in Prompt,
        Result as Human Message."""
        return [
            self.config_panel.get_by_role("switch", name=name)
            for name in (
                "Interrupt Before",
                "Finish Iteration",
                "Resolve Dynamic Values in Prompt",
                "Result as Human Message",
            )
        ]

    @property
    def custom_node_type_selector(self) -> Locator:
        """'Custom node type' selector of the Custom panel."""
        return self.config_panel.locator("#custom-node-selector")

    @property
    def output_template_textarea(self) -> Locator:
        """Output Template textarea, the required config field of the state-processor custom node."""
        return self.config_panel.get_by_placeholder("Enter Output Template", exact=True)

    @property
    def required_field_errors(self) -> Locator:
        """'Field is required' messages shown under required custom node config fields."""
        return self.config_panel.get_by_text(REQUIRED_FIELD_ERROR, exact=True)

    @property
    def save_button(self) -> Locator:
        """Save button in the footer of the node configuration panel."""
        return self.config_panel.get_by_role("button", name="Save")

    def node_section_header(self, title: str) -> Locator:
        """Accordion header of the node-specific configuration section (e.g. 'Tool Configuration')."""
        return self.config_panel.get_by_role("button", name=title).first

    def custom_node_type_option(self, label: str) -> Locator:
        """Option of the opened 'Custom node type' list; the list renders at page level."""
        return self.page.get_by_role("option", name=label, exact=True)

    # ==============================================
    # METHODS - ACTIONS
    # ==============================================

    @step
    def select_custom_node_type(self, label: str):
        """Choose a custom node type in the selector without saving the node."""
        self.custom_node_type_selector.click()
        self.custom_node_type_option(label).click()
        return self

    @step
    def fill_state_id(self, state_id: str):
        """Replace the State ID."""
        self.state_id_input.fill(state_id)
        return self

    @step
    def click_save(self):
        """Click Save in the node configuration panel footer."""
        self.save_button.click()
        return self

    # ==============================================
    # METHODS - VERIFICATION & ASSERTIONS
    # ==============================================

    @staticmethod
    def _expect_presence(locator: Locator, present: bool):
        """Assert the element is visible (present=True) or not rendered at all (present=False)."""
        if present:
            expect(locator.first).to_be_visible()
        else:
            expect(locator).to_have_count(0)

    @step
    def should_be_visible(self):
        """Verify the panel is open and its State Settings rendered (State ID visible).

        Call this before any 'absent' assertion so a panel that has not rendered yet
        cannot make a missing-field check pass.
        """
        expect(self.config_panel).to_be_visible()
        expect(self.state_id_input).to_be_visible()
        return self

    @step
    def should_show_node_section(self, title: str):
        """Verify the node-specific configuration section is present (right node-type panel)."""
        expect(self.node_section_header(title)).to_be_visible()
        return self

    @step
    def should_have_task_visibility(self, visible: bool):
        """Verify the Task textarea is shown (visible=True) or absent (visible=False)."""
        self._expect_presence(self.task_textarea, visible)
        return self

    @step
    def should_have_output_schema_visibility(self, visible: bool):
        """Verify the Output Schema textarea is shown (visible=True) or absent (visible=False)."""
        self._expect_presence(self.output_schema_textarea, visible)
        return self

    @step
    def should_have_other_state_settings_visibility(self, visible: bool):
        """Verify the four State Settings switches after Output Schema are all present or all absent."""
        # Switch inputs are visually hidden (sr-only), so count them in the DOM instead.
        for switch in self.other_state_settings_switches:
            expect(switch).to_have_count(1 if visible else 0)
        return self

    @step
    def should_have_selected_custom_node_type(self, label: Optional[str]):
        """Verify the type selector shows the given type, or its placeholder when label is None."""
        expect(self.custom_node_type_selector).to_contain_text(
            label if label else CUSTOM_NODE_TYPE_PLACEHOLDER
        )
        return self

    @step
    def should_show_required_config_field(self):
        """Verify the state-processor config form (with its required Output Template) rendered."""
        expect(self.output_template_textarea).to_be_visible()
        return self

    @step
    def should_show_required_field_error(self):
        """Verify the 'Field is required' message appears under the missing required config field."""
        expect(self.required_field_errors).to_have_count(1)
        return self

    @step
    def should_remain_open(self):
        """Verify the node configuration panel is still open (the save did not close it)."""
        expect(self.config_panel).to_be_visible()
        return self
