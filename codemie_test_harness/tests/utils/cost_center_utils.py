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

"""Utility functions for cost center management in tests."""

import logging
import random
import re
import string
from typing import TYPE_CHECKING
from uuid import UUID

from codemie_sdk.models.cost_center import CostCenterResponse
from codemie_test_harness.tests.utils.base_utils import BaseUtils

if TYPE_CHECKING:
    # Only the rollup helpers use these; importing them at runtime would break every test
    # session on an SDK release that predates the rollup.
    from codemie_sdk.models.cost_center import (
        CostCenterAssignedBudgetSummary,
        CostCenterBudgetSummary,
    )

logger = logging.getLogger(__name__)

# Matches get_random_cost_center_name()'s shape: 3 lowercase letters + "-" +
# 10 lowercase letters (e.g. "xju-nxherepeao"). Real, meaningfully-named
# cost centers (e.g. "qa-test", "engineering") won't collide with this.
TEST_COST_CENTER_NAME_RE = re.compile(r"^[a-z]{3}-[a-z]{10}$")


def get_random_cost_center_name() -> str:
    """Generate a valid cost center name in the format <letters>-<letters>.

    Cost center names must contain exactly one '-' between lowercase letters
    or digits, e.g. 'eng-123' or 'at-xyzabc'.
    """
    prefix = "".join(random.choice(string.ascii_lowercase) for _ in range(3))
    suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(10))
    return f"{prefix}-{suffix}"


class CostCenterUtils(BaseUtils):
    """Helper class for cost center admin operations."""

    def create_cost_center(
        self,
        name: str,
        description: str | None = None,
    ) -> CostCenterResponse:
        """Create a new cost center via the admin API.

        Args:
            name: Cost center name
            description: Optional description

        Returns:
            CostCenterResponse with the created cost center details including id
        """
        return self.client.cost_centers.create_cost_center(
            name=name,
            description=description,
        )

    def delete_cost_center(self, cost_center_id: UUID) -> None:
        """Soft-delete a cost center via the admin API.

        Args:
            cost_center_id: UUID of the cost center to delete
        """
        self.client.cost_centers.delete_cost_center(cost_center_id=cost_center_id)

    def list_cost_centers(self, per_page: int = 100) -> list[CostCenterResponse]:
        """List every cost center, paginating until exhausted."""
        items: list[CostCenterResponse] = []
        page = 0
        while True:
            response = self.client.cost_centers.list_cost_centers(
                page=page, per_page=per_page
            )
            items.extend(response.data)
            if len(response.data) < per_page:
                break
            page += 1
        return items

    def get_budget_rollup(self, cost_center_id: UUID) -> "CostCenterBudgetSummary":
        """Get the budget rollup across the projects linked to a cost center.

        Args:
            cost_center_id: UUID of the cost center

        Returns:
            CostCenterBudgetSummary with overall totals and the per-category breakdown
        """
        return self.client.cost_centers.get_budget_rollup(cost_center_id=cost_center_id)

    @staticmethod
    def rollup_category(
        summary: "CostCenterBudgetSummary", category: str
    ) -> "CostCenterAssignedBudgetSummary | None":
        """Return the summary's entry for a category, or None when it has no rows.

        The rollup only lists categories that have budget rows, so an absent category
        is not a zero entry.
        """
        return next((b for b in summary.budgets if b.budget_category == category), None)
