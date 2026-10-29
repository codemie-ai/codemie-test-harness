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

from playwright.sync_api import Page, Locator, expect
from reportportal_client import step
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    get_minimal_assistant_mcp_config_data,
)


class AssistantMCPIntegrationModal:
    def __init__(self, page: Page):
        self.page = page

    @property
    def mcp_pop_up(self):
        """Main dialog container using p-dialog class"""
        return self.page.locator("div.p-dialog[role='dialog']").filter(
            has_text="Add new MCP server"
        )

    def mcp_pop_up_header(self):
        """Dialog header with 'Add new MCP server' text"""
        return self.mcp_pop_up.locator(
            "h4.text-base.font-semibold:has-text('Add new MCP server')"
        )

    # --- Name input ---
    @property
    def name_input(self) -> Locator:
        return self.mcp_pop_up.locator("input[name='name'][placeholder='Name*']")

    # --- Description textarea ---
    @property
    def description_textarea(self) -> Locator:
        return self.mcp_pop_up.locator(
            "textarea[name='description'][placeholder='Description*']"
        )

    # --- Tools Tokens Size Limit input ---
    @property
    def tokens_size_limit_input(self) -> Locator:
        return self.mcp_pop_up.locator("input[name='tokensSizeLimit'][type='number']")

    # --- Configuration mode select (JSON/Form) ---
    @property
    def config_mode_switch(self) -> Locator:
        return self.mcp_pop_up.locator("div.p-selectbutton.p-button-group")

    @property
    def config_mode_json_radio(self) -> Locator:
        return self.config_mode_switch.locator(
            "div.p-button[role='button']:has(span:has-text('JSON'))"
        )

    @property
    def config_mode_form_radio(self) -> Locator:
        return self.config_mode_switch.locator(
            "div.p-button[role='button']:has(span:has-text('Form'))"
        )

    # --- Configuration (JSON) textarea ---
    @property
    def configuration_json_textarea(self) -> Locator:
        return self.mcp_pop_up.locator("textarea[name='configJson']#json-config")

    # --- Environment Variables dropdown ---
    @property
    def env_vars_dropdown(self) -> Locator:
        return self.mcp_pop_up.locator(
            "div.p-dropdown:has(span.p-dropdown-label:text('Environment Variables'))"
        )

    # --- MCP-Connect URL input ---
    @property
    def mcp_connect_url_input(self) -> Locator:
        return self.mcp_pop_up.locator(
            "input[name='connectUrl'][placeholder='https://']"
        )

    # --- Buttons ---
    @property
    def cancel_button(self) -> Locator:
        return self.mcp_pop_up.locator(
            "button.bg-button-secondary-bg:has-text('Cancel')"
        )

    @property
    def test_integration_button(self) -> Locator:
        return self.mcp_pop_up.locator(
            "button.bg-button-secondary-bg:has-text('Test Integration')"
        )

    @property
    def add_button(self) -> Locator:
        return self.mcp_pop_up.locator("button.bg-button-primary-bg:has-text('Add')")

    # ---- Action Methods ----

    @step
    def fill_name(self, value: str):
        self.name_input.fill(value)

    @step
    def fill_description(self, value: str):
        self.description_textarea.fill(value)

    @step
    def fill_tokens_size_limit(self, value: int):
        self.tokens_size_limit_input.fill(str(value))

    @step
    def select_config_mode(self, mode: str):
        if mode.lower() == "json":
            self.config_mode_json_radio.click()
        elif mode.lower() == "form":
            self.config_mode_form_radio.click()
        else:
            raise ValueError("Mode must be 'json' or 'form'")

    @step
    def fill_configuration_json(self, value: str):
        self.configuration_json_textarea.fill(value)

    @step
    def open_env_vars_dropdown(self):
        self.env_vars_dropdown.click()

    @step
    def fill_mcp_connect_url(self, value: str):
        self.mcp_connect_url_input.fill(value)

    @step
    def click_cancel(self):
        self.cancel_button.click()

    @step
    def click_test_integration(self):
        self.test_integration_button.click()

    @step
    def click_add(self):
        self.add_button.click()

    @step
    def fill_mcp_server_base_form(self):
        test_data = get_minimal_assistant_mcp_config_data()
        self.fill_name(test_data.name)
        self.fill_description(test_data.description)
        self.fill_configuration_json(test_data.configuration)
        self.click_add()

    # --- Assertions (optional helpers) ---

    def is_pop_visible(self):
        return self.mcp_pop_up_header().count() > 0

    @step
    def should_see_name(self, name: str):
        expect(self.name_input).to_have_value(name)

    @step
    def should_see_description(self, description: str):
        expect(self.description_textarea).to_have_value(description)

    @step
    def should_see_tokens_size_limit(self, token_size: str):
        expect(self.tokens_size_limit_input).to_have_value(token_size)

    @step
    def should_see_configuration_json(self, config: str):
        expect(self.configuration_json_textarea).to_have_value(config)

    @step
    def should_see_mcp_connect_url(self, url: str):
        expect(self.mcp_connect_url_input).to_have_value(url)
