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

    @property
    def use_project_allocation_button(self):
        """Any 'Use project allocation' action of the modal's category cards."""
        return self.dialog.get_by_role("button", name="Use project allocation")

    def category_card(self, label: str):
        """One category's card (e.g. 'Platform', 'CLI') of the bulk modal, resolved from its heading.

        The card is the nearest grid ancestor of the category heading, as in the member modal.
        """
        heading = self.dialog.get_by_role("heading", name=label, exact=True)
        return heading.locator("xpath=ancestor::div[contains(@class, 'grid')][1]")

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def cancel(self):
        """Click 'Cancel' to dismiss the modal without saving."""
        self.cancel_button.click()
        return self

    @step
    def use_project_allocation_for(self, label: str):
        """Click 'Use project allocation' on one category's card only."""
        self.category_card(label).get_by_role(
            "button", name="Use project allocation"
        ).click()
        return self

    @step
    def undo_for(self, label: str):
        """Click 'Undo' on one category's card to cancel its pending 'use project allocation'."""
        self.category_card(label).get_by_role("button", name="Undo").click()
        return self

    @step
    def set_hard_limit_for(self, label: str, value: float):
        """Enter the hard limit of one category's card."""
        self.category_card(label).get_by_role("textbox", name="Hard Limit").fill(
            str(value)
        )
        return self

    @step
    def save_override(self):
        """Click 'Save Override' in the modal footer."""
        self.save_override_button.click()
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
    def should_offer_use_project_allocation_for(self, label: str):
        """Verify one category's card offers 'Use project allocation'."""
        expect(
            self.category_card(label).get_by_role(
                "button", name="Use project allocation"
            )
        ).to_be_visible()
        return self

    @step
    def should_not_offer_use_project_allocation(self):
        """Verify no category card of the modal offers 'Use project allocation'."""
        expect(self.use_project_allocation_button).to_have_count(0)
        return self

    @step
    def should_show_undo_for(self, label: str):
        """Verify one category's card is pending 'use project allocation' ('Undo' offered)."""
        card = self.category_card(label)
        expect(card.get_by_role("button", name="Undo")).to_be_visible()
        expect(card.get_by_role("button", name="Use project allocation")).to_have_count(
            0
        )
        return self

    @step
    def should_show_hard_limit_for(self, label: str, value: re.Pattern):
        """Verify one category's card shows the given hard limit."""
        expect(
            self.category_card(label).get_by_role("textbox", name="Hard Limit")
        ).to_have_value(value)
        return self

    @step
    def should_show_saved_toast(self, text: str):
        """Verify the success toast of a saved bulk override is shown."""
        self.toast.should_show(text)
        return self

    @step
    def should_be_closed(self):
        """Verify the bulk modal is closed."""
        expect(self.dialog).not_to_be_visible()
        return self

    @step
    def should_disable_save_override(self):
        """Verify 'Save Override' is disabled, i.e. no category is pending a change."""
        expect(self.save_override_button).to_be_disabled()
        return self
