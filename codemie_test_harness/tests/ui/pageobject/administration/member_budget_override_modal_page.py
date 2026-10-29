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

"""Page object for the member 'Budget Override' modal on the Project Details page.

Opened by clicking a member's budget allocation button in the Project members table.
"""

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class MemberBudgetOverrideModalPage(BasePage):
    """Modal used to set a fixed hard/soft allocation for one project member."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def dialog(self):
        """The 'Budget Override — <member>' dialog."""
        return self.page.get_by_role("dialog").filter(has_text="Budget Override")

    @property
    def hard_limit_input(self):
        """Hard limit numeric input."""
        return self.dialog.get_by_role("textbox", name="Hard Limit")

    @property
    def soft_limit_input(self):
        """Soft limit numeric input."""
        return self.dialog.get_by_role("textbox", name="Soft Limit")

    @property
    def save_override_button(self):
        """'Save Override' button."""
        return self.dialog.get_by_role("button", name="Save Override")

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def set_hard_limit(self, value: float):
        """Enter the hard limit."""
        self.hard_limit_input.fill(str(value))
        return self

    @step
    def set_soft_limit(self, value: float):
        """Enter the soft limit."""
        self.soft_limit_input.fill(str(value))
        return self

    @step
    def save_override(self):
        """Click 'Save Override'."""
        self.save_override_button.click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self):
        """Verify the override modal is open with both limit inputs and a save action."""
        expect(self.dialog).to_be_visible()
        expect(self.hard_limit_input).to_be_enabled()
        expect(self.soft_limit_input).to_be_enabled()
        expect(self.save_override_button).to_be_visible()
        return self

    @step
    def should_be_closed(self):
        """Verify the override modal is closed."""
        expect(self.dialog).not_to_be_visible()
        return self
