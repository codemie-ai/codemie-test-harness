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

import requests

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.utils.base_utils import BaseUtils


class AdminBudgetUtils(BaseUtils):
    def __init__(self, client):
        super().__init__(client)
        self._headers = {
            "Authorization": f"Bearer {client.token}",
            "Content-Type": "application/json",
        }

    def list_budgets(self, page: int = 0, per_page: int = 10) -> list:
        resp = requests.get(
            f"{API_DOMAIN}/v1/admin/budgets",
            params={"page": page, "per_page": per_page},
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        # PaginatedBudgetListResponse.data (rest_api/models/budget.py), not "items".
        return resp.json().get("data", [])

    def get_budget(self, budget_id: str) -> dict:
        resp = requests.get(
            f"{API_DOMAIN}/v1/admin/budgets/{budget_id}",
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    def update_budget(self, budget_id: str, **fields) -> dict:
        """PATCH /v1/admin/budgets/{budget_id}. At least one field must be given."""
        resp = requests.patch(
            f"{API_DOMAIN}/v1/admin/budgets/{budget_id}",
            json=fields,
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    def _iter_all_budgets(self, per_page: int = 100):
        """Yield every budget across every page, newest first (the API's own order)."""
        page = 0
        while True:
            budgets = self.list_budgets(page=page, per_page=per_page)
            yield from budgets
            if len(budgets) < per_page:
                return
            page += 1

    def find_preconfigured_budget(self) -> dict:
        """First predefined/system budget visible on this stand (``is_preconfigured`` true).

        Searches every page. Raises when none is found, since the preconfigured/system
        budget is a precondition the stand must already seed (AC-3, AC-6, AC-12).
        """
        for budget in self._iter_all_budgets():
            if budget.get("is_preconfigured"):
                return budget
        raise AssertionError("No preconfigured/system budget found on this stand")

    def find_budget_in_list(self, budget_id: str) -> dict | None:
        """The budget with this id as GET /v1/admin/budgets returns it, searching every
        page, or None when it is not present in the list."""
        return next(
            (b for b in self._iter_all_budgets() if b["budget_id"] == budget_id), None
        )

    def create_budget(self, budget_id: str, category: str) -> dict:
        resp = requests.post(
            f"{API_DOMAIN}/v1/admin/budgets",
            json={
                "budget_id": budget_id,
                "name": f"Autotest budget {budget_id}",
                "soft_budget": 50.0,
                "max_budget": 100.0,
                "budget_duration": "30d",
                "budget_category": category,
            },
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    def assign_user_budget(self, user_id: str, category: str, budget_id: str) -> None:
        resp = requests.put(
            f"{API_DOMAIN}/v1/admin/users/{user_id}/budgets",
            json={"assignments": {category: budget_id}},
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()

    def sync_budgets(self) -> dict:
        resp = requests.post(
            f"{API_DOMAIN}/v1/admin/budgets/sync",
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    def unassign_user_budget(self, user_id: str, category: str) -> None:
        resp = requests.put(
            f"{API_DOMAIN}/v1/admin/users/{user_id}/budgets",
            json={"assignments": {category: None}},
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        if resp.status_code == 404:
            return
        resp.raise_for_status()
