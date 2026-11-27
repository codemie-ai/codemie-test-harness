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

"""Test data for the budget category filter of the project list."""

import pytest

PLATFORM = "platform"
CLI = "cli"
PREMIUM = "premium_models"

# Distinct hard limits per category, so a swapped, dropped or duplicated row changes the sum of
# a project's limits. Zero spend only: no LLM traffic is generated.
_PLATFORM_LIMIT = {PLATFORM: {"max_budget": 10.0, "soft_budget": 5.0}}
_CLI_LIMIT = {CLI: {"max_budget": 20.0, "soft_budget": 10.0}}
_PREMIUM_LIMIT = {PREMIUM: {"max_budget": 30.0, "soft_budget": 15.0}}

# Project label -> budget categories it is created with.
PROJECT_BUDGETS = {
    "all": {**_PLATFORM_LIMIT, **_CLI_LIMIT, **_PREMIUM_LIMIT},
    "platform_cli": {**_PLATFORM_LIMIT, **_CLI_LIMIT},
    "platform_premium": {**_PLATFORM_LIMIT, **_PREMIUM_LIMIT},
}

# Filter -> labels of the budgeted projects it must list.
EXPECTED_LISTED_BY_FILTER = {
    PLATFORM: {"all", "platform_cli", "platform_premium"},
    CLI: {"all", "platform_cli"},
    PREMIUM: {"all", "platform_premium"},
}

CATEGORY_FILTERS = [
    pytest.param(PLATFORM, id="platform"),
    pytest.param(CLI, id="cli"),
    pytest.param(PREMIUM, id="premium_models"),
]

# One pair per project a filter must list, so a failure names the filter and the project.
LISTED_PROJECT_PAIRS = [
    pytest.param(category, label, id=f"{category}-{label}")
    for category, labels in EXPECTED_LISTED_BY_FILTER.items()
    for label in sorted(labels)
]
