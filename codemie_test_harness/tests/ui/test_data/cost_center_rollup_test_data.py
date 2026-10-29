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
