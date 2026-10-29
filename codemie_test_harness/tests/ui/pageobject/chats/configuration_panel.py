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
Chat Configuration Panel Component for CodeMie UI Testing

This module implements the chat configuration side panel component following the established
POM patterns. It provides comprehensive support for configuration management including
LLM engine selection, assistant management, and configuration testing.

Architecture follows the same patterns as other panel components:
- Property-based element locators with precise unique selectors
- Method chaining support for fluent API
- ReportPortal integration via @step decorators
- Comprehensive verification methods
"""

import re

from hamcrest import assert_that, contains_string
from playwright.sync_api import expect, Locator
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.chats.configure_and_test_panel import (
    ConfigureAndTestPanel,
)


class ConfigurationPanel:
    """
    Chat configuration side panel component with comprehensive configuration management.

    This component handles all configuration-related interactions including:
    - Managing LLM engine selection
    - Interacting with connected assistants
    - Configuring and testing assistants
    - Verification of configuration states

    Follows established POM patterns with property-based locators.
    """

    def __init__(self, page):
        self.page = page

    # ==================== PANEL CONTAINER ELEMENTS ====================

    @property
    def panel(self) -> Locator:
        """Main configuration panel content container - the aside element."""
        return self.page.locator("aside[data-testid='chat-configuration-panel'] > div")

    @property
    def general_section(self) -> Locator:
        """General configuration section."""
        return self.panel.locator("h3").filter(has_text="General")

    @property
    def tool_outputs_section(self) -> Locator:
        """Tool outputs configuration section heading."""
        return self.panel.locator("h4").filter(has_text="Tool outputs")

    @property
    def hide_tool_outputs_toggle(self) -> Locator:
        """Hide tool outputs toggle switch (input[role='switch'] named via label text)."""
        return self.panel.get_by_role("switch", name="Hide tool outputs")

    @property
    def hide_tool_outputs_label(self) -> Locator:
        """'Hide tool outputs' label text element."""
        return self.panel.get_by_text("Hide tool outputs", exact=True)

    @property
    def connected_assistants_section(self) -> Locator:
        """Connected Assistants section."""
        return self.panel.locator("h4").filter(has_text="Connected Assistants")

    # ==================== LLM ENGINE CONFIGURATION ====================

    @property
    def primary_llm_engine_label(self) -> Locator:
        """Primary LLM Engine label."""
        return self.panel.locator('label:has-text("LLM Model")')

    @property
    def primary_llm_engine_dropdown(self) -> Locator:
        """Primary LLM Engine dropdown selector."""
        return self.panel.locator('.p-multiselect[aria-label="LLM Model"]')

    @property
    def llm_engine_dropdown_trigger(self) -> Locator:
        """LLM Engine dropdown trigger button."""
        return self.primary_llm_engine_dropdown.locator(
            'div[data-pc-section="trigger"]'
        )

    @property
    def llm_engine_current_selection(self) -> Locator:
        """Current LLM Engine selection display."""
        return self.primary_llm_engine_dropdown.locator('div[data-pc-section="label"]')

    # ==================== ASSISTANT LIST ELEMENTS ====================
    class ConnectedAssistantCard:
        def __init__(self, page, title: str):
            self.page = page
            self.assistant_card = self.page.locator(
                "div.flex.flex-col.p-4.rounded-lg.border"
            ).filter(has=self.page.locator("h5.font-semibold").filter(has_text=title))
            self.id_field = self.assistant_card.locator(
                "div.flex.gap-1.text-xs:has-text('ID:')"
            )
            self.link_field = self.assistant_card.locator("a[href*='/assistants/']")
            self.config_button = self.assistant_card.locator("button").filter(
                has_text="Configure"
            )

    @property
    def assistant_list(self) -> Locator:
        """Container for all assistant cards."""
        return self.panel.locator(
            "h4:has-text('Connected Assistants') + div.flex.flex-col.gap-4"
        )

    # ==================== HIDE TOOL OUTPUTS INTERACTION METHODS ====================

    @step
    def enable_hide_tool_outputs(self):
        """Enable the 'Hide tool outputs' toggle (asserts unchecked before click, checked after).

        The toggle input has Tailwind class 'sr-only' (visually hidden) and a sibling
        <span class="switch"> renders the visual affordance. Clicking the input directly
        fails because the span intercepts pointer events. force=True bypasses Playwright's
        actionability / interception check so the click event is dispatched directly to
        the input, which changes the native checked state and triggers the peer-checked CSS.
        """
        self.should_have_hide_tool_outputs_toggle_unchecked()
        self.hide_tool_outputs_toggle.click(force=True)
        self.should_have_hide_tool_outputs_toggle_checked()
        return self

    @step
    def disable_hide_tool_outputs(self):
        """Disable the 'Hide tool outputs' toggle (asserts checked before click, unchecked after)."""
        self.should_have_hide_tool_outputs_toggle_checked()
        self.hide_tool_outputs_toggle.click(force=True)
        self.should_have_hide_tool_outputs_toggle_unchecked()
        return self

    # ==================== HIDE TOOL OUTPUTS VERIFICATION METHODS ====================

    @step
    def should_have_hide_tool_outputs_toggle_visible(self):
        """Assert the 'Hide tool outputs' toggle is visible in the config panel."""
        expect(self.hide_tool_outputs_toggle).to_be_visible()
        return self

    @step
    def should_have_hide_tool_outputs_toggle_checked(self):
        """Assert the 'Hide tool outputs' toggle is checked (ON)."""
        expect(self.hide_tool_outputs_toggle).to_be_checked()
        return self

    @step
    def should_have_hide_tool_outputs_toggle_unchecked(self):
        """Assert the 'Hide tool outputs' toggle is unchecked (OFF / default)."""
        expect(self.hide_tool_outputs_toggle).not_to_be_checked()
        return self

    @step
    def should_not_have_hide_tool_outputs_toggle(self):
        """Assert the 'Hide tool outputs' toggle is absent from the config panel DOM."""
        expect(self.hide_tool_outputs_toggle).to_have_count(0)
        return self

    @step
    def should_have_hide_tool_outputs_label_visible(self):
        """Assert the 'Hide tool outputs' label text is visible."""
        expect(self.hide_tool_outputs_label).to_be_visible()
        return self

    # ==================== PANEL INTERACTION METHODS ====================

    @step
    def open_llm_engine_dropdown(self):
        """Open the Primary LLM Engine dropdown."""
        if self.primary_llm_engine_dropdown.is_visible():
            self.llm_engine_dropdown_trigger.click()
            self.page.wait_for_timeout(1000)
        return self

    @step
    def select_llm_engine_option(self, llm_name: str):
        """Select an option from the LLM Engine dropdown."""
        self.open_llm_engine_dropdown()

        search_input = self.page.locator(".p-multiselect-filter")
        search_input.fill(llm_name)
        option_item = self.page.get_by_text(llm_name, exact=True)
        if option_item.is_visible():
            option_item.click()
        else:
            raise Exception(f"'{llm_name} LLM is not found!")

        return self

    @step
    def open_assistant_configuration(self, assistant_name: str):
        assistant_card = self.ConnectedAssistantCard(
            page=self.page, title=assistant_name
        )
        assistant_card.config_button.click()
        return ConfigureAndTestPanel(self.page)

    # ==================== VERIFICATION METHODS ====================

    @step
    def should_be_visible(self):
        """Verify that the configuration panel is visible."""
        expect(self.panel).to_be_visible()
        return self

    @step
    def should_be_hidden(self):
        """Verify that the configuration panel is hidden."""
        expect(self.panel).to_be_hidden()
        return self

    @step
    def should_have_general_section_visible(self):
        """Verify that the General section is visible."""
        expect(self.general_section).to_be_visible()
        return self

    @step
    def should_have_connected_assistants_section_visible(self):
        """Verify that the Connected Assistants section is visible."""
        expect(self.connected_assistants_section).to_be_visible()
        return self

    @step
    def should_have_llm_engine_dropdown_visible(self):
        """Verify that the Primary LLM Engine dropdown is visible."""
        expect(self.primary_llm_engine_dropdown).to_be_visible()
        return self

    @step
    def should_have_llm_engine_selection(self, expected_text: str):
        """
        Verify the LLM Engine dropdown shows expected selection.

        Args:
            expected_text: Expected selection text (e.g., "Default: GPT-4.1 2025-04-14")
        """
        expect(self.llm_engine_current_selection).to_contain_text(expected_text)
        return self

    @step
    def should_have_assistant_list_visible(
        self,
    ):
        expect(self.assistant_list).to_be_visible()
        return self

    @step
    def should_have_assistant_visible(self, assistant_name: str):
        """
        Verify that a specific assistant is visible.

        Args:
            assistant_name: Name of the assistant to verify
        """
        assistant_card = self.ConnectedAssistantCard(
            page=self.page, title=assistant_name
        )
        expect(assistant_card.id_field).to_be_visible()
        expect(assistant_card.link_field).to_be_visible()
        expect(assistant_card.config_button).to_be_visible()
        return self

    @step
    def should_have_all_sections_visible(self):
        """Verify that all main panel sections are visible."""
        self.should_have_general_section_visible()
        self.should_have_connected_assistants_section_visible()
        self.should_have_llm_engine_dropdown_visible()
        self.should_have_assistant_list_visible()
        self.should_have_assistant_visible("AI/Run Chatbot")
        return self

    # ==================== PREMIUM MODEL ELEMENTS ====================

    def _llm_option(self, model_name: str) -> Locator:
        """LLM dropdown option matching exactly one model by name.

        A plain ``has_text=model_name`` substring filter is ambiguous once the
        environment has both a base model and its "(DIAL)"-suffixed sibling
        (e.g. "GPT-5.6 Sol" and "GPT-5.6 Sol (DIAL)") — the base name is a
        literal text prefix of the DIAL variant's option, so it matches both.
        The negative lookahead rejects any option whose text continues the
        matched name with a parenthetical suffix, keeping only the option
        for the exact model asked for.
        """
        pattern = re.compile(rf"^{re.escape(model_name)}(?!\s*\()")
        return self.page.get_by_role("option").filter(has_text=pattern)

    def premium_badge_in_llm_option(self, model_name: str) -> Locator:
        """Premium meta label inside the LLM dropdown option for a named model.

        The premium indicator is rendered as
        ``<span data-testid="llm-option-meta">...<span class="text-aborted-primary">Premium</span>...</span>``
        — there is no ``role="status"`` element.
        """
        return self._llm_option(model_name).locator('[data-testid="llm-option-meta"]')

    def premium_tooltip_in_llm_option(self, model_name: str) -> Locator:
        """Row span carrying ``data-tooltip-content`` inside the LLM dropdown option.

        The tooltip is on ``<span data-testid="llm-option-row" data-tooltip-content="…">``.
        In the multiselect the content format is ``"{model} · {tooltip_text}"``.
        """
        return self._llm_option(model_name).locator('[data-testid="llm-option-row"]')

    # ==================== PREMIUM MODEL INTERACTION METHODS ====================

    @step
    def open_llm_dropdown_and_search(self, model_name: str):
        """Open the LLM engine dropdown and type a search term."""
        self.open_llm_engine_dropdown()
        search_input = self.page.locator(".p-multiselect-filter")
        search_input.fill(model_name)
        return self

    # ==================== PREMIUM MODEL VERIFICATION METHODS ====================

    @step
    def should_show_premium_badge_for_model(self, model_name: str):
        """Assert the premium badge is visible for the given model in the LLM dropdown."""
        expect(self.premium_badge_in_llm_option(model_name)).to_be_visible()
        return self

    @step
    def should_show_premium_tooltip_for_model(
        self, model_name: str, expected_text: str
    ):
        """Assert the premium tooltip content contains the expected text.

        The multiselect tooltip value is ``"{model_name} · {expected_text}"``, so
        ``contains_string`` is used instead of an exact-match.
        """
        actual = self.premium_tooltip_in_llm_option(model_name).get_attribute(
            "data-tooltip-content"
        )
        assert_that(
            actual, contains_string(expected_text), "Premium tooltip text mismatch"
        )
        return self

    # ==================== UTILITY METHODS ====================

    @step
    def is_visible(self) -> bool:
        """Check if the configuration panel is currently visible."""
        return self.panel.is_visible()

    @step
    def get_current_llm_engine_selection(self) -> str:
        """Get the current LLM Engine selection text."""
        return self.llm_engine_current_selection.text_content()
