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

from playwright.sync_api import expect
from reportportal_client import step


class WorkflowExecutionState:
    """Component representing a single execution state in the workflow execution details."""

    def __init__(self, page, state_locator):
        """
        Initialize workflow execution state component.

        Args:
            page: Playwright page object
            state_locator: Locator for the specific state container
        """
        self.page = page
        self.state = state_locator

    # ==================== STATE ELEMENT PROPERTIES ====================

    @property
    def container(self):
        """Main state container element."""
        return self.state

    @property
    def state_row(self):
        """State row container with icon and content."""
        return self.state.locator("div.flex.flex-row.gap-5")

    @property
    def status_icon_container(self):
        """Status icon container with styling."""
        return self.state_row.locator("xpath=./div[1]")

    @property
    def status_icon(self):
        """Status icon (success/failure/running)."""
        return self.status_icon_container.locator("svg")

    @property
    def success_icon(self):
        """Success checkmark icon."""
        return self.status_icon.locator('path[stroke="#03FE06"]')

    @property
    def failure_icon(self):
        """Failure/error icon."""
        return self.status_icon.locator('path[stroke="#FF0000"], path[fill="#FF0000"]')

    @property
    def in_progress_icon(self):
        """In progress/running icon."""
        return self.status_icon.locator('path[stroke="#FFA500"], path[fill="#FFA500"]')

    @property
    def content_section(self):
        """Main content section containing state information."""
        return self.state_row.locator("div.grow")

    @property
    def state_name_and_task(self):
        """State name and task description section."""
        return self.content_section

    @property
    def timestamps_section(self):
        """Timestamps section with started and completed times."""
        return self.content_section.locator("div.mt-5").first

    @property
    def output_section(self):
        """Output section with open button."""
        return self.content_section.locator(
            "div.mt-5.flex.items-center.justify-between"
        )

    @property
    def output_label(self):
        """Output label text."""
        return self.output_section.locator('div:has-text("Output:")').first

    @property
    def output_open_button(self):
        """Output open button."""
        return self.output_section.get_by_role("button", name="Open")

    @property
    def toggle_button(self):
        """Expand/collapse toggle button."""
        return self.state_row.locator("div").last.locator("button")

    @property
    def expanded_content(self):
        """Expanded content container (when state is expanded)."""
        return self.state.locator("div.markdown")

    @property
    def expanded_message(self):
        """Expanded message content."""
        return self.expanded_content.locator("div.message")

    @property
    def expanded_result(self):
        """Expanded result content."""
        return self.expanded_content.locator("div.result")

    @property
    def copy_button(self):
        """Copy button in expanded content."""
        return self.expanded_content.locator(
            'button[title="Copy"], button[data-tooltip="Copy"]'
        )

    # ==================== TEXT EXTRACTION METHODS ====================

    @step
    def get_state_name(self) -> str:
        """Get the state name from the content."""
        text = self.content_section.text_content()
        if "State name:" in text:
            state_name_part = text.split("State name:")[1]
            if "Task:" in state_name_part:
                return state_name_part.split("Task:")[0].strip()
            return state_name_part.strip()
        return ""

    @step
    def get_task_description(self) -> str:
        """Get the task description from the content."""
        text = self.content_section.text_content()
        if "Task:" in text:
            task_part = text.split("Task:")[1]
            if "Started:" in task_part:
                return task_part.split("Started:")[0].strip()
            return task_part.strip()
        return ""

    @step
    def get_started_time(self) -> str:
        """Get the started timestamp."""
        text = self.timestamps_section.text_content()
        if "Started:" in text:
            started_part = text.split("Started:")[1]
            if "Completed" in started_part:
                return started_part.split("Completed")[0].strip()
            return started_part.strip()
        return ""

    @step
    def get_completed_time(self) -> str:
        """Get the completed timestamp."""
        text = self.timestamps_section.text_content()
        if "Completed" in text:
            return text.split("Completed")[1].strip()
        return ""

    @step
    def get_full_timestamps_text(self) -> str:
        """Get the full timestamps text content."""
        return self.timestamps_section.text_content().strip()

    # ==================== STATE CHECKING METHODS ====================

    @step
    def is_successful(self) -> bool:
        """Check if the state completed successfully."""
        return self.success_icon.is_visible()

    @step
    def is_failed(self) -> bool:
        """Check if the state failed."""
        return self.failure_icon.is_visible()

    @step
    def is_in_progress(self) -> bool:
        """Check if the state is in progress."""
        return self.in_progress_icon.is_visible()

    @step
    def has_output_section(self) -> bool:
        """Check if the state has an output section."""
        return self.output_section.is_visible()

    @step
    def has_timestamps(self) -> bool:
        """Check if the state has timestamps section."""
        return self.timestamps_section.is_visible()

    # ==================== INTERACTION METHODS ====================
    @step
    def toggle_expand_collapse(self):
        """Toggle between expanded and collapsed states."""
        self.toggle_button.click()

    @step
    def open_output(self):
        """Open/view the state output."""
        if self.has_output_section():
            self.output_open_button.click()

    @step
    def copy_content(self):
        """Copy the state content (requires expansion first)."""
        if self.copy_button.is_visible():
            self.copy_button.click()

    @step
    def hover(self):
        """Hover over the state container."""
        self.container.hover()

    @step
    def click(self):
        """Click on the state container."""
        self.container.click()

    @step
    def wait_for_visible(self, timeout: int = 5000):
        """Wait for the state to be visible."""
        self.container.wait_for(state="visible", timeout=timeout)

    # ==================== VERIFICATION METHODS ====================

    @step
    def should_be_visible(self):
        """Verify the state is visible."""
        expect(self.container).to_be_visible()

    @step
    def should_not_be_visible(self):
        """Verify the state is not visible."""
        expect(self.container).not_to_be_visible()

    @step
    def should_have_state_name(self, expected_name: str):
        """Verify the state has the expected name."""
        expect(self.content_section).to_contain_text(f"State name: {expected_name}")

    @step
    def should_have_task_description(self, expected_task: str):
        """Verify the state has the expected task description."""
        expect(self.content_section).to_contain_text(f"Task: {expected_task}")

    @step
    def should_have_started_time(self, expected_time: str):
        """Verify the state has the expected started time."""
        expect(self.timestamps_section).to_contain_text(f"Started: {expected_time}")

    @step
    def should_have_completed_time(self, expected_time: str):
        """Verify the state has the expected completed time."""
        expect(self.timestamps_section).to_contain_text(f"Completed {expected_time}")

    @step
    def should_have_successful_status(self):
        """Verify the state has successful status with proper styling."""
        expect(self.status_icon_container).to_have_class("bg-success-secondary")
        expect(self.status_icon_container).to_have_class("text-success-main")
        expect(self.status_icon_container).to_have_class("border-success-main")
        expect(self.success_icon).to_be_visible()

    @step
    def should_have_failed_status(self):
        """Verify the state has failed status with proper styling."""
        expect(self.status_icon_container).to_have_class("bg-error-secondary")
        expect(self.status_icon_container).to_have_class("text-error-main")
        expect(self.status_icon_container).to_have_class("border-error-main")
        expect(self.failure_icon).to_be_visible()

    @step
    def should_have_in_progress_status(self):
        """Verify the state has in progress status with proper styling."""
        expect(self.status_icon_container).to_have_class("bg-in-progress-secondary")
        expect(self.status_icon_container).to_have_class("text-in-progress-main")
        expect(self.status_icon_container).to_have_class("border-in-progress-main")
        expect(self.in_progress_icon).to_be_visible()

    @step
    def should_have_timestamps_section(self):
        """Verify the state has timestamps section visible."""
        expect(self.timestamps_section).to_be_visible()
        expect(self.timestamps_section).to_contain_text("Started:")

    @step
    def should_have_output_section(self):
        """Verify the state has output section visible."""
        expect(self.output_section).to_be_visible()
        expect(self.output_label).to_be_visible()
        expect(self.output_open_button).to_be_visible()
        expect(self.output_open_button).to_be_enabled()

    @step
    def should_have_toggle_button(self):
        """Verify the state has toggle button visible."""
        expect(self.toggle_button).to_be_visible()
        expect(self.toggle_button).to_be_enabled()

    @step
    def should_be_expanded(self):
        """Verify the state is expanded."""
        expect(self.expanded_content).to_be_visible(timeout=10000)

    @step
    def should_be_collapsed(self):
        """Verify the state is collapsed."""
        expect(self.expanded_content).not_to_be_visible()

    @step
    def should_have_expanded_content(self):
        """Verify the state has expanded content visible."""
        expect(self.expanded_content).to_be_visible()

    @step
    def should_have_copy_button_when_expanded(self):
        """Verify the state has copy button when expanded."""
        expect(self.copy_button).to_be_visible()
        expect(self.copy_button).to_be_enabled()

    @step
    def should_have_main_elements_visible(self):
        """Verify all main elements are visible."""
        expect(self.container).to_be_visible()
        expect(self.state_row).to_be_visible()
        expect(self.status_icon_container).to_be_visible()
        expect(self.status_icon).to_be_visible()
        expect(self.content_section).to_be_visible()
        expect(self.toggle_button).to_be_visible()

    @step
    def should_have_proper_styling(self):
        """Verify the state has proper styling classes."""
        expect(self.container).to_have_class("bg-new-panel-tertiary")
        expect(self.container).to_have_class("rounded-lg")
        expect(self.container).to_have_class("border-1")
        expect(self.container).to_have_class("border-border-secondary")
        expect(self.status_icon_container).to_have_class("rounded-lg")
        expect(self.status_icon_container).to_have_class("border-1")

    @step
    def should_be_interactive(self):
        """Verify the state is interactive."""
        expect(self.toggle_button).to_be_enabled()
        if self.has_output_section():
            expect(self.output_open_button).to_be_enabled()

    @step
    def should_respond_to_hover(self):
        """Verify the state responds to hover actions."""
        self.hover()
        # Add specific hover styling checks if needed

    @step
    def should_have_all_content_sections(self):
        """Verify all content sections are present."""
        expect(self.state_name_and_task).to_be_visible()

        if self.has_timestamps():
            expect(self.timestamps_section).to_be_visible()

        if self.has_output_section():
            expect(self.output_section).to_be_visible()

        expect(self.toggle_button).to_be_visible()

    @step
    def should_toggle_expansion_correctly(self):
        """Verify the state toggles expansion correctly."""
        # Start collapsed
        self.should_be_collapsed()

        # Expand
        self.should_be_expanded()

        # Collapse again
        self.should_be_collapsed()

    @step
    def should_have_complete_state_info(self, state_name: str, task_description: str):
        """Verify the state has complete information."""
        self.should_have_state_name(state_name)
        self.should_have_task_description(task_description)
        self.should_have_timestamps_section()
        self.should_have_output_section()
        self.should_have_toggle_button()
        self.should_have_main_elements_visible()

    @step
    def should_have_consistent_status_styling(self):
        """Verify the state has consistent status styling."""
        if self.is_successful():
            self.should_have_successful_status()
        elif self.is_failed():
            self.should_have_failed_status()
        elif self.is_in_progress():
            self.should_have_in_progress_status()
