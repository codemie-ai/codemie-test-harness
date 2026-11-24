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

"""Test data for the 'Your personal spending' panel UI tests."""

from dataclasses import dataclass

from codemie_test_harness.tests.test_data.budget_test_data import (
    CHROME_EXTENSION_CLIENT_HEADER,
    CLI_CLIENT_HEADER,
    PREMIUM_MODEL,
)

# The panel draws a table only for two or more rows, so the project budget group spans two
# categories: percentages of the group total, as the budget group distribution endpoint takes them.
TWO_CATEGORY_DISTRIBUTION = {"platform": 50.0, "cli": 50.0}
# Every category a member can spend on, so that each has a row of its own.
THREE_CATEGORY_DISTRIBUTION = {"platform": 40.0, "cli": 30.0, "premium_models": 30.0}

# Column that the table hides by design; the API still returns it.
HIDDEN_COLUMN_ID = "budget_limit"

# Columns the table does not draw: their values go into the usage block of the Total cell, or
# are only flags (is_shared_limit); the API still returns all of them.
HIDDEN_COLUMN_IDS = ("budget_limit", "current_spending", "is_shared_limit")

# Limit labels of the usage block and the tooltip of a shared limit.
PERSONAL_LIMIT_LABEL = "Personal limit"
AVAILABLE_TO_YOU_LABEL = "Available to you"
SHARED_LIMIT_TOOLTIP = "This budget is shared across the project with other members"


@dataclass(frozen=True)
class LimitLabelRow:
    """One kind of project row of the table: how the project is set up and what the row shows."""

    enforce_member_spend_limits: bool
    is_default_project: bool
    limit_label: str
    is_shared_limit: bool


# Without enforcement the project's whole budget is shared; with it every member has a limit
# of their own. The default project's rows say "Personal limit".
LIMIT_LABEL_ROWS = {
    "shared_non_default": LimitLabelRow(
        enforce_member_spend_limits=False,
        is_default_project=False,
        limit_label=AVAILABLE_TO_YOU_LABEL,
        is_shared_limit=True,
    ),
    "personal_limit_non_default": LimitLabelRow(
        enforce_member_spend_limits=True,
        is_default_project=False,
        limit_label=AVAILABLE_TO_YOU_LABEL,
        is_shared_limit=False,
    ),
    "personal_limit_default": LimitLabelRow(
        enforce_member_spend_limits=True,
        is_default_project=True,
        limit_label=PERSONAL_LIMIT_LABEL,
        is_shared_limit=False,
    ),
}

# Real chat spend is a few cents, which the table rounds to 0.0% of a 50 dollar budget. The
# category that receives the spend gets a one dollar budget instead. The
# requests carry the CLI client header, which routes them to the cli key once the project has one.
SPENT_CATEGORY = "cli"


@dataclass(frozen=True)
class CategorySpend:
    """How a member's request lands on one category of a project that has all three budgets.

    ``model`` None means the stand's default model. The routing is the one the API budget tests
    check: the chrome extension client goes to the platform key, the CLI client to the cli key,
    and a premium model to the premium_models key.
    """

    category: str
    row_suffix: str
    client_header: dict
    model: str | None


SPEND_CATEGORIES = (
    CategorySpend(
        category="platform",
        row_suffix="",
        client_header=CHROME_EXTENSION_CLIENT_HEADER,
        model=None,
    ),
    CategorySpend(
        category="cli", row_suffix=" (cli)", client_header=CLI_CLIENT_HEADER, model=None
    ),
    CategorySpend(
        category="premium_models",
        row_suffix=" (premium)",
        client_header=CLI_CLIENT_HEADER,
        model=PREMIUM_MODEL,
    ),
)
