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

"""Expected messages and parameters of the budget delete tests.

The messages come from ``BudgetService.delete_budget`` (budget_service.py): the 409, 404
and 403 texts below are the contract the API returns for a refused delete.
"""

import secrets

# Parameters of the LiteLLM state the budget is in when it is deleted.
LITELLM_PRESENT = "present"
LITELLM_ALREADY_ABSENT = "already_absent"

DELETE_REASON_MANUAL = "manual_delete"


def budget_in_use_message(budget_id: str, user_count: int) -> str:
    """409 text of a delete refused because users are assigned ("user" for exactly one)."""
    users_label = "user" if user_count == 1 else "users"
    return f"Budget '{budget_id}' is in use: {user_count} {users_label} assigned"


def budget_not_found_message(budget_id: str) -> str:
    """404 text of a delete for an id that is not a global budget."""
    return f"Budget '{budget_id}' not found"


def budget_preconfigured_delete_message(budget_id: str) -> str:
    """403 text of a delete for a preconfigured budget."""
    return f"Budget '{budget_id}' is preconfigured and cannot be deleted via API"


def unknown_budget_id() -> str:
    """An id no budget has."""
    return f"autotest-missing-{secrets.token_hex(6)}"
