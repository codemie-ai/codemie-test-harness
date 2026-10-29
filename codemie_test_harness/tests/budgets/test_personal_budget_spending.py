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

import datetime
import logging

import pytest
from hamcrest import assert_that, close_to, equal_to, greater_than, none, not_none

from codemie_test_harness.tests.test_data.budget_test_data import (
    budget_chat_prompt,
    CLI_CLIENT_HEADER,
    DEFAULT_CLI_BUDGET_ID,
    DEFAULT_PREMIUM_BUDGET_ID,
    PREMIUM_MODEL,
)

logger = logging.getLogger(__name__)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_chat_spending_recorded_in_default_budget(
    keycloak_user,
    user_assistant,
    user_assistant_utils,
    user_budget_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    assistant = user_assistant(project_name=email)

    logger.info("Sending assistant request as %s", email)
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    logger.info("Waiting for personal platform spending (user=%s)", email)
    customer = lite_llm_budget_utils.wait_for_spending(email)
    assert_that(customer, not_none(), f"LiteLLM customer not found for {email}")
    assert_that(
        customer["litellm_budget_table"],
        not_none(),
        f"No budget table assigned in LiteLLM for {email}",
    )
    assert_that(
        customer["litellm_budget_table"]["budget_id"],
        equal_to("default"),
        f"Expected default budget assigned in LiteLLM for {email}",
    )
    assert_that(float(customer["spend"]), greater_than(0))

    platform_row = user_budget_utils.get_budget_row_for_project(email)
    assert_that(platform_row, not_none(), f"No budget row for {email}")

    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"),
        none(),
        f"Premium models LiteLLM customer should not exist for {email}",
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_CLI_BUDGET_ID}"),
        none(),
        f"CLI LiteLLM customer should not exist for {email}",
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()

    logger.info(
        "Waiting for platform spend in project_spend_tracking (project=%s)", email
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        email, today, today, "platform"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(customer["spend"]), 0.0001),
        "project_spend_tracking total_spend should match personal platform spending.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_chat_spending_recorded_in_premium_model_budget(
    keycloak_user,
    user_proxy_utils,
    user_budget_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user

    logger.info("Sending premium model request as %s", email)
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=CLI_CLIENT_HEADER,
    ).raise_for_status()

    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    logger.info("Waiting for premium spending (customer=%s)", premium_customer_id)
    customer = lite_llm_budget_utils.wait_for_spending(premium_customer_id)
    assert_that(
        customer, not_none(), f"LiteLLM customer not found for {premium_customer_id}"
    )
    assert_that(
        customer["litellm_budget_table"],
        not_none(),
        f"No budget table assigned in LiteLLM for {premium_customer_id}",
    )
    assert_that(float(customer["spend"]), greater_than(0))

    premium_row = user_budget_utils.get_budget_row_for_premium(email)
    assert_that(premium_row, not_none(), f"No premium budget row for {email}")

    assert_that(
        lite_llm_budget_utils.get_customer_info(email),
        none(),
        f"Platform LiteLLM customer should not exist for {email}",
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_CLI_BUDGET_ID}"),
        none(),
        f"CLI LiteLLM customer should not exist for {email}",
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()

    logger.info(
        "Waiting for premium_models spend in project_spend_tracking (project=%s)", email
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        email, today, today, "premium_models"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(customer["spend"]), 0.0001),
        "project_spend_tracking total_spend should match personal premium_models spending.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_chat_spending_recorded_in_cli_budget(
    keycloak_user,
    default_llm,
    user_proxy_utils,
    user_budget_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user

    logger.info("Sending CLI request as %s", email)
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=CLI_CLIENT_HEADER,
    ).raise_for_status()

    cli_customer_id = f"{email}_{DEFAULT_CLI_BUDGET_ID}"
    logger.info("Waiting for CLI spending (customer=%s)", cli_customer_id)
    customer = lite_llm_budget_utils.wait_for_spending(cli_customer_id)
    assert_that(
        customer, not_none(), f"LiteLLM customer not found for {cli_customer_id}"
    )
    assert_that(
        customer["litellm_budget_table"],
        not_none(),
        f"No budget table assigned in LiteLLM for {cli_customer_id}",
    )
    assert_that(float(customer["spend"]), greater_than(0))

    cli_row = user_budget_utils.get_budget_row_for_cli(email)
    assert_that(cli_row, not_none(), f"No CLI budget row for {email}")

    assert_that(
        lite_llm_budget_utils.get_customer_info(email),
        none(),
        f"Platform LiteLLM customer should not exist for {email}",
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"),
        none(),
        f"Premium models LiteLLM customer should not exist for {email}",
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()

    logger.info("Waiting for CLI spend in project_spend_tracking (project=%s)", email)
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        email, today, today, "cli"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(customer["spend"]), 0.0001),
        "project_spend_tracking total_spend should match personal CLI spending.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_chat_spending_recorded_on_litellm_key_for_platform_request(
    keycloak_user,
    default_llm,
    user_litellm_key,
    user_litellm_integration,
    user_proxy_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user

    logger.info(
        "Sending platform request via personal LiteLLM key (integration=%s)",
        user_litellm_integration.id,
    )
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        integration_id=user_litellm_integration.id,
    ).raise_for_status()

    logger.info("Waiting for personal LiteLLM key spending")
    key_info = lite_llm_budget_utils.wait_for_key_spending(user_litellm_key)
    assert_that(key_info, not_none(), "LiteLLM key info not found")
    assert_that(float(key_info["spend"]), greater_than(0))

    assert_that(
        lite_llm_budget_utils.get_customer_info(email),
        none(),
        f"Platform LiteLLM customer should not exist for {email}",
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"),
        none(),
        f"Premium models LiteLLM customer should not exist for {email}",
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_CLI_BUDGET_ID}"),
        none(),
        f"CLI LiteLLM customer should not exist for {email}",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_chat_spending_recorded_on_litellm_key_for_premium_model(
    keycloak_user,
    user_litellm_key,
    user_litellm_integration,
    user_proxy_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user

    logger.info(
        "Sending premium model request via personal LiteLLM key (integration=%s)",
        user_litellm_integration.id,
    )
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        integration_id=user_litellm_integration.id,
        extra_headers=CLI_CLIENT_HEADER,
    ).raise_for_status()

    logger.info("Waiting for personal LiteLLM key spending")
    key_info = lite_llm_budget_utils.wait_for_key_spending(user_litellm_key)
    assert_that(key_info, not_none(), "LiteLLM key info not found")
    assert_that(float(key_info["spend"]), greater_than(0))

    assert_that(
        lite_llm_budget_utils.get_customer_info(email),
        none(),
        f"Platform LiteLLM customer should not exist for {email}",
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"),
        none(),
        f"Premium models LiteLLM customer should not exist for {email}",
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_CLI_BUDGET_ID}"),
        none(),
        f"CLI LiteLLM customer should not exist for {email}",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_chat_spending_recorded_on_litellm_key_for_cli_request(
    keycloak_user,
    default_llm,
    user_litellm_key,
    user_litellm_integration,
    user_proxy_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user

    logger.info(
        "Sending CLI request via personal LiteLLM key (integration=%s)",
        user_litellm_integration.id,
    )
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        integration_id=user_litellm_integration.id,
        extra_headers=CLI_CLIENT_HEADER,
    ).raise_for_status()

    logger.info("Waiting for personal LiteLLM key spending")
    key_info = lite_llm_budget_utils.wait_for_key_spending(user_litellm_key)
    assert_that(key_info, not_none(), "LiteLLM key info not found")
    assert_that(float(key_info["spend"]), greater_than(0))

    assert_that(
        lite_llm_budget_utils.get_customer_info(email),
        none(),
        f"Platform LiteLLM customer should not exist for {email}",
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"),
        none(),
        f"Premium models LiteLLM customer should not exist for {email}",
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_CLI_BUDGET_ID}"),
        none(),
        f"CLI LiteLLM customer should not exist for {email}",
    )
