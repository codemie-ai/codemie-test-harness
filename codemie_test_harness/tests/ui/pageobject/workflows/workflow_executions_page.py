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

from typing import List, Optional

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.components.workflow_execution_history_item import (
    WorkflowExecutionHistoryItem,
)


class WorkflowExecutionsPage(BasePage):
    """Page object for the Workflow Executions page showing detailed execution history."""

    def __init__(self, page):
        super().__init__(page)
        self.page = page

    # ==================== HEADER ELEMENTS ====================

    @property
    def workflow_title(self) -> Locator:
        """Workflow title in the header."""
        return self.page.get_by_role("heading", level=1)

    @property
    def edit_button(self) -> Locator:
        """Edit workflow button in the header."""
        return self.page.get_by_role("button", name="Edit")

    @property
    def clear_all_executions_button(self) -> Locator:
        """Clear all executions icon button in the header."""
        return self.page.locator('[data-tooltip-content="Clear all executions"]')

    @property
    def configuration_button(self) -> Locator:
        """Configuration button in the header."""
        return self.page.get_by_role("button", name="Configuration")

    # ==================== SIDEBAR ELEMENTS ====================

    @property
    def sidebar(self) -> Locator:
        """Left sidebar container (execution history panel)."""
        return self.page.locator("aside").first

    @property
    def execution_history_title(self) -> Locator:
        """Execution history title in sidebar."""
        return self.page.locator('h2:has-text("Workflow Execution History")')

    @property
    def time_period_label(self) -> Locator:
        """Time period label (Last 7 days)."""
        return self.page.get_by_role("heading", level=3, name="Last 7 days")

    @property
    def execution_history_items(self) -> Locator:
        """All execution history items in sidebar."""
        return self.sidebar.locator("div[class*='rounded-xl'][class*='cursor-pointer']")

    @property
    def active_execution_item(self) -> Locator:
        """Currently active/selected execution item in sidebar."""
        return self.page.locator(
            "div[class*='bg-surface-specific-dropdown-hover/60'][class*='text-text-primary']"
        )

    @property
    def hide_sidebar_button(self) -> Locator:
        """Hide Sidebar button in the left sidebar."""
        return self.page.get_by_role("button", name="Hide Sidebar")

    @property
    def open_sidebar_button(self) -> Locator:
        """Open Sidebar button visible when the sidebar is collapsed."""
        return self.page.get_by_role("button", name="Open Sidebar")

    # ==================== MAIN CONTENT ACTION BUTTONS ====================

    @property
    def info_button(self) -> Locator:
        """Info button that opens the Execution Info dialog."""
        return self.page.get_by_role("button", name="Info")

    @property
    def export_button(self) -> Locator:
        """Export as .md or .html button in main content."""
        return self.page.locator('[data-tooltip-content="Export as .md or .html"]')

    @property
    def run_chat_button(self) -> Locator:
        """Run Chat button."""
        return self.page.get_by_role("button", name="Run Chat")

    @property
    def rerun_workflow_button(self) -> Locator:
        """Run workflow button."""
        return self.page.get_by_role("button", name="Run workflow")

    # ==================== WORKFLOW GRAPH ====================

    @property
    def workflow_graph(self) -> Locator:
        """React Flow workflow graph visualization."""
        return self.page.get_by_role("application")

    @property
    def control_panel(self) -> Locator:
        """Graph control panel container."""
        return self.page.get_by_role("generic", name="Control Panel")

    @property
    def zoom_in_button(self) -> Locator:
        """Zoom in button in the graph control panel."""
        return self.page.get_by_role("button", name="Zoom in")

    @property
    def zoom_out_button(self) -> Locator:
        """Zoom out button in the graph control panel."""
        return self.page.get_by_role("button", name="Zoom out")

    @property
    def fit_view_button(self) -> Locator:
        """Fit view button in the graph control panel."""
        return self.page.get_by_role("button", name="Fit view")

    @property
    def graph_download_button(self) -> Locator:
        """Download (graph image) button inside the React Flow application container."""
        return self.workflow_graph.get_by_role("button", name="Download")

    @property
    def graph_expand_button(self) -> Locator:
        """Expand (full-screen) button in the graph control panel.

        Uses exact name matching — the page also has an unrelated
        "Expand prompt" button whose accessible name otherwise matches
        "Expand" as a substring, causing a strict-mode violation."""
        return self.page.get_by_role("button", name="Expand", exact=True)

    # ==================== EXECUTION INFO DIALOG ====================

    @property
    def info_dialog(self) -> Locator:
        """Execution Info dialog (opened via Info button)."""
        return self.page.get_by_role("dialog", name="Execution Info")

    @property
    def status_badge(self) -> Locator:
        """Status value inside the Info dialog."""
        return self.info_dialog.locator(
            '//p[text()="Status:"]/following-sibling::div[1]'
        )

    @property
    def triggered_by(self) -> Locator:
        """Triggered by value inside the Info dialog."""
        return self.info_dialog.locator(
            '//p[text()="Triggered by:"]/following-sibling::div[1]'
        )

    @property
    def started_date(self) -> Locator:
        """Started time value inside the Info dialog."""
        return self.info_dialog.locator(
            '//p[text()="Started:"]/following-sibling::div[1]'
        )

    @property
    def finished_date(self) -> Locator:
        """Finished time value inside the Info dialog."""
        return self.info_dialog.locator(
            '//p[text()="Finished:"]/following-sibling::div[1]'
        )

    @property
    def runtime_in_dialog(self) -> Locator:
        """Runtime duration value inside the Info dialog."""
        return self.info_dialog.locator(
            '//p[text()="Runtime:"]/following-sibling::div[1]'
        )

    @property
    def execution_id_in_dialog(self) -> Locator:
        """Execution ID paragraph inside the Info dialog."""
        return self.info_dialog.locator(
            '//p[contains(text(),"ID:")]/following-sibling::div//p'
        )

    @property
    def execution_id_copy_button_in_dialog(self) -> Locator:
        """Copy button for execution ID inside the Info dialog."""
        return self.info_dialog.locator(
            '//p[contains(text(),"ID:")]/following-sibling::div//button'
        )

    @property
    def spending_metrics_heading(self) -> Locator:
        """'Spending metrics' section heading inside the Info dialog."""
        return self.info_dialog.get_by_role("heading", level=4, name="Spending metrics")

    @property
    def money_spent(self) -> Locator:
        """Money spent value inside the Info dialog."""
        return self.info_dialog.locator(
            '//p[text()="Money spent:"]/following-sibling::div[1]'
        )

    @property
    def input_tokens(self) -> Locator:
        """Input tokens value inside the Info dialog."""
        return self.info_dialog.locator(
            '//p[text()="Input tokens:"]/following-sibling::div[1]'
        )

    @property
    def output_tokens(self) -> Locator:
        """Output tokens value inside the Info dialog."""
        return self.info_dialog.locator(
            '//p[text()="Output tokens:"]/following-sibling::div[1]'
        )

    # ==================== PROMPT / STEP DETAIL SECTION ====================

    @property
    def prompt_section(self) -> Locator:
        """First code block in the step detail area (prompt/input content)."""
        return self.page.locator("code").first

    @property
    def prompt_code_block(self) -> Locator:
        """Container wrapping the Input label and code block."""
        return self.page.locator("p:has-text('Input')").locator("..")

    @property
    def prompt_title(self) -> Locator:
        """Input label paragraph."""
        return self.page.locator("p:has-text('Input')")

    @property
    def prompt_copy_button(self) -> Locator:
        """Copy button in the Input section."""
        return (
            self.page.locator("p:has-text('Input')")
            .locator("..")
            .get_by_role("button", name="Copy")
        )

    @property
    def prompt_download_button(self) -> Locator:
        """Download button in the Input section."""
        return (
            self.page.locator("p:has-text('Input')")
            .locator("..")
            .get_by_role("button", name="Download")
        )

    @property
    def prompt_info_button(self) -> Locator:
        """Expand/view-full button next to the Input label (opens full prompt dialog)."""
        return (
            self.page.locator("p:has-text('Input')")
            .locator("..")
            .locator("button")
            .last
        )

    @property
    def prompt_content(self) -> Locator:
        """Input code content (first code block)."""
        return self.page.locator("code").first

    @property
    def step_result_section(self) -> Locator:
        """Result section visible when a non-Starting-Prompt step is selected."""
        return self.page.locator("p:has-text('Result')").locator("..")

    @property
    def step_result_code(self) -> Locator:
        """Result code block for the selected execution step.

        Uses XPath to find the nearest ancestor of the Result label
        that contains a code element, then selects that code block.
        """
        return self.page.locator(
            "xpath=//p[contains(text(),'Result')]"
            "/ancestor::*[descendant::code][1]/descendant::code[1]"
        )

    # ==================== FULL PROMPT DIALOG ====================

    @property
    def full_prompt_dialog(self) -> Locator:
        """Full prompt dialog (named 'Input')."""
        return self.page.get_by_role("dialog", name="Input")

    @property
    def full_prompt_dialog_close_button(self) -> Locator:
        """Close button in full prompt dialog."""
        return self.full_prompt_dialog.get_by_role("button", name="Close")

    @property
    def full_prompt_dialog_code(self) -> Locator:
        """Code block containing the full prompt text inside the dialog."""
        return self.full_prompt_dialog.locator("code")

    # ==================== EXECUTION STEPS SECTION ====================

    @property
    def execution_steps(self) -> Locator:
        """All execution step buttons (Starting Prompt + node steps).

        Step buttons are each wrapped in a div, so go 2 levels up from the
        'Starting Prompt' button to reach the container holding all siblings.
        """
        return (
            self.page.get_by_role("button", name="Starting Prompt")
            .locator("../..")
            .locator("button")
        )

    # ==================== RIGHT SIDEBAR (CONFIGURATION) ====================

    @property
    def configuration_sidebar(self) -> Locator:
        """Right sidebar for configuration (when open)."""
        return self.page.locator("aside").nth(1)

    @property
    def configure_workflow_title(self) -> Locator:
        """Configure workflow title in right sidebar."""
        return self.configuration_sidebar.get_by_role(
            "heading", level=2, name="Configure Workflow"
        )

    @property
    def workflow_info_card(self) -> Locator:
        """Workflow information card in right sidebar."""
        return self.configure_workflow_title.locator("..").locator("> div").first

    @property
    def workflow_avatar_sidebar(self) -> Locator:
        """Workflow avatar in sidebar."""
        return self.workflow_info_card.locator("img")

    @property
    def workflow_name_sidebar(self) -> Locator:
        """Workflow name in sidebar."""
        return self.workflow_info_card.get_by_role("heading", level=4)

    @property
    def workflow_id_container(self) -> Locator:
        """Workflow ID container in sidebar."""
        return self.workflow_info_card.locator('p:has-text("ID:")').locator("..")

    @property
    def workflow_id_value(self) -> Locator:
        """Workflow ID paragraph in sidebar."""
        return self.workflow_info_card.locator('p:has-text("ID:")')

    @property
    def workflow_id_copy_button(self) -> Locator:
        """Workflow ID copy button in sidebar."""
        return self.workflow_id_container.locator("button")

    @property
    def configure_button(self) -> Locator:
        """Configure button in sidebar."""
        return self.workflow_info_card.locator(
            'button.button.secondary.medium.w-full:has-text("Configure")'
        )

    @property
    def yaml_configuration_title(self) -> Locator:
        """YAML configuration title in sidebar."""
        return self.configuration_sidebar.get_by_role(
            "heading", level=3, name="Yaml configuration"
        )

    @property
    def edit_yaml_button(self) -> Locator:
        """Edit YAML button in sidebar."""
        return self.configuration_sidebar.get_by_role("button", name="Edit")

    @property
    def yaml_code_block(self) -> Locator:
        """YAML code block in sidebar."""
        return self.configuration_sidebar.locator("div.code-block")

    @property
    def yaml_code_content(self) -> Locator:
        """YAML code content."""
        return self.yaml_code_block.locator("code")

    # ==================== NAVIGATION METHODS ====================

    @step
    def navigate_to(self, workflow_id: str, execution_id: str):
        """Navigate to the workflow executions page for a specific workflow."""
        url = f"/workflows/{workflow_id}/workflow-executions/{execution_id}"
        self.page.goto(url)

    @step
    def navigate_to_executions_list(self, workflow_id: str):
        """Navigate to the bare workflow-executions route (no executionId).

        Regression path: this URL used to 404 because the
        router only defined the ``:executionId``-suffixed variant.
        """
        url = f"/workflows/{workflow_id}/workflow-executions"
        self.page.goto(url)

    @step
    def click_edit(self):
        """Click the Edit workflow button."""
        self.edit_button.click()

    @step
    def click_export(self):
        """Click the export button."""
        self.export_button.click()

    @step
    def click_configuration(self):
        """Click the configuration button to open/close right sidebar."""
        self.configuration_button.click()

    @step
    def click_hide_sidebar(self):
        """Click the Hide Sidebar button to collapse the execution history sidebar."""
        self.hide_sidebar_button.click()

    @step
    def open_info_dialog(self):
        """Click Info button and wait for the Execution Info dialog to appear."""
        self.info_button.click()
        expect(self.info_dialog).to_be_visible()
        return self

    @step
    def close_info_dialog(self):
        """Close the Execution Info dialog."""
        self.info_dialog.get_by_role("button", name="Close").click()
        return self

    @step
    def click_rerun_workflow(self):
        """Click the Run workflow button."""
        self.rerun_workflow_button.click()

    # ==================== EXECUTION HISTORY METHODS ====================

    @step
    def get_execution_history_item(
        self, index: int = 0
    ) -> WorkflowExecutionHistoryItem:
        """Get an execution history item from the sidebar by index (0-based)."""
        item_locator = self.execution_history_items.nth(index)
        return WorkflowExecutionHistoryItem(self.page, item_locator)

    @step
    def get_first_execution_history_item(self) -> WorkflowExecutionHistoryItem:
        """Get the first execution history item."""
        return self.get_execution_history_item(0)

    @step
    def get_all_execution_history_items(self) -> List[WorkflowExecutionHistoryItem]:
        """Get all execution history items as components."""
        items = []
        count = self.execution_history_items.count()
        for i in range(count):
            item_locator = self.execution_history_items.nth(i)
            items.append(WorkflowExecutionHistoryItem(self.page, item_locator))
        return items

    # ==================== PROMPT INTERACTION METHODS ====================

    @step
    def view_full_prompt(self):
        """Open the full prompt dialog by clicking the expand button."""
        self.prompt_info_button.click()
        return self

    @step
    def close_full_prompt_dialog(self):
        """Close the full prompt dialog."""
        self.full_prompt_dialog_close_button.click()
        return self

    @step
    def click_copy_prompt(self):
        """Click the Copy button in the Input section."""
        self.prompt_copy_button.click()

    @step
    def click_download_prompt(self):
        """Click the Download button in the Input section."""
        self.prompt_download_button.click()

    @step
    def click_execution_step(self, step_name: str):
        """Click an execution step button by partial name match."""
        self.execution_steps.filter(has_text=step_name).first.click()
        return self

    @step
    def click_execution_step_by_index(self, index: int):
        """Click an execution step button by 0-based index."""
        self.execution_steps.nth(index).click()
        return self

    # ==================== VERIFICATION METHODS ====================

    @step
    def should_be_on_workflow_executions_page(self):
        """Verify that we are on the workflow executions page."""
        expect(self.workflow_title).to_be_visible()
        expect(self.execution_history_title).to_be_visible()
        expect(self.sidebar).not_to_contain_class("w-0")

    @step
    def should_have_workflow_title(self, expected_title: str):
        """Verify the workflow title."""
        expect(self.workflow_title).to_have_text(expected_title)

    @step
    def should_have_header_elements_visible(self):
        """Verify that all header elements are visible."""
        expect(self.back_button).to_be_visible()
        expect(self.workflow_title).to_be_visible()
        expect(self.edit_button).to_be_visible()
        expect(self.clear_all_executions_button).to_be_visible()
        expect(self.configuration_button).to_be_visible()

    @step
    def should_have_sidebar_visible(self):
        """Verify that the sidebar is expanded (not collapsed)."""
        expect(self.sidebar).not_to_contain_class("w-0")
        expect(self.execution_history_title).to_be_visible()
        expect(self.time_period_label).to_be_visible()
        expect(self.time_period_label).to_have_text("Last 7 days")

    @step
    def should_have_sidebar_collapsed(self):
        """Verify that the sidebar is collapsed (width = 0)."""
        expect(self.sidebar).to_contain_class("w-0")
        expect(self.open_sidebar_button).to_be_visible()

    @step
    def should_have_execution_history_items(self, expected_count: Optional[int] = None):
        """Verify execution history items are present."""
        expect(self.execution_history_items.first).to_be_visible()
        if expected_count is not None:
            expect(self.execution_history_items).to_have_count(expected_count)
        return self

    @step
    def should_have_active_execution_item(self):
        """Verify that there is an active execution item selected."""
        expect(self.active_execution_item).to_be_visible()

    @step
    def should_have_status(self, expected_status: str):
        """Verify the execution status in the Info dialog."""
        expect(self.status_badge).to_contain_text(expected_status)

    @step
    def should_have_succeeded_status(self):
        """Verify the execution status is Succeeded with proper styling."""
        self.should_have_status("Succeeded")

    @step
    def should_have_triggered_by(self, expected_user: str):
        """Verify the triggered by user in the Info dialog."""
        expect(self.triggered_by).to_have_text(expected_user)

    @step
    def should_have_started_time(self, expected_time: str):
        """Verify the started time in the Info dialog."""
        expect(self.started_date).to_have_text(expected_time)

    @step
    def should_have_finished_time(self, expected_time: str):
        """Verify the finished time in the Info dialog."""
        expect(self.finished_date).to_have_text(expected_time)

    @step
    def should_have_action_buttons_visible(self):
        """Verify that action buttons are visible and enabled."""
        expect(self.info_button).to_be_visible()
        expect(self.export_button).to_be_visible()
        expect(self.rerun_workflow_button).to_be_visible()
        expect(self.info_button).to_be_enabled()
        expect(self.export_button).to_be_enabled()
        expect(self.rerun_workflow_button).to_be_enabled()

    @step
    def should_have_prompt_section_visible(self):
        """Verify that the prompt section is visible."""
        expect(self.prompt_section).to_be_visible()
        expect(self.prompt_code_block).to_be_visible()
        expect(self.prompt_content).to_be_visible()

    @step
    def should_have_prompt_text(self, expected_prompt: str):
        """Verify the prompt text content."""
        expect(self.prompt_content).to_have_text(expected_prompt)

    @step
    def should_have_prompt_buttons_visible(self):
        """Verify that prompt action buttons are visible."""
        expect(self.prompt_info_button).to_be_visible()
        expect(self.prompt_copy_button).to_be_visible()
        expect(self.prompt_download_button).to_be_visible()

    @step
    def should_have_full_prompt_dialog_visible(self):
        """Verify that the full prompt dialog is visible with all elements."""
        expect(self.full_prompt_dialog).to_be_visible()
        expect(self.full_prompt_dialog.get_by_role("heading", level=4)).to_be_visible()
        expect(self.full_prompt_dialog_close_button).to_be_visible()
        return self

    @step
    def should_not_have_full_prompt_dialog_visible(self):
        """Verify that the full prompt dialog is not visible."""
        expect(self.full_prompt_dialog).not_to_be_visible()
        return self

    @step
    def should_have_execution_steps(self, expected_count: Optional[int] = None):
        """Verify execution step buttons are present."""
        expect(self.execution_steps.first).to_be_visible()
        if expected_count:
            expect(self.execution_steps).to_have_count(expected_count)

    @step
    def should_have_step_result_visible(self):
        """Verify the Result section is visible after selecting a non-Starting-Prompt step."""
        expect(self.step_result_section).to_be_visible()
        expect(self.step_result_code).to_be_visible()

    @step
    def should_have_workflow_graph_visible(self):
        """Verify the workflow graph and control panel are visible."""
        expect(self.workflow_graph).to_be_visible()
        expect(self.zoom_in_button).to_be_visible()
        expect(self.zoom_out_button).to_be_visible()
        expect(self.fit_view_button).to_be_visible()
        expect(self.graph_download_button).to_be_visible()
        expect(self.graph_expand_button).to_be_visible()

    @step
    def should_have_info_dialog_spending_metrics(self):
        """Verify the Spending metrics section is present in the Info dialog."""
        expect(self.spending_metrics_heading).to_be_visible()
        expect(self.money_spent).to_be_visible()
        expect(self.input_tokens).to_be_visible()
        expect(self.output_tokens).to_be_visible()

    @step
    def should_have_configuration_sidebar_closed(self):
        """Verify that the configuration sidebar is closed."""
        expect(self.configuration_sidebar).to_contain_class("w-0")

    @step
    def should_have_configuration_sidebar_open(self):
        """Verify that the configuration sidebar is open."""
        expect(self.configuration_sidebar).to_contain_class("w-96")
        expect(self.configure_workflow_title).to_be_visible()
        expect(self.workflow_info_card).to_be_visible()

    @step
    def should_have_yaml_configuration_visible(self):
        """Verify that YAML configuration is visible in sidebar."""
        expect(self.yaml_configuration_title).to_be_visible()
        expect(self.edit_yaml_button).to_be_visible()
        expect(self.yaml_code_block).to_be_visible()
        expect(self.yaml_code_content).to_be_visible()

    @step
    def should_have_workflow_info_in_sidebar(
        self, workflow_id: str, workflow_name: str
    ):
        """Verify workflow information in the sidebar."""
        expect(self.workflow_avatar_sidebar).to_be_visible()
        expect(self.workflow_name_sidebar).to_have_text(workflow_name)
        expect(self.workflow_id_value).to_contain_text(workflow_id)
        expect(self.workflow_id_copy_button).to_be_visible()

    @step
    def should_have_all_main_sections_visible(self):
        """Verify all main page sections are visible."""
        self.should_have_header_elements_visible()
        self.should_have_sidebar_visible()
        self.should_have_prompt_section_visible()
        self.should_have_execution_steps()

    @step
    def should_preserve_state_after_interactions(self):
        """Verify that the configuration sidebar opens and closes correctly."""
        self.click_configuration()
        self.should_have_configuration_sidebar_open()
        self.click_configuration()
        self.should_have_configuration_sidebar_closed()
