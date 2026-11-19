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

"""Texts of the budget delete flow on the Budgets management page.

The strings come from BudgetsManagementPage.tsx (delete confirmation message,
``getDeleteBlockedHint``, the success toast).
"""


def delete_confirmation_message(budget_name: str, budget_id: str) -> str:
    """Text of the delete confirmation dialog on the Budgets management page."""
    return f'Delete budget "{budget_name}" ({budget_id})? This cannot be undone.'


def delete_blocked_tooltip(user_count: int) -> str:
    """Tooltip of the disabled Delete item of a budget with assigned users."""
    assigned = "1 user is" if user_count == 1 else f"{user_count} users are"
    return f"{assigned} assigned to this budget. Unassign them before deleting."


BUDGET_DELETED_TOAST = "Budget deleted successfully"
