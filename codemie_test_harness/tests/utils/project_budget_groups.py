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

"""Create project budget groups in tests and clean them up with their LiteLLM objects."""

import logging
import secrets
from dataclasses import dataclass

from codemie_test_harness.tests.test_data.budget_test_data import (
    PLATFORM_BUDGET_CATEGORIES,
    project_key_alias,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.lite_llm_budget_utils import LiteLLMBudgetUtils

logger = logging.getLogger(__name__)


@dataclass
class ProjectBudget:
    project_name: str
    group_id: str
    budget_ids: dict[str, str]
    """Category name to budget id, for every category the group created a budget for."""

    def alias(self, category: str = "platform") -> str:
        return project_key_alias(self.project_name, category)


class ProjectBudgetGroups:
    """Creates project budget groups and deletes them, with their LiteLLM budget objects.

    Groups without a "platform" category also get the minimal platform budget that
    ``AdminProjectBudgetUtils.create_budget_group`` adds, so ``budget_ids`` and the
    waited-for LiteLLM keys always include "platform".
    """

    def __init__(
        self,
        admin_project_budget_utils: AdminProjectBudgetUtils,
        lite_llm_budget_utils: LiteLLMBudgetUtils,
    ):
        self._admin = admin_project_budget_utils
        self._lite_llm = lite_llm_budget_utils
        self._created: list[ProjectBudget] = []

    def create(
        self,
        project_name: str,
        categories: dict | None = None,
        name_prefix: str = "autotest-proj",
        budget_duration: str = "30d",
    ) -> ProjectBudget:
        """Create the group and wait until LiteLLM has a key for each of its categories."""
        response = self._admin.create_budget_group(
            project_name,
            name=f"{name_prefix}-{secrets.token_hex(4)}",
            categories=categories or PLATFORM_BUDGET_CATEGORIES,
            budget_duration=budget_duration,
        )
        budget = ProjectBudget(
            project_name=project_name,
            group_id=response["group_id"],
            budget_ids=AdminProjectBudgetUtils.budget_ids_by_category(response),
        )
        self._created.append(budget)
        logger.info(
            "Budget group %s created for %s (budgets=%s), waiting for LiteLLM keys",
            budget.group_id,
            project_name,
            budget.budget_ids,
        )
        for category in budget.budget_ids:
            self._lite_llm.wait_for_key_alias(budget.alias(category))
        return budget

    def delete(self, budget: ProjectBudget, user_id: str | None = None) -> None:
        """Delete the group and the LiteLLM budget objects of all its categories."""
        self._admin.delete_budget_group(budget.group_id)
        for budget_id in budget.budget_ids.values():
            self._lite_llm.delete_project_budget_objects(budget_id, user_id)
        if budget in self._created:
            self._created.remove(budget)

    def cleanup(self) -> None:
        for budget in reversed(list(self._created)):
            try:
                self.delete(budget)
            except Exception as e:
                logger.warning(
                    f"Failed to delete budget group {budget.group_id} "
                    f"of project {budget.project_name}: {e}"
                )
