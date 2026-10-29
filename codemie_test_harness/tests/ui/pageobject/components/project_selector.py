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


class ProjectSelector:
    """Component representing the project selector on different create pages."""

    def __init__(self, page):
        """
        Initialize project selector object.

        Args:
            page: Playwright page object
        """
        self.page = page

    @property
    def project_multiselect(self):
        return self.page.locator("#project-selector")

    @property
    def disabled_project_multiselect(self):
        return self.page.locator("#project-selector.p-disabled")

    @property
    def disabled_project_multiselect_value(self):
        return self.disabled_project_multiselect.locator("input")

    @property
    def project_multiselect_value(self):
        return self.page.locator("div.p-multiselect-label")

    @property
    def project_multiselect_input(self):
        return self.page.locator("input.p-multiselect-filter.p-inputtext.p-component")

    @property
    def project_multiselect_top_three(self):
        return self.page.locator("div.p-multiselect-items-wrapper ul li")

    @property
    def project_multiselect_top_three_checkbox(self):
        return self.project_multiselect_top_three.locator("input")

    @property
    def project_multiselect_top_three__value(self):
        return self.project_multiselect_top_three.locator("span")

    # ----------------------------------
    # Verification Methods
    # ----------------------------------

    @step
    def should_see_multiselect(self):
        """Asserts the selector widget is present and visible."""
        expect(self.project_multiselect).to_be_visible()
        return self

    @step
    def should_see_multiselect_input(self):
        """Asserts the filter/search input is visible (after opening dropdown)."""
        expect(self.project_multiselect_input).to_be_visible()
        return self

    @step
    def should_have_selected(self, project_name: str):
        """Asserts that project_name is shown as the selected project."""
        expect(self.project_multiselect_value).to_have_text(project_name)
        return self

    @step
    def should_see_disabled_multiselect(self, project_name: str):
        """Asserts that project selector is disabled or shown as text."""
        # Try to find disabled multiselect first
        if self.disabled_project_multiselect.count() > 0:
            expect(self.disabled_project_multiselect).to_be_visible()
            expect(self.disabled_project_multiselect_value).to_have_value(project_name)
        else:
            # If not found, look for project name as plain text
            expect(self.page.get_by_text(project_name, exact=True)).to_be_visible()
        return self

    # ----------------------------------
    # Interaction Methods
    # ----------------------------------

    @step
    def open(self):
        """Clicks to open the multiselect project dropdown."""
        self.project_multiselect.click()
        return self

    @step
    def search_for(self, text: str):
        """
        Types in the project multiselect input to filter/search projects.
        Dropdown must be open first.
        """
        self.should_see_multiselect_input()
        self.project_multiselect_input.fill(text)
        return self

    @step
    def select_by_text(self, text: str):
        """
        Selects a project by its visible text.
        Dropdown must be open and filtered unless all options are visible.
        """
        self.page.get_by_text(text, exact=True).click()

        return self

    @step
    def search_and_select_project(self, project_name: str):
        (
            self.open()
            .search_for(project_name)
            .select_by_text(project_name)
            .should_have_selected(project_name)
        )
        return self
