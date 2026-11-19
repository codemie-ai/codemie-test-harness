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
import requests
from hamcrest import assert_that, equal_to, not_none

from codemie_test_harness.tests.test_data.budget_default_assignment_test_data import (
    DEFAULT_BUDGET_CUSTOMERS,
    DEFAULT_PROVISIONING_POLL_INTERVAL,
    DEFAULT_PROVISIONING_POLL_TIMEOUT,
)
from codemie_test_harness.tests.utils.base_utils import poll_until

logger = logging.getLogger(__name__)

# LiteLLM can answer 5xx/429 or drop the connection while a customer is being provisioned;
# the poll treats those like "not there yet" and keeps waiting. Other 4xx (a wrong key,
# a bad request) are not transient and fail the test at once; an unknown customer is a
# 404, which `get_customer_info` already maps to None.
TRANSIENT_LITELLM_ERRORS = (
    requests.exceptions.HTTPError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.parametrize("default_customer", DEFAULT_BUDGET_CUSTOMERS)
# @case default-budget-on-user-creation_TC_001
# Provisioning is eventual: the backend schedules it after the user's first IdP login
# with a 30 s deadline, no LLM request needed (AC-1, AC-2). The platform, cli and
# premium_models customers were confirmed live on the preview stand right after the
# first login, so all three categories are asserted without a stand-based skip.
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

    last_error = []

    def fetch_customer():
        last_error.clear()
        try:
            return lite_llm_budget_utils.get_customer_info(customer_id)
        except TRANSIENT_LITELLM_ERRORS as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            if status is not None and status < 500 and status != 429:
                raise
            last_error[:] = [f"{type(error).__name__} (status={status})"]
            logger.warning(
                "LiteLLM customer lookup failed, retrying: %s", last_error[0]
            )
            return None

    customer = poll_until(
        fetch_customer,
        lambda found: found is not None
        and (found.get("litellm_budget_table") or {}).get("budget_id")
        == default_customer.default_budget_id,
        timeout=DEFAULT_PROVISIONING_POLL_TIMEOUT,
        interval=DEFAULT_PROVISIONING_POLL_INTERVAL,
    )

    last_error_note = f"; last LiteLLM error: {last_error[0]}" if last_error else ""
    assert_that(
        customer,
        not_none(),
        f"No LiteLLM customer {customer_id} for the new user before any LLM session"
        f"{last_error_note}",
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
