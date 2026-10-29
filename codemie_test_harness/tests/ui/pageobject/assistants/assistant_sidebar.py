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

from playwright.sync_api import Page, Locator
from reportportal_client import step


class AssistantSidebar:
    """Page Object Model for the Assistants Page Sidebar."""

    def __init__(self, page: Page):
        self.page = page

    # --- Locators ---

    @property
    def main_sidebar(self) -> Locator:
        """The sidebar <aside>."""
        return self.page.locator("aside.flex.flex-col.border-r.bg-sidebar-gradient")

    @property
    def title(self) -> Locator:
        """Sidebar title: 'Assistants'."""
        return self.main_sidebar.locator("h2:text-is('Assistants')")

    @property
    def subtitle(self) -> Locator:
        """Sidebar subtitle paragraph."""
        return self.main_sidebar.locator("p.text-sm.text-text-secondary")

    @property
    def categories_label(self) -> Locator:
        """The 'Categories' label/heading."""
        return self.main_sidebar.locator("span:text-is('Categories')")

    @property
    def categories_list(self) -> Locator:
        """<ul> under 'Categories'."""
        return self.categories_label.locator("xpath=../../ul")

    @property
    def category_items(self) -> Locator:
        """All category <li> elements."""
        return self.categories_list.locator("li")

    def category_button(self, name: str) -> Locator:
        """Button for a category by visible text."""
        return self.categories_list.locator(f"button:has-text('{name}')")

    @property
    def filters_label(self) -> Locator:
        """'Filters' span above filters section."""
        return self.main_sidebar.locator("span:text-is('Filters')")

    @property
    def clear_all_filters_button(self) -> Locator:
        """'Clear all' filter reset button."""
        return self.main_sidebar.locator("button:has-text('Clear all')")

    @property
    def search_input(self) -> Locator:
        """Filter/search input."""
        return self.main_sidebar.locator("input[placeholder='Search']")

    # Accordion and filter options are unique/complex:
    def accordion_tab(self, tab_title: str) -> Locator:
        """Accordion tab by title, e.g. 'PROJECT', 'CREATED BY', ..."""
        return self.main_sidebar.locator(
            f".p-accordion-header-text span:has-text('{tab_title.upper()}')"
        ).locator("xpath=../../..")

    def multiselect_filter(self, label: str) -> Locator:
        """Filter dropdown by its label in filter accordion, e.g. 'Project'."""
        return self.main_sidebar.locator(f".p-multiselect-label:has-text('{label}')")

    def created_by_input(self) -> Locator:
        """Input for 'Created By' filter."""
        return self.main_sidebar.locator("input[placeholder='Created By']")

    def radio_filter_option(self, label: str) -> Locator:
        """Radio 'Shared' filter options like All/With Project/Not Shared."""
        return (
            self.main_sidebar.locator(f"label.flex.items-center span:text('{label}')")
            .locator("xpath=..")
            .locator("input[type='radio']")
        )

    # --- Methods ---

    @step
    def click_category(self, name: str):
        """Clicks on a category item by label."""
        self.category_button(name).click()

    @step
    def select_filter_tab(self, tab_title: str):
        """Expands a filter accordion tab by label."""
        tab = self.accordion_tab(tab_title)
        tab.locator("a.p-accordion-header-link").click()

    @step
    def clear_filters(self):
        """Clicks the 'Clear all' button in filters."""
        self.clear_all_filters_button.click()

    @step
    def search(self, text: str):
        """Sets sidebar search/filter."""
        self.search_input.fill(text)

    @step
    def select_multiselect_option(self, label: str):
        """Clicks on a filter dropdown and selects the label (if supported)."""
        ms = self.multiselect_filter(label)
        ms.click()
        ms.locator(f"..//li[.='{label}']").click()

    @step
    def set_created_by(self, author: str):
        """Sets the 'Created By' filter text."""
        input_field = self.created_by_input()
        input_field.fill(author)

    @step
    def select_radio_option(self, option_label: str):
        """Selects a radio option for shared status."""
        self.radio_filter_option(option_label).check(force=True)

    @step
    def visible_categories(self):
        """Returns the names of all visible categories."""
        return [
            self.category_items.nth(i).inner_text().strip()
            for i in range(self.category_items.count())
        ]

    @step
    def visible_filter_radios(self):
        """Returns the text values of radio options in Shared filter."""
        # Find all labels within the 'Shared' tab
        tab = self.accordion_tab("SHARED")
        radios = tab.locator("label.flex.items-center")
        return [radios.nth(i).inner_text().strip() for i in range(radios.count())]
