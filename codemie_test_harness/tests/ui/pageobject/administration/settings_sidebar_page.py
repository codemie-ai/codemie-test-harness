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

"""Page object for the Settings sidebar navigation.

Provides assertions for the Administration section items:
  - Projects management
  - Users management
  - Budgets management

Locators derived from live UI inspection on 2026-08-18.
The sidebar renders as a complementary landmark with nested navigation lists.
"""

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class SettingsSidebarPage(BasePage):
    """Settings sidebar shared component — Administration navigation items."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def administration_section_button(self):
        """'Administration' expandable group button in the sidebar."""
        return self.page.get_by_role("button", name="Administration")

    @property
    def budgets_item(self):
        """'Budgets management' navigation button in the Administration section."""
        return self.page.get_by_role("button", name="Budgets management")

    @property
    def projects_item(self):
        """'Projects management' navigation button in the Administration section."""
        return self.page.get_by_role("button", name="Projects management")

    @property
    def users_item(self):
        """'Users management' navigation button in the Administration section."""
        return self.page.get_by_role("button", name="Users management")

    @property
    def customer_configuration_item(self):
        """'Customer Configuration' navigation button in the Administration section."""
        return self.page.get_by_role("button", name="Customer Configuration")

    def _sidebar_item(self, item_name: str):
        """Locate a sidebar navigation button by its exact label."""
        return self.page.get_by_role("button", name=item_name)

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def expand_administration_section(self):
        """Expand the Administration section if it is collapsed."""
        btn = self.administration_section_button
        if btn.get_attribute("aria-expanded") == "false":
            btn.click()
            expect(self.customer_configuration_item).to_be_visible(timeout=5000)
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_see_sidebar_item(self, item: str):
        """Assert a named sidebar item is visible.

        Args:
            item: Exact label of the sidebar button, e.g. 'Projects management'.
        """
        expect(self._sidebar_item(item)).to_be_visible(timeout=10000)
        return self

    @step
    def should_not_see_sidebar_item(self, item: str):
        """Assert a named sidebar item is NOT present in the DOM.

        Args:
            item: Exact label of the sidebar button.
        """
        expect(self._sidebar_item(item)).to_have_count(0)
        return self

    @step
    def navigate_to_customer_configuration(self):
        """Click the 'Customer Configuration' item in the Administration section.

        Returns:
            ``self`` for chaining.
        """
        self.expand_administration_section()
        self.customer_configuration_item.click()
        return self
