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

"""
Create/Edit Skill Page Object following Page Object Model (POM) best practices.

This class encapsulates all interactions with the Create/Edit Skill form.
"""

import re
from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.assistants.tools_section import (
    ToolsSection,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.assistant_test_data import Section
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


class CreateEditSkillPage(BasePage):
    """Page object for the Create/Edit Skill form."""

    page_url = "/skills/new"

    def __init__(self, page):
        """Initialize the Create/Edit Skill page object."""
        super().__init__(page)
        self.tools = ToolsSection(page)

    # =============================================================================
    # LOCATORS - Page Elements
    # =============================================================================

    @property
    def page_title(self) -> Locator:
        """Page title 'Create New Skill' or 'Edit Skill'"""
        return self.page.locator('h1:has-text("Skill")')

    @property
    def back_button(self) -> Locator:
        """Back button"""
        return self.page.get_by_role("button", name="Back")

    @property
    def cancel_button(self) -> Locator:
        """Cancel button"""
        return self.page.get_by_role("button", name="Cancel")

    @property
    def update_button(self) -> Locator:
        """Update Skill button (in edit mode)"""
        return self.page.get_by_role("button", name="Update Skill")

    @property
    def save_button(self) -> Locator:
        """Generic save button (works for both create and update)"""
        if self.create_button.count() > 0:
            return self.create_button
        return self.update_button

    @property
    def download_example_button(self) -> Locator:
        """Download Example button"""
        return self.page.get_by_role("button", name="Download Example")

    @property
    def import_from_file_button(self) -> Locator:
        """Import File or Bundle button"""
        return self.page.get_by_role("button", name="Import File or Bundle")

    # Skill Setup Section
    @property
    def skill_setup_heading(self) -> Locator:
        """Skill Setup section heading"""
        return self.page.locator('h4:has-text("Skill Setup")')

    @property
    def project_dropdown(self) -> Locator:
        """Project name dropdown"""
        return self.page.get_by_role("combobox", name="Project name")

    @property
    def shared_toggle(self) -> Locator:
        """'Shared with project' toggle switch"""
        return self.page.locator('label:has-text("Shared with project")')

    @property
    def shared_toggle_input(self) -> Locator:
        """'Shared with project' checkbox input (for checking state)"""
        return self.page.get_by_role("switch", name="Shared with project")

    @property
    def name_input(self) -> Locator:
        """Skill name input field"""
        return self.page.get_by_placeholder("Name*").or_(
            self.page.locator('input[placeholder*="my-skill-name"]')
        )

    @property
    def description_textarea(self) -> Locator:
        """Skill description textarea"""
        return self.page.locator('textarea[name="description"]')

    @property
    def categories_dropdown(self) -> Locator:
        """Categories dropdown combobox"""
        return self.page.get_by_role("combobox", name="Categories")

    # Instructions Section
    @property
    def instructions_heading(self) -> Locator:
        """Instructions section heading"""
        return self.page.locator('text="Instructions"').first

    @property
    def instructions_textarea(self) -> Locator:
        """Instructions textarea"""
        return self.page.locator("textarea").last

    @property
    def expand_button(self) -> Locator:
        """Expand instructions button"""
        return self.page.get_by_role("button", name="Expand")

    @property
    def instructions_char_count(self) -> Locator:
        """Instructions character count label"""
        return self.page.locator("text=/Instructions \\(\\d+\\/30,000\\)/")

    # Required Tools Section
    @property
    def required_tools_heading(self) -> Locator:
        """Required Tools section heading"""
        return self.page.locator('h4:has-text("Required Tools")')

    @property
    def available_tools(self) -> Locator:
        """Available Tools expandable button/section"""
        return self.page.get_by_role("button").filter(has_text="Available Tools")

    @property
    def external_tools(self) -> Locator:
        """External Tools expandable button/section"""
        return self.page.get_by_role("button").filter(has_text="External Tools")

    @property
    def validation_error_message(self) -> Locator:
        """Validation error message"""
        return self.page.locator('.error-message, [class*="error"]').first

    # =============================================================================
    # NAVIGATION METHODS
    # =============================================================================

    @property
    def generate_with_ai_dialog(self) -> Locator:
        """'Generate Skill with AI' dialog that auto-opens on page load"""
        return self.page.get_by_role("dialog", name="Generate Skill with AI")

    @property
    def create_manually_button(self) -> Locator:
        """'Create Manually' button inside the Generate with AI dialog"""
        return self.page.get_by_role("button", name="Create Manually")

    @step("Navigate to Create Skill page")
    def navigate_to(self):
        """Navigate to the Create Skill page."""
        self.page.goto(self.page_url)
        self.wait_for_page_load()
        self.create_manually_button.click()
        return self

    @step("Navigate to Edit Skill page")
    def navigate_to_edit(self, skill_id: str):
        """Navigate to the Edit Skill page."""
        self.page.goto(f"/skills/{skill_id}/edit")
        self.wait_for_page_load()
        return self

    # =============================================================================
    # FORM INTERACTION METHODS
    # =============================================================================

    @step("Fill skill name")
    def fill_name(self, name: str):
        """Fill the skill name field."""
        self.name_input.clear()
        self.name_input.fill(name)
        return self

    @step("Fill skill description")
    def fill_description(self, description: str):
        """Fill the skill description field."""
        self.description_textarea.clear()
        self.description_textarea.fill(description)
        return self

    @step("Fill skill instructions")
    def fill_instructions(self, instructions: str):
        """Fill the skill instructions field."""
        self.instructions_textarea.clear()
        self.instructions_textarea.fill(instructions)
        return self

    def get_skill_name(self) -> str:
        """
        Get the current value of the skill name field.

        Returns:
            str: The current skill name
        """
        return self.name_input.input_value()

    @step("Toggle shared with project")
    def toggle_shared(self, shared: bool = True):
        """Toggle the shared/project setting."""
        is_currently_checked = self.shared_toggle_input.is_checked()
        if (shared and not is_currently_checked) or (
            not shared and is_currently_checked
        ):
            self.shared_toggle.click()
        return self

    @step("Upload skill file")
    def upload_skill_file(self, file_path: str):
        """Upload a skill markdown file via Import from File button."""
        # Click Import button to trigger file chooser
        with self.page.expect_file_chooser() as fc_info:
            self.import_from_file_button.click()
        file_chooser = fc_info.value
        file_chooser.set_files(file_path)
        # Wait for file to be processed
        self.page.wait_for_load_state("domcontentloaded")
        return self

    @step("Select category")
    def select_category(self, category_name: str):
        """
        Select a category from the categories dropdown.

        Args:
            category_name: Name of the category to select (e.g., "Testing", "Development")
        """
        # Click to open the categories dropdown using force to bypass pointer interception
        self.categories_dropdown.click(force=True)

        # Wait for listbox with options to appear
        self.page.get_by_role("listbox").wait_for(state="visible", timeout=5000)

        # Now find and click the option
        option_locator = self.page.get_by_role("option", name=category_name)
        expect(option_locator).to_be_visible(timeout=5000)
        option_locator.click()

        return self

    @step("Select tool from toolkit")
    def select_tool(self, toolkit: str = "Cloud", tool_name: str = "AWS"):
        """
        Select a tool from the Available Tools section.

        Delegates to ToolsSection which is shared with the assistant create/edit page.

        Args:
            toolkit: Name of the toolkit category (default: "Cloud")
            tool_name: Name of the tool to select (default: "AWS")
        """
        self.tools.select_section(Section.AVAILABLE_TOOLS.value)
        self.tools.select_toolkit(Section.AVAILABLE_TOOLS.value, toolkit)
        self.tools.select_tool(tool_name)
        return self

    # =============================================================================
    # ACTION METHODS
    # =============================================================================

    @step("Click Create button")
    def click_create(self):
        """Click the Create button to save the skill."""
        self.create_button.click()
        return self

    @step("Click Create/Save button")
    def click_save(self):
        """Click the Create/Update button to save the skill."""
        self.save_button.click()
        # Wait for page to process the save action
        self.page.wait_for_load_state("networkidle")
        return self

    @step("Click Back button")
    def click_back(self):
        """Click the Back button to return to skills list."""
        self.back_button.click()
        return self

    @step("Click Cancel button")
    def click_cancel(self):
        """Click the Cancel button."""
        self.cancel_button.click()
        return self

    @step("Click Download Example button")
    def click_download_example(self):
        """Click the Download Example button."""
        self.download_example_button.click()
        return self

    # =============================================================================
    # COMPREHENSIVE SKILL CREATION METHOD
    # =============================================================================

    @step("Create skill with all fields")
    def create_skill(
        self,
        name: str,
        description: str,
        instructions: str,
        shared: bool = False,
        categories: list[str] = None,
    ):
        """
        Complete skill creation workflow with all required parameters.

        Args:
            name: Skill name (kebab-case)
            description: Skill description
            instructions: Skill instructions (markdown)
            shared: Whether to share with project (default: False/Private)
            categories: Optional list of category names to select (e.g., ["Testing", "Development"])
        """
        self.fill_name(name)
        self.fill_description(description)
        self.fill_instructions(instructions)
        self.toggle_shared(shared)

        # Select categories if provided
        if categories:
            for category in categories:
                self.select_category(category)

        self.click_save()
        return self

    # =============================================================================
    # VERIFICATION METHODS
    # =============================================================================

    @step("Verify on Create Skill page")
    def should_be_on_create_skill_page(self):
        """Verify that we are on the Create Skill page."""
        expect(self.page).to_have_url(re.compile(r".*/skills/new.*"))
        return self

    @step("Verify all form fields are visible")
    def should_have_all_form_fields_visible(self):
        """Verify that all essential form fields are visible."""
        # Skill Setup section
        expect(self.project_dropdown).to_be_visible()
        expect(self.shared_toggle_input).to_be_visible()
        expect(self.name_input).to_be_visible()
        expect(self.description_textarea).to_be_visible()
        expect(self.categories_dropdown).to_be_visible()

        # Instructions section
        expect(self.instructions_textarea).to_be_visible()

        # Required Tools section
        expect(self.available_tools).to_be_visible()
        if EnvironmentResolver.is_preview() or EnvironmentResolver.is_production():
            expect(self.external_tools).to_be_visible()
        return self

    @step("Verify action buttons are visible")
    def should_have_action_buttons_visible(self):
        """Verify that action buttons (Save, Cancel) are visible."""
        expect(self.save_button).to_be_visible()
        expect(self.cancel_button).to_be_visible()
        return self

    @step("Verify import button is visible")
    def should_have_import_button_visible(self):
        """Verify that the Import from File button is visible."""
        expect(self.import_from_file_button).to_be_visible()
        expect(self.import_from_file_button).to_be_enabled()
        return self

    @step("Verify download example button is visible")
    def should_have_download_button_visible(self):
        """Verify that the Download Example button is visible."""
        expect(self.download_example_button).to_be_visible()
        expect(self.download_example_button).to_be_enabled()
        return self

    @step("Verify shared toggle is checked")
    def should_have_shared_checked(self):
        """Verify shared toggle is checked (Project scope)."""
        expect(self.shared_toggle_input).to_be_checked()
        return self

    @step("Verify shared toggle is unchecked")
    def should_have_shared_unchecked(self):
        """Verify shared toggle is unchecked (Private scope)."""
        expect(self.shared_toggle_input).not_to_be_checked()
        return self

    @step("Verify name field is populated")
    def should_have_name_populated(self):
        """Verify that the name field contains a value (not empty)."""
        expect(self.name_input).not_to_have_value("")
        return self

    @step("Verify description field is populated")
    def should_have_description_populated(self):
        """Verify that the description field contains a value (not empty)."""
        expect(self.description_textarea).not_to_have_value("")
        return self

    @step("Verify instructions field is populated")
    def should_have_instructions_populated(self):
        """Verify that the instructions field contains a value (not empty)."""
        expect(self.instructions_textarea).not_to_have_value("")
        return self

    @step("Verify validation error is displayed")
    def should_have_validation_error(self, error_text: str = None):
        """Verify that a validation error is displayed."""
        expect(self.validation_error_message).to_be_visible()
        if error_text:
            expect(self.validation_error_message).to_contain_text(error_text)
        return self

    @step("Verify required name field error")
    def should_have_required_name_error(self):
        """Verify that name field shows 'Name is required' error."""
        error = self.page.locator('text="Name is required"')
        expect(error).to_be_visible(timeout=5000)
        return self

    @step("Verify required description field error")
    def should_have_required_description_error(self):
        """Verify that description field shows 'Description is required' error."""
        error = self.page.locator('text="Description is required"')
        expect(error).to_be_visible(timeout=5000)
        return self

    @step("Verify required instructions field error")
    def should_have_required_instructions_error(self):
        """Verify that instructions field shows 'Instructions are required' error."""
        error = self.page.locator('text="Instructions are required"')
        expect(error).to_be_visible(timeout=5000)
        return self

    @step("Verify name format error")
    def should_have_name_format_error(self):
        """Verify that name field shows kebab-case format error."""
        error = self.page.locator(
            'text="Name must be kebab-case (lowercase letters, numbers, and hyphens only)"'
        )
        expect(error).to_be_visible(timeout=5000)
        return self

    @step("Verify description length error")
    def should_have_description_length_error(self):
        """Verify that description field shows minimum length error."""
        error = self.page.locator('text="Description must be at least 10 characters"')
        expect(error).to_be_visible(timeout=5000)
        return self

    @step("Verify instructions length error")
    def should_have_instructions_length_error(self):
        """Verify that instructions field shows minimum length error."""
        error = self.page.locator('text="Instructions must be at least 100 characters"')
        expect(error).to_be_visible(timeout=5000)
        return self

    # =============================================================================
    # BUNDLE FILES CEILING WARNING
    # =============================================================================

    @property
    def bundle_ceiling_warning(self) -> Locator:
        """Warning that the uploaded bundle has more files or bytes than a workspace receives"""
        return self.page.get_by_text("will not be available in an assistant workspace")

    def bundle_file_entry(self, file_name: str) -> Locator:
        """Entry of one bundle file in the bundle files section"""
        return self.page.get_by_text(file_name, exact=True).first

    @step("Verify the bundle file is listed")
    def should_list_bundle_file(self, file_name: str):
        """Assert that the uploaded bundle was read and its file is listed in the editor."""
        expect(self.bundle_file_entry(file_name)).to_be_attached(timeout=15_000)
        return self

    @step("Verify no bundle ceiling warning is shown")
    def should_not_see_bundle_ceiling_warning(self):
        """Assert that no warning about the bundle's file count or size is shown."""
        expect(self.bundle_ceiling_warning).to_have_count(0)
        return self

    @step("Verify the bundle file count warning is shown")
    def should_see_bundle_file_count_warning(self, file_count: int, limit: int):
        """Assert that the warning names how many files exceed the limit, the limit, and what the limit means."""
        excess = file_count - limit
        expect(
            self.page.get_by_text(f"{excess} file(s) exceed the {limit}-file limit")
        ).to_be_visible(timeout=10_000)
        expect(self.bundle_ceiling_warning).to_contain_text(
            "These files will not be available in an assistant workspace"
        )
        return self

    # =============================================================================
    # IMPORT ERROR TOAST
    # =============================================================================

    @property
    def import_error_toast(self) -> Locator:
        """Error toast shown after a failed bundle import (inherited from BasePage)."""
        return self.error_toast

    @property
    def import_error_toast_header(self) -> Locator:
        """The heading (h2.codemie-toast-header) of the first error toast."""
        return self.error_toast.locator(".codemie-toast-header").first

    @step("Verify import error toast shows a user-friendly message")
    def should_see_import_error_toast(self):
        """Assert that a user-friendly error toast appeared after a failed bundle import.

        Verifies the heading is visible, does not contain the raw HTTP error string,
        and contains at least one known human-readable phrase from the backend.
        """
        expect(self.import_error_toast).to_be_visible(timeout=10_000)
        expect(self.import_error_toast_header).to_be_visible(timeout=10_000)
        expect(self.import_error_toast_header).not_to_contain_text("HTTP error")
        expect(self.import_error_toast_header).not_to_contain_text(
            re.compile(r"HTTP\s+error\s+400", re.I)
        )
        expect(self.import_error_toast_header).to_contain_text(
            re.compile(r"Invalid skill bundle|SKILL\.md|Oops", re.I)
        )
        return self

    # =============================================================================
    # BUILT-IN SUBAGENTS SECTION
    # =============================================================================

    @property
    def builtin_subagents_toggle(self) -> Locator:
        """Toggle switch for enabling General Purpose built-in subagent spawning."""
        return (
            self.page.get_by_role("switch", name="General Purpose")
            .or_(self.page.get_by_label("General Purpose"))
            .or_(self.page.locator('[data-testid="builtin-subagent-toggle"]'))
        ).first

    @property
    def builtin_subagents_section(self) -> Locator:
        """Built-in Subagents section container."""
        return self.page.locator(
            '[data-section="builtin-subagents"], '
            'section:has-text("Built-in Subagents"), '
            'div:has-text("Built-in Subagents")'
        ).first

    @step("Verify built-in subagent toggle is visible")
    def should_see_subagent_toggle(self):
        """Verify the General Purpose subagent toggle is visible on the skill settings page."""
        expect(self.builtin_subagents_toggle).to_be_visible(timeout=10000)
        return self

    @step("Toggle General Purpose subagent spawning")
    def toggle_subagent_spawning(self, enable: bool):
        """Enable or disable General Purpose subagent spawning.

        Args:
            enable: True to enable subagent spawning, False to disable it.
        """
        self.builtin_subagents_toggle.wait_for(state="visible")
        is_checked = self.builtin_subagents_toggle.is_checked()
        if enable and not is_checked:
            self.builtin_subagents_toggle.click()
            expect(self.builtin_subagents_toggle).to_be_checked(timeout=7500)
        elif not enable and is_checked:
            self.builtin_subagents_toggle.click()
            expect(self.builtin_subagents_toggle).not_to_be_checked(timeout=7500)
        return self

    @step("Verify built-in subagent setting value")
    def should_see_subagent_setting(self, value: bool):
        """Verify the current state of the General Purpose subagent toggle.

        Args:
            value: Expected state — True means enabled (checked), False means disabled.
        """
        if value:
            expect(self.builtin_subagents_toggle).to_be_checked(timeout=5000)
        else:
            expect(self.builtin_subagents_toggle).not_to_be_checked(timeout=5000)
        return self
