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

"""Test data for the cost center budget rollup tests.

Every project of one test gets different amounts, so a sum that drops or double counts a
project cannot give the expected figure by accident.
"""

# Tolerance for amounts: the rollup rounds each sum to 2 decimals, and a bundled group
# stores amounts derived from percentages, which can drift by a float epsilon.
AMOUNT_TOLERANCE = 0.01

# The rollup rounds every category sum and the overall spend to 2 decimals, so it can differ
# from the unrounded sum of the projects' own spend by at most half a cent.
SPEND_ROUNDING_TOLERANCE = 0.0051

PROJECT_A_ALL_CATEGORIES = {
    "platform": {"max_budget": 40.0, "soft_budget": 20.0},
    "cli": {"max_budget": 30.0, "soft_budget": 15.0},
    "premium_models": {"max_budget": 20.0, "soft_budget": 10.0},
}
PROJECT_B_PLATFORM_ONLY = {"platform": {"max_budget": 10.0, "soft_budget": 5.0}}

SINGLE_PROJECT_PLATFORM = {"platform": {"max_budget": 40.0, "soft_budget": 20.0}}
SINGLE_PROJECT_PLATFORM_AFTER_UPDATE = {
    "platform": {"max_budget": 60.0, "soft_budget": 30.0}
}

PROJECT_A_PLATFORM_ONLY = {"platform": {"max_budget": 40.0, "soft_budget": 20.0}}
PROJECT_B_PLATFORM_AND_CLI = {
    "platform": {"max_budget": 12.0, "soft_budget": 6.0},
    "cli": {"max_budget": 8.0, "soft_budget": 4.0},
}
DEFAULT_RESET_WINDOW = "30d"
SHORT_RESET_WINDOW = "7d"

SPENDING_PLATFORM_ONLY = {"platform": {"max_budget": 20.0, "soft_budget": 10.0}}
