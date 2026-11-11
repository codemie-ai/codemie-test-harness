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

"""UI tests for the Budgets management 'Created By' column and the budget details popup.

Covers:
    TC-001 (AC-1, AC-2, AC-10, AC-11, AC-14)  the list column and the details popup both
        show the creator's name, with no extra GET to v1/admin/users
    TC-003 (AC-3, AC-12, AC-13)  a preconfigured/system budget shows "System" and a budget
        with an unresolvable creator shows the em dash "—", in both the list and the popup
    TC-010 (gap from the change, no AC)  the preconfigured budget's row-actions menu now
        offers 'View details' (Edit stays hidden)
"""

import secrets

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.budget_details_popup_page import (
    BudgetDetailsPopupPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.budgets_management_page import (
    BudgetsManagementPage,
)
from codemie_test_harness.tests.utils.admin_budget_utils import AdminBudgetUtils

# ---------------------------------------------------------------------------
# TC-001
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.ui
def test_budget_list_and_popup_show_creator_name_without_users_lookup(
    page, maintainer_client
):
    """@case budget-created-by-column_TC_001

    AC-1/AC-2/AC-10/AC-11: the 'Created By' list column and the details popup's 'Created
    by' row both render the creator's own display name (getBudgetCreatorDisplay,
    BudgetsManagementPage.tsx:114-115, BudgetDetailsPopup.tsx:54).
    AC-14: the budgets store only calls v1/admin/budgets* (store/budgets.ts:75) — neither
    mount issues a GET to v1/admin/users.
    """
    budget_id = f"autotest-cbn-{secrets.token_hex(4)}"
    budget = AdminBudgetUtils(maintainer_client).create_budget(budget_id, "platform")
    creator_name = maintainer_client.users.about_me().name

    budgets_page = BudgetsManagementPage(page)
    budgets_page.capture_requests()
    budgets_page.navigate_to()
    budgets_page.should_have_created_by(budget["name"], creator_name)

    budgets_page.click_view_details(budget["name"])
    popup = BudgetDetailsPopupPage(page)
    popup.should_have_created_by(creator_name)
    popup.close()

    budgets_page.should_not_have_requested("v1/admin/users")


# ---------------------------------------------------------------------------
# TC-003
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.ui
@pytest.mark.parametrize(
    "budget_and_expected_display",
    ["system", "unresolved"],
    indirect=True,
    ids=["preconfigured_system", "unresolved_creator"],
)
def test_budget_list_and_popup_show_missing_creator_state(
    page, budget_and_expected_display
):
    """@case budget-created-by-column_TC_003

    AC-3/AC-12/AC-13: getBudgetCreatorDisplay (budget.ts:98-102) shows "System" for a
    preconfigured/system budget and the em dash "—" for any other budget whose
    created_by_name cannot resolve, in both the list cell and the details popup.
    """
    budget, expected_display = budget_and_expected_display

    budgets_page = BudgetsManagementPage(page)
    budgets_page.navigate_to()
    budgets_page.show_up_to_100_items_per_page()
    budgets_page.should_have_created_by(budget["name"], expected_display)

    budgets_page.click_view_details(budget["name"])
    BudgetDetailsPopupPage(page).should_have_created_by(expected_display)


# ---------------------------------------------------------------------------
# TC-010
# ---------------------------------------------------------------------------


@pytest.mark.budget
@pytest.mark.ui
def test_preconfigured_budget_row_actions_offer_view_details_not_edit(
    page, admin_budget_utils
):
    """@case budget-created-by-column_TC_010

    Gap from the change (no AC): a preconfigured budget's row-actions menu — previously
    absent entirely — now offers 'View details'; 'Edit' stays hidden (canEdit excludes
    is_preconfigured, BudgetsManagementPage.tsx:266).
    """
    budget = admin_budget_utils.find_preconfigured_budget()

    budgets_page = BudgetsManagementPage(page)
    budgets_page.navigate_to()
    budgets_page.show_up_to_100_items_per_page()
    budgets_page.should_offer_view_details_but_not_edit(budget["name"])
