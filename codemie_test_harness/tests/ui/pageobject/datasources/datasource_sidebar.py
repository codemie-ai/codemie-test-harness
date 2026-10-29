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

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DATA_SOURCE_FILTER_STATUSES_LIST,
    DATA_SOURCE_FILTER_TYPES_LIST,
    PROJECT_LABEL,
    STATUS_LABEL,
)


class DataSourceSidebar(BasePage):
    """Sidebar for Data Sources page: filters, search, type, etc."""

    def __init__(self, page):
        super().__init__(page)

    @property
    def sidebar_container(self):
        """Main sidebar container."""
        return self.page.locator("aside.bg-sidebar-gradient")

    @property
    def page_title(self):
        """Page title."""
        return self.sidebar_container.locator("h2.text-2xl")

    @property
    def page_subtitle(self):
        """Subtitle below title."""
        return self.sidebar_container.locator("p.text-sm")

    @property
    def search_input(self):
        """Search input in Filters section."""
        return self.sidebar_container.locator('input[placeholder="Search"]')

    @property
    def filters_section(self):
        """The Filters section."""
        return self.sidebar_container.locator("span").filter(has_text="Filters")

    @property
    def type_filter_section(self):
        """Type filter accordion."""
        return (
            self.sidebar_container.get_by_role("button", name="TYPE")
            .locator("..")
            .locator("..")
        )

    def get_type_checkbox(self, type_label: str):
        """
        Returns the locator for a TYPE filter checkbox by its label text.
        """
        return self.sidebar_container.locator("label").filter(has_text=type_label)

    def get_type_checkbox_div(self, type_label: str):
        """
        Returns the outer <div class="p-checkbox ..."> for a specific checkbox type.
        """
        return self.get_type_checkbox(type_label).locator(
            "xpath=../../div[contains(@class, 'p-checkbox')]"
        )

    @property
    def project_filter_multiselect(self):
        """Project filter dropdown."""
        return self.sidebar_container.locator('div[data-pc-name="multiselect"]')

    @property
    def created_by_me_checkbox(self):
        """'Created by Me' filter checkbox."""
        return (
            self.page.locator("label")
            .filter(has_text="Me")
            .locator("xpath=../../div[contains(@class, 'p-checkbox')]")
        )

    @property
    def created_by_field(self):
        """Created By user autocomplete input."""
        return self.page.locator('#created_by input[type="text"]')

    @property
    def status_dropdown(self):
        """Status filter dropdown."""
        return self.sidebar_container.locator("#status")

    def status_dropdown_items(self, status: str):
        """Status dropdown items."""
        return self.page.get_by_role("option", name=status)

    @property
    def clear_all_button(self):
        """Clear all button."""
        return self.sidebar_container.locator(".button").filter(has_text="Clear All")

    @property
    def hide_type_filter_button(self):
        """Hide Type filter button."""
        return self.sidebar_container.locator(
            '.leading-normal.font-semibold:has-text("TYPE")'
        )

    @property
    def hide_project_filter_button(self):
        """Hide Project filter button."""
        return self.sidebar_container.locator(
            '.leading-normal.font-semibold:has-text("PROJECT")'
        )

    @property
    def hide_created_by_filter_button(self):
        """Hide Created By filter button."""
        return self.sidebar_container.locator(
            '.leading-normal.font-semibold:has-text("CREATED BY")'
        )

    @property
    def hide_status_filter_button(self):
        """Hide Status filter button."""
        return self.sidebar_container.locator(
            '.leading-normal.font-semibold:has-text("STATUS")'
        )

    # -----------------
    # Action Methods
    # -----------------
    @step
    def click_create_datasource(self):
        self.create_datasource_button.click()
        return self

    @step
    def input_data_search(self, search_term: str):
        self.search_input.fill(search_term)
        return self

    @step
    def toggle_type_filter(self, type_label: str):
        self.get_type_checkbox(type_label).click()
        return self

    @step
    def select_project(self, project_name: str):
        self.project_filter_multiselect.click()
        self.page.locator(f'li:has-text("{project_name}")').click()
        return self

    @step
    def toggle_created_by_me(self):
        self.created_by_me_checkbox.click()
        return self

    @step
    def filter_by_creator(self, user_name: str):
        self.created_by_field.fill(user_name)
        self.page.keyboard.press("Enter")
        return self

    @step
    def select_status(self, status_label: str):
        self.status_dropdown.click()
        self.page.locator(f'li:has-text("{status_label}")').click()
        return self

    @step
    def click_clear_all_button(self):
        self.clear_all_button.click()
        return self

    @step
    def click_type_filter_hide_button(self):
        self.hide_type_filter_button.click()
        return self

    @step
    def click_project_filter_hide_button(self):
        self.hide_project_filter_button.click()
        return self

    @step
    def click_created_by_filter_hide_button(self):
        self.hide_created_by_filter_button.click()
        return self

    @step
    def click_status_filter_hide_button(self):
        self.hide_status_filter_button.click()
        return self

    # -----------------
    # Verification Methods
    # -----------------
    @step
    def should_see_title_subtitle(self, title: str, subtitle: str):
        expect(self.page_title).to_be_visible(timeout=15000)
        expect(self.page_title).to_have_text(title, timeout=15000)
        expect(self.page_subtitle).to_be_visible(timeout=15000)
        expect(self.page_subtitle).to_have_text(subtitle, timeout=15000)
        return self

    @step
    def should_see_filters_section(self):
        expect(self.filters_section).to_be_visible()
        expect(self.filters_section).to_be_enabled()
        return self

    @step
    def should_see_project_filter(self):
        expect(self.project_filter_multiselect).to_be_visible()
        expect(self.project_filter_multiselect).to_be_enabled()
        return self

    @step
    def should_see_status_dropdown(self):
        expect(self.status_dropdown).to_be_visible()
        self.status_dropdown.click()
        for status in DATA_SOURCE_FILTER_STATUSES_LIST:
            expected_statuses = self.status_dropdown_items(status)
            expect(expected_statuses).to_be_visible()
        self.status_dropdown.click()
        return self

    @step
    def should_select_status_dropdown(self):
        for status in DATA_SOURCE_FILTER_STATUSES_LIST:
            self.status_dropdown.click()
            expected_status = self.status_dropdown_items(status)
            expected_status.click()
            expect(self.status_dropdown.locator(".p-dropdown-label")).to_have_text(
                status
            )

    @step
    def should_see_type_checkboxes(self):
        """
        Verifies the type checkbox with the given label is visible in the sidebar.
        """
        for type_label in DATA_SOURCE_FILTER_TYPES_LIST:
            checkbox = self.get_type_checkbox(type_label)
            expect(checkbox).to_be_visible()
        return self

    @step
    def should_see_selected_checkboxes(self):
        for type_label in DATA_SOURCE_FILTER_TYPES_LIST:
            expect(self.get_type_checkbox_div(type_label)).to_have_attribute(
                "data-p-highlight", "false"
            )
            self.toggle_type_filter(type_label)
            expect(self.get_type_checkbox_div(type_label)).to_have_attribute(
                "data-p-highlight", "true"
            )
        return self

    @step
    def should_see_search_input(self, text: str):
        expect(self.search_input).to_have_value(text)
        expect(self.clear_all_button).to_be_visible()
        return self

    @step
    def should_see_created_by_me_value(self, user: str):
        expect(self.created_by_field).to_have_value(user)
        return self

    @step
    def should_see_cleared_filters(self):
        expect(self.clear_all_button).not_to_be_visible()
        expect(self.search_input).to_have_value("")
        for type_label in DATA_SOURCE_FILTER_TYPES_LIST:
            expect(self.get_type_checkbox_div(type_label)).to_have_attribute(
                "data-p-highlight", "false"
            )
        expect(self.project_filter_multiselect).to_have_text(PROJECT_LABEL)
        expect(self.created_by_field).to_have_value("")
        expect(self.status_dropdown.locator(".p-dropdown-label")).to_have_text(
            STATUS_LABEL
        )
        return self

    @step
    def should_not_see_type_filters(self):
        for type_label in DATA_SOURCE_FILTER_TYPES_LIST:
            expect(self.get_type_checkbox(type_label)).not_to_be_visible()
        return self

    @step
    def should_not_see_project_filters(self):
        expect(self.project_filter_multiselect).not_to_be_visible()
        return self

    @step
    def should_not_see_created_by_filters(self):
        expect(self.created_by_field).not_to_be_visible()
        expect(self.created_by_me_checkbox).not_to_be_visible()
        return self

    @step
    def should_not_see_status_filters(self):
        expect(self.status_dropdown).not_to_be_visible()
        return self
