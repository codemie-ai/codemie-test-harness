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

"""Utilities for project budget group operations."""

from codemie_test_harness.tests.utils.base_utils import BaseUtils


class AdminProjectBudgetGroupUtils(BaseUtils):
    """Wraps GET and PUT for /v1/admin/project-budget-groups/{group_id}.

    Uses the SDK-first pattern via ``client.project_budget_groups``.
    """

    def list_by_project(self, project_name: str) -> list:
        """List all budget groups for a project and return the items list.

        Args:
            project_name: The project name to query.

        Returns:
            List of budget group dicts; each has a ``group_id`` UUID key.
        """
        response = self.client.project_budget_groups.list_by_project(project_name)
        return response.get("items", [])

    def get_group_id_for_project(self, project_name: str) -> str:
        """Return the UUID of the first (and typically only) budget group for a project.

        Args:
            project_name: The project name to query.

        Returns:
            The ``group_id`` UUID string.

        Raises:
            ValueError: If no budget group is found for the project.
        """
        items = self.list_by_project(project_name)
        if not items:
            raise ValueError(f"No budget group found for project: {project_name}")
        group_id = items[0].get("group_id")
        if not group_id:
            raise ValueError(
                f"Budget group for project '{project_name}' has no 'group_id' field; "
                f"got keys: {list(items[0].keys())}"
            )
        return group_id

    def get_category_budgets(self, group_id: str) -> dict:
        """Return {category_name: max_budget} extracted from a budget group GET response.

        Args:
            group_id: The budget group identifier.

        Returns:
            Mapping of category name to max_budget dollar value.
        """
        group_data = self.get_group(group_id)
        result = {}
        for item in group_data.get("categories", []):
            cat = item.get("category")
            max_budget = item.get("max_budget")
            if cat is not None and max_budget is not None:
                try:
                    result[cat] = float(max_budget)
                except (TypeError, ValueError):
                    pass
        return result

    def get_category_soft_budgets(self, group_id: str) -> dict:
        """Return {category_name: soft_budget} extracted from a budget group GET response.

        Args:
            group_id: The budget group identifier.

        Returns:
            Mapping of category name to soft_budget dollar value.
        """
        group_data = self.get_group(group_id)
        result = {}
        for item in group_data.get("categories", []):
            cat = item.get("category")
            soft_budget = item.get("soft_budget")
            if cat is not None and soft_budget is not None:
                try:
                    result[cat] = float(soft_budget)
                except (TypeError, ValueError):
                    pass
        return result

    def get_group(self, group_id: str) -> dict:
        """Retrieve a project budget group by its ID.

        Args:
            group_id: The budget group identifier (same as the budget_id used
                      when calling ``admin_project_budget_utils.create_budget``).

        Returns:
            Budget group data as dict.
        """
        return self.client.project_budget_groups.get(group_id)

    def update_group(self, group_id: str, categories: dict) -> dict:
        """Update the spend bucket distribution for a project budget group.

        Args:
            group_id: The budget group identifier.
            categories: Mapping of category name to percentage,
                        e.g. ``{"platform": 60.0, "cli": 40.0}``.

        Returns:
            Updated budget group data as dict.
        """
        return self.client.project_budget_groups.update(group_id, categories)

    def update_raw(self, group_id: str, body: dict) -> dict:
        """Update a budget group with an arbitrary request body.

        Used in tests to verify field-level restrictions.

        Args:
            group_id: The budget group identifier.
            body: Arbitrary JSON body for the PUT request.

        Returns:
            Updated budget group data as dict.
        """
        return self.client.project_budget_groups._update_raw(group_id, body)

    def create_budget_group(
        self,
        project_name: str,
        total_amount: float = 100.0,
        budget_duration: str = "30d",
        categories: dict | None = None,
    ) -> dict:
        """Create a new project budget group via POST.

        Args:
            project_name: The project this group belongs to.
            total_amount: Total budget hard limit.
            budget_duration: Budget reset period, e.g. ``"30d"``.
            categories: Flat category percentage map, e.g. ``{"platform": 100.0}``.
                        Defaults to ``{"platform": 100.0}``.

        Returns:
            Created budget group dict; includes ``group_id`` UUID.
        """
        if categories is None:
            categories = {"platform": 100.0}
        return self.client.project_budget_groups.create(
            project_name=project_name,
            name=project_name,
            total_amount=total_amount,
            budget_duration=budget_duration,
            categories=categories,
        )

    def delete_budget_group(self, group_id: str) -> None:
        """Delete a project budget group by its UUID.

        Args:
            group_id: UUID of the budget group to delete.
        """
        self.client.project_budget_groups.delete(group_id)
