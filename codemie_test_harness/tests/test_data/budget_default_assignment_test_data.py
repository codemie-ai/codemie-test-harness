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

"""Parameters of the default budget assignment on user creation tests.

Every new user gets one LiteLLM customer per default budget category without sending
any LLM request. The platform customer is keyed by the bare username (the e-mail on
the test stands); the cli and premium_models customers carry the default budget id
as a suffix, the same way the personal budget assignment tests key them.
"""

from dataclasses import dataclass

import pytest

from codemie_test_harness.tests.test_data.budget_test_data import (
    DEFAULT_CLI_BUDGET_ID,
    DEFAULT_PLATFORM_BUDGET_ID,
    DEFAULT_PREMIUM_BUDGET_ID,
)

# The backend gives provisioning 30 seconds (it runs in the background and is eventual),
# so the poll window is that deadline plus a margin for the LiteLLM round trip.
DEFAULT_PROVISIONING_POLL_TIMEOUT = 45.0
DEFAULT_PROVISIONING_POLL_INTERVAL = 2.0


@dataclass(frozen=True)
class DefaultBudgetCustomer:
    """A default budget category and the LiteLLM customer provisioned for it."""

    category: str
    customer_suffix: str
    default_budget_id: str

    def customer_id(self, email: str) -> str:
        return f"{email}{self.customer_suffix}"


DEFAULT_BUDGET_CUSTOMERS = [
    pytest.param(
        DefaultBudgetCustomer("platform", "", DEFAULT_PLATFORM_BUDGET_ID),
        id="platform",
    ),
    pytest.param(
        DefaultBudgetCustomer(
            "cli", f"_{DEFAULT_CLI_BUDGET_ID}", DEFAULT_CLI_BUDGET_ID
        ),
        id="cli",
    ),
    pytest.param(
        DefaultBudgetCustomer(
            "premium_models",
            f"_{DEFAULT_PREMIUM_BUDGET_ID}",
            DEFAULT_PREMIUM_BUDGET_ID,
        ),
        id="premium_models",
    ),
]
