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


class WorkflowSidebar:
    """Component representing the workflow sidebar with categories and filters."""

    def __init__(self, page):
        """
        Initialize workflow sidebar component.

        Args:
            page: Playwright page object
        """
        self.page = page

    # Main container and sidebar
    @property
    def sidebar_container(self):
        """Main sidebar container.
        Note: class-based selector removed — the sidebar CSS class changes
        with theme updates, so we match on the semantic element type only.
        """
        return self.page.locator("aside").first

    @property
    def page_title(self):
        """Main page title 'Workflows'."""
        return self.sidebar_container.locator(
            "h2.text-2xl.font-semibold:has-text('Workflows')"
        )

    @property
    def page_subtitle(self):
        """Page subtitle."""
        return self.sidebar_container.locator(
            "text=Browse and run available AI-powered workflows"
        )

    # Categories section
    @property
    def categories_header(self):
        """Categories section header."""
        return self.sidebar_container.locator('h3:has-text("Categories")')

    @property
    def my_workflows_link(self):
        """My Workflows navigation link."""
        return self.sidebar_container.get_by_text("My Workflows")

    @property
    def all_workflows_link(self):
        """All Workflows navigation link."""
        return self.sidebar_container.get_by_text("All Workflows")

    @property
    def templates_link(self):
        """Templates navigation link."""
        return self.sidebar_container.get_by_text("Templates")

    # Filters section
    @property
    def filters_sidebar(self):
        """Filters section sidebar."""
        return self.sidebar_container.locator('h3:has-text("Filters")')

    @property
    def search_form(self):
        """Search form container."""
        return self.sidebar_container.locator("form.form")

    @property
    def search_input_container(self):
        """Search input container."""
        return self.sidebar_container.locator("div.search")

    # Project filter section
    @property
    def project_filter_sidebar(self):
        """Project filter expandable sidebar."""
        return self.sidebar_container.locator('a:has-text("project")')

    @property
    def project_filter_arrow(self):
        """Project filter dropdown arrow."""
        return self.sidebar_container.locator('a:has-text("project") svg')

    @property
    def project_multiselect(self):
        """Project multiselect dropdown."""
        return self.sidebar_container.locator('.p-multiselect[name="project"]')

    @property
    def project_multiselect_label(self):
        """Project multiselect label."""
        return self.sidebar_container.locator(
            '.p-multiselect[name="project"] .p-multiselect-label'
        )

    @property
    def project_multiselect_trigger(self):
        """Project multiselect trigger button."""
        return self.sidebar_container.locator(
            '.p-multiselect[name="project"] .p-multiselect-trigger'
        )

    @property
    def project_hidden_input(self):
        """Project multiselect hidden input."""
        return self.sidebar_container.locator(
            '.p-multiselect[name="project"] input[type="text"]'
        )

    # Category filter section (distinct from the My/All/Templates "Categories" nav header)
    @property
    def category_filter_dropdown(self):
        """Categories filter multiselect."""
        return self.sidebar_container.locator(
            'div.p-multiselect[aria-label="Categories"]'
        )

    @property
    def category_filter_listbox(self):
        """Options list of the opened Categories filter (rendered in a portal)."""
        return self.page.get_by_role("listbox")

    @property
    def clear_all_button(self):
        """'Clear all' button that resets the applied filters."""
        return self.sidebar_container.get_by_role("button", name="Clear all")

    # Shared filter section
    @property
    def shared_filter_sidebar(self):
        """Shared filter expandable sidebar."""
        return self.sidebar_container.locator('a:has-text("shared")')

    @property
    def shared_filter_arrow(self):
        """Shared filter dropdown arrow."""
        return self.sidebar_container.locator('a:has-text("shared") svg')

    @property
    def with_project_radio_group(self):
        """With Project radio button group."""
        return self.sidebar_container.locator('label[for="shared-1"]')

    @property
    def with_project_radio_input(self):
        """With Project radio button input."""
        return self.sidebar_container.locator("#shared-1")

    @property
    def with_project_radio_label(self):
        """With Project radio button label."""
        return self.sidebar_container.locator('label[for="shared-1"]')

    @property
    def with_project_custom_radio(self):
        """With Project custom radio button styling."""
        return self.sidebar_container.locator('label[for="shared-1"] .p-radiobutton')

    @property
    def not_shared_radio_group(self):
        """Not Shared radio button group."""
        return self.sidebar_container.locator('label[for="shared-2"]')

    @property
    def not_shared_radio_input(self):
        """Not Shared radio button input."""
        return self.sidebar_container.locator("#shared-2")

    @property
    def not_shared_radio_label(self):
        """Not Shared radio button label."""
        return self.sidebar_container.locator('label[for="shared-2"]')

    @property
    def not_shared_custom_radio(self):
        """Not Shared custom radio button styling."""
        return self.sidebar_container.locator('label[for="shared-2"] .p-radiobutton')

    # Action methods for navigation
    @step
    def navigate_to_my_workflows(self):
        """Navigate to My Workflows section."""
        self.my_workflows_link.click()
        return self

    @step
    def navigate_to_all_workflows(self):
        """Navigate to All Workflows section."""
        self.all_workflows_link.click()
        self.page.wait_for_load_state("networkidle", timeout=10000)
        return self

    @step
    def navigate_to_templates(self):
        """Navigate to Templates section."""
        self.templates_link.click()
        return self

    # Action methods for filters
    @step
    def expand_project_filter(self):
        """Expand the project filter section."""
        if not self.is_project_filter_expanded():
            self.project_filter_sidebar.click()
        return self

    @step
    def collapse_project_filter(self):
        """Collapse the project filter section."""
        if self.is_project_filter_expanded():
            self.project_filter_sidebar.click()
        return self

    @step
    def open_project_multiselect(self):
        """Open the project multiselect dropdown."""
        self.project_multiselect_trigger.click()
        return self

    @step
    def select_project_option(self, project_name: str):
        """
        Select a project from the multiselect dropdown.

        Args:
            project_name: Name of the project to select
        """
        self.open_project_multiselect()
        project_option = self.sidebar_container.locator(
            f'li:has-text("{project_name}")'
        )
        project_option.click()
        return self

    @step
    def expand_shared_filter(self):
        """Expand the shared filter section."""
        if not self.is_shared_filter_expanded():
            self.shared_filter_sidebar.click()
        return self

    @step
    def collapse_shared_filter(self):
        """Collapse the shared filter section."""
        if self.is_shared_filter_expanded():
            self.shared_filter_sidebar.click()
        return self

    @step
    def select_with_project_filter(self):
        """Select the 'With Project' radio button."""
        self.with_project_radio_label.click()
        return self

    @step
    def select_not_shared_filter(self):
        """Select the 'Not Shared' radio button."""
        self.not_shared_radio_label.click()
        return self

    @step
    def clear_shared_filters(self):
        """Clear all shared filter selections."""
        # If either radio button is selected, we need to uncheck them
        # Since these are radio buttons, we can't directly uncheck them
        # This would depend on the actual implementation behavior
        if self.is_with_project_selected() or self.is_not_shared_selected():
            # Implementation depends on whether there's a way to clear radio selections
            # For now, we'll assume clicking the same option again clears it
            if self.is_with_project_selected():
                self.with_project_radio_label.click()
            elif self.is_not_shared_selected():
                self.not_shared_radio_label.click()
        return self

    @step
    def select_category_filter(self, name: str):
        """Open the Categories filter, pick the named option and close the list."""
        self.category_filter_dropdown.click()
        self.category_filter_listbox.wait_for(state="visible")
        self.category_filter_listbox.get_by_role(
            "option", name=name, exact=True
        ).click()
        self.page.keyboard.press("Escape")
        self.category_filter_listbox.wait_for(state="hidden")
        return self

    @step
    def clear_all_filters(self):
        """Reset every applied sidebar filter (including Categories) with 'Clear all'."""
        self.clear_all_button.click()
        return self

    # Utility methods
    @step
    def is_project_filter_expanded(self) -> bool:
        """Check if the project filter section is expanded."""
        # This would depend on the actual implementation
        # We can check if the multiselect dropdown is visible
        return self.project_multiselect.is_visible()

    @step
    def is_shared_filter_expanded(self) -> bool:
        """Check if the shared filter section is expanded."""
        # Check if the radio button groups are visible
        return self.with_project_radio_group.is_visible()

    @step
    def is_with_project_selected(self) -> bool:
        """Check if 'With Project' radio button is selected."""
        return self.with_project_radio_input.is_checked()

    @step
    def is_not_shared_selected(self) -> bool:
        """Check if 'Not Shared' radio button is selected."""
        return self.not_shared_radio_input.is_checked()

    @step
    def get_selected_project(self) -> str:
        """Get the currently selected project name."""
        return self.project_multiselect_label.text_content().strip()

    @step
    def get_current_category(self) -> str:
        """Get the currently active category."""
        # Check which category link has the active class
        if self.my_workflows_link.get_attribute(
            "class"
        ) and "bg-new-stroke" in self.my_workflows_link.get_attribute("class"):
            return "My Workflows"
        elif self.all_workflows_link.get_attribute(
            "class"
        ) and "bg-new-stroke" in self.all_workflows_link.get_attribute("class"):
            return "All Workflows"
        elif self.templates_link.get_attribute(
            "class"
        ) and "bg-new-stroke" in self.templates_link.get_attribute("class"):
            return "Templates"
        else:
            return "Unknown"

    # Verification methods
    @step
    def should_be_visible(self):
        """Verify that the sidebar is visible."""
        expect(self.sidebar_container).to_be_visible()
        return self

    @step
    def should_have_workflows_title(self):
        """Verify that the 'Workflows' title is displayed."""
        expect(self.page_title).to_be_visible()
        expect(self.page_title).to_have_text("Workflows")
        return self

    @step
    def should_have_subtitle(self):
        """Verify that the subtitle is displayed."""
        expect(self.page_subtitle).to_be_visible()
        expect(self.page_subtitle).to_have_text(
            "Browse and run available AI-powered workflows"
        )
        return self

    @step
    def should_have_categories_section(self):
        """Verify that the categories section is visible."""
        expect(self.categories_header).to_be_visible()
        expect(self.my_workflows_link).to_be_visible()
        expect(self.all_workflows_link).to_be_visible()
        expect(self.templates_link).to_be_visible()
        return self

    @step
    def should_have_category_filter_visible(self):
        """Verify that the Categories filter multiselect is visible."""
        expect(self.category_filter_dropdown).to_be_visible()
        return self

    @step
    def should_have_filters_section(self):
        """Verify that the filters section is visible."""
        expect(self.filters_sidebar).to_be_visible()
        return self

    @step
    def filters_should_be_hidden(self):
        """Verify that the filters section is hidden."""
        expect(self.filters_sidebar).to_be_hidden()
        return self

    @step
    def should_have_project_filter_collapsed(self):
        """Verify that the project filter is collapsed."""
        expect(self.project_filter_sidebar).to_be_visible()
        expect(self.project_multiselect).not_to_be_visible()
        return self

    @step
    def should_have_project_filter_expanded(self):
        """Verify that the project filter is expanded."""
        expect(self.project_filter_sidebar).to_be_visible()
        expect(self.project_multiselect).to_be_visible()
        return self

    @step
    def should_have_shared_filter_collapsed(self):
        """Verify that the shared filter is collapsed."""
        expect(self.shared_filter_sidebar).to_be_visible()
        expect(self.with_project_radio_group).not_to_be_visible()
        expect(self.not_shared_radio_group).not_to_be_visible()
        return self

    @step
    def should_have_shared_filter_expanded(self):
        """Verify that the shared filter is expanded."""
        expect(self.shared_filter_sidebar).to_be_visible()
        expect(self.with_project_radio_group).to_be_visible()
        expect(self.not_shared_radio_group).to_be_visible()
        return self

    @step
    def should_have_with_project_selected(self):
        """Verify that 'With Project' filter is selected."""
        expect(self.with_project_radio_input).to_be_checked()
        return self

    @step
    def should_have_not_shared_selected(self):
        """Verify that 'Not Shared' filter is selected."""
        expect(self.not_shared_radio_input).to_be_checked()
        return self

    @step
    def should_have_no_shared_filter_selected(self):
        """Verify that no shared filter is selected."""
        expect(self.with_project_radio_input).not_to_be_checked()
        expect(self.not_shared_radio_input).not_to_be_checked()
        return self

    @step
    def should_have_project_selected(self, project_name: str):
        """Verify that the specified project is selected."""
        expect(self.project_multiselect_label).to_have_text(project_name)
        return self

    @step
    def should_have_default_project_placeholder(self):
        """Verify that the project dropdown shows default placeholder."""
        expect(self.project_multiselect_label).to_have_text("Project")
        return self

    @step
    def should_have_my_workflows_active(self):
        """Verify that 'My Workflows' is the active category."""
        expect(self.my_workflows_link).to_have_class("bg-new-stroke")
        return self

    @step
    def should_have_all_workflows_active(self):
        """Verify that 'All Workflows' is the active category."""
        expect(self.all_workflows_link).to_have_class("bg-new-stroke")
        return self

    @step
    def should_have_templates_active(self):
        """Verify that 'Templates' is the active category."""
        expect(self.templates_link).to_have_class("bg-new-stroke")
        return self

    @step
    def should_have_project_multiselect_accessible(self):
        """Verify that the project multiselect is accessible with proper ARIA attributes."""
        expect(self.project_hidden_input).to_have_attribute("role", "combobox")
        expect(self.project_hidden_input).to_have_attribute("aria-haspopup", "listbox")
        return self

    @step
    def should_have_radio_buttons_accessible(self):
        """Verify that radio buttons are properly labeled and accessible."""
        expect(self.with_project_radio_input).to_have_attribute("type", "radio")
        expect(self.not_shared_radio_input).to_have_attribute("type", "radio")
        expect(self.with_project_radio_label).to_be_visible()
        expect(self.not_shared_radio_label).to_be_visible()
        return self

    @step
    def should_have_all_main_elements_visible(self):
        """Verify that all main sidebar elements are visible."""
        self.should_be_visible()
        self.should_have_workflows_title()
        self.should_have_subtitle()
        self.should_have_categories_section()
        self.should_have_filters_section()
        return self

    @step
    def should_show_project_filter_icon(self):
        """Verify that project filter has expand/collapse icon."""
        expect(self.project_filter_arrow).to_be_visible()
        return self

    @step
    def should_show_shared_filter_icon(self):
        """Verify that shared filter has expand/collapse icon."""
        expect(self.shared_filter_arrow).to_be_visible()
        return self

    # Additional convenience methods moved from page objects
    @step
    def select_with_project_filter_with_expand(self):
        """Select the 'With Project' filter (with auto-expand)."""
        self.expand_shared_filter()
        self.select_with_project_filter()
        return self

    @step
    def select_not_shared_filter_with_expand(self):
        """Select the 'Not shared' filter (with auto-expand)."""
        self.expand_shared_filter()
        self.select_not_shared_filter()
        return self

    @step
    def select_project_filter_with_expand(self, project_name: str):
        """Select a specific project filter (with auto-expand)."""
        self.expand_project_filter()
        self.select_project_option(project_name)
        return self

    @step
    def should_have_filters_cleared(self):
        """Verify that all filters are cleared."""
        self.should_have_no_shared_filter_selected()
        return self

    @step
    def should_have_with_project_filter_selected(self):
        """Verify that 'With Project' filter is selected."""
        self.should_have_with_project_selected()
        return self

    @step
    def should_have_not_shared_filter_selected(self):
        """Verify that 'Not shared' filter is selected."""
        self.should_have_not_shared_selected()
        return self
