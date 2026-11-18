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

import logging

import pytest
from hamcrest import assert_that, equal_to, not_none

from codemie_test_harness.tests.test_data.budget_default_assignment_test_data import (
    DEFAULT_BUDGET_CUSTOMERS,
    DEFAULT_PROVISIONING_POLL_INTERVAL,
    DEFAULT_PROVISIONING_POLL_TIMEOUT,
)
from codemie_test_harness.tests.utils.base_utils import poll_until

logger = logging.getLogger(__name__)


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.parametrize("default_customer", DEFAULT_BUDGET_CUSTOMERS)
# @case default-budget-on-user-creation_TC_001
# Grounding: budget_provider_adapter.py:1056 get_or_create_customer_with_budget(<litellm_user_id>,
# <default budget_id>) per default category; platform uses the bare username (AC-1),
# provisioning is a background task bounded by 30s, no LLM session needed (AC-2).
def test_default_budget_customer_exists_for_new_user_without_llm_session(
    default_customer,
    keycloak_user,
    user_id,
    lite_llm_budget_utils,
):
    # `user_id` logs the fresh user in (first IdP login on a Keycloak stand), which
    # creates the backend user; no LLM request is sent anywhere in this test.
    email, _ = keycloak_user
    customer_id = default_customer.customer_id(email)
    logger.info(
        "Waiting for the default %s customer of a new user (customer=%s, user_id=%s)",
        default_customer.category,
        customer_id,
        user_id,
    )

    customer = poll_until(
        lambda: lite_llm_budget_utils.get_customer_info(customer_id),
        lambda found: found is not None
        and (found.get("litellm_budget_table") or {}).get("budget_id")
        == default_customer.default_budget_id,
        timeout=DEFAULT_PROVISIONING_POLL_TIMEOUT,
        interval=DEFAULT_PROVISIONING_POLL_INTERVAL,
    )

    assert_that(
        customer,
        not_none(),
        f"No LiteLLM customer {customer_id} for the new user before any LLM session",
    )
    assert_that(
        customer["litellm_budget_table"],
        not_none(),
        f"LiteLLM customer {customer_id} has no budget",
    )
    assert_that(
        customer["litellm_budget_table"]["budget_id"],
        equal_to(default_customer.default_budget_id),
        f"{default_customer.category} customer {customer_id} is not on the default budget",
    )
