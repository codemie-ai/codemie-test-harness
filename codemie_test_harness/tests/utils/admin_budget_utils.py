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

    def list_budgets(self, per_page: int = 10) -> list:
        resp = requests.get(
            f"{API_DOMAIN}/v1/admin/budgets",
            params={"per_page": per_page},
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])

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

    def sync_budgets(self) -> None:
        resp = requests.post(
            f"{API_DOMAIN}/v1/admin/budgets/sync",
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()

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
