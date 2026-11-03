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
from urllib.parse import urlparse

from hamcrest import assert_that, is_not, none
from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.administration.bulk_budget_override_modal_page import (
    BulkBudgetOverrideModalPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.member_budget_override_modal_page import (
    MemberBudgetOverrideModalPage,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


USER_LIST_PATH = "/v1/admin/users"

ALLOCATION_BUTTON_NAME = re.compile(r"^\w+ (-|\$\d[\d,.]*) [/] \$\d")


class ProjectMembersBudgetSection(BasePage):
    """Project members table on the Project Details page, budget allocation aspect."""

    def __init__(self, page):
        super().__init__(page)
        self._user_list_bodies: list = []

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

    def category_allocation(self, email: str, category_label: str):
        """Allocation control of one budget category (e.g. 'CLI') in the member's row."""
        return self.member_row(email).get_by_role(
            "button", name=re.compile(rf"^{re.escape(category_label)}\b")
        )

    def selection_checkbox(self, email: str):
        """Selection checkbox cell of the member's row (bulk actions)."""
        return self.member_row(email).locator("[data-selection-checkbox]")

    @property
    def bulk_actions_bar(self):
        """The 'N selected' bar, located as the parent of its 'Clear selection' button."""
        return self.page.get_by_role("button", name="Clear selection").locator(
            "xpath=.."
        )

    @property
    def bulk_actions_menu_button(self):
        """'Bulk Actions' menu trigger inside the selection bar."""
        return self.bulk_actions_bar.get_by_role("button", name="More options")

    @property
    def bulk_override_budgets_item(self):
        """'Override budgets' item of the bulk actions menu."""
        return self.page.get_by_role("menuitem", name="Override budgets")

    # ── Network capture ───────────────────────────────────────────────────────

    @step
    def capture_user_list_responses(self):
        """Record every GET /v1/admin/users response body the page receives from now on."""
        self.page.on("response", self._record_user_list_response)
        return self

    def _record_user_list_response(self, response):
        if (
            response.request.method == "GET"
            and urlparse(response.url).path.rstrip("/").endswith(USER_LIST_PATH)
            and response.ok
        ):
            self._user_list_bodies.append(response.json())

    def received_personal_budget(self, email: str, category: str):
        """Latest personal budget assignment of the category the client received for the user.

        Returns the assignment dict, or None when no user list response carried one.
        """
        for body in reversed(self._user_list_bodies):
            for user in body.get("data") or body.get("items") or []:
                if user.get("email") != email:
                    continue
                for assignment in user.get("budget_assignments") or []:
                    if assignment.get("category") == category:
                        return assignment
        return None

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def open_override_modal(self, email: str) -> MemberBudgetOverrideModalPage:
        """Click the member's allocation button to open the override modal."""
        self.allocation_button(email).click()
        modal = MemberBudgetOverrideModalPage(self.page)
        modal.should_be_visible()
        return modal

    @step
    def select_members(self, *emails: str):
        """Tick the selection checkbox of every given member and wait for the selection bar."""
        for email in emails:
            self.selection_checkbox(email).click()
        expect(self.bulk_actions_bar).to_contain_text(f"{len(emails)} selected")
        return self

    @step
    def open_bulk_override_modal(self, user_count: int) -> BulkBudgetOverrideModalPage:
        """Open 'Bulk Actions' > 'Override budgets' for the selected members."""
        self.bulk_actions_menu_button.click()
        self.bulk_override_budgets_item.click()
        modal = BulkBudgetOverrideModalPage(self.page)
        modal.should_be_visible(user_count)
        return modal

    def allocation_text(self, email: str) -> str:
        """Text currently shown on the member's allocation button."""
        return self.allocation_button(email).inner_text()

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
    def should_not_show_fixed_allocation_marker(self, email: str):
        """Verify the member's allocation does not carry the 'Overridden' badge."""
        expect(self.allocation_button(email)).not_to_contain_text("Overridden")
        return self

    @step
    def should_show_allocation_text(self, email: str, text: str):
        """Verify the member's allocation button shows exactly the given text."""
        expect(self.allocation_button(email)).to_have_text(text)
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

    @step
    def should_not_show_category_allocation(self, email: str, category_label: str):
        """Verify the member's row shows no allocation (and no spend) for the category."""
        expect(self.category_allocation(email, category_label)).to_have_count(0)
        return self

    @step
    def should_have_received_personal_budget(self, email: str, category: str):
        """Verify the client received a personal budget of the category for the user."""
        assert_that(
            self.received_personal_budget(email, category),
            is_not(none()),
            f"No personal '{category}' budget reached the client for {email}",
        )
        return self
