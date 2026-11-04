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

import re

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

    @property
    def cancel_button(self):
        """'Cancel' button (dismiss action) of the modal footer."""
        return self.dialog.get_by_role("button", name="Cancel", exact=True)

    @property
    def override_reason_input(self):
        """'Override reason' textarea."""
        return self.dialog.get_by_label("Override reason")

    @property
    def reset_budget_usage_button(self):
        """Any 'Reset budget usage' button inside the modal (removed from the Members page)."""
        return self.dialog.get_by_role("button", name=re.compile(r"Reset budget usage"))

    @property
    def use_project_allocation_button(self):
        """Per-category 'Use project allocation' action of a fixed override."""
        return self.dialog.get_by_role("button", name="Use project allocation")

    @property
    def undo_button(self):
        """Per-category 'Undo' action shown once 'Use project allocation' is pending."""
        return self.dialog.get_by_role("button", name="Undo")

    def category_card(self, label: str):
        """One category's card (e.g. 'Platform', 'CLI'), resolved from its heading.

        The card is the nearest grid ancestor of the category heading.
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
    def use_project_allocation(self):
        """Click 'Use project allocation' to drop the member's fixed override on save."""
        self.use_project_allocation_button.click()
        return self

    @step
    def use_project_allocation_for(self, label: str):
        """Click 'Use project allocation' on one category's card only."""
        self.category_card(label).get_by_role(
            "button", name="Use project allocation"
        ).click()
        return self

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
        """Verify the override modal is open with limit inputs and a save action.

        With several budget categories the modal holds one input pair per category;
        the first pair stands for them.
        """
        expect(self.dialog).to_be_visible()
        expect(self.hard_limit_input.first).to_be_enabled()
        expect(self.soft_limit_input.first).to_be_enabled()
        expect(self.save_override_button).to_be_visible()
        return self

    @step
    def should_be_closed(self):
        """Verify the override modal is closed."""
        expect(self.dialog).not_to_be_visible()
        return self

    @step
    def should_not_offer_reset_budget_usage(self):
        """Verify the modal has no 'Reset budget usage' button."""
        expect(self.reset_budget_usage_button).to_have_count(0)
        return self

    @step
    def should_offer_cancel_save_and_reason(self):
        """Verify the footer keeps 'Cancel' and 'Save Override' and the reason field remains."""
        expect(self.cancel_button).to_be_visible()
        expect(self.save_override_button).to_be_visible()
        expect(self.override_reason_input).to_be_visible()
        return self

    @step
    def should_mark_category_as_using_project_allocation(self):
        """Verify the category is pending 'use project allocation' (action toggled to 'Undo')."""
        expect(self.undo_button).to_be_visible()
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
    def should_still_offer_use_project_allocation_for(self, label: str):
        """Verify one category's card still holds its override (no 'Undo' pending)."""
        card = self.category_card(label)
        expect(
            card.get_by_role("button", name="Use project allocation")
        ).to_be_visible()
        expect(card.get_by_role("button", name="Undo")).to_have_count(0)
        return self
