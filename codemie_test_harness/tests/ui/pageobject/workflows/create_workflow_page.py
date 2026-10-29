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

from playwright.sync_api import expect, Locator
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.workflows.base_workflow_form_page import (
    BaseWorkflowFormPage,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


class CreateWorkflowPage(BaseWorkflowFormPage):
    """Page object for the Create Workflow page with Visual Editor."""

    page_url = "/workflows/new"

    def __init__(self, page):
        super().__init__(page)

    # ==================== PROPERTIES ====================
    # Header elements specific to Create page
    @property
    def page_title(self):
        """Page title 'Create Workflow'."""
        return self.page.get_by_role("heading", name="Create Workflow")

    # Help button and panel elements
    @property
    def help_button(self) -> Locator:
        """Help button in bottom right corner."""
        return self.page.get_by_role("button", name="Help").filter(
            has=self.page.locator("svg")
        )

    @property
    def help_panel_title(self) -> Locator:
        """Help panel title 'CodeMie Helper'."""
        return self.page.get_by_role("heading", name="CodeMie Helper", level=3)

    @property
    def help_panel_description(self) -> Locator:
        """Help panel description text."""
        return self.page.get_by_text(
            "If you'd like to learn more or understand how it works in detail"
        )

    @property
    def help_panel_close_button(self) -> Locator:
        """Close button in help panel.
        Uses exact=True to avoid matching toast notification 'Close notification' button.
        """
        return self.page.locator(".w-96").get_by_role("button", name="Close")

    @property
    def help_create_workflows_button(self) -> Locator:
        """'How to create Workflows' button in help panel."""
        return self.page.get_by_role("button", name="How to create Workflows")

    @property
    def help_yaml_config_button(self) -> Locator:
        """'How to work with YAML Configuration' button in help panel."""
        return self.page.get_by_role("button", name="How to work with YAML")

    @property
    def template_variables_dialog(self) -> Locator:
        """'Configure Template Variables' dialog.

        Shown only when the selected template declares one or more
        ``${input:name}`` placeholders — the user must supply a value for
        each required field before the canvas becomes usable."""
        return self.page.get_by_role("dialog", name="Configure Template Variables")

    @property
    def template_variables_dialog_apply_button(self) -> Locator:
        """'Apply' button inside the template-variables dialog."""
        return self.template_variables_dialog.get_by_role("button", name="Apply")

    # ==================== NAVIGATION METHODS ====================
    @step
    def navigate_to(self):
        """Navigate to the Create Workflow page."""
        self.page.goto(self.page_url)
        self.wait_for_page_load()

    # ==================== INTERACTION METHODS ====================

    @step
    def fill_template_variables_if_present(self, value: str = "test-value"):
        """Fill and apply the 'Configure Template Variables' dialog if the
        template just selected declares required ${input:...} placeholders.

        Not every template has variables, so the dialog is optional — a short
        wait distinguishes "not shown for this template" from "still
        rendering" without slowing down the common case."""
        try:
            self.template_variables_dialog.wait_for(state="visible", timeout=3000)
        except PlaywrightTimeoutError:
            return self
        textboxes = self.template_variables_dialog.get_by_role("textbox")
        for i in range(textboxes.count()):
            textboxes.nth(i).fill(value)
        self.template_variables_dialog_apply_button.click()
        expect(self.template_variables_dialog).to_be_hidden()
        return self

    @step
    def click_help_button(self):
        """Click the help button in bottom right corner."""
        self.help_button.click()
        # Wait for help panel to appear
        expect(self.help_panel_title).to_be_visible()
        return self

    @step
    def close_help_panel(self):
        """Close the help panel."""
        self.help_panel_close_button.click()
        # Wait for help panel to disappear
        expect(self.help_panel_title).to_be_hidden()
        return self

    @step
    def click_help_create_workflows(self):
        """Click 'How to create Workflows' button in help panel."""
        self.help_create_workflows_button.click()
        return self

    @step
    def click_help_yaml_config(self):
        """Click 'How to work with YAML Configuration' button in help panel."""
        self.help_yaml_config_button.click()
        return self

    @step
    def create_workflow(
        self,
        name: str = "",
        project_name: str = "",
        description: str = "",
        icon_url: str = "",
        yaml_config: str = "",
        shared: bool = False,
        categories: list[str] | None = None,
    ):
        """
        Complete workflow creation with provided details using YAML Editor.

        Args:
            name: Workflow name (required)
            project_name: Project name (optional)
            description: Workflow description (optional)
            icon_url: Icon URL (optional)
            yaml_config: YAML configuration (optional)
            shared: Whether to share with project team (optional)
            categories: Names of categories to select (optional, up to 3)
        """

        name = name or get_random_name()

        # Open workflow config panel
        workflow_config_panel = self.open_workflow_config_panel()

        # Switch to Basic tab to fill basic fields
        workflow_config_panel.switch_to_basic_tab()

        # Fill name
        workflow_config_panel.fill_name(name)

        # Select project if provided
        if project_name:
            workflow_config_panel.select_project(project_name)

        # Fill description if provided
        if description:
            workflow_config_panel.fill_description(description)

        # Fill icon URL if provided
        if icon_url:
            workflow_config_panel.fill_icon_url(icon_url)

        # Toggle shared if needed
        if shared:
            workflow_config_panel.toggle_shared_switch()

        # Select categories if provided
        if categories:
            workflow_config_panel.select_categories(categories)

        # Save config on panel
        workflow_config_panel.click_save()

        # Fill YAML config if provided
        if yaml_config:
            workflow_config_panel = self.open_yaml_panel()
            workflow_config_panel.fill_yaml_config(yaml_config)
            workflow_config_panel.click_save()

        # Save workflow
        self.click_save()

    # ==================== VERIFICATION METHODS ====================
    @step
    def should_be_on_create_workflow_page(self, page_title="Create Workflow"):
        """Verify that we are on the Create Workflow page."""
        expect(self.page_title).to_have_text(page_title, timeout=15000)
        expect(self.save_button).to_be_visible(timeout=15000)
        expect(self.cancel_button).to_be_visible(timeout=15000)
        expect(self.canvas).to_be_visible(timeout=15000)
        return self

    @step
    def should_have_menu_elements_visible(self):
        """Verify that all header menu elements are visible."""
        expect(self.back_button).to_be_visible()
        expect(self.page_title).to_be_visible()
        expect(self.cancel_button).to_be_visible()
        expect(self.save_button).to_be_visible()
        expect(self.save_and_run_button).to_be_visible()

    @step
    def should_have_navigation_buttons_visible(self):
        """Verify that all navigation buttons are visible."""
        expect(self.back_button).to_be_visible()
        expect(self.cancel_button).to_be_visible()
        expect(self.save_button).to_be_visible()

    @step
    def should_have_help_button_visible(self):
        """Verify that the help button is visible in bottom right corner."""
        expect(self.help_button).to_be_visible()
        return self

    @step
    def should_have_help_panel_visible(self):
        """Verify that the help panel is visible with all elements."""
        expect(self.help_panel_title).to_be_visible()
        expect(self.help_panel_description).to_be_visible()
        expect(self.help_panel_close_button).to_be_visible()
        expect(self.help_create_workflows_button).to_be_visible()
        expect(self.help_yaml_config_button).to_be_visible()
        return self
