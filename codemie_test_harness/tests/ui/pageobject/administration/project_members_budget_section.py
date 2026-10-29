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

"""Page object for the Project members table (budget allocation column) on the
Project Details administration page.

URL: /settings/administration/projects/{project_name}

Project Admins and Maintainers see a 'Budget Allocations' column whose per-row
'<Category> $spent / $allocated' button opens the member budget override modal.
Members without those rights get the table with User/Role columns only.
"""

import re

from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.administration.member_budget_override_modal_page import (
    MemberBudgetOverrideModalPage,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


ALLOCATION_BUTTON_NAME = re.compile(r"^\w+ (-|\$\d[\d,.]*) [/] \$\d")


class ProjectMembersBudgetSection(BasePage):
    """Project members table on the Project Details page, budget allocation aspect."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def user_column_header(self):
        """'User' column header of the members table."""
        return self.page.get_by_role("columnheader", name="User", exact=True)

    @property
    def allocation_column_header(self):
        """'Budget Allocations' column header of the members table."""
        return self.page.get_by_role("columnheader", name="Budget Allocations")

    @property
    def allocation_buttons(self):
        """Every per-member '<Category> $spent / $allocated' button in the table."""
        return self.page.get_by_role("button", name=ALLOCATION_BUTTON_NAME)

    def member_row(self, email: str):
        """Members table row of the user with the given email."""
        return self.page.get_by_role("row").filter(has_text=email)

    def allocation_button(self, email: str):
        """Budget allocation button (override control) in the member's row."""
        return self.member_row(email).get_by_role("button", name=ALLOCATION_BUTTON_NAME)

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def open_override_modal(self, email: str) -> MemberBudgetOverrideModalPage:
        """Click the member's allocation button to open the override modal."""
        self.allocation_button(email).click()
        modal = MemberBudgetOverrideModalPage(self.page)
        modal.should_be_visible()
        return modal

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_list_member(self, email: str):
        """Verify the members table lists the given user."""
        expect(self.user_column_header).to_be_visible()
        expect(self.member_row(email)).to_be_visible()
        return self

    @step
    def should_show_allocation_column(self):
        """Verify the 'Budget Allocations' column is rendered."""
        expect(self.allocation_column_header).to_be_visible()
        return self

    @step
    def should_show_override_control(self, email: str):
        """Verify the member's allocation button is visible and enabled."""
        expect(self.allocation_button(email)).to_be_visible()
        expect(self.allocation_button(email)).to_be_enabled()
        return self

    @step
    def should_show_allocation(self, email: str, spent: float, allocated: float):
        """Verify the member's allocation button shows '$spent / $allocated'.

        Zero spend is rendered as '-', and the text nodes carry no whitespace
        between them, so the match tolerates both.
        """
        spent_pattern = r"(?:-|\$0\.00)" if spent == 0 else re.escape(f"${spent:,.2f}")
        expect(self.allocation_button(email)).to_contain_text(
            re.compile(rf"{spent_pattern}\s*/\s*{re.escape(f'${allocated:,.2f}')}")
        )
        return self

    @step
    def should_show_fixed_allocation_marker(self, email: str):
        """Verify the member's allocation carries the 'Overridden' badge."""
        expect(self.allocation_button(email)).to_contain_text("Overridden")
        return self

    @step
    def should_not_show_error_notification(self):
        """Verify no error toast is displayed."""
        expect(self.error_toast).not_to_be_visible()
        return self

    @step
    def should_not_show_allocation_column(self):
        """Verify the 'Budget Allocations' column is not rendered."""
        expect(self.allocation_column_header).to_have_count(0)
        return self

    @step
    def should_not_show_override_controls(self):
        """Verify no member allocation / override buttons are rendered."""
        expect(self.allocation_buttons).to_have_count(0)
        return self
