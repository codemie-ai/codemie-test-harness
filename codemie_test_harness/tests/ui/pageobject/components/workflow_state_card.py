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


class WorkflowStateCard:
    """Component representing a single workflow state card."""

    def __init__(self, page, card_locator):
        """
        Initialize workflow state card component.

        Args:
            page: Playwright page object
            card_locator: Locator for the specific state card container
        """
        self.page = page
        self.card = card_locator

    # Card elements
    @property
    def container(self):
        """Main container element."""
        return self.card

    @property
    def status_icon(self):
        """Status icon (success/failure/running)."""
        return self.card.locator(".min-w-\\[2rem\\].w-\\[2rem\\].h-\\[2rem\\] svg")

    @property
    def status_icon_container(self):
        """Status icon container with styling."""
        return self.card.locator(".min-w-\\[2rem\\].w-\\[2rem\\].h-\\[2rem\\]")

    @property
    def content_section(self):
        """Main content section containing state info."""
        return self.card.locator(".grow").first

    @property
    def state_name_section(self):
        """State name section."""
        return self.content_section

    @property
    def timestamps_section(self):
        """Started/Completed timestamps section."""
        return self.card.locator(".mt-5").first

    @property
    def output_section(self):
        """Output section with open button."""
        return self.card.locator(".mt-5.flex.items-center.justify-between")

    @property
    def output_button(self):
        """Output open button."""
        return self.output_section.locator('button:has-text("Open")')

    @property
    def toggle_button(self):
        """Expand/collapse toggle button."""
        return self.card.locator("button").last

    @property
    def toggle_up_arrow(self):
        """Up arrow for collapse action."""
        return self.toggle_button.locator('svg path[d*="3.172 11.12"]')

    @property
    def toggle_down_arrow(self):
        """Down arrow for expand action."""
        return self.toggle_button.locator('svg path[d*="14.828 6.88"]')

    @property
    def expanded_content(self):
        """Expanded content container."""
        return self.card.locator(".wrapper")

    @property
    def message_content(self):
        """Message content within expanded state."""
        return self.expanded_content.locator(".message .markdown")

    @property
    def copy_button(self):
        """Copy button for state content."""
        return self.expanded_content.locator('button[data-pd-tooltip="true"]')

    @property
    def result_content(self):
        """Result content in expanded view."""
        return self.expanded_content.locator(
            ".relative.border-1.border-new-stroke.rounded-xl"
        )

    # Utility methods
    @step
    def get_state_name_text(self) -> str:
        """Get state name from the content."""
        text = self.content_section.text_content()
        if "State name:" in text:
            return text.split("State name:")[1].split("Task:")[0].strip()
        return ""

    @step
    def get_task_description_text(self) -> str:
        """Get task description text."""
        text = self.content_section.text_content()
        if "Task:" in text:
            return text.split("Task:")[1].split("Started:")[0].strip()
        return ""

    @step
    def get_timestamps_text(self) -> str:
        """Get timestamps text."""
        return self.timestamps_section.text_content().strip()

    @step
    def get_started_time(self) -> str:
        """Get started timestamp."""
        text = self.timestamps_section.text_content()
        if "Started:" in text:
            return text.split("Started:")[1].split("Completed")[0].strip()
        return ""

    @step
    def get_completed_time(self) -> str:
        """Get completed timestamp."""
        text = self.timestamps_section.text_content()
        if "Completed" in text:
            return text.split("Completed")[1].strip()
        return ""

    @step
    def is_successful(self) -> bool:
        """Check if state completed successfully."""
        return self.status_icon.locator('path[stroke="#03FE06"]').is_visible()

    @step
    def is_failed(self) -> bool:
        """Check if state failed."""
        return (
            self.status_icon.locator('path[stroke="#FF0000"]').is_visible()
            or self.status_icon.locator('path[fill="#FF0000"]').is_visible()
        )

    @step
    def is_expanded(self) -> bool:
        """Check if state is expanded."""
        return self.toggle_up_arrow.is_visible()

    @step
    def is_collapsed(self) -> bool:
        """Check if state is collapsed."""
        return self.toggle_down_arrow.is_visible()

    # Action methods
    @step
    def expand(self):
        """Expand the state card."""
        if not self.is_expanded():
            self.toggle_button.click()
        return self

    @step
    def collapse(self):
        """Collapse the state card."""
        if self.is_expanded():
            self.toggle_button.click()
        return self

    @step
    def toggle_expand_collapse(self):
        """Toggle expand/collapse state."""
        self.toggle_button.click()
        return self

    @step
    def open_output(self):
        """Open state output."""
        self.output_button.click()
        return self

    @step
    def copy_content(self):
        """Copy state content."""
        self.expand()
        self.copy_button.click()
        return self

    @step
    def hover(self):
        """Hover over the state card."""
        self.card.hover()
        return self

    @step
    def wait_for_visible(self, timeout: int = 5000):
        """Wait for the state card to be visible."""
        self.card.wait_for(state="visible", timeout=timeout)
        return self

    # Verification methods
    @step
    def should_be_visible(self):
        """Verify the state card is visible."""
        expect(self.container).to_be_visible()
        return self

    @step
    def should_not_be_visible(self):
        """Verify the state card is not visible."""
        expect(self.container).not_to_be_visible()
        return self

    @step
    def should_have_state_name(self, expected_name: str):
        """Verify the state has the expected name."""
        expect(self.content_section).to_contain_text(f"State name: {expected_name}")
        return self

    @step
    def should_have_task_description(self, expected_description: str):
        """Verify the state has the expected task description."""
        expect(self.content_section).to_contain_text(f"Task: {expected_description}")
        return self

    @step
    def should_have_successful_status(self):
        """Verify the state has successful status."""
        expect(self.status_icon_container).to_have_class("bg-success-secondary")
        expect(self.status_icon_container).to_have_class("text-success-main")
        expect(self.status_icon_container).to_have_class("border-success-main")
        expect(self.status_icon.locator('path[stroke="#03FE06"]')).to_be_visible()
        return self

    @step
    def should_have_failed_status(self):
        """Verify the state has failed status."""
        expect(self.status_icon_container).to_have_class("bg-error-secondary")
        expect(self.status_icon_container).to_have_class("text-error-main")
        expect(self.status_icon_container).to_have_class("border-error-main")
        return self

    @step
    def should_have_in_progress_status(self):
        """Verify the state has in progress status."""
        expect(self.status_icon_container).to_have_class("bg-in-progress-secondary")
        expect(self.status_icon_container).to_have_class("text-in-progress-main")
        expect(self.status_icon_container).to_have_class("border-in-progress-main")
        return self

    @step
    def should_have_timestamps(self):
        """Verify the state has timestamps section."""
        expect(self.timestamps_section).to_be_visible()
        expect(self.timestamps_section).to_contain_text("Started:")
        return self

    @step
    def should_have_started_time(self, expected_time: str):
        """Verify the state has expected started time."""
        expect(self.timestamps_section).to_contain_text(f"Started: {expected_time}")
        return self

    @step
    def should_have_completed_time(self, expected_time: str):
        """Verify the state has expected completed time."""
        expect(self.timestamps_section).to_contain_text(f"Completed {expected_time}")
        return self

    @step
    def should_have_output_section(self):
        """Verify the state has output section."""
        expect(self.output_section).to_be_visible()
        expect(self.output_button).to_be_visible()
        expect(self.output_button).to_be_enabled()
        return self

    @step
    def should_have_toggle_button(self):
        """Verify the state has toggle button."""
        expect(self.toggle_button).to_be_visible()
        expect(self.toggle_button).to_be_enabled()
        return self

    @step
    def should_be_expanded(self):
        """Verify the state is expanded."""
        expect(self.toggle_up_arrow).to_be_visible()
        expect(self.expanded_content).to_be_visible()
        return self

    @step
    def should_be_collapsed(self):
        """Verify the state is collapsed."""
        expect(self.toggle_down_arrow).to_be_visible()
        expect(self.expanded_content).not_to_be_visible()
        return self

    @step
    def should_have_expanded_content(self):
        """Verify the state has expanded content visible."""
        expect(self.expanded_content).to_be_visible()
        return self

    @step
    def should_have_message_content(self):
        """Verify the state has message content in expanded view."""
        self.expand()
        expect(self.message_content).to_be_visible()
        return self

    @step
    def should_have_copy_button(self):
        """Verify the state has copy button in expanded view."""
        self.expand()
        expect(self.copy_button).to_be_visible()
        expect(self.copy_button).to_be_enabled()
        return self

    @step
    def should_have_result_content(self):
        """Verify the state has result content in expanded view."""
        self.expand()
        expect(self.result_content).to_be_visible()
        return self

    @step
    def should_have_all_main_elements(self):
        """Verify all main elements are visible."""
        expect(self.container).to_be_visible()
        expect(self.status_icon_container).to_be_visible()
        expect(self.status_icon).to_be_visible()
        expect(self.content_section).to_be_visible()
        expect(self.timestamps_section).to_be_visible()
        expect(self.output_section).to_be_visible()
        expect(self.toggle_button).to_be_visible()
        return self

    @step
    def should_have_proper_styling(self):
        """Verify the state card has proper styling."""
        expect(self.container).to_have_class("bg-new-panel-tertiary")
        expect(self.container).to_have_class("rounded-lg")
        expect(self.container).to_have_class("border-1")
        expect(self.container).to_have_class("border-border-secondary")
        return self

    @step
    def should_be_clickable(self):
        """Verify the state card elements are clickable."""
        expect(self.toggle_button).to_be_enabled()
        expect(self.output_button).to_be_enabled()
        return self
