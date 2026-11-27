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

"""Create budgeted projects and read the project list with a budget category filter.

The list is read through the authenticated HTTP client (the client's bearer token), because
the SDK's project list call does not take the ``budget_category`` parameter.
"""

import logging
import secrets

import requests

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.test_data.budget_test_data import project_key_alias
from codemie_test_harness.tests.utils.base_utils import BaseUtils
from codemie_test_harness.tests.utils.project_budget_groups import ProjectBudgetGroups
from codemie_test_harness.tests.utils.project_utils import ProjectUtils

logger = logging.getLogger(__name__)

_CATEGORIES = ("platform", "cli", "premium_models")
_PAGE_SIZE = 100


class ProjectBudgetCategoryFilterUtils(BaseUtils):
    """Creates projects with chosen budget categories and lists them with a category filter.

    All projects get one run-unique name prefix, so a listing narrowed with it holds only the
    projects of this test even on a stand that has many projects.
    """

    def __init__(
        self,
        client,
        project_utils: ProjectUtils,
        project_budget_groups: ProjectBudgetGroups,
        lite_llm_budget_utils,
    ):
        super().__init__(client)
        self._headers = {
            "Authorization": f"Bearer {client.token}",
            "Content-Type": "application/json",
        }
        self._projects = project_utils
        self._groups = project_budget_groups
        self._lite_llm = lite_llm_budget_utils
        self.prefix = f"autotest-bcf-{secrets.token_hex(3)}"
        self._created: list[str] = []

    def create_project(self, label: str, categories: dict | None = None) -> str:
        """Create a project named after ``label``; give it a budget group when ``categories`` is set."""
        name = f"{self.prefix}-{label}".replace("_", "-")
        self._projects.create_project(
            name=name, description="Autotest budget category filter project"
        )
        self._created.append(name)
        if categories:
            self._groups.create(name, categories, name_prefix="autotest-bcf")
        return name

    def list_projects(self, budget_category: str | None = None) -> dict[str, dict]:
        """The test's projects as listed by ``GET /v1/projects`` with budgets, keyed by name."""
        found: dict[str, dict] = {}
        page = 0
        while True:
            params = {
                "include_budgets": "true",
                "search": self.prefix,
                "page": page,
                "per_page": _PAGE_SIZE,
            }
            if budget_category:
                params["budget_category"] = budget_category
            response = requests.get(
                f"{API_DOMAIN}/v1/projects",
                params=params,
                headers=self._headers,
                verify=VERIFY_SSL,
            )
            response.raise_for_status()
            body = response.json()
            for item in body["data"]:
                found[item["name"]] = item
            pagination = body["pagination"]
            if (page + 1) * pagination["per_page"] >= pagination["total"]:
                return found
            page += 1

    @staticmethod
    def rows_by_category(project: dict) -> dict[str, tuple[float, float]]:
        """``{category: (hard limit, spend)}`` of a listed project's budget rows."""
        return {
            b["budget_category"]: (
                float(b["max_budget"]),
                float(b.get("current_spending") or 0),
            )
            for b in project.get("budgets") or []
        }

    def cleanup(self) -> None:
        for name in reversed(self._created):
            for category in _CATEGORIES:
                try:
                    self._lite_llm.delete_key_by_alias(
                        project_key_alias(name, category)
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to delete LiteLLM key for {name}/{category}: {e}"
                    )
            try:
                self._projects.delete_project_cascade(name)
            except Exception as e:
                logger.warning(f"Failed to delete project {name}: {e}")
        self._created.clear()
