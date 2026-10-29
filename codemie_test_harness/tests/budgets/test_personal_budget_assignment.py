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
from hamcrest import assert_that, close_to, equal_to, greater_than, not_none

from codemie_test_harness.tests.test_data.budget_test_data import (
    budget_chat_prompt,
    DEFAULT_CLI_BUDGET_ID,
    DEFAULT_PLATFORM_BUDGET_ID,
    DEFAULT_PREMIUM_BUDGET_ID,
    PREMIUM_MODEL,
    CLI_CLIENT_HEADER,
)

logger = logging.getLogger(__name__)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_assigns_platform_budget_to_user(
    keycloak_user,
    default_llm,
    user_proxy_utils,
    user_id,
    admin_budget_utils,
    lite_llm_budget_utils,
    assigned_platform_budget,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    budget_id, initial_spend = assigned_platform_budget

    logger.info(
        "Waiting for platform customer budget to be assigned (user=%s, budget=%s)",
        email,
        budget_id,
    )
    customer = lite_llm_budget_utils.wait_for_customer_budget_id(email, budget_id)
    assert_that(customer, not_none(), f"LiteLLM customer not found for {email}")
    assert_that(customer["litellm_budget_table"], not_none())
    assert_that(
        customer["litellm_budget_table"]["budget_id"],
        equal_to(budget_id),
    )

    logger.info("Sending platform request with assigned budget (user=%s)", email)
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
    ).raise_for_status()
    logger.info("Waiting for platform spending to exceed initial %.6f", initial_spend)
    customer = lite_llm_budget_utils.wait_for_spending_above(email, initial_spend)
    spend_after_assigned = float(customer.get("spend", 0))
    assert_that(spend_after_assigned, greater_than(initial_spend))

    logger.info("Unassigning platform budget from user %s", email)
    admin_budget_utils.unassign_user_budget(user_id, "platform")

    logger.info("Sending platform request after budget unassignment (user=%s)", email)
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
    ).raise_for_status()
    logger.info(
        "Waiting for platform spending to exceed %.6f after unassignment",
        spend_after_assigned,
    )
    customer = lite_llm_budget_utils.wait_for_spending_above(
        email, spend_after_assigned
    )
    final_spend = float(customer.get("spend", 0))
    assert_that(final_spend, greater_than(spend_after_assigned))

    logger.info("Waiting for platform budget to revert to default (user=%s)", email)
    customer = lite_llm_budget_utils.wait_for_customer_budget_id(
        email, DEFAULT_PLATFORM_BUDGET_ID
    )
    assert_that(customer, not_none())
    assert_that(customer["litellm_budget_table"], not_none())
    assert_that(
        customer["litellm_budget_table"]["budget_id"],
        equal_to(DEFAULT_PLATFORM_BUDGET_ID),
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends()
    logger.info(
        "Waiting for platform spend in project_spend_tracking (project=%s)", email
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        email, today, today, "platform"
    )
    assert_that(
        spends["total_spend"],
        close_to(final_spend, 0.0001),
        "project_spend_tracking total_spend should match user platform spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_assigns_cli_budget_to_user(
    keycloak_user,
    default_llm,
    user_proxy_utils,
    user_id,
    admin_budget_utils,
    lite_llm_budget_utils,
    assigned_cli_budget,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    budget_id, initial_spend = assigned_cli_budget
    cli_customer_id = f"{email}_{DEFAULT_CLI_BUDGET_ID}"

    logger.info(
        "Waiting for CLI customer budget to be assigned (customer=%s, budget=%s)",
        cli_customer_id,
        budget_id,
    )
    customer = lite_llm_budget_utils.wait_for_customer_budget_id(
        cli_customer_id, budget_id
    )
    assert_that(
        customer, not_none(), f"LiteLLM customer not found for {cli_customer_id}"
    )
    assert_that(customer["litellm_budget_table"], not_none())
    assert_that(customer["litellm_budget_table"]["budget_id"], equal_to(budget_id))

    logger.info(
        "Sending CLI request with assigned budget (customer=%s)", cli_customer_id
    )
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=CLI_CLIENT_HEADER,
    ).raise_for_status()
    logger.info("Waiting for CLI spending to exceed initial %.6f", initial_spend)
    customer = lite_llm_budget_utils.wait_for_spending_above(
        cli_customer_id, initial_spend
    )
    spend_after_assigned = float(customer.get("spend", 0))
    assert_that(spend_after_assigned, greater_than(initial_spend))

    logger.info("Unassigning CLI budget from user %s", email)
    admin_budget_utils.unassign_user_budget(user_id, "cli")

    logger.info(
        "Sending CLI request after budget unassignment (customer=%s)", cli_customer_id
    )
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=CLI_CLIENT_HEADER,
    ).raise_for_status()
    logger.info(
        "Waiting for CLI spending to exceed %.6f after unassignment",
        spend_after_assigned,
    )
    customer = lite_llm_budget_utils.wait_for_spending_above(
        cli_customer_id, spend_after_assigned
    )
    final_spend = float(customer.get("spend", 0))
    assert_that(final_spend, greater_than(spend_after_assigned))

    logger.info(
        "Waiting for CLI budget to revert to default (customer=%s)", cli_customer_id
    )
    customer = lite_llm_budget_utils.wait_for_customer_budget_id(
        cli_customer_id, DEFAULT_CLI_BUDGET_ID
    )
    assert_that(customer, not_none())
    assert_that(customer["litellm_budget_table"], not_none())
    assert_that(
        customer["litellm_budget_table"]["budget_id"],
        equal_to(DEFAULT_CLI_BUDGET_ID),
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends()
    logger.info("Waiting for cli spend in project_spend_tracking (project=%s)", email)
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        email, today, today, "cli"
    )
    assert_that(
        spends["total_spend"],
        close_to(final_spend, 0.0001),
        "project_spend_tracking total_spend should match user cli spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_assigns_premium_budget_to_user(
    keycloak_user,
    user_proxy_utils,
    user_id,
    admin_budget_utils,
    lite_llm_budget_utils,
    assigned_premium_budget,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    budget_id, initial_spend = assigned_premium_budget
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"

    logger.info(
        "Waiting for premium customer budget to be assigned (customer=%s, budget=%s)",
        premium_customer_id,
        budget_id,
    )
    customer = lite_llm_budget_utils.wait_for_customer_budget_id(
        premium_customer_id, budget_id
    )
    assert_that(
        customer, not_none(), f"LiteLLM customer not found for {premium_customer_id}"
    )
    assert_that(customer["litellm_budget_table"], not_none())
    assert_that(customer["litellm_budget_table"]["budget_id"], equal_to(budget_id))

    logger.info(
        "Sending premium request with assigned budget (customer=%s)",
        premium_customer_id,
    )
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
    ).raise_for_status()
    logger.info("Waiting for premium spending to exceed initial %.6f", initial_spend)
    customer = lite_llm_budget_utils.wait_for_spending_above(
        premium_customer_id, initial_spend
    )
    spend_after_assigned = float(customer.get("spend", 0))
    assert_that(spend_after_assigned, greater_than(initial_spend))

    logger.info("Unassigning premium budget from user %s", email)
    admin_budget_utils.unassign_user_budget(user_id, "premium_models")

    logger.info(
        "Sending premium request after budget unassignment (customer=%s)",
        premium_customer_id,
    )
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
    ).raise_for_status()
    logger.info(
        "Waiting for premium spending to exceed %.6f after unassignment",
        spend_after_assigned,
    )
    customer = lite_llm_budget_utils.wait_for_spending_above(
        premium_customer_id, spend_after_assigned
    )
    final_spend = float(customer.get("spend", 0))
    assert_that(final_spend, greater_than(spend_after_assigned))

    logger.info(
        "Waiting for premium budget to revert to default (customer=%s)",
        premium_customer_id,
    )
    customer = lite_llm_budget_utils.wait_for_customer_budget_id(
        premium_customer_id, DEFAULT_PREMIUM_BUDGET_ID
    )
    assert_that(customer, not_none())
    assert_that(customer["litellm_budget_table"], not_none())
    assert_that(
        customer["litellm_budget_table"]["budget_id"],
        equal_to(DEFAULT_PREMIUM_BUDGET_ID),
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends()
    logger.info(
        "Waiting for premium_models spend in project_spend_tracking (project=%s)", email
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        email, today, today, "premium_models"
    )
    assert_that(
        spends["total_spend"],
        close_to(final_spend, 0.0001),
        "project_spend_tracking total_spend should match user premium_models spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_assigns_premium_budget_to_user_via_chat(
    keycloak_user,
    user_assistant_utils,
    user_premium_assistant,
    user_id,
    admin_budget_utils,
    lite_llm_budget_utils,
    assigned_premium_budget,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    budget_id, initial_spend = assigned_premium_budget
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"

    logger.info(
        "Waiting for premium customer budget to be assigned (customer=%s, budget=%s)",
        premium_customer_id,
        budget_id,
    )
    customer = lite_llm_budget_utils.wait_for_customer_budget_id(
        premium_customer_id, budget_id
    )
    assert_that(
        customer, not_none(), f"LiteLLM customer not found for {premium_customer_id}"
    )
    assert_that(customer["litellm_budget_table"], not_none())
    assert_that(customer["litellm_budget_table"]["budget_id"], equal_to(budget_id))

    logger.info(
        "Creating premium assistant and chatting (customer=%s)", premium_customer_id
    )
    assistant = user_premium_assistant(project_name=email)
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info("Waiting for premium spending to exceed initial %.6f", initial_spend)
    customer = lite_llm_budget_utils.wait_for_spending_above(
        premium_customer_id, initial_spend
    )
    spend_after_assigned = float(customer.get("spend", 0))
    assert_that(spend_after_assigned, greater_than(initial_spend))

    logger.info("Unassigning premium budget from user %s", email)
    admin_budget_utils.unassign_user_budget(user_id, "premium_models")

    logger.info(
        "Sending another assistant chat after budget unassignment (customer=%s)",
        premium_customer_id,
    )
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info(
        "Waiting for premium spending to exceed %.6f after unassignment",
        spend_after_assigned,
    )
    customer = lite_llm_budget_utils.wait_for_spending_above(
        premium_customer_id, spend_after_assigned
    )
    final_spend = float(customer.get("spend", 0))
    assert_that(final_spend, greater_than(spend_after_assigned))

    logger.info(
        "Waiting for premium budget to revert to default (customer=%s)",
        premium_customer_id,
    )
    customer = lite_llm_budget_utils.wait_for_customer_budget_id(
        premium_customer_id, DEFAULT_PREMIUM_BUDGET_ID
    )
    assert_that(customer, not_none())
    assert_that(customer["litellm_budget_table"], not_none())
    assert_that(
        customer["litellm_budget_table"]["budget_id"],
        equal_to(DEFAULT_PREMIUM_BUDGET_ID),
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends()
    logger.info(
        "Waiting for premium_models spend in project_spend_tracking (project=%s)", email
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        email, today, today, "premium_models"
    )
    assert_that(
        spends["total_spend"],
        close_to(final_spend, 0.0001),
        "project_spend_tracking total_spend should match user premium_models spend.",
    )
