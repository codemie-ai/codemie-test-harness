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
State Settings block (State ID, Task, four switches) and a "Contracts" block (Input
contract, Output contract, Save validation). Which of their fields are rendered depends
on the node type; this class asserts that.

Contracts evidence (frontend): ContractFields.tsx (labels, placeholders, select id
``node_validation_mode_select``), CommonStateFields.tsx (the "Contracts" accordion,
expanded by default), Textarea.tsx / FieldAnnouncer.tsx (amber warning and red error
styling of a field).
"""

import re
from typing import Optional

from playwright.sync_api import Locator, Page, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage

CUSTOM_NODE_TYPE_PLACEHOLDER = "Select a custom node type"
REQUIRED_FIELD_ERROR = "Field is required"
NODE_SAVE_VALIDATION_SELECT_ID = "node_validation_mode_select"
FIELD_WARNING_BORDER_CLASS = "border-aborted-secondary"
FIELD_ERROR_BORDER_CLASS = "border-border-error"
FIELD_WARNING_TEXT_CLASS = "text-aborted-primary"


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
    def input_contract_textarea(self) -> Locator:
        """Input contract textarea of the Contracts block."""
        return self.config_panel.get_by_placeholder(
            "Expected input format (JSON Schema)", exact=True
        )

    @property
    def save_validation_select(self) -> Locator:
        """Node-level 'Save validation' select of the Contracts block."""
        return self.config_panel.locator(f"#{NODE_SAVE_VALIDATION_SELECT_ID}")

    @property
    def contracts_heading(self) -> Locator:
        """Heading of the 'Contracts' accordion."""
        return self.config_panel.get_by_role("heading", name="Contracts", exact=True)

    @property
    def field_warnings(self) -> Locator:
        """Amber inline warning messages under the panel fields."""
        return self.config_panel.locator(f".{FIELD_WARNING_TEXT_CLASS}")

    @property
    def field_errors(self) -> Locator:
        """Inline error messages under the panel fields."""
        return self.config_panel.get_by_role("alert")

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
    def fill_input_contract(self, schema: str):
        """Replace the Input contract text."""
        self.input_contract_textarea.fill(schema)
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
    def should_have_output_schema_value(self, value: str):
        """Verify the Output contract textarea is shown with ``value``."""
        expect(self.output_schema_textarea).to_have_value(value)
        return self

    @step
    def should_have_input_contract_visibility(self, visible: bool):
        """Verify the Input contract textarea is shown (visible=True) or absent (visible=False)."""
        self._expect_presence(self.input_contract_textarea, visible)
        return self

    @step
    def should_have_save_validation_visibility(self, visible: bool):
        """Verify the node 'Save validation' select is shown (visible=True) or absent."""
        self._expect_presence(self.save_validation_select, visible)
        if visible:
            expect(
                self.config_panel.get_by_text("Save validation", exact=True)
            ).to_be_visible()
        return self

    @step
    def should_have_contracts_accordion_expanded(self):
        """Verify the 'Contracts' accordion is shown and expanded (its Input contract is visible)."""
        expect(self.contracts_heading).to_be_visible()
        expect(self.input_contract_textarea).to_be_visible()
        return self

    @step
    def should_have_no_contract_controls(self):
        """Verify the panel has no Contracts accordion, Input contract, Output contract or
        Save validation."""
        expect(self.contracts_heading).to_have_count(0)
        expect(self.input_contract_textarea).to_have_count(0)
        expect(self.output_schema_textarea).to_have_count(0)
        expect(self.save_validation_select).to_have_count(0)
        return self

    @step
    def should_show_panel_text(self, text: str):
        """Verify the panel shows ``text``; proves the panel of the expected node type rendered."""
        expect(self.config_panel).to_contain_text(text)
        return self

    @step
    def should_have_task_warning(self, message: str):
        """Verify the Task field has the amber warning border and the amber inline ``message``."""
        expect(self.task_textarea).to_be_visible()
        expect(self.task_textarea).to_have_class(
            re.compile(re.escape(FIELD_WARNING_BORDER_CLASS))
        )
        expect(self.field_warnings.filter(has_text=message).first).to_be_visible()
        return self

    @step
    def should_have_input_contract_error(self, message: str):
        """Verify the Input contract field has the red error border and the inline ``message``."""
        expect(self.input_contract_textarea).to_be_visible()
        expect(self.input_contract_textarea).to_have_class(
            re.compile(re.escape(FIELD_ERROR_BORDER_CLASS))
        )
        expect(self.field_errors.filter(has_text=message).first).to_be_visible()
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
