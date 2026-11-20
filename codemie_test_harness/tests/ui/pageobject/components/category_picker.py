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

"""The category multiselect the hosted-application form, publish dialog and catalog filter share."""

import re

from playwright.sync_api import Locator, Page, expect
from reportportal_client import step

# The picker is named "Categories" in the form and the filter, and "Select up to 3 categories"
# in the publish dialog.
PICKER_NAME = re.compile("categories", re.IGNORECASE)


class CategoryPicker:
    """A multiselect of categories inside one container of the page.

    The options list opens in an overlay outside the container, so options are looked up on the
    page; only one picker is open at a time.
    """

    def __init__(self, page: Page, container: Locator):
        self.page = page
        self.container = container

    @property
    def combobox(self) -> Locator:
        """The focusable control of the picker."""
        return self.container.get_by_role("combobox", name=PICKER_NAME)

    @property
    def options_list(self) -> Locator:
        """The open list of categories."""
        return self.page.get_by_role("listbox")

    def option(self, name: str) -> Locator:
        """The row of the category with exactly this name in the open list."""
        return self.options_list.get_by_role("option").filter(
            has=self.page.get_by_text(name, exact=True)
        )

    @property
    def picked_options(self) -> Locator:
        """The rows of the open list that are picked."""
        return self.options_list.get_by_role("option", selected=True)

    @step
    def open(self):
        """Open the list of categories from the keyboard."""
        self.combobox.focus()
        self.page.keyboard.press("ArrowDown")
        expect(self.options_list).to_be_visible()
        return self

    @step
    def close(self):
        """Close the list with Escape; the picker keeps the focus."""
        self.page.keyboard.press("Escape")
        expect(self.options_list).to_be_hidden()
        return self

    @step
    def pick(self, name: str):
        """Toggle a category in the open list."""
        self.option(name).click()
        return self

    @step
    def toggle(self, names: list[str]):
        """Open the list, toggle each category and close the list."""
        self.open()
        for name in names:
            self.pick(name)
        return self.close()

    @step
    def should_have_picked(self, names: list[str]):
        """Exactly these categories are picked: the list is opened to read it, then closed."""
        self.open()
        expect(self.picked_options).to_have_count(len(names))
        for name in names:
            expect(self.option(name)).to_have_attribute("aria-selected", "true")
        return self.close()

    @step
    def should_not_have_picked(self, name: str):
        """The category is not picked: the list is opened to read it, then closed."""
        self.open()
        expect(self.option(name)).to_have_attribute("aria-selected", "false")
        return self.close()
