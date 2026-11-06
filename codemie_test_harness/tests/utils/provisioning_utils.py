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

"""Create the projects, cost centers and budgets provisioning tests need, read back what a
provisioning call changed, and remove everything afterwards."""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils, get_random_name
from codemie_test_harness.tests.utils.cost_center_utils import (
    get_random_cost_center_name,
)
from codemie_test_harness.tests.utils.project_budget_groups import ProjectBudget

logger = logging.getLogger(__name__)

PROVISIONING_PATH_PREFIX = "/v1/provisioning"


@dataclass(frozen=True)
class ProjectState:
    """What a provisioning call can change on a project; equal states mean nothing changed."""

    exists: bool
    cost_center: str | None = None
    admin_ids: frozenset[str] = field(default_factory=frozenset)
    member_ids: frozenset[str] = field(default_factory=frozenset)
    group_id: str | None = None
    categories: tuple[tuple[str, float], ...] = ()


class ProvisioningUtils(BaseUtils):
    """Admin-side helper for provisioning tests.

    Every project and cost center name it hands out is remembered, so ``cleanup`` also removes
    what a provisioning call created under that name. Request this fixture after the user
    fixtures a test uses, so the users still exist when their projects are removed.
    """

    def __init__(
        self,
        client,
        project_utils,
        cost_center_utils,
        project_budget_groups,
    ):
        super().__init__(client)
        self._projects = project_utils
        self._cost_centers = cost_center_utils
        self._budget_groups = project_budget_groups
        self._admin_budgets = AdminProjectBudgetUtils(client)
        self._group_utils = AdminProjectBudgetGroupUtils(client)
        self._project_names: list[str] = []
        self._cost_center_names: list[str] = []

    # --- names and setup -------------------------------------------------------------

    def new_project_name(self) -> str:
        """A valid new project name that does not exist yet; removed on cleanup if used."""
        name = get_random_name()
        self._project_names.append(name)
        return name

    def new_cost_center_name(self) -> str:
        """A valid new cost center name that does not exist yet; removed on cleanup if used."""
        name = get_random_cost_center_name()
        self._cost_center_names.append(name)
        return name

    def track_cost_center(self, name: str) -> str:
        """Remove the cost center on cleanup, whatever created it."""
        self._cost_center_names.append(name)
        return name

    def track_project(self, name: str) -> str:
        """Remove the project on cleanup, whatever created it."""
        self._project_names.append(name)
        return name

    def create_project(
        self,
        categories: dict | None = None,
        cost_center_id: UUID | None = None,
        name: str | None = None,
    ) -> str:
        """Create a project as the admin, with a budget group when ``categories`` is given."""
        name = self.track_project(name) if name else self.new_project_name()
        self._projects.create_project(
            name=name,
            description="Autotest provisioning project",
            cost_center_id=cost_center_id,
        )
        if categories:
            self._budget_groups.create(name, categories, name_prefix="autotest-prov")
        return name

    def create_deleted_project(self) -> str:
        """Create a project and delete it again."""
        name = self.create_project()
        self._projects.delete_project(name)
        return name

    # --- reads -----------------------------------------------------------------------

    def project_exists(self, name: str) -> bool:
        found = self._projects.list_projects(search=name, per_page=100)
        return any(project.name == name for project in found.data)

    def cost_center_exists(self, name: str | None) -> bool:
        return name is not None and any(
            cost_center.name == name
            for cost_center in self._cost_centers.list_cost_centers()
        )

    def active_budget_group(self, project_name: str) -> dict | None:
        """The project's budget group that is not deleted, or None."""
        return next(
            (
                group
                for group in self._admin_budgets.list_budget_groups(project_name)
                if group.get("deleted_at") is None
            ),
            None,
        )

    def category_budgets(self, project_name: str) -> dict[str, float]:
        """Category to max budget of the project's active budget group; empty without one."""
        group = self.active_budget_group(project_name)
        return (
            self._group_utils.get_category_budgets(group["group_id"]) if group else {}
        )

    def soft_budgets(self, project_name: str) -> dict[str, float]:
        """Category to soft budget of the project's active budget group; empty without one."""
        group = self.active_budget_group(project_name)
        return (
            self._group_utils.get_category_soft_budgets(group["group_id"])
            if group
            else {}
        )

    def admin_ids(self, project_name: str) -> frozenset[str]:
        detail = self._projects.get_project_detail(project_name)
        return frozenset(m.user_id for m in detail.members if m.is_project_admin)

    def cost_center_of(self, project_name: str) -> str | None:
        return self._projects.get_project_detail(project_name).cost_center_name

    def state(self, project_name: str) -> ProjectState:
        """Everything a provisioning call can change on the project."""
        if not self.project_exists(project_name):
            return ProjectState(exists=False)
        detail = self._projects.get_project_detail(project_name)
        group = self.active_budget_group(project_name)
        return ProjectState(
            exists=True,
            cost_center=detail.cost_center_name,
            admin_ids=frozenset(
                m.user_id for m in detail.members if m.is_project_admin
            ),
            member_ids=frozenset(m.user_id for m in detail.members),
            group_id=group["group_id"] if group else None,
            categories=tuple(sorted(self.category_budgets(project_name).items())),
        )

    # --- cleanup ---------------------------------------------------------------------

    def cleanup(self) -> None:
        for name in reversed(self._project_names):
            self._cleanup_project(name)
        for name in self._cost_center_names:
            self._cleanup_cost_center(name)

    def _cleanup_project(self, name: str) -> None:
        try:
            if not self.project_exists(name):
                return
            for group in self._admin_budgets.list_budget_groups(name):
                if group.get("deleted_at") is None:
                    self._budget_groups.delete(
                        ProjectBudget(
                            project_name=name,
                            group_id=group["group_id"],
                            budget_ids=AdminProjectBudgetUtils.budget_ids_by_category(
                                group
                            ),
                        )
                    )
            self._projects.delete_project_with_all_members(name)
        except Exception as e:
            logger.warning(f"Failed to remove provisioning project {name}: {e}")

    def _cleanup_cost_center(self, name: str) -> None:
        try:
            for cost_center in self._cost_centers.list_cost_centers():
                if cost_center.name == name:
                    self._cost_centers.delete_cost_center(cost_center.id)
        except Exception as e:
            logger.warning(f"Failed to remove provisioning cost center {name}: {e}")


