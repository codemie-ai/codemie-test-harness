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

"""Test data for the Platform hard limit > 0 rule of project budget groups."""

from dataclasses import dataclass

# Total budget of the group the API tests work against. With a total of 100 every
# category percentage equals its hard limit in dollars.
GROUP_TOTAL_AMOUNT = 100.0

# Fragments of the backend message "Category 'platform' hard limit must be greater than 0, got pct 0.0".
PLATFORM_ZERO_MESSAGE_PARTS = ("platform", "hard limit must be greater than 0")


@dataclass
class PlatformDistribution:
    """A category distribution whose Platform share is above 0 while the rest may be 0."""

    id: str
    pcts: dict
    """Category name to percentage, summing to 100. Soft limits are always sent as 0."""

    def create_categories(self) -> dict:
        """Categories in the {"max_budget", "soft_budget"} shape of AdminProjectBudgetUtils.create_budget_group."""
        return {
            category: {
                "max_budget": pct * GROUP_TOTAL_AMOUNT / 100,
                "soft_budget": 0.0,
            }
            for category, pct in self.pcts.items()
        }

    def update_body(self) -> dict:
        """PUT body that moves the group to this distribution with every soft limit at 0."""
        return {
            "categories": {
                category: {"pct": pct, "soft_budget": 0.0}
                for category, pct in self.pcts.items()
            }
        }

    def expected_hard_limits(self) -> dict:
        """Hard limit in dollars per category, for categories that keep a share."""
        return {
            category: pct * GROUP_TOTAL_AMOUNT / 100
            for category, pct in self.pcts.items()
            if pct > 0
        }


@dataclass
class PlatformZeroData:
    """Payload data for requests the backend must reject."""

    platform_zero_pcts: dict
    """Platform 0, CLI takes the whole group: sums to 100 so only the Platform rule can reject it."""


def platform_zero_data() -> PlatformZeroData:
    return PlatformZeroData(platform_zero_pcts={"platform": 0.0, "cli": 100.0})


ACCEPTED_DISTRIBUTIONS = [
    PlatformDistribution(
        id="platform_100_others_0",
        pcts={"platform": 100.0, "cli": 0.0, "premium_models": 0.0},
    ),
    PlatformDistribution(
        id="platform_0_01_cli_99_99",
        pcts={"platform": 0.01, "cli": 99.99},
    ),
]
