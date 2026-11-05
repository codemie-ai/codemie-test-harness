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

"""Page object for the bulk 'Budget Override — N users' modal on the Project Details page.

Opened from the Members tab: select members, then 'Bulk Actions' > 'Override budgets'.
"""

import re

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class BulkBudgetOverrideModalPage(BasePage):
    """Modal used to override budget allocations of several project members at once."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def dialog(self):
        """The 'Budget Override — N users' dialog."""
        return self.page.get_by_role("dialog").filter(
            has_text=re.compile(r"Budget Override — \d+ users")
        )

    @property
    def cancel_button(self):
        """'Cancel' button of the modal footer."""
        return self.dialog.get_by_role("button", name="Cancel", exact=True)

    @property
    def save_override_button(self):
        """'Save Override' button of the modal footer."""
        return self.dialog.get_by_role("button", name="Save Override")

    @property
    def reset_budget_usage_button(self):
        """Any 'Reset budget usage for N users' button inside the modal."""
        return self.dialog.get_by_role("button", name=re.compile(r"Reset budget usage"))

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def cancel(self):
        """Click 'Cancel' to dismiss the modal without saving."""
        self.cancel_button.click()
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self, user_count: int):
        """Verify the bulk modal is open for the given number of users."""
        expect(self.dialog).to_contain_text(f"Budget Override — {user_count} users")
        expect(self.save_override_button).to_be_visible()
        return self

    @step
    def should_not_offer_reset_budget_usage(self):
        """Verify the modal has no 'Reset budget usage for N users' button."""
        expect(self.reset_budget_usage_button).to_have_count(0)
        return self

    @step
    def should_offer_cancel_and_save(self):
        """Verify the footer keeps 'Cancel' and 'Save Override'."""
        expect(self.cancel_button).to_be_visible()
        expect(self.save_override_button).to_be_visible()
        return self

    @step
    def should_be_closed(self):
        """Verify the bulk modal is closed."""
        expect(self.dialog).not_to_be_visible()
        return self
