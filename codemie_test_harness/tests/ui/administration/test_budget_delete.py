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

"""UI tests for deleting a budget on the Budgets management page.

Only a maintainer manages budgets, so the browser logs in as a maintainer. The budgets are
created (and assigned) through the API; the budget of TC-009 is deleted through the UI.

Covers:
    TC-009 (AC-1)  the row menu offers Delete, the confirmation names the budget, the toast
        shows and the row is gone
    TC-010 (AC-2)  Delete is disabled with a tooltip while a user is assigned
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.budgets_management_page import (
    BudgetsManagementPage,
)
from codemie_test_harness.tests.ui.test_data.budget_delete_ui_test_data import (
    BUDGET_DELETED_TOAST,
    delete_blocked_tooltip,
    delete_confirmation_message,
)


@pytest.mark.budget
@pytest.mark.ui
@pytest.mark.parametrize("acting_credentials", ["maintainer"], indirect=True)
def test_maintainer_deletes_budget_from_budgets_page(page, manual_budget):
    """@case delete-budget_TC_009

    AC-1: Delete is offered in the budget's row menu, choosing it asks 'Delete budget
    "<name>" (<id>)? This cannot be undone.', confirming shows 'Budget deleted successfully'
    and the row disappears (BudgetsManagementPage.tsx:239, :389).
    """
    budget_name = manual_budget["name"]

    budgets_page = BudgetsManagementPage(page)
    budgets_page.navigate_to()
    budgets_page.show_up_to_100_items_per_page()
    budgets_page.find_budget_row(budget_name)
    budgets_page.open_row_actions(budget_name)
    budgets_page.should_offer_delete()

    budgets_page.choose_delete()
    budgets_page.should_ask_to_confirm_delete(
        delete_confirmation_message(budget_name, manual_budget["budget_id"])
    )

    budgets_page.confirm_delete()
    budgets_page.should_see_budget_deleted_toast(BUDGET_DELETED_TOAST)
    budgets_page.should_not_see_budget_row(budget_name)


@pytest.mark.budget
@pytest.mark.ui
@pytest.mark.parametrize("acting_credentials", ["maintainer"], indirect=True)
def test_delete_is_disabled_with_tooltip_while_users_are_assigned(
    page, manual_budget, assign_budget_user, platform_user
):
    """@case delete-budget_TC_010

    AC-2: the Delete item of a budget with one assigned user is disabled and its tooltip
    reads '1 user is assigned to this budget. Unassign them before deleting.'
    (BudgetsManagementPage.tsx:121-125).
    """
    budget_name = manual_budget["name"]
    assign_budget_user(platform_user.user_id)

    budgets_page = BudgetsManagementPage(page)
    budgets_page.navigate_to()
    budgets_page.show_up_to_100_items_per_page()
    budgets_page.find_budget_row(budget_name)
    budgets_page.open_row_actions(budget_name)
    budgets_page.should_see_delete_disabled()

    budgets_page.hover_delete_item()
    budgets_page.should_see_delete_tooltip(delete_blocked_tooltip(1))
