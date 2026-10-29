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

"""Test data for the Platform hard limit minimum in the budget popup."""

from dataclasses import dataclass

import pytest

# Group the popup opens on: total 1000 split 30 / 60 / 10 (the popup's default distribution).
TOTAL_BUDGET = 1000.0
PLATFORM_HARD = 300.0
CLI_HARD = 600.0
PREMIUM_HARD = 100.0

# Text shown by the 'Platform hard limit' input for the starting group, and the
# lowest value the allocation slider can reach on that total (0.01% of 1000).
PLATFORM_HARD_TEXT = "300"
PLATFORM_SLIDER_MIN_TEXT = "0.10"
PLATFORM_SLIDER_MIN_AMOUNT = 0.1

# Amount below the minimum share (0.04 on 1000 is 0.004%), raised to 0.01% = 0.1.
SUB_MINIMUM_PLATFORM_TEXT = "0.04"

# A typed value recalculates no other field, so after the raise the Platform soft
# limit is lowered to fit under its hard limit and the freed share goes to CLI hard (1000 - 0.1 - 100).
SUB_MINIMUM_PLATFORM_SOFT_TEXT = "0"
SUB_MINIMUM_CLI_HARD_TEXT = "899.9"
SUB_MINIMUM_CLI_HARD_AMOUNT = 899.9

# Reset to Default gives Platform 30%; lowering the total to 10 keeps the share.
LOWERED_TOTAL_BUDGET_TEXT = "10"
LOWERED_TOTAL_BUDGET = 10.0
PLATFORM_HARD_AFTER_LOWERED_TOTAL = 3.0

# Platform hard limit entries the input must refuse.
REJECTED_PLATFORM_INPUTS = [
    pytest.param("0", id="zero"),
    pytest.param("-5", id="negative"),
    pytest.param("", id="empty"),
]


@dataclass
class BudgetCategories:
    """Per-category hard/soft amounts used to create the starting group."""

    categories: dict


def starting_budget_categories() -> BudgetCategories:
    return BudgetCategories(
        categories={
            "platform": {"max_budget": PLATFORM_HARD, "soft_budget": 150.0},
            "cli": {"max_budget": CLI_HARD, "soft_budget": 300.0},
            "premium_models": {"max_budget": PREMIUM_HARD, "soft_budget": 50.0},
        }
    )


@dataclass
class ZeroLimitCase:
    """Limits that must stay settable to 0 once Platform hard limit is restricted to > 0.

    A typed hard limit recalculates no other field, so zeroing one hard limit
    leaves the category total below 100% and blocks save. A zeroed hard limit also needs its
    own soft limit zeroed (a soft above its hard blocks save), and the missing share is typed
    into the other non-Platform hard limit before saving.
    """

    id: str
    limits: tuple
    """Limit names as understood by UnifiedProjectBudgetModalPage.set_limits_to_zero."""
    hard_limit_texts: tuple
    """(Platform, CLI, Premium Models) hard limit texts shown right after the limits are zeroed."""
    compensations: tuple
    """(limit name, text) pairs typed after zeroing so the categories total 100% again."""
    saved_hard_amounts: dict
    """Hard limit amount expected per category after save."""
    zero_hard_categories: tuple
    """Categories whose saved hard limit must be 0."""
    zero_soft_categories: tuple
    """Categories whose saved soft limit must be 0."""


ZERO_LIMIT_CASES = [
    ZeroLimitCase(
        id="cli_hard",
        limits=("cli_hard", "cli_soft"),
        hard_limit_texts=(PLATFORM_HARD_TEXT, "0", "100"),
        compensations=(("premium_hard", "700"),),
        saved_hard_amounts={"platform": 300.0, "cli": 0.0, "premium_models": 700.0},
        zero_hard_categories=("cli",),
        zero_soft_categories=("cli",),
    ),
    ZeroLimitCase(
        id="premium_hard",
        limits=("premium_hard", "premium_soft"),
        hard_limit_texts=(PLATFORM_HARD_TEXT, "600", "0"),
        compensations=(("cli_hard", "700"),),
        saved_hard_amounts={"platform": 300.0, "cli": 700.0, "premium_models": 0.0},
        zero_hard_categories=("premium_models",),
        zero_soft_categories=("premium_models",),
    ),
    ZeroLimitCase(
        id="all_soft_limits",
        limits=("platform_soft", "cli_soft", "premium_soft"),
        hard_limit_texts=(PLATFORM_HARD_TEXT, "600", "100"),
        compensations=(),
        saved_hard_amounts={
            "platform": PLATFORM_HARD,
            "cli": CLI_HARD,
            "premium_models": PREMIUM_HARD,
        },
        zero_hard_categories=(),
        zero_soft_categories=("platform", "cli", "premium_models"),
    ),
]