def openapi_names(spec: dict, path_prefix: str = PROVISIONING_PATH_PREFIX) -> list[str]:
    """Paths, parameter names and request/response field names of the routes under a prefix."""
    names: list[str] = []
    for path, operations in spec.get("paths", {}).items():
        if not path.startswith(path_prefix):
            continue
        names.append(path)
        for operation in operations.values():
            names.extend(
                parameter["name"] for parameter in operation.get("parameters", [])
            )
            names.extend(_operation_field_names(spec, operation))
    return names


def _operation_field_names(spec: dict, operation: dict) -> list[str]:
    schemas = [
        content.get("schema", {})
        for body in [operation.get("requestBody", {})]
        + list(operation.get("responses", {}).values())
        for content in body.get("content", {}).values()
    ]
    seen: set[str] = set()
    names: list[str] = []
    for schema in schemas:
        names.extend(_schema_field_names(spec, schema, seen))
    return names


def _schema_field_names(spec: dict, schema: Any, seen: set[str]) -> list[str]:
    if not isinstance(schema, dict):
        return []
    ref = schema.get("$ref")
    if ref:
        if ref in seen:
            return []
        seen.add(ref)
        target: Any = spec
        for part in ref.removeprefix("#/").split("/"):
            target = target[part]
        return _schema_field_names(spec, target, seen)
    properties = schema.get("properties", {})
    nested = [
        *properties.values(),
        schema.get("items"),
        schema.get("additionalProperties"),
        *schema.get("anyOf", []),
        *schema.get("allOf", []),
        *schema.get("oneOf", []),
    ]
    names = list(properties)
    for child in nested:
        names.extend(_schema_field_names(spec, child, seen))
    return names


def names_with_vendor(names: list[str], vendors: tuple[str, ...]) -> list[str]:
    """The names that contain any vendor name, ignoring case."""
    return [name for name in names if any(v in name.lower() for v in vendors)]
