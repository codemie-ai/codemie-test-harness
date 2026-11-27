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
    CLI_CLIENT_HEADER,
    DEFAULT_CLI_BUDGET_ID,
    DEFAULT_PREMIUM_BUDGET_ID,
    PREMIUM_MODEL,
)
from codemie_test_harness.tests.test_data.budget_usage_project_rows_test_data import (
    CLI_ROW_SUFFIX,
    PREMIUM_ROW_SUFFIX,
)

# The panel draws a table only for two or more rows, so the project budget group spans two
# categories: percentages of the group total, as the budget group distribution endpoint takes them.
TWO_CATEGORY_DISTRIBUTION = {"platform": 50.0, "cli": 50.0}

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
class PersonalBudget:
    """One personal default budget of a user with no project, and how a request lands on it.

    The row is labelled with the user's e-mail plus ``row_suffix``; the spend goes to the LiteLLM
    customer named by the e-mail plus ``customer_suffix``. ``client_header`` None means the spend
    comes from chat with the user's personal assistant (POST /v1/assistants/{id}/model), the way
    tests/budgets/test_personal_budget_spending.py spends on the platform budget; otherwise it is
    a /v1/messages request with that header and no project header. ``model`` None means the
    stand's default model; a premium model goes to the premium budget.
    """

    category: str
    row_suffix: str
    customer_suffix: str
    client_header: dict | None
    model: str | None


PERSONAL_BUDGETS = (
    PersonalBudget(
        category="platform",
        row_suffix="",
        customer_suffix="",
        client_header=None,
        model=None,
    ),
    PersonalBudget(
        category="cli",
        row_suffix=CLI_ROW_SUFFIX,
        customer_suffix=f"_{DEFAULT_CLI_BUDGET_ID}",
        client_header=CLI_CLIENT_HEADER,
        model=None,
    ),
    PersonalBudget(
        category="premium_models",
        row_suffix=PREMIUM_ROW_SUFFIX,
        customer_suffix=f"_{DEFAULT_PREMIUM_BUDGET_ID}",
        client_header=CLI_CLIENT_HEADER,
        model=PREMIUM_MODEL,
    ),
)

# Spend per call, measured on the preview stand (2026-11-25, logged by the spend loop): platform
# assistant chat 0.020, cli 0.017, premium_models 0.041. One batch of SPEND_REQUESTS_PER_BATCH (5)
# calls reaches MIN_VISIBLE_SPEND (0.006) about 15 times over, so every category uses the shared
# SPEND_MAX_BATCHES bound and the loop stops after its first batch.

# A personal row shows the customer spend about 15 seconds after LiteLLM records it; the wait
# re-reads both sides at this interval, with a timeout well above that delay.
PERSONAL_ROW_WAIT_TIMEOUT = 240.0
PERSONAL_ROW_POLL_INTERVAL = 15.0
