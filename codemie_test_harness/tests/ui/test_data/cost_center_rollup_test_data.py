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

"""Test data for the cost center budget rollup UI tests."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryBudget:
    max_budget: float
    soft_budget: float

    def as_category(self) -> dict:
        return {"max_budget": self.max_budget, "soft_budget": self.soft_budget}


PLATFORM_BUDGET = CategoryBudget(max_budget=20.0, soft_budget=10.0)
CLI_BUDGET = CategoryBudget(max_budget=30.0, soft_budget=15.0)

# Platform and CLI, no Premium models: the rollup card shows Premium models as not assigned.
PLATFORM_AND_CLI_CATEGORIES = {
    "platform": PLATFORM_BUDGET.as_category(),
    "cli": CLI_BUDGET.as_category(),
}
TOTAL_BUDGET = PLATFORM_BUDGET.max_budget + CLI_BUDGET.max_budget

PLATFORM_LABEL = "Platform"
CLI_LABEL = "CLI"
PREMIUM_MODELS_LABEL = "Premium models"
