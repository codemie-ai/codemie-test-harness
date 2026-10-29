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

from time import sleep
from typing import Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.assistants.generate_with_ai_modal import (
    AIAssistantGeneratorPage,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.assistants.assistant_mcp_server import (
    AssistantMCPIntegrationModal,
)
from codemie_test_harness.tests.ui.pageobject.assistants.assistant_sidebar import (
    AssistantSidebar,
)
from codemie_test_harness.tests.ui.pageobject.assistants.tools_section import (
    ToolsSection,
)
from codemie_test_harness.tests.ui.pageobject.assistants.mcp_servers_section import (
    MCPServersSection,
)


class CreateEditAssistantPage(BasePage):
    """
    Create/Edit Assistant page object following Page Object Model (POM) best practices.

    This class encapsulates all interactions with the Create Assistant page,
    providing a clean interface for test automation while hiding implementation details.
    Updated with accurate locators based on real HTML structure.
    """

    page_url = "/assistants/new"

    def __init__(self, page):
        """Initialize the Create Assistant page object."""
        super().__init__(page)
        self.sidebar = AssistantSidebar(page)
        self.mcp = AssistantMCPIntegrationModal(page)
        self.ai_generator_modal = AIAssistantGeneratorPage(
            page
        )  # AI Assistant Generator modal
        self.tools = ToolsSection(page)
        self.mcp_servers = MCPServersSection(page)

    # =============================================================================
    # LOCATORS - Core Page Elements
    # =============================================================================

    @property
    def main_container(self) -> Locator:
        """Main page container"""
        return self.page.locator("main")

    @property
    def create_page_title(self) -> Locator:
        """Page title 'Create Assistant' element"""
        # h1 with class "text-lg text-text-primary font-semibold" confirmed in live UI
        return self.page.get_by_role("heading", name="Create Assistant", level=1)

    @property
    def edit_page_title(self) -> Locator:
        """Page title 'Edit Assistant' heading shown in edit mode"""
        return self.page.get_by_role("heading", name="Edit Assistant", level=1)

    @property
    def pinned_assistant_title(self) -> Locator:
        """Pinned assistant name subtitle shown below the Edit Assistant heading."""
        return self.edit_page_title.locator("xpath=following-sibling::div[1]")

    @property
    def generate_with_ai_button(self) -> Locator:
        """Generate with AI button in header with magical styling"""
        # Two "Generate with AI" buttons exist on the page: header + system instructions.
        # The header button is the first one rendered.
        return self.page.locator(
            'button.bg-magical-button:has-text("Generate with AI")'
        ).first

    @property
    def create_button(self) -> Locator:
        """Create button with plus icon (primary button)
        Note: In the redesigned UI the button label is 'Save' on create form too.
        This locator is kept for backward compat; prefer save_button.
        """
        return self.page.locator('button.bg-button-primary-bg:has-text("Create")')

    @property
    def save_button(self) -> Locator:
        """Save button (primary action button in header).
        Uses role-based locator scoped to the page header for reliability.
        The CSS class bg-button-primary-bg is present on other primary buttons too;
        using getByRole with exact name avoids false matches and is more stable.
        """
        return self.page.locator("div.min-h-layout-header").get_by_role(
            "button", name="Save", exact=True
        )

    @property
    def cancel_button(self) -> Locator:
        """Cancel button in header - class bg-surface-base-secondary"""
        return self.page.locator('button.bg-surface-base-secondary:has-text("Cancel")')

    @property
    def back_button(self) -> Locator:
        """Back button with arrow icon - identified by aria-label"""
        return self.page.locator('button[aria-label="Back"]')

    @property
    def skip_validation_save_button(self) -> Locator:
        """Save button with validation skip"""
        return self.page.locator("button:has-text('Skip Validation & Save')")

    @property
    def validation_save_button(self) -> Locator:
        """Save button with validation"""
        return self.page.locator("button:has-text('Validate & Save')")

    # =============================================================================
    # LOCATORS - Help Button and Panel
    # =============================================================================

    @property
    def help_button(self) -> Locator:
        """Help button in bottom right corner - has aria-label="Help", no visible text"""
        return self.page.locator('button[aria-label="Help"]')

    @property
    def help_panel_title(self) -> Locator:
        """Help panel title 'CodeMie Helper' - h3 element"""
        return self.page.get_by_role("heading", name="CodeMie Helper", level=3)

    @property
    def help_panel_description(self) -> Locator:
        """Help panel description text"""
        return self.page.get_by_text(
            "If you'd like to learn more or understand how it works in detail"
        )

    @property
    def help_panel_close_button(self) -> Locator:
        """Close button in help panel - has aria-label Close"""
        return self.page.locator(".w-96").get_by_role("button", name="Close")

    @property
    def help_create_assistant_button(self) -> Locator:
        """'How to create Assistant' button in help panel"""
        return self.page.get_by_role("button", name="How to create Assistant")

    @property
    def help_connect_tools_button(self) -> Locator:
        """'How to properly connect Tools' button in help panel"""
        return self.page.get_by_role("button", name="How to properly connect Tools")

    @property
    def help_connect_integrations_button(self) -> Locator:
        """'How to properly connect Integrations' button in help panel"""
        return self.page.get_by_role(
            "button", name="How to properly connect Integrations"
        )

    # =============================================================================
    # LOCATORS - Assistant Setup Section
    # =============================================================================

    @property
    def assistant_setup_section(self) -> Locator:
        """Assistant Setup section header - now an h1 (not h4) in the redesigned UI"""
        return self.page.get_by_role("heading", name="Assistant Setup", level=1)

    @property
    def project_selector(self) -> Locator:
        """Project name selector (PrimeReact multiselect)"""
        return self.page.locator("div#project-selector.p-multiselect")

    @property
    def shared_toggle(self) -> Locator:
        """'Shared with project' toggle switch - the outer label element is clickable"""
        return self.page.locator(
            'label:has(input.sr-only.peer):has-text("Shared with project")'
        )

    @property
    def shared_toggle_checkbox(self) -> Locator:
        """'Shared with project' checkbox input (sr-only, hidden) - use for checking state only.
        Reuses shared_toggle locator to avoid duplicating the parent selector, which makes
        this resilient to label text or class changes (only one place to update).
        """
        return self.shared_toggle.locator('input[type="checkbox"]')

    @property
    def attach_file_toggle(self) -> Locator:
        """'Enable file attachments' toggle switch - the outer label element is clickable.

        Controls whether users chatting with this assistant see an active
        Attach File control in the chat composer.
        Follows the same sr-only-checkbox toggle pattern as `shared_toggle`.
        """
        return self.page.locator(
            'label:has(input.sr-only.peer):has-text("Enable file attachments")'
        )

    @property
    def attach_file_toggle_checkbox(self) -> Locator:
        """'Enable file attachments' checkbox input (sr-only, hidden) - use for checking state only.
        Reuses attach_file_toggle locator to avoid duplicating the parent selector, which makes
        this resilient to label text or class changes (only one place to update).
        """
        return self.attach_file_toggle.locator('input[type="checkbox"]')

    @property
    def hide_tool_outputs_switch(self) -> Locator:
        """'Hide tool outputs from end users' switch (input[role='switch']).

        Rendered by ToolOutputVisibilitySection inside the Tools header row.
        The accessible name is the label text; the Switch also
        renders a hint tooltip button inside the same label, so the name is
        matched as a substring.
        """
        return self.page.get_by_role("switch", name="Hide tool outputs from end users")

    def tool_output_visibility_note(self, text: str) -> Locator:
        """Screen-reader status node (role=status) that carries a tooltip's text.

        TooltipButton renders its content twice: as the hover tooltip and as an
        always-present `role="status"` sr-only node. The status node is the stable
        DOM anchor for the helper hint (always rendered) and for the 'applies to
        everyone including you' note (rendered only while the switch is ON).
        """
        return self.page.get_by_role("status").filter(has_text=text)

    @property
    def file_attachments_accordion_header(self) -> Locator:
        """PrimeReact accordion header for the collapsed 'File attachments' section.

        The 'Enable file attachments' toggle lives inside this collapsed accordion
        panel. Confirmed via live DOM inspection: the header is rendered as
        `a.p-accordion-header-link` containing an `h1` with text "File attachments"
        (same pattern as `skills_accordion_header`). While collapsed
        (`aria-expanded="false"`), the header's own subtree intercepts pointer
        events aimed at the hidden toggle underneath, causing Playwright click
        timeouts — the accordion must be expanded first.
        """
        return self.page.locator(
            'a.p-accordion-header-link:has(h1:text-is("File attachments"))'
        )

    @property
    def name_input(self) -> Locator:
        """Assistant name input field.
        Note: placeholder text may vary across UI versions, so we match by
        name attribute only for stability.
        """
        return self.page.locator('input[name="name"]')

    @property
    def slug_input(self) -> Locator:
        """Assistant slug input field.
        Note: Moved to 'Extra configuration' accordion in the redesigned UI.
        The accordion must be expanded before this locator resolves.
        """
        return self.page.locator(
            'input[name="slug"][placeholder="Unique human-readable identifier"]'
        )

    @property
    def icon_url_input(self) -> Locator:
        """Assistant icon URL input field.
        Note: placeholder changed in redesign from 'URL to the assistant's icon'
        to 'https://example.com/logo.jpg'. Identified by name attribute.
        """
        return self.page.locator('input[name="icon_url"]')

    @property
    def description_textarea(self) -> Locator:
        """Assistant description textarea"""
        return self.page.locator(
            'textarea[name="description"][placeholder="Description*"]'
        )

    @property
    def categories_dropdown(self) -> Locator:
        """Categories selection multiselect dropdown - identified by aria-label in redesigned UI"""
        return self.page.locator('div.p-multiselect[aria-label="Categories"]')

    @property
    def conversation_starters_label(self) -> Locator:
        """Conversation starters label - plain text node, not a <label> element in redesigned UI"""
        return self.page.locator('text="Conversation starters"')

    @property
    def conversation_starters_input(self) -> Locator:
        """Conversation starters input field"""
        return self.page.locator('input[name="conversation_starters"]')

    @property
    def add_conversation_starter_button(self) -> Locator:
        """Add conversation starter button - aria-label: Add conversation starter"""
        return self.page.locator('button[aria-label="Add conversation starter"]')

    @property
    def delete_conversation_starter_button(self) -> Locator:
        """Delete conversation starter button - aria-label: Delete"""
        return self.page.locator('button[aria-label="Delete"]')

    @property
    def name_error_message(self):
        """Name field error message - rendered as role=alert"""
        return self.page.locator(
            'div.input-field-wrapper:has(input[name="name"]) div[role="alert"]'
        )

    @property
    def icon_error_message(self):
        """Icon field error message - rendered as role=alert"""
        return self.page.locator(
            'div.input-field-wrapper:has(input[name="icon_url"]) div[role="alert"]'
        )

    @property
    def description_error_message(self):
        """Description field error message - rendered as role=alert with error classes"""
        return self.page.locator(
            'div:has(textarea[name="description"]) div[role="alert"].text-text-error.text-sm'
        )

    @property
    def system_prompt_error_message(self):
        """System prompt field error message - class: text-text-error text-sm"""
        return self.page.locator(
            'div:has(textarea[placeholder="System Instructions*"]) div.text-text-error.text-sm'
        )

    @property
    def temperature_error_message(self):
        """Temperature field error message - div[role=alert] rendered by FieldAnnouncer as
        a sibling of the input's wrapper inside the shared .input-field-wrapper ancestor"""
        return self.page.locator(
            'div.input-field-wrapper:has(input[name="temperature"]) div[role="alert"]'
        )

    @property
    def top_p_error_message(self):
        """Top P field error message - div[role=alert] rendered by FieldAnnouncer as
        a sibling of the input's wrapper inside the shared .input-field-wrapper ancestor"""
        return self.page.locator(
            'div.input-field-wrapper:has(input[name="top_p"]) div[role="alert"]'
        )

    # =============================================================================
    # LOCATORS - System Instructions (part of Assistant Setup accordion in redesigned UI)
    # NOTE: "Behavior & Logic" section has been REMOVED in the UI redesign.
    # System Instructions are now inside the "Assistant Setup" accordion.
    # LLM model, Temperature, Top P, and Slug are inside "Extra configuration" accordion.
    # =============================================================================

    @property
    def system_instructions_label(self) -> Locator:
        """System Instructions label - now a <p> with class 'text-sm font-mono text-text-quaternary'"""
        return self.page.locator(
            'p.text-sm.font-mono.text-text-quaternary:has-text("System Instructions")'
        )

    @property
    def system_prompt_textarea(self) -> Locator:
        """System instructions textarea"""
        return self.page.locator('textarea[placeholder="System Instructions*"]')

    @property
    def generate_with_ai_system_instructions_button(self) -> Locator:
        """Generate with AI button scoped to the System Instructions row (second magical button)"""
        return (
            self.page.locator('p.text-sm.font-mono:has-text("System Instructions")')
            .locator("..")
            .locator('button.bg-magical-button:has-text("Generate with AI")')
        )

    @property
    def expand_system_prompt_button(self) -> Locator:
        """Expand system prompt button - class bg-surface-base-secondary"""
        return self.page.locator('button.bg-surface-base-secondary:has-text("Expand")')

    @property
    def current_user_prompt_var_button(self) -> Locator:
        """Current User prompt variable button"""
        return self.page.locator(
            'button.cursor-pointer.font-mono.font-semibold:has-text("Current User")'
        )

    @property
    def date_prompt_var_button(self) -> Locator:
        """Date prompt variable button"""
        return self.page.locator(
            'button.cursor-pointer.font-mono.font-semibold:has-text("Date")'
        )

    @property
    def manage_prompt_vars_button(self) -> Locator:
        """Manage Prompt Vars button"""
        return self.page.locator(
            'button.bg-button-primary-bg:has-text("Manage Prompt Vars")'
        )

    # =============================================================================
    # LOCATORS - Manage Prompt Variables Modal
    # =============================================================================

    @property
    def manage_prompt_vars_modal(self) -> Locator:
        """Manage Prompt Variables modal dialog"""
        return self.page.get_by_role("dialog", name="Manage Prompt Variables")

    @property
    def manage_prompt_vars_modal_heading(self) -> Locator:
        """Manage Prompt Variables modal heading"""
        return self.page.get_by_role("heading", name="Manage Prompt Variables", level=4)

    @property
    def add_variable_button(self) -> Locator:
        """Add variable button in prompt variables modal"""
        return self.page.get_by_role("button", name="Add variable")

    @property
    def prompt_var_key_input(self) -> Locator:
        """Key input field for prompt variable"""
        return self.page.get_by_placeholder("e.g., project_name")

    @property
    def prompt_var_default_value_input(self) -> Locator:
        """Default value input field for prompt variable"""
        return self.page.get_by_role("textbox", name="Default value")

    @property
    def prompt_var_description_input(self) -> Locator:
        """Description input field for prompt variable"""
        return self.page.get_by_placeholder("What does this variable represent?")

    @property
    def prompt_var_sensitive_checkbox(self) -> Locator:
        """Sensitive variable checkbox"""
        return self.page.get_by_role(
            "checkbox",
            name="Sensitive Variable (Contains secrets like API keys or passwords)",
        )

    @property
    def prompt_var_add_button(self) -> Locator:
        """Add button in prompt variable form - filters to get the last 'Add' button"""
        # There are two "Add" buttons: "Add variable" and "Add" (to save the variable)
        # We want the second one, so we use .last
        return self.manage_prompt_vars_modal.get_by_role("button", name="Add").last

    @property
    def prompt_var_cancel_button(self) -> Locator:
        """Cancel button in prompt variable form"""
        return self.manage_prompt_vars_modal.get_by_role("button", name="Cancel")

    @property
    def manage_prompt_vars_close_button(self) -> Locator:
        """Close button for Manage Prompt Variables modal"""
        return self.manage_prompt_vars_modal.get_by_role("button", name="Close")

    # =============================================================================
    # LOCATORS - Extra Configuration accordion (LLM model, temperature, top_p, slug)
    # NOTE: These fields moved from "Behavior & Logic" to "Extra configuration" accordion.
    # The accordion must be expanded before these locators resolve.
    # =============================================================================

    @property
    def extra_configuration_accordion(self) -> Locator:
        """Extra configuration accordion button - expands to show LLM model, temp, top_p, slug"""
        return self.page.get_by_role("button", name="Extra configuration")

    @property
    def context_data_sources_accordion(self) -> Locator:
        """Context & Data Sources accordion button"""
        return self.page.get_by_role("button", name="Context & Data Sources")

    @property
    def llm_model_dropdown(self) -> Locator:
        """LLM model selection dropdown - PrimeReact multiselect with aria-label 'LLM model'
        Note: Requires 'Extra configuration' accordion to be expanded first.
        """
        return self.page.locator('div.p-multiselect[aria-label="LLM model"]')

    @property
    def temperature_input(self) -> Locator:
        """Temperature input field.
        Locator is model-agnostic: placeholder varies by model (e.g. '0-2' for GPT, '0-1' for Claude).
        Use should_have_temperature_placeholder() to assert the rendered placeholder separately.
        Note: Requires 'Extra configuration' accordion to be expanded first.
        """
        return self.page.locator('input[name="temperature"]')

    @property
    def top_p_input(self) -> Locator:
        """Top P input field (0-1 range).
        Note: Requires 'Extra configuration' accordion to be expanded first.
        """
        return self.page.locator('input[name="top_p"][placeholder="0-1"]')

    @property
    def tools_tokens_size_limit_input(self) -> Locator:
        """Tools Tokens Size Limit input field (positive integer).
        Note: Requires 'Extra configuration' accordion to be expanded first.
        """
        return self.page.locator(
            'input[name="tools_tokens_size_limit"][placeholder="30000"]'
        )

    # ==================== Context & Data Sources Section ====================
    @property
    def context_data_sources_section(self) -> Locator:
        """Context & Data Sources section header - now an h1 in the redesigned UI"""
        return self.page.get_by_role("heading", name="Context & Data Sources", level=1)

    @property
    def datasource_context_label(self):
        """Label 'Datasource Context' above the dropdown."""
        return (
            self.page.locator("#context-selector")
            .locator("xpath=../..")
            .get_by_text("Datasource Context")
        )

    @property
    def datasource_context_add_button(self):
        """'Create' button next to the Datasource Context label.
        Note: button label changed from 'Add' to 'Create' in the redesigned UI.
        """
        return self.page.locator(
            'div:has(div:has-text("Datasource Context")) button:has-text("Create")'
        ).first

    @property
    def datasource_context_dropdown(self):
        """Datasource Context dropdown - id='context-selector' is preserved in the redesign."""
        return self.page.locator("#context-selector")

    @property
    def datasource_context_dropdown_label(self):
        """The visible label text inside the datasource context dropdown."""
        return self.datasource_context_dropdown.locator(".p-multiselect-label")

    # ==================== Sub-Assistant Context ====================
    @property
    def sub_assistants_label(self):
        """Label 'Sub-Assistants' above the sub assistants dropdown."""
        return (
            self.page.locator('div.p-multiselect[aria-label="Select Sub-Assistants"]')
            .locator("xpath=../..")
            .get_by_text("Sub-Assistants")
            .first
        )

    @property
    def sub_assistants_dropdown(self):
        """Sub Assistants dropdown - identified by aria-label in the redesigned UI."""
        return self.page.locator(
            'div.p-multiselect[aria-label="Select Sub-Assistants"]'
        )

    @property
    def sub_assistants_dropdown_label(self):
        """The label inside the sub assistants dropdown."""
        return self.sub_assistants_dropdown.locator("div.p-multiselect-label")

    # ======= Skills Section =======

    @property
    def skills_section(self) -> Locator:
        """Skills section header - now an h1 in the redesigned UI"""
        return self.page.get_by_role("heading", name="Skills", level=1)

    @property
    def skills_accordion_header(self) -> Locator:
        """PrimeReact accordion header for the Skills section"""
        return self.page.locator('a.p-accordion-header-link:has(h1:text-is("Skills"))')

    @property
    def skills_description(self) -> Locator:
        """Skills section description paragraph"""
        return self.page.locator(
            'p:has-text("Add specialized knowledge and expertise to your assistant.")'
        )

    @property
    def skills_add_button(self) -> Locator:
        """Add button inside the Skills accordion panel.
        The button appears next to a 'Skills' label (div.text-xs.text-text-quaternary)
        inside the expanded Skills accordion content area.
        """
        return self.page.locator(
            'div.text-xs.text-text-quaternary:has-text("Skills") ~ button:has-text("Add")'
        )

    @property
    def skills_dropdown(self) -> Locator:
        """Skills selection dropdown - PrimeReact multiselect with aria-label 'Select skills'"""
        return self.page.locator('div.p-multiselect[aria-label="Select skills"]')

    @property
    def skills_info_text(self) -> Locator:
        """Skills info text about limit"""
        return self.page.locator(
            'text="Choose up to 10 skills to enhance your assistant."'
        )

    def attached_skill(self, skill_name: str) -> Locator:
        """Get attached skill element by name - checks dropdown label text"""
        # Skills appear as tokens or text in the p-multiselect-label container
        return self.skills_dropdown.locator(".p-multiselect-label").filter(
            has_text=skill_name
        )

    def skill_remove_button(self, skill_name: str) -> Locator:
        """Get remove button for attached skill"""
        return self.attached_skill(skill_name).locator('button[aria-label="Remove"]')

    @step
    def expand_skills_section(self):
        """Expand the Skills accordion section if it is not already expanded."""
        header = self.skills_accordion_header
        is_expanded = header.get_attribute("aria-expanded") == "true"
        if not is_expanded:
            header.click()
            self.page.wait_for_timeout(300)
        return self

    @step
    def expand_file_attachments_section(self):
        """Expand the 'File attachments' accordion section if not already expanded.

        Must be called before reading or clicking `attach_file_toggle` /
        `attach_file_toggle_checkbox` — the toggle is rendered inside this
        collapsed accordion panel, and while collapsed the header intercepts
        pointer events aimed at the toggle underneath, causing Playwright's
        click actionability check to time out.
        """
        header = self.file_attachments_accordion_header
        is_expanded = header.get_attribute("aria-expanded") == "true"
        if not is_expanded:
            header.click()
        expect(self.attach_file_toggle).to_be_visible()
        return self

    # ==================== NAVIGATION METHODS ====================

    @step
    def navigate_to(self):
        """
        Navigate to the Create Assistant page.

        Returns:
            self: Returns the page object for method chaining
        """
        self.page.goto(self.page_url)
        self.wait_for_page_load()

        if self.is_ai_generator_modal_visible():
            self.ai_generator_modal.click_create_manually()
            self.ai_generator_modal.modal_container.wait_for(
                state="hidden", timeout=5000
            )

        return self

    @step
    def expand_extra_configuration(self):
        """
        Expand the 'Extra configuration' accordion to reveal Slug, LLM model,
        Temperature, and Top P fields.

        In the redesigned UI these fields moved from the top-level form into a
        collapsible 'Extra configuration' accordion inside 'Assistant Setup'.

        Returns:
            self: Returns the page object for method chaining
        """
        accordion = self.extra_configuration_accordion
        if accordion.get_attribute("aria-expanded") != "true":
            accordion.click()
            self.temperature_input.wait_for(state="visible", timeout=5000)
        return self

    @step
    def expand_context_data_sources(self):
        """
        Expand the 'Context & Data Sources' accordion to reveal datasource context
        and sub-assistants fields.

        This accordion is collapsed by default and must be expanded before accessing
        datasource_context_label, datasource_context_dropdown, sub_assistants_dropdown, etc.

        Returns:
            self: Returns the page object for method chaining
        """
        accordion_button = self.context_data_sources_accordion
        if accordion_button.get_attribute("aria-expanded") != "true":
            accordion_button.click()
            self.datasource_context_dropdown.wait_for(state="visible", timeout=5000)
        return self

    # ==================== HELP PANEL METHODS ====================

    @step
    def click_help_button(self):
        """Click the help button in bottom right corner"""
        self.help_button.click()
        # Wait for help panel to appear
        expect(self.help_panel_title).to_be_visible()
        return self

    @step
    def close_help_panel(self):
        """Close the help panel"""
        self.help_panel_close_button.click()
        # Wait for help panel to disappear
        expect(self.help_panel_title).to_be_hidden()
        return self

    @step
    def should_have_help_button_visible(self):
        """Verify that the help button is visible in bottom right corner"""
        expect(self.help_button).to_be_visible()
        return self

    @step
    def should_have_help_panel_visible(self):
        """Verify that the help panel is visible with all elements"""
        expect(self.help_panel_title).to_be_visible()
        expect(self.help_panel_description).to_be_visible()
        expect(self.help_panel_close_button).to_be_visible()
        expect(self.help_create_assistant_button).to_be_visible()
        expect(self.help_connect_tools_button).to_be_visible()
        expect(self.help_connect_integrations_button).to_be_visible()
        return self

    # ==================== AI GENERATOR MODAL METHODS ====================

    @step
    def is_ai_generator_modal_visible(self) -> bool:
        """
        Check if the AI Assistant Generator modal is currently visible.
        Waits up to 2s for the modal to appear (it may open with a short delay after page load).

        Returns:
            bool: True if modal is visible, False otherwise
        """
        try:
            self.ai_generator_modal.modal_container.wait_for(
                state="visible", timeout=2000
            )
            return True
        except PlaywrightTimeoutError:
            return False

    @step
    def close_ai_generator_modal(self):
        """
        Close the AI Assistant Generator modal if it's visible.

        Returns:
            self: Returns the page object for method chaining
        """
        if self.is_ai_generator_modal_visible():
            self.ai_generator_modal.close_modal()
        return self

    @step
    def verify_ai_generator_modal_visible(self):
        """
        Verify that the AI Assistant Generator modal is visible with correct structure.

        Returns:
            self: Returns the page object for method chaining
        """
        assert self.is_ai_generator_modal_visible(), (
            "AI Assistant Generator modal should be visible"
        )

        # Verify modal structure using updated methods
        self.ai_generator_modal.verify_modal_title()
        self.ai_generator_modal.verify_description_text()
        self.ai_generator_modal.verify_prompt_label()
        self.ai_generator_modal.verify_note_text()

        return self

    @step
    def verify_ai_generator_modal_not_visible(self):
        """
        Verify that the AI Assistant Generator modal is not visible.

        Returns:
            self: Returns the page object for method chaining
        """
        assert not self.is_ai_generator_modal_visible(), (
            "AI Assistant Generator modal should not be visible"
        )
        return self

    @step
    def create_manually_from_ai_modal(self):
        """
        Click 'Create Manually' from the AI Generator modal to proceed with manual creation.

        Returns:
            self: Returns the page object for method chaining
        """
        if self.is_ai_generator_modal_visible():
            self.ai_generator_modal.click_create_manually()
            self.ai_generator_modal.modal_container.wait_for(
                state="hidden", timeout=5000
            )
        return self

    @step
    def generate_with_ai_from_modal(
        self,
        description: str,
        include_tools: bool = True,
        do_not_show_again: bool = False,
    ):
        """
        Use the AI Generator modal to create an assistant with AI.

        Args:
            description: Description of the assistant to generate
            include_tools: Whether to include tools in the assistant
            do_not_show_again: Whether to check 'do not show popup' option

        Returns:
            self: Returns the page object for method chaining
        """
        if self.is_ai_generator_modal_visible():
            self.ai_generator_modal.complete_ai_generation_workflow(
                prompt=description,
                include_tools=include_tools,
                dont_show_again=do_not_show_again,
            )
        return self

    # ==================== FORM INTERACTION METHODS ====================

    @step
    def fill_name(self, name: str):
        """
        Fill the assistant name field.

        Args:
            name: The name for the assistant

        Returns:
            self: Returns the page object for method chaining
        """
        self.name_input.clear()
        self.name_input.fill(name)
        return self

    @step
    def fill_description(self, description: str):
        """
        Fill the assistant description field.

        Args:
            description: The description for the assistant

        Returns:
            self: Returns the page object for method chaining
        """
        self.description_textarea.clear()
        self.description_textarea.fill(description)
        return self

    @step
    def fill_system_prompt(self, prompt: str):
        """
        Fill the system prompt field.

        Args:
            prompt: The system prompt text

        Returns:
            self: Returns the page object for method chaining
        """
        self.system_prompt_textarea.clear()
        self.system_prompt_textarea.fill(prompt)
        return self

    @step
    def fill_icon_url(self, icon_url: str):
        """
        Fill the icon URL field and trigger validation by moving focus away.

        Args:
            icon_url: The URL for the assistant icon

        Returns:
            self: Returns the page object for method chaining
        """
        self.icon_url_input.clear()
        self.icon_url_input.fill(icon_url)
        # Press Tab to move focus away and trigger blur-based validation
        self.icon_url_input.press("Tab")
        return self

    @step
    def fill_slug(self, slug: str):
        """
        Fill the slug field.
        Note: Slug is inside 'Extra configuration' accordion in the redesigned UI.
        This method auto-expands the accordion if needed.

        Args:
            slug: The unique identifier for the assistant

        Returns:
            self: Returns the page object for method chaining
        """
        self.expand_extra_configuration()
        self.slug_input.clear()
        self.slug_input.fill(slug)
        return self

    @step
    def toggle_shared_assistant(self, shared: bool = True):
        """
        Toggle the shared/public setting for the assistant.

        Args:
            shared: Whether the assistant should be shared (True) or private (False)

        Returns:
            self: Returns the page object for method chaining
        """
        # Check current state using the hidden checkbox and toggle if needed by clicking the label
        is_currently_checked = self.shared_toggle_checkbox.is_checked()
        if (shared and not is_currently_checked) or (
            not shared and is_currently_checked
        ):
            self.shared_toggle.click()
        return self

    @step
    def toggle_attach_file_setting(self, enabled: bool = True):
        """
        Toggle whether users can attach files when chatting with this assistant.

        Args:
            enabled: True to allow file attachments (default), False to disable
                the Attach File control for chat users of this assistant.

        Returns:
            self: Returns the page object for method chaining
        """
        # The toggle lives inside the collapsed "File attachments" accordion
        # panel; it must be expanded first or the collapsed header intercepts
        # the click meant for the toggle underneath.
        self.expand_file_attachments_section()
        is_currently_checked = self.attach_file_toggle_checkbox.is_checked()
        if (enabled and not is_currently_checked) or (
            not enabled and is_currently_checked
        ):
            self.attach_file_toggle.click()
        return self

    # Mapping from ModelTypes enum values to their display labels in the LLM model dropdown.
    # Used by select_llm_model() to search the PrimeReact multiselect by display name.
    _LLM_MODEL_DISPLAY_NAMES: dict = {
        "claude-sonnet-4-6": "Bedrock Claude Sonnet 4.6",
        "claude-sonnet-4-6-vertex": "VertexAI Claude Sonnet 4.6",
        "claude-4-5-sonnet": "Bedrock Claude 4.5 Sonnet",
        "claude-4-5-sonnet-vertex": "VertexAI Claude Sonnet 4.5",
        "claude-sonnet-5": "Bedrock Claude Sonnet 5",
        "claude-opus-4-6-20260205": "Bedrock Claude Opus 4.6",
        "claude-opus-4-6-vertex": "VertexAI Claude Opus 4.6",
    }

    @step
    def select_llm_model(self, model_value: str):
        """
        Select an LLM model in the Extra configuration accordion.
        Expands the accordion if needed, then searches the PrimeReact multiselect
        by the model's display label and clicks it.

        Args:
            model_value: ModelTypes enum value string (e.g. 'claude-sonnet-4-6')

        Returns:
            self: Returns the page object for method chaining
        """
        self.expand_extra_configuration()
        # Open the dropdown
        combobox = self.llm_model_dropdown.locator('input[role="combobox"]')
        if combobox.get_attribute("aria-expanded") != "true":
            self.llm_model_dropdown.click()
            self.page.wait_for_timeout(300)

        # Derive display label
        display_name = self._LLM_MODEL_DISPLAY_NAMES.get(model_value, model_value)

        # Search in the filter input
        filter_input = self.page.locator('input[role="searchbox"]').first
        filter_input.wait_for(state="visible", timeout=5000)
        filter_input.fill(display_name)
        self.page.wait_for_timeout(300)

        # Click the matching option
        option = (
            self.page.locator(".p-multiselect-item").filter(has_text=display_name).first
        )
        option.wait_for(state="visible", timeout=5000)
        option.click()

        # Close the dropdown by clicking the page header (neutral area)
        self.page.locator("div.min-h-layout-header").click()
        self.page.wait_for_timeout(300)
        return self

    @step
    def fill_temperature(self, temperature: str):
        """
        Fill the temperature field.
        Note: Temperature is inside 'Extra configuration' accordion in the redesigned UI.
        This method auto-expands the accordion if needed.

        Args:
            temperature: Temperature value (0-2)

        Returns:
            self: Returns the page object for method chaining
        """
        self.expand_extra_configuration()
        self.temperature_input.clear()
        self.temperature_input.fill(temperature)
        return self

    @step
    def fill_top_p(self, top_p: str):
        """
        Fill the Top P field.
        Note: Top P is inside 'Extra configuration' accordion in the redesigned UI.
        This method auto-expands the accordion if needed.

        Args:
            top_p: Top P value (0-1)

        Returns:
            self: Returns the page object for method chaining
        """
        self.expand_extra_configuration()
        self.top_p_input.clear()
        self.top_p_input.fill(top_p)
        return self

    @step
    def fill_tools_tokens_size_limit(self, value: str):
        """
        Fill the Tools Tokens Size Limit field.
        Note: Field is inside 'Extra configuration' accordion in the redesigned UI.
        This method auto-expands the accordion if needed.
        Pass empty string to clear the field (means no limit).

        Args:
            value: Positive integer as string (e.g. "30000"), or "" to clear

        Returns:
            self: Returns the page object for method chaining
        """
        self.expand_extra_configuration()
        self.tools_tokens_size_limit_input.clear()
        self.tools_tokens_size_limit_input.fill(value)
        return self

    @step
    def should_have_tools_tokens_size_limit(self, expected: str):
        """
        Assert the current value of the Tools Tokens Size Limit field.
        Note: Auto-expands 'Extra configuration' accordion if needed.

        Args:
            expected: Expected value string (e.g. "30000" or "" for empty)

        Returns:
            self: Returns the page object for method chaining
        """
        self.expand_extra_configuration()
        expect(self.tools_tokens_size_limit_input).to_have_value(expected)
        return self

    @step
    def click_manage_prompt_vars(self):
        """
        Click the Manage Prompt Vars button to open the modal.

        Returns:
            self: Returns the page object for method chaining
        """
        self.manage_prompt_vars_button.click()
        # Wait for modal to be visible
        expect(self.manage_prompt_vars_modal).to_be_visible()
        return self

    @step
    def add_prompt_variable(
        self,
        key: str,
        default_value: str = "",
        description: str = "",
        is_sensitive: bool = False,
    ):
        """
        Add a custom prompt variable in the Manage Prompt Variables modal.
        Assumes the modal is already open.

        Args:
            key: Variable key/name (e.g., "ticket_id")
            default_value: Default value for the variable
            description: Description of what the variable represents
            is_sensitive: Whether to mark the variable as sensitive

        Returns:
            self: Returns the page object for method chaining
        """
        # Click Add variable button to show the form
        self.add_variable_button.click()

        # Fill in the key field
        self.prompt_var_key_input.fill(key)

        # Fill in default value if provided
        if default_value:
            self.prompt_var_default_value_input.fill(default_value)

        # Fill in description if provided
        if description:
            self.prompt_var_description_input.fill(description)

        # Check sensitive checkbox if needed
        if is_sensitive:
            self.prompt_var_sensitive_checkbox.check()

        # Wait for Add button to be enabled (it's disabled until required fields are filled)
        expect(self.prompt_var_add_button).to_be_enabled()

        # Click Add button to save the variable
        self.prompt_var_add_button.click()

        return self

    @step
    def close_manage_prompt_vars_modal(self):
        """
        Close the Manage Prompt Variables modal.

        Returns:
            self: Returns the page object for method chaining
        """
        self.manage_prompt_vars_close_button.click()
        # Wait for modal to be hidden
        expect(self.manage_prompt_vars_modal).not_to_be_visible()
        return self

    # ==================== ACTION METHODS ====================

    @step
    def click_create(self):
        """
        Click the Save/Create button to create the assistant.
        Uses Save button if available (create mode), otherwise Create button.

        Returns:
            self: Returns the page object for method chaining
        """
        # Try Save button first (used in create mode), fallback to Create button
        if self.save_button.count() > 0:
            self.save_button.click()
        else:
            self.create_button.click()
        return self

    @step
    def click_save(self):
        """
        Click the Create button to create the assistant.

        Returns:
            self: Returns the page object for method chaining
        """
        self.save_button.click()
        return self

    @step
    def click_cancel(self):
        """
        Click the Cancel button to abort assistant creation.

        Returns:
            self: Returns the page object for method chaining
        """
        self.cancel_button.click()
        return self

    @step
    def click_back(self):
        """
        Click the Back button to return to assistants list.

        Returns:
            self: Returns the page object for method chaining
        """
        self.back_button.click()
        return self

    @step
    def click_save_with_validation_skip(self):
        """
        Click the 'Skip Validation & Save' button in the validation dialog.

        NOTE: locator.is_visible(timeout=N) is deprecated and DOES NOT wait — it
        returns immediately. Use wait_for(state='visible', timeout=N) instead,
        which actively polls until the element appears or the timeout expires.

        Returns:
            self: Returns the page object for method chaining
        """
        self.skip_validation_save_button.wait_for(state="visible", timeout=15000)
        self.skip_validation_save_button.click()
        return self

    @step
    def click_save_with_validation(self):
        """
        Click the Save button with validation to create the assistant.

        Returns:
            self: Returns the page object for method chaining
        """
        self.validation_save_button.click()
        return self

    @step
    def click_generate_with_ai_header(self):
        """
        Click the Generate with AI button in the header.

        Returns:
            self: Returns the page object for method chaining
        """
        self.generate_with_ai_button.click()
        return self

    # ==================== SKILLS ATTACHMENT METHODS ====================

    @step
    def attach_skill(self, skill_name: str):
        """
        Attach a skill to the assistant.

        Args:
            skill_name: Name of the skill to attach

        Returns:
            self: Returns the page object for method chaining
        """
        # Expand the Skills accordion section first
        self.expand_skills_section()

        # Check if dropdown is already expanded
        combobox = self.skills_dropdown.locator('input[role="combobox"]')
        is_expanded = combobox.get_attribute("aria-expanded") == "true"

        # Only click to open if not already expanded
        if not is_expanded:
            self.skills_dropdown.click()
            self.page.wait_for_timeout(500)

        # Look for the filter/search input in the dropdown panel
        # PrimeReact puts it in a separate input with placeholder
        filter_input = self.page.locator(
            'input[role="searchbox"][placeholder*="search" i], input[role="searchbox"][placeholder*="filter" i]'
        ).first

        filter_input.fill(skill_name)
        self.page.wait_for_timeout(300)

        # Find the specific option role element for this skill in the dropdown
        # After filtering/typing, the skill should be visible in the dropdown
        skill_option = self.page.get_by_role("option").filter(has_text=skill_name)

        if skill_option.count() > 0:
            skill_option.first.click()
            self.page.wait_for_timeout(500)

        # The dropdown should remain open for multi-select, no need to close it

        return self

    @step
    def detach_skill(self, skill_name: str):
        """
        Remove/detach a skill from the assistant.

        Args:
            skill_name: Name of the skill to remove

        Returns:
            self: Returns the page object for method chaining
        """
        # Expand the Skills accordion section first
        self.expand_skills_section()

        # Check if dropdown is already expanded
        combobox = self.skills_dropdown.locator('input[role="combobox"]')
        is_expanded = combobox.get_attribute("aria-expanded") == "true"

        # Only click to open if not already expanded
        if not is_expanded:
            self.skills_dropdown.click()
            self.page.wait_for_timeout(500)

        # Look for the filter/search input in the dropdown panel
        # PrimeReact puts it in a separate input with placeholder
        filter_input = self.page.locator(
            'input[role="searchbox"][placeholder*="search" i], input[role="searchbox"][placeholder*="filter" i]'
        ).first

        filter_input.fill(skill_name)
        self.page.wait_for_timeout(300)

        # Find the skill option (which should be selected) and click it to deselect
        # Use role="option" to target the actual dropdown options
        skill_option = self.page.get_by_role("option").filter(has_text=skill_name)

        if skill_option.count() > 0:
            skill_option.first.click()
            self.page.wait_for_timeout(500)

        self.page.locator("div.min-h-layout-header").click()
        self.page.wait_for_timeout(300)

        return self

    @step
    def should_show_selected_skill_name(self, skill_name: str):
        """
        Verify the Skills field renders the attached skill by its real name
        (and never as the literal text "null").

        Args:
            skill_name: Expected name of the attached skill

        Returns:
            self: Returns the page object for method chaining
        """
        self.expand_skills_section()
        label = self.skills_dropdown.locator(".p-multiselect-label")
        expect(label).to_contain_text(skill_name)
        expect(label).not_to_contain_text("null")
        return self

    @step
    def should_have_skills_section_visible(self):
        """
        Verify that the Skills section is visible.

        Returns:
            self: Returns the page object for method chaining
        """
        expect(self.skills_section).to_be_visible()
        expect(self.skills_description).to_be_visible()
        self.expand_skills_section()
        expect(self.skills_dropdown).to_be_visible()
        return self

    # ==================== COMPREHENSIVE ASSISTANT CREATION METHOD ====================

    @step
    def create_assistant(
        self,
        name: str,
        description: str,
        system_prompt: str,
        icon_url: Optional[str] = None,
        shared: bool = False,
        temperature: Optional[str] = None,
        top_p: Optional[str] = None,
    ):
        """
        Complete assistant creation workflow with all required parameters.

        This method encapsulates the entire assistant creation process,
        following the critical happy path scenario outlined in the requirements.

        Args:
            name: Assistant name (required)
            description: Assistant description (required)
            system_prompt: System prompt for the assistant (required)
            slug: Optional unique identifier for the assistant
            icon_url: Optional icon URL for the assistant
            shared: Whether to make the assistant shared/public (default: False)
            temperature: Optional temperature value (0-2)
            top_p: Optional Top P value (0-1)

        Returns:
            self: Returns the page object for method chaining
        """
        # Fill essential required fields
        self.fill_name(name)
        self.fill_description(description)
        self.fill_system_prompt(system_prompt)

        # Fill optional fields if provided
        # if icon_url:
        #     self.fill_icon_url(icon_url)
        # if temperature:
        #     self.fill_temperature(temperature)
        # if top_p:
        #     self.fill_top_p(top_p)

        # Set sharing preference
        self.toggle_shared_assistant(shared)

        # Submit the form
        self.click_create()

        return self

    # ==================== VERIFICATION METHODS ====================

    @step
    def should_be_on_create_assistant_page(self):
        """Verify that we are on the Create Assistant page."""
        expect(self.create_page_title).to_be_visible()
        expect(self.page).to_have_url(f"{self.page_url}")
        return self

    @step
    def should_have_pinned_title(self, expected_name: str):
        """Verify the pinned assistant name subtitle under 'Assistant Details' heading."""
        expect(self.pinned_assistant_title).to_be_visible()
        expect(self.pinned_assistant_title).to_have_text(expected_name)
        return self

    @step
    def should_have_all_form_fields_visible(self):
        """Verify that all essential form fields are visible.

        Note: slug is inside the 'Extra configuration' accordion — this method
        expands it automatically before checking visibility.
        """
        expect(self.name_input).to_be_visible()
        expect(self.description_textarea).to_be_visible()
        expect(self.system_prompt_textarea).to_be_visible()
        self.expand_extra_configuration()
        # Wait for accordion animation to complete before asserting slug visibility
        self.slug_input.wait_for(state="visible", timeout=10000)
        expect(self.slug_input).to_be_visible()
        return self

    @step
    def should_have_action_buttons_visible(self):
        """Verify that action buttons (Save/Create, Cancel) are visible."""
        # Check for Save button (used in create mode) or Create button (if present)
        if self.save_button.count() > 0:
            expect(self.save_button).to_be_visible()
        else:
            expect(self.create_button).to_be_visible()
        expect(self.cancel_button).to_be_visible()
        return self

    @step
    def should_have_name_value(self, expected_name: str):
        """Verify name field has expected value."""
        expect(self.name_input).to_have_value(expected_name)
        return self

    @step
    def should_have_description_value(self, expected_description: str):
        """Verify description field has expected value."""
        expect(self.description_textarea).to_have_value(expected_description)
        return self

    @step
    def should_have_system_prompt_value(self, expected_prompt: str):
        """Verify system prompt field has expected value."""
        expect(self.system_prompt_textarea).to_have_value(expected_prompt)
        return self

    @step
    def should_have_categories_visible(self):
        """Verify categories dropdown is visible.."""
        expect(self.categories_dropdown).to_be_visible()
        return self

    @step
    def should_have_icon_url_value(self, expected_url: str):
        """Verify icon URL field has expected value."""
        expect(self.icon_url_input).to_have_value(expected_url)
        return self

    @step
    def should_have_shared_checked(self):
        """Verify shared toggle is checked."""
        expect(self.shared_toggle_checkbox).to_be_checked()
        return self

    @step
    def should_have_shared_unchecked(self):
        """Verify shared toggle is unchecked."""
        expect(self.shared_toggle_checkbox).not_to_be_checked()
        return self

    @step
    def should_have_attach_file_toggle_visible(self):
        """Verify the 'Enable file attachments' setting control is visible and reachable (AC-1)."""
        self.expand_file_attachments_section()
        expect(self.attach_file_toggle).to_be_visible()
        return self

    @step
    def should_have_attach_file_setting_enabled(self):
        """Verify the attach-file setting is currently ON (checked)."""
        self.expand_file_attachments_section()
        expect(self.attach_file_toggle_checkbox).to_be_checked()
        return self

    @step
    def should_have_attach_file_setting_disabled(self):
        """Verify the attach-file setting is currently OFF (unchecked)."""
        self.expand_file_attachments_section()
        expect(self.attach_file_toggle_checkbox).not_to_be_checked()
        return self

    @step
    def should_have_create_button_enabled(self):
        """Verify Save/Create button is enabled."""
        # Check Save button (used in create mode) or Create button
        if self.save_button.count() > 0:
            expect(self.save_button).to_be_enabled()
        else:
            expect(self.create_button).to_be_enabled()
        return self

    @step
    def should_have_create_button_disabled(self):
        """Verify Save/Create button is disabled."""
        # Check Save button (used in create mode) or Create button
        if self.save_button.count() > 0:
            expect(self.save_button).to_be_disabled()
        else:
            expect(self.create_button).to_be_disabled()
        return self

    @step
    def should_have_cancel_button_enabled(self):
        """Verify cancel button is enabled."""
        expect(self.cancel_button).to_be_enabled()
        return self

    @step
    def should_have_empty_fields(self):
        """Verify all form fields are empty."""
        expect(self.name_input).to_have_value("")
        expect(self.description_textarea).to_have_value("")
        expect(self.system_prompt_textarea).to_have_value("")
        expect(self.icon_url_input).to_have_value("")
        return self

    @step
    def should_have_top_p_and_temperature(self):
        """Verify top p and temperature fields are visible.
        Note: These are inside 'Extra configuration' accordion - auto-expands if needed.
        """
        self.expand_extra_configuration()
        expect(self.temperature_input).to_be_visible()
        expect(self.top_p_input).to_be_visible()
        return self

    @step
    def should_have_top_p_and_temperature_value(self, temperature: str, top_p: str):
        """Verify top p and temperature field values.
        Note: These are inside 'Extra configuration' accordion - auto-expands if needed.
        """
        self.expand_extra_configuration()
        expect(self.temperature_input).to_have_value(temperature)
        expect(self.top_p_input).to_have_value(top_p)

    @step
    def should_have_temperature_placeholder(self, expected_placeholder: str):
        """Assert the placeholder attribute of the temperature input.

        After selecting a Claude model the placeholder should be '0-1';
        for non-Claude models it remains '0-2'.
        Note: Auto-expands 'Extra configuration' accordion if needed.

        Args:
            expected_placeholder: Expected placeholder string, e.g. '0-1' or '0-2'

        Returns:
            self: Returns the page object for method chaining
        """
        self.expand_extra_configuration()
        expect(self.temperature_input).to_have_attribute(
            "placeholder", expected_placeholder
        )
        return self

    @step
    def should_have_datasource_context(self):
        """Verify datasource context fields are visible.

        Note: fields are inside 'Context & Data Sources' accordion — auto-expands if needed.
        """
        self.expand_context_data_sources()
        expect(self.datasource_context_label).to_be_visible()
        expect(self.datasource_context_add_button).to_be_visible()
        expect(self.datasource_context_dropdown).to_be_visible()
        return self

    @step
    def should_have_sub_assistants_context(self):
        """Verify sub assistants context fields are visible.

        Note: fields are inside 'Context & Data Sources' accordion — auto-expands if needed.
        """
        self.expand_context_data_sources()
        expect(self.sub_assistants_label).to_be_visible()
        expect(self.sub_assistants_dropdown).to_be_visible()
        return self

    @step
    def should_have_name_error_textarea(self, error_message: str):
        """Verify name error text field is visible."""
        expect(self.name_error_message).to_be_visible()
        expect(self.name_error_message).to_have_text(error_message)
        return self

    @step
    def should_have_description_error_textarea(self, error_message: str):
        """Verify description error text field is visible."""
        expect(self.description_error_message).to_be_visible()
        expect(self.description_error_message).to_have_text(error_message)
        return self

    @step
    def should_have_system_prompt_error_textarea(self, error_message: str):
        """Verify system prompt error text field is visible."""
        expect(self.system_prompt_error_message).to_be_visible()
        expect(self.system_prompt_error_message).to_have_text(error_message)
        return self

    @step
    def should_have_icon_error_textarea(self, error_message: str):
        """Verify icon error text field is visible."""
        expect(self.icon_error_message).to_be_visible()
        expect(self.icon_error_message).to_have_text(error_message)
        return self

    @step
    def should_have_temperature_error_textarea(self, error_message: str):
        """Verify temperature error text field is visible."""
        expect(self.temperature_error_message).to_be_visible()
        expect(self.temperature_error_message).to_have_text(error_message)
        return self

    @step
    def should_have_top_p_error_textarea(self, error_message: str):
        """Verify top p error text field is visible."""
        expect(self.top_p_error_message).to_be_visible()
        expect(self.top_p_error_message).to_have_text(error_message)
        return self

    # ==================== DATASOURCE CONTEXT METHODS ====================

    @step
    def attach_datasource_from_dropdown(self, datasource_name: str):
        """Attach a datasource by selecting it from the datasource context dropdown."""
        self.expand_context_data_sources()
        self.datasource_context_dropdown.scroll_into_view_if_needed()
        sleep(1)

        # Open dropdown if not already open
        combobox = self.datasource_context_dropdown.locator('input[role="combobox"]')
        if combobox.get_attribute("aria-expanded") != "true":
            self.datasource_context_dropdown.click()

        # Wait for options to load, then click if not already selected
        filter_input = self.page.locator(
            'input[role="searchbox"][placeholder*="search" i], input[role="searchbox"][placeholder*="filter" i]'
        ).first
        filter_input.wait_for(state="visible", timeout=15000)

        filter_input.fill(datasource_name)
        self.page.wait_for_timeout(300)

        datasource_option = (
            self.page.get_by_role("option").filter(has_text=datasource_name).first
        )
        datasource_option.wait_for(state="visible", timeout=10000)
        if datasource_option.get_attribute("aria-selected") != "true":
            datasource_option.click()

        return self

    @step
    def remove_datasource_from_dropdown(self, datasource_name: str):
        """Remove a datasource by deselecting it from the datasource context dropdown."""
        self.expand_context_data_sources()
        self.datasource_context_dropdown.scroll_into_view_if_needed()

        # Open dropdown if not already open
        combobox = self.datasource_context_dropdown.locator('input[role="combobox"]')
        if combobox.get_attribute("aria-expanded") != "true":
            self.datasource_context_dropdown.click()

        # Wait for options to load, then click if currently selected
        datasource_option = (
            self.page.get_by_role("option").filter(has_text=datasource_name).first
        )
        datasource_option.wait_for(state="visible", timeout=10000)
        if datasource_option.get_attribute("aria-selected") == "true":
            datasource_option.click()

        return self

    @step
    def should_have_datasource_attached(self, datasource_name: str):
        """Verify that a datasource is currently attached (visible in dropdown label)."""
        self.expand_context_data_sources()
        dropdown_label = self.datasource_context_dropdown.locator(
            ".p-multiselect-label"
        )
        expect(dropdown_label).to_contain_text(datasource_name, timeout=15000)
        return self

    @step
    def should_not_see_success_toast(self):
        """Assert that no success toast notification is visible on the page.

        Used after a save attempt that should be blocked by validation errors —
        the form must not submit and no 'updated successfully' toast must appear.

        Returns:
            self: Returns the page object for method chaining
        """
        expect(self.page.locator(".codemie-toast")).not_to_be_visible(timeout=3000)
        return self

    # ==================== HIDE TOOL OUTPUTS ====================

    @step
    def enable_hide_tool_outputs_setting(self):
        """Turn the 'Hide tool outputs from end users' switch ON.

        Asserts the switch is OFF before the click and ON after it. The input is
        visually hidden (sr-only) behind a styled span, so the click is forced.
        """
        self.should_have_hide_tool_outputs_switch_unchecked()
        self.hide_tool_outputs_switch.click(force=True)
        self.should_have_hide_tool_outputs_switch_checked()
        return self

    @step
    def disable_hide_tool_outputs_setting(self):
        """Turn the 'Hide tool outputs from end users' switch OFF.

        Asserts the switch is ON before the click (the assertion retries, so it also
        waits for the stored value to be loaded into the form) and OFF after it.
        """
        self.should_have_hide_tool_outputs_switch_checked()
        self.hide_tool_outputs_switch.click(force=True)
        self.should_have_hide_tool_outputs_switch_unchecked()
        return self

    @step
    def should_see_toast_message(self, text: str):
        """Verify a toast notification with the given header text is shown."""
        toast_header = self.page.locator(".codemie-toast .codemie-toast-header")
        expect(toast_header).to_be_visible()
        expect(toast_header).to_have_text(text)
        return self

    @step
    def should_have_hide_tool_outputs_switch_visible(self):
        """Verify the 'Hide tool outputs from end users' switch is present."""
        expect(self.hide_tool_outputs_switch).to_be_visible()
        return self

    @step
    def should_have_hide_tool_outputs_switch_checked(self):
        """Verify the 'Hide tool outputs from end users' switch is ON."""
        expect(self.hide_tool_outputs_switch).to_be_checked()
        return self

    @step
    def should_have_hide_tool_outputs_switch_unchecked(self):
        """Verify the 'Hide tool outputs from end users' switch is OFF."""
        expect(self.hide_tool_outputs_switch).not_to_be_checked()
        return self

    @step
    def should_have_hide_tool_outputs_hint(self, hint_text: str):
        """Verify the helper text of the switch is present (rendered regardless of state)."""
        expect(self.tool_output_visibility_note(hint_text)).to_have_count(1)
        return self

    @step
    def should_have_hide_tool_outputs_enabled_note(self, note_text: str):
        """Verify the 'applies to everyone including you' note is present (switch ON)."""
        expect(self.tool_output_visibility_note(note_text)).to_have_count(1)
        return self

    @step
    def should_not_have_hide_tool_outputs_enabled_note(self, note_text: str):
        """Verify the 'applies to everyone including you' note is absent (switch OFF)."""
        expect(self.tool_output_visibility_note(note_text)).to_have_count(0)
        return self
