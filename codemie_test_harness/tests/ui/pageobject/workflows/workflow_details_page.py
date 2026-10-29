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

from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.workflows.assistant_node_panel_page import (
    AssistantNodePanelPage,
)


class WorkflowDetailsPage(BasePage):
    """Page object for the Workflow Details page."""

    page_url = "/workflows"

    # ==================== PROPERTIES ====================

    @property
    def workflow_name(self) -> Locator:
        """Workflow name h1 heading in the page header."""
        return self.page.locator("h1")

    @property
    def edit_button(self) -> Locator:
        """Edit workflow button."""
        return self.page.get_by_role("button", name="Edit")

    @property
    def configuration_button(self) -> Locator:
        """Configuration button that opens the configuration sidebar."""
        return self.page.get_by_role("button", name="Configuration")

    @property
    def run_workflow_button(self) -> Locator:
        """Run workflow button (first occurrence in header area)."""
        return self.page.get_by_role("button", name="Run workflow").first

    @property
    def run_chat_button(self) -> Locator:
        """Run Chat button (first occurrence in header area)."""
        return self.page.get_by_role("button", name="Run Chat").first

    @property
    def no_executions_text(self) -> Locator:
        """'No Executions Yet' text in the execution history sidebar."""
        return self.page.get_by_text("No Executions Yet")

    @property
    def new_execution_dialog(self) -> Locator:
        """New Workflow Execution dialog."""
        return self.page.get_by_role("dialog", name="New Workflow Execution")

    @property
    def new_execution_dialog_close_button(self) -> Locator:
        """Close button in the New Workflow Execution dialog."""
        return self.new_execution_dialog.get_by_role("button", name="Close")

    # Configuration Sidebar Properties
    @property
    def configuration_sidebar(self) -> Locator:
        """Configuration right sidebar (visible only when open)."""
        return self.page.locator("aside").filter(has_text="Configure Workflow")

    @property
    def workflow_name_in_sidebar(self) -> Locator:
        """Workflow name h4 in configuration sidebar."""
        return self.configuration_sidebar.locator("h4")

    @property
    def workflow_id_in_sidebar(self) -> Locator:
        """Workflow ID paragraph in configuration sidebar."""
        return self.configuration_sidebar.locator("p").filter(has_text="ID:")

    @property
    def workflow_id_copy_button(self) -> Locator:
        """Copy button for workflow ID in configuration sidebar."""
        return self.workflow_id_in_sidebar.locator("..").get_by_role("button")

    @property
    def configure_button_in_sidebar(self) -> Locator:
        """Configure button inside the sidebar (opens Edit Workflow form)."""
        return self.configuration_sidebar.get_by_role("button", name="Configure")

    @property
    def description_field(self) -> Locator:
        """Description text element (data-testid='workflow-description') inside the configuration sidebar."""
        return self.configuration_sidebar.get_by_test_id("workflow-description")

    @property
    def description_toggle(self) -> Locator:
        """Show more / Show less toggle button for long descriptions."""
        return self.configuration_sidebar.get_by_test_id("description-toggle")

    # ==================== NAVIGATION METHODS ====================

    @step
    def navigate_to(self, workflow_id: str):
        """Navigate to the Workflow Details page with workflow ID."""
        self.page.goto(f"{self.page_url}/{workflow_id}")

    # ==================== INTERACTION METHODS ====================

    @step
    def click_back(self):
        """Click the back button."""
        self.back_button.click()

    @step
    def click_edit(self):
        """Click the edit workflow button."""
        self.edit_button.click()

    @step
    def click_run_workflow(self):
        """Click the run workflow button."""
        self.run_workflow_button.click()

    @step
    def click_run_chat(self):
        """Click the run chat button."""
        self.run_chat_button.click()

    @step
    def close_new_execution_dialog(self):
        """Close the New Workflow Execution dialog."""
        self.new_execution_dialog_close_button.click()

    @step
    def click_configuration(self):
        """Click the Configuration button to open/close the configuration sidebar."""
        self.configuration_button.click()

    @step
    def click_copy_workflow_id(self):
        """Click the copy workflow ID button in the configuration sidebar."""
        self.workflow_id_copy_button.click()

    # ==================== VERIFICATION METHODS ====================

    @step
    def should_be_on_workflow_details_page(self):
        """Verify that we are on the Workflow Details page."""
        expect(self.back_button).to_be_visible()
        expect(self.workflow_name).to_be_visible()

    @step
    def should_have_workflow_name(self, expected_name: str):
        """Verify the workflow name heading."""
        expect(self.workflow_name).to_have_text(expected_name)

    @step
    def should_have_header_elements_visible(self):
        """Verify that all header elements are visible."""
        expect(self.back_button).to_be_visible()
        expect(self.workflow_name).to_be_visible()
        expect(self.edit_button).to_be_visible()
        expect(self.configuration_button).to_be_visible()
        expect(self.run_workflow_button).to_be_visible()
        expect(self.run_chat_button).to_be_visible()

    @step
    def should_have_action_buttons_visible(self):
        """Verify that action buttons are visible."""
        expect(self.edit_button).to_be_visible()
        expect(self.run_workflow_button).to_be_visible()
        expect(self.run_chat_button).to_be_visible()

    @step
    def should_have_edit_button_enabled(self):
        """Verify that the edit button is enabled."""
        expect(self.edit_button).to_be_enabled()

    @step
    def should_have_run_workflow_button_enabled(self):
        """Verify that the run workflow button is enabled."""
        expect(self.run_workflow_button).to_be_enabled()

    @step
    def should_have_run_chat_button_enabled(self):
        """Verify that the run chat button is enabled."""
        expect(self.run_chat_button).to_be_enabled()

    @step
    def should_have_new_execution_dialog_visible(self):
        """Verify that the New Workflow Execution dialog is visible."""
        expect(self.new_execution_dialog).to_be_visible()

    @step
    def should_have_no_executions_message(self):
        """Verify that the 'No Executions Yet' message is visible."""
        expect(self.no_executions_text).to_be_visible()

    @step
    def should_have_configuration_sidebar_closed(self):
        """Verify that the configuration sidebar is not visible."""
        expect(self.configuration_sidebar).to_be_hidden()

    @step
    def should_have_configuration_sidebar_open(self):
        """Verify that the configuration sidebar is visible."""
        expect(self.configuration_sidebar).to_be_visible()

    @step
    def should_have_workflow_info_in_sidebar(
        self, workflow_id: str, workflow_name: str
    ):
        """Verify workflow info in configuration sidebar."""
        expect(self.workflow_name_in_sidebar).to_have_text(workflow_name)
        expect(self.workflow_id_in_sidebar).to_contain_text(workflow_id)

    @step
    def should_have_configure_button_visible(self):
        """Verify that the Configure button is visible in the sidebar."""
        expect(self.configure_button_in_sidebar).to_be_visible()

    # ==================== ASSISTANT NODE PANEL METHODS ====================

    @step
    def open_assistant_node_panel(self, node_id: str) -> AssistantNodePanelPage:
        """Click on a workflow canvas node to open its assistant node panel.

        The node is identified by its React Flow node ID, which maps to the
        ``data-testid="rf__node-{node_id}"`` attribute on the canvas element.

        Args:
            node_id: The React Flow node ID for the assistant node.

        Returns:
            AssistantNodePanelPage instance for interacting with the opened panel.
        """
        node = self.page.get_by_test_id(f"rf__node-{node_id}")
        node.click()
        return AssistantNodePanelPage(self.page)

    @step
    def should_have_description_visible(self, expected_text: str):
        """Verify the description text is visible in the configuration sidebar.

        Requires the sidebar to already be open (call click_configuration() first).
        """
        expect(self.description_field).to_be_visible()
        expect(self.description_field).to_contain_text(expected_text)

    @step
    def should_have_description_not_editable(self):
        """Verify the description element is read-only (not an editable input/textarea).

        Checks that:
        - No contenteditable attribute exists (catches both "" and "true" values).
        - Element does not have the ARIA textbox role (catches <input> and <textarea>).
        """
        expect(self.description_field).not_to_have_attribute(
            "contenteditable", re.compile(r".*")
        )
        expect(self.description_field).not_to_have_role("textbox")

    @step
    def should_have_description_in_configuration_sidebar(self, expected_text: str):
        """Verify the configuration sidebar contains the expected description text.

        Used as a regression guard to confirm the description is shown inside the
        configuration sidebar (AC-3).  Requires the sidebar to already be open.
        """
        expect(self.configuration_sidebar).to_contain_text(expected_text)
