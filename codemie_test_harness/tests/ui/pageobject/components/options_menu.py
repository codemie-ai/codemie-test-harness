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

"""The "Options" popup menu the application cards and pages open from their More options button."""

import re

from playwright.sync_api import Locator, expect
from reportportal_client import step


class OptionsMenu:
    """Popup menu named "Options" (role menu) with a row per action (role menuitem)."""

    def __init__(self, page):
        self.page = page

    @property
    def menu(self) -> Locator:
        """The open menu."""
        return self.page.get_by_role("menu", name="Options")

    def item(self, name: str) -> Locator:
        """The menu row with exactly this name."""
        return self.menu.get_by_role("menuitem", name=name, exact=True)

    @step
    def should_be_open(self):
        """Verify the menu is shown."""
        expect(self.menu).to_be_visible()
        return self

    @step
    def should_list_item(self, name: str):
        """Verify the menu has a row with this name."""
        expect(self.item(name)).to_be_visible()
        return self

    @step
    def should_not_list_item(self, name: str):
        """Verify the open menu has no row with this name."""
        self.should_be_open()
        expect(self.item(name)).to_have_count(0)
        return self

    @step
    def should_list_only_items(self, names: list[str]):
        """Verify the menu has exactly these rows, in this order, and no others."""
        self.should_be_open()
        expect(self.menu.get_by_role("menuitem")).to_have_text(names)
        return self

    @step
    def should_list_items_matching(self, pattern: str, names: list[str]):
        """Verify the rows whose name contains the pattern (any case) are exactly these, in order."""
        self.should_be_open()
        rows = self.menu.get_by_role("menuitem").filter(
            has_text=re.compile(pattern, re.IGNORECASE)
        )
        if names:
            expect(rows).to_have_text(names)
        else:
            expect(rows).to_have_count(0)
        return self

    @step
    def should_have_item_enabled(self, name: str):
        """Verify the row can be chosen."""
        expect(self.item(name)).to_be_enabled()
        return self

    @step
    def should_have_item_disabled_with_tooltip(self, name: str, tooltip: str):
        """Verify the row cannot be chosen and explains why in its tooltip."""
        expect(self.item(name)).to_be_disabled()
        expect(self.item(name)).to_have_attribute("data-tooltip-content", tooltip)
        return self

    @step
    def choose_item(self, name: str):
        """Choose the row with this name."""
        self.item(name).click()
        return self

    @step
    def close(self):
        """Close the menu with Escape."""
        self.page.keyboard.press("Escape")
        expect(self.menu).to_be_hidden()
        return self
