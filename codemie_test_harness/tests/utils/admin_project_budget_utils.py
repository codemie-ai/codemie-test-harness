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
from codemie_test_harness.tests.test_data.budget_test_data import (
    MIN_PLATFORM_BUDGET,
    PLATFORM_BUDGET_CATEGORIES,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils, poll_until


class AdminProjectBudgetUtils(BaseUtils):
    def __init__(self, client):
        super().__init__(client)
        self._headers = {
            "Authorization": f"Bearer {client.token}",
            "Content-Type": "application/json",
        }

    def override_member(
        self,
        budget_id: str,
        user_id: str,
        allocated_max_budget: float,
        allocated_soft_budget: float,
    ) -> dict:
        resp = requests.patch(
            f"{API_DOMAIN}/v1/admin/project-budgets/{budget_id}/members/{user_id}",
            json={
                "allocated_max_budget": allocated_max_budget,
                "allocated_soft_budget": allocated_soft_budget,
            },
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    def clear_member_override(self, budget_id: str, user_id: str) -> None:
        resp = requests.delete(
            f"{API_DOMAIN}/v1/admin/project-budgets/{budget_id}/members/{user_id}/override",
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        if resp.status_code == 404:
            return
        resp.raise_for_status()

    def wait_until_member_override_permitted(
        self,
        budget_id: str,
        user_id: str,
        allocated_max_budget: float,
        allocated_soft_budget: float,
        timeout: float = 90.0,
    ) -> bool:
        """Poll until the client may consistently override and clear a member allocation.

        A freshly assigned project admin is denied (403) by instances that still
        serve a stale project membership from their process-local cache. Returns
        once several consecutive override/clear round trips are permitted, leaving
        the member without an override; returns False if ``timeout`` elapses first.
        """

        def permitted() -> bool:
            for _ in range(3):
                try:
                    self.override_member(
                        budget_id, user_id, allocated_max_budget, allocated_soft_budget
                    )
                    self.clear_member_override(budget_id, user_id)
                except requests.HTTPError as error:
                    if error.response.status_code == 403:
                        return False
                    raise
            return True

        return poll_until(permitted, bool, timeout=timeout, interval=2.0)

    def get_budget(self, budget_id: str) -> dict:
        resp = requests.get(
            f"{API_DOMAIN}/v1/admin/project-budgets/{budget_id}",
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    def rebalance_budget(self, budget_id: str) -> dict:
        resp = requests.post(
            f"{API_DOMAIN}/v1/admin/project-budgets/{budget_id}/rebalance",
            json={"apply_immediately": True},
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    def create_budget_group(
        self,
        project_name: str,
        name: str,
        categories: dict[str, dict] | None = None,
        budget_duration: str = "30d",
    ) -> dict:
        """Create a project budget group covering one or more categories in a
        single call. `categories` maps category name -> {"max_budget": float,
        "soft_budget": float} (soft_budget optional, defaults to 50% of that
        category's max_budget). Defaults to a single "platform" category with
        max_budget=100.0, soft_budget=50.0 when omitted.

        total_amount (sent to the backend) = sum(max_budget across categories);
        each category's pct = max_budget / total_amount * 100. For a single
        category this reproduces max_budget/soft_budget exactly (pct=100 is
        exact regardless of total_amount); for 2+ bundled categories pct is
        generally a non-terminating fraction, so persisted max_budget may drift
        by a negligible float epsilon.

        Returns the full parsed response: {"group_id": ..., "categories":
        [{"budget_id": ..., "category": ..., "max_budget": ..., ...}, ...], ...}.
        Use budget_ids_by_category(response) for a {category: budget_id} map.

        The backend requires every group to include a "platform" category with
        a hard limit above 0 — if the caller only wants "cli"
        or "premium_models", MIN_PLATFORM_BUDGET is added automatically, so
        the group also gets a (small) real platform budget and LiteLLM key.
        """
        if categories is None:
            categories = PLATFORM_BUDGET_CATEGORIES
        if "platform" not in categories:
            categories = {**categories, "platform": MIN_PLATFORM_BUDGET}
        total_amount = sum(spec["max_budget"] for spec in categories.values())
        payload_categories = {
            category: {
                "pct": (spec["max_budget"] / total_amount) * 100,
                "soft_budget": spec.get("soft_budget", spec["max_budget"] * 0.5),
            }
            for category, spec in categories.items()
        }
        resp = requests.post(
            f"{API_DOMAIN}/v1/admin/project-budget-groups",
            json={
                "project_name": project_name,
                "name": name,
                "total_amount": total_amount,
                "budget_duration": budget_duration,
                "categories": payload_categories,
            },
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def budget_ids_by_category(group_response: dict) -> dict[str, str]:
        """Extract {category: budget_id} from a create_budget_group() response."""
        return {c["category"]: c["budget_id"] for c in group_response["categories"]}

    def delete_budget_group(self, group_id: str) -> None:
        resp = requests.delete(
            f"{API_DOMAIN}/v1/admin/project-budget-groups/{group_id}",
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        if resp.status_code == 404:
            return
        resp.raise_for_status()

    def get_group(self, group_id: str) -> dict:
        resp = requests.get(
            f"{API_DOMAIN}/v1/admin/project-budget-groups/{group_id}",
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    def list_budget_groups(self, project_name: str) -> list:
        """Fetch all budget groups (active + soft-deleted history) for a project."""
        resp = requests.get(
            f"{API_DOMAIN}/v1/admin/project-budget-groups",
            params={"project_name": project_name},
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json().get("items") or []

    def get_group_id_for_project(self, project_name: str) -> str:
        """Return the currently-active budget group's group_id for a project."""
        for group in self.list_budget_groups(project_name):
            if group.get("deleted_at") is None:
                return group["group_id"]
        raise ValueError(f"No active budget group found for project: {project_name}")

    def cleanup_active_budget_groups(self, project_name: str) -> None:
        """Delete the currently-active budget group for a project, if any.

        A project can have only one active budget group at a time (the backend
        409s a create otherwise) — call this before create_budget_group() when
        reusing a shared/session-scoped project across many tests.
        """
        for group in self.list_budget_groups(project_name):
            if group.get("deleted_at") is None:
                self.delete_budget_group(group["group_id"])

    def rebalance_budget_group(self, group_id: str) -> dict:
        resp = requests.post(
            f"{API_DOMAIN}/v1/admin/project-budget-groups/{group_id}/rebalance",
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    def update_budget_group_category(
        self,
        group_id: str,
        category: str,
        max_budget: float | None = None,
        soft_budget: float | None = None,
        budget_duration: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> dict:
        """Update a budget group. `name`/`description` update the GROUP's own
        fields (there is no endpoint to update an individual category budget's
        name/description after creation — confirmed via backend source).

        `max_budget`/`soft_budget`/`budget_duration` update the given category's
        underlying Budget row. The backend only recomputes a category's amount
        when the PUT body's `categories` field is present at all (sending
        total_amount alone is a no-op for amounts), and omitting `soft_budget`
        within a category entry resets it to a default percentage of the new
        max_budget rather than preserving it — so every category (the one being
        changed and every sibling) must be resent explicitly with its current
        values, and total_amount/pct recomputed across all of them.
        """
        payload: dict = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description

        if (
            max_budget is not None
            or soft_budget is not None
            or budget_duration is not None
        ):
            current = self.get_group(group_id)
            current_by_category = {c["category"]: c for c in current["categories"]}
            if category not in current_by_category:
                raise ValueError(f"Category {category!r} not in group {group_id}")

            resolved = {
                cat: {
                    "max_budget": max_budget
                    if cat == category and max_budget is not None
                    else c["max_budget"],
                    "soft_budget": soft_budget
                    if cat == category and soft_budget is not None
                    else c["soft_budget"],
                }
                for cat, c in current_by_category.items()
            }
            new_total_amount = sum(spec["max_budget"] for spec in resolved.values())
            payload["total_amount"] = new_total_amount
            payload["categories"] = {
                cat: {
                    "pct": (spec["max_budget"] / new_total_amount) * 100,
                    "soft_budget": spec["soft_budget"],
                }
                for cat, spec in resolved.items()
            }
            if budget_duration is not None:
                payload["budget_duration"] = budget_duration

        resp = requests.put(
            f"{API_DOMAIN}/v1/admin/project-budget-groups/{group_id}",
            json=payload,
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
        return resp.json()

    def reset_user_budget(self, user_id: str) -> None:
        resp = requests.post(
            f"{API_DOMAIN}/v1/admin/users/{user_id}/budgets/reset",
            json={"categories": []},
            headers=self._headers,
            verify=VERIFY_SSL,
        )
        resp.raise_for_status()
