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

"""Test data for the per-project rows on the personal spending page."""

# Row keys of GET /v1/analytics/budget_usage, shared by personal and per-project rows.
# is_default is a row key only: it is not one of the response columns.
BUDGET_USAGE_ROW_KEYS = {
    "project_name",
    "current_spending",
    "budget_reset_at",
    "time_until_reset",
    "budget_limit",
    "total",
    "is_default",
}

# Spend annotations the backend adds to a row when the ledger figure is partial or unavailable.
BUDGET_USAGE_SPEND_ANNOTATION_KEYS = {
    "spend_partial",
    "spend_unavailable",
    "spend_missing_amount",
}

# Column ids of GET /v1/analytics/budget_usage, in response order.
BUDGET_USAGE_COLUMN_IDS = [
    "project_name",
    "current_spending",
    "budget_reset_at",
    "time_until_reset",
    "budget_limit",
    "total",
]

# Column ids of GET /v1/analytics/user-project-spending: the key column, then one per budget category.
USER_PROJECT_SPENDING_COLUMN_IDS = [
    "project_name",
    "platform",
    "cli",
    "premium_models",
]

# Row keys of GET /v1/analytics/user-project-spending: spend and limit per budget category.
USER_PROJECT_SPENDING_ROW_KEYS = {
    "project_name",
    "platform",
    "cli",
    "premium_models",
    "platform_limit",
    "cli_limit",
    "premium_models_limit",
}

# The same spend annotations, one set per budget category.
USER_PROJECT_SPENDING_SPEND_ANNOTATION_KEYS = {
    f"{category}_{annotation}"
    for category in ("platform", "cli", "premium_models")
    for annotation in ("spend_partial", "spend_unavailable", "spend_missing_amount")
}

# Suffixes of the row label per budget category (the platform row carries the bare label).
CLI_ROW_SUFFIX = " (cli)"
PREMIUM_ROW_SUFFIX = " (premium)"

# budget_usage rounds money to 2 decimals; the admin view returns the raw value.
ROUNDING_TOLERANCE = 0.01
# Tolerance for comparing already-rounded spend values of the same snapshot.
SPEND_PARITY_TOLERANCE = 0.0001

# Member allocations and project budget availability settle asynchronously on the stand.
ROW_WAIT_TIMEOUT = 90.0
ROW_WAIT_INTERVAL = 3.0

# The personal page rounds money to 2 decimals, so spend below half a cent reads as 0.00 there.
# Spend must reach MIN_VISIBLE_SPEND for the personal-page value to be a discriminating check.
VISIBLE_AT_TWO_DECIMALS = 0.005
MIN_VISIBLE_SPEND = 0.006

# Spend generation: long completions, in bounded batches, until the member's LiteLLM
# customer shows MIN_VISIBLE_SPEND.
SPEND_REQUEST_MAX_TOKENS = 2000
SPEND_REQUEST_TIMEOUT = 120
SPEND_REQUESTS_PER_BATCH = 5
SPEND_MAX_BATCHES = 3
SPEND_POLL_TIMEOUT = 60.0
SPEND_POLL_INTERVAL = 5.0
SPEND_SETTLE_CHECKS = 6

# Real chat spend costs fractions of a cent, so percentages of a 100 dollar project limit would
# round to 0.00. The spend tests use the smallest platform budget the admin API accepts instead,
# and compute every expected value from the measured spend.
SCALED_PROJECT_LIMIT = 1.0
SCALED_PROJECT_SOFT_LIMIT = 0.5
SCALED_PLATFORM_CATEGORIES = {
    "platform": {
        "max_budget": SCALED_PROJECT_LIMIT,
        "soft_budget": SCALED_PROJECT_SOFT_LIMIT,
    }
}

# Equal split of the scaled limit over two members (the project owner and one member).
SCALED_SHARE_OF_TWO = 0.5
# Member override of 40 percent of the scaled limit; the other two members split the rest.
SCALED_OVERRIDE_MAX = 0.4
SCALED_OVERRIDE_SOFT = 0.2
SCALED_SHARE_OF_REST = 0.3
# Override equal to the whole project limit: the cap then binds as soon as anybody else spends.
SCALED_OVERRIDE_EQUAL_TO_LIMIT_SOFT = SCALED_PROJECT_SOFT_LIMIT

# Money on the personal page is rounded to 2 decimals; percentages are rounded to 2 decimals too.
MONEY_TOLERANCE = 0.006
PERCENT_TOLERANCE = 0.01

# Two measured spends are told apart on the page only when they still differ after rounding
# to 2 decimals.
DISTINCT_SPEND_GAP = 0.011

# Project key spend and member customer spend are written by LiteLLM in batches: a value is
# settled once it did not change over this many consecutive reads.
SPEND_STABLE_READS = 3
KEY_SPEND_SETTLE_TIMEOUT = 120.0
# The first budget_usage read of a project refreshes its stored values and keeps them for the
# staleness window, so spend is settled before that first read and polled only for propagation.
USAGE_WAIT_TIMEOUT = 120.0

# A row catches up with the measured spend only after the ledger has collected it, which a
# periodic job does about every one or two minutes. The wait for a row to catch up covers
# one such window plus a margin of the same size, not the 10 minute staleness threshold
# (BUDGET_USAGE_STALENESS_THRESHOLD_MS, 600000 ms by default).
ROW_CATCH_UP_WINDOW = 120.0
STORED_ROW_WAIT_TIMEOUT = ROW_CATCH_UP_WINDOW * 2
STORED_ROW_POLL_INTERVAL = 10.0
