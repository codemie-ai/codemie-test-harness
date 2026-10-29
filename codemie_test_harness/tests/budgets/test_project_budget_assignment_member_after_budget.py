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
from time import sleep

import pytest
from hamcrest import assert_that, close_to, equal_to, greater_than, none, not_none

from codemie_test_harness.tests.test_data.budget_test_data import (
    budget_chat_prompt,
    BUDGET_CACHE_DELAY,
    CLI_BUDGET_CATEGORIES,
    CLI_CLIENT_HEADER,
    CLI_PROJECT_HEADER,
    DEFAULT_CLI_BUDGET_ID,
    DEFAULT_PREMIUM_BUDGET_ID,
    PREMIUM_BUDGET_CATEGORIES,
    PREMIUM_MODEL,
    project_key_alias,
)

logger = logging.getLogger(__name__)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_platform_budget_created_before_member_assigned_routes_spending_to_project_key(
    keycloak_user,
    user_id,
    user_assistant,
    user_assistant_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_no_member,
    project_budget_groups,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_no_member
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")

    budget = project_budget_groups.create(project_name)
    logger.info("Assigning user (%s) to project (platform budget pre-set)", user_id)
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    sleep(30)

    # Phase 1 — user joined with platform budget already active: first request routes to project key
    logger.info(
        "Phase 1: user assigned after platform budget — expecting project platform key spending for %s",
        email,
    )
    assistant = user_assistant(project_name=project_name)
    logger.info("Sending assistant request (project platform budget pre-set)")
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info(
        "Waiting for project platform key alias spending (alias=%s)", platform_alias
    )
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    assert_that(lite_llm_budget_utils.get_customer_info(email), none())
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_CLI_BUDGET_ID}"),
        none(),
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"),
        none(),
    )
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for platform spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "platform"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(project_key_info["spend"]), 0.0001),
        "project_spend_tracking total_spend should match project platform key spend.",
    )

    # Phase 2 — project budget deleted: spending reverts to personal
    logger.info(
        "Phase 2: deleting project platform budget — expecting spending to revert to personal"
    )
    project_budget_groups.delete(budget)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending assistant request (project budget deleted)")
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info("Waiting for personal spending (user=%s)", email)
    customer = lite_llm_budget_utils.wait_for_spending(email)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_cli_budget_created_before_member_assigned_routes_cli_spending_to_project_key(
    keycloak_user,
    user_id,
    user_proxy_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_no_member,
    project_budget_groups,
    default_llm,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_no_member
    cli_customer_id = f"{email}_{DEFAULT_CLI_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    budget = project_budget_groups.create(project_name, CLI_BUDGET_CATEGORIES)
    logger.info("Assigning user (%s) to project (CLI budget pre-set)", user_id)
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    sleep(30)

    # Phase 1 — user joined with CLI budget already active: first request routes to project CLI key
    logger.info(
        "Phase 1: user assigned after CLI budget — expecting project CLI key spending for %s",
        cli_customer_id,
    )
    logger.info("Sending CLI request (project CLI budget pre-set)")
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info("Waiting for project CLI key alias spending (alias=%s)", cli_alias)
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(cli_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    assert_that(lite_llm_budget_utils.get_customer_info(cli_customer_id), none())
    assert_that(lite_llm_budget_utils.get_customer_info(email), none())
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"),
        none(),
    )
    assert_that(
        lite_llm_budget_utils.get_key_spend_by_alias(platform_alias),
        equal_to(0),
        "Platform key of the minimal platform budget must not be charged.",
    )
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for cli spend in project_spend_tracking (project=%s)", project_name
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "cli"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(project_key_info["spend"]), 0.0001),
        "project_spend_tracking total_spend should match project cli key spend.",
    )

    # Phase 2 — project budget deleted: spending reverts to personal CLI customer
    logger.info(
        "Phase 2: deleting project CLI budget — expecting CLI spending to revert to personal"
    )
    project_budget_groups.delete(budget)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending CLI request (project budget deleted)")
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info("Waiting for personal CLI spending (customer=%s)", cli_customer_id)
    customer = lite_llm_budget_utils.wait_for_spending(cli_customer_id)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_premium_budget_created_before_member_assigned_routes_premium_spending_to_project_key(
    keycloak_user,
    user_id,
    user_proxy_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_no_member,
    project_budget_groups,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_no_member
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    budget = project_budget_groups.create(project_name, PREMIUM_BUDGET_CATEGORIES)
    logger.info("Assigning user (%s) to project (premium budget pre-set)", user_id)
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    sleep(30)

    # Phase 1 — user joined with premium budget already active: first request routes to project premium key
    logger.info(
        "Phase 1: user assigned after premium budget — expecting project premium key spending for %s",
        premium_customer_id,
    )
    logger.info("Sending premium request (project premium budget pre-set)")
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info(
        "Waiting for project premium key alias spending (alias=%s)", premium_alias
    )
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    assert_that(lite_llm_budget_utils.get_customer_info(premium_customer_id), none())
    assert_that(lite_llm_budget_utils.get_customer_info(email), none())
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_CLI_BUDGET_ID}"),
        none(),
    )
    assert_that(
        lite_llm_budget_utils.get_key_spend_by_alias(platform_alias),
        equal_to(0),
        "Platform key of the minimal platform budget must not be charged.",
    )
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for premium_models spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "premium_models"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(project_key_info["spend"]), 0.0001),
        "project_spend_tracking total_spend should match project premium_models key spend.",
    )

    # Phase 2 — project budget deleted: spending reverts to personal premium customer
    logger.info(
        "Phase 2: deleting project premium budget — expecting premium spending to revert to personal"
    )
    project_budget_groups.delete(budget)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending premium request (project budget deleted)")
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info(
        "Waiting for personal premium spending (customer=%s)", premium_customer_id
    )
    customer = lite_llm_budget_utils.wait_for_spending(premium_customer_id)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_all_budgets_created_before_member_assigned_platform_request_routes_to_platform_key(
    keycloak_user,
    user_id,
    user_assistant,
    user_assistant_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_no_member_with_all_three_budgets,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name, _, _, _, platform_alias, cli_alias, premium_alias = (
        project_no_member_with_all_three_budgets
    )

    logger.info("Assigning user (%s) to project (all 3 budgets pre-set)", user_id)
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    sleep(30)

    assistant = user_assistant(project_name=project_name)
    logger.info(
        "Sending assistant (platform) request — user joined with all 3 budgets active"
    )
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    logger.info("Waiting for platform key spending (alias=%s)", platform_alias)
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))

    cli_key_info = lite_llm_budget_utils.get_key_info_by_alias(cli_alias)
    assert_that(cli_key_info, not_none())
    assert_that(float(cli_key_info["spend"]), equal_to(0))

    premium_key_info = lite_llm_budget_utils.get_key_info_by_alias(premium_alias)
    assert_that(premium_key_info, not_none())
    assert_that(float(premium_key_info["spend"]), equal_to(0))

    assert_that(lite_llm_budget_utils.get_customer_info(email), none())

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for platform spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "platform"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(project_key_info["spend"]), 0.0001),
        "project_spend_tracking total_spend should match project platform key spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_all_budgets_created_before_member_assigned_cli_request_routes_to_cli_key(
    keycloak_user,
    user_id,
    user_proxy_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    default_llm,
    project_no_member_with_all_three_budgets,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name, _, _, _, platform_alias, cli_alias, premium_alias = (
        project_no_member_with_all_three_budgets
    )
    cli_customer_id = f"{email}_{DEFAULT_CLI_BUDGET_ID}"
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    logger.info("Assigning user (%s) to project (all 3 budgets pre-set)", user_id)
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    sleep(30)

    logger.info("Sending CLI request — user joined with all 3 budgets active")
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()

    logger.info("Waiting for CLI key spending (alias=%s)", cli_alias)
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(cli_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))

    platform_key_info = lite_llm_budget_utils.get_key_info_by_alias(platform_alias)
    assert_that(platform_key_info, not_none())
    assert_that(float(platform_key_info["spend"]), equal_to(0))

    premium_key_info = lite_llm_budget_utils.get_key_info_by_alias(premium_alias)
    assert_that(premium_key_info, not_none())
    assert_that(float(premium_key_info["spend"]), equal_to(0))

    assert_that(lite_llm_budget_utils.get_customer_info(cli_customer_id), none())

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for cli spend in project_spend_tracking (project=%s)", project_name
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "cli"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(project_key_info["spend"]), 0.0001),
        "project_spend_tracking total_spend should match project cli key spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_all_budgets_created_before_member_assigned_premium_request_routes_to_premium_key(
    keycloak_user,
    user_id,
    user_proxy_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_no_member_with_all_three_budgets,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name, _, _, _, platform_alias, cli_alias, premium_alias = (
        project_no_member_with_all_three_budgets
    )
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    logger.info("Assigning user (%s) to project (all 3 budgets pre-set)", user_id)
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    sleep(30)

    logger.info("Sending premium request — user joined with all 3 budgets active")
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()

    logger.info("Waiting for premium key spending (alias=%s)", premium_alias)
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))

    platform_key_info = lite_llm_budget_utils.get_key_info_by_alias(platform_alias)
    assert_that(platform_key_info, not_none())
    assert_that(float(platform_key_info["spend"]), equal_to(0))

    cli_key_info = lite_llm_budget_utils.get_key_info_by_alias(cli_alias)
    assert_that(cli_key_info, not_none())
    assert_that(float(cli_key_info["spend"]), equal_to(0))

    assert_that(lite_llm_budget_utils.get_customer_info(premium_customer_id), none())

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for premium_models spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "premium_models"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(project_key_info["spend"]), 0.0001),
        "project_spend_tracking total_spend should match project premium_models key spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_platform_budget_created_before_member_assigned_routes_cli_spending_to_platform_key(
    keycloak_user,
    user_id,
    user_proxy_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_no_member,
    project_budget_groups,
    default_llm,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_no_member
    cli_customer_id = f"{email}_{DEFAULT_CLI_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    budget = project_budget_groups.create(project_name)
    logger.info(
        "Assigning user (%s) to project (platform budget pre-set, no CLI budget)",
        user_id,
    )
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    sleep(30)

    # Phase 1 — only platform budget pre-set: CLI request falls back to platform key
    logger.info(
        "Phase 1: user assigned after platform-only budget — expecting CLI spending on platform key (alias=%s)",
        platform_alias,
    )
    logger.info("Sending CLI request (only project platform budget pre-set)")
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info(
        "Waiting for project platform key alias spending (alias=%s)", platform_alias
    )
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    assert_that(lite_llm_budget_utils.get_customer_info(cli_customer_id), none())
    assert_that(lite_llm_budget_utils.get_customer_info(email), none())
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"),
        none(),
    )
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for platform spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "platform"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(project_key_info["spend"]), 0.0001),
        "project_spend_tracking total_spend should match project platform key spend.",
    )

    # Phase 2 — project budget deleted: spending reverts to personal CLI customer
    logger.info(
        "Phase 2: deleting project platform budget — expecting CLI spending to revert to personal"
    )
    project_budget_groups.delete(budget)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending CLI request (project budget deleted)")
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info("Waiting for personal CLI spending (customer=%s)", cli_customer_id)
    customer = lite_llm_budget_utils.wait_for_spending(cli_customer_id)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_platform_budget_created_before_member_assigned_routes_premium_spending_to_platform_key(
    keycloak_user,
    user_id,
    user_proxy_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_no_member,
    project_budget_groups,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_no_member
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    budget = project_budget_groups.create(project_name)
    logger.info(
        "Assigning user (%s) to project (platform budget pre-set, no premium budget)",
        user_id,
    )
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    sleep(30)

    # Phase 1 — only platform budget pre-set: premium request falls back to platform key
    logger.info(
        "Phase 1: user assigned after platform-only budget — expecting premium spending on platform key (alias=%s)",
        platform_alias,
    )
    logger.info("Sending premium request (only project platform budget pre-set)")
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info(
        "Waiting for project platform key alias spending (alias=%s)", platform_alias
    )
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    assert_that(lite_llm_budget_utils.get_customer_info(premium_customer_id), none())
    assert_that(lite_llm_budget_utils.get_customer_info(email), none())
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_CLI_BUDGET_ID}"),
        none(),
    )
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for platform spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "platform"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(project_key_info["spend"]), 0.0001),
        "project_spend_tracking total_spend should match project platform key spend.",
    )

    # Phase 2 — project budget deleted: spending reverts to personal premium customer
    logger.info(
        "Phase 2: deleting project platform budget — expecting premium spending to revert to personal"
    )
    project_budget_groups.delete(budget)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending premium request (project budget deleted)")
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info(
        "Waiting for personal premium spending (customer=%s)", premium_customer_id
    )
    customer = lite_llm_budget_utils.wait_for_spending(premium_customer_id)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_cli_budget_created_before_member_assigned_routes_premium_spending_to_cli_key(
    keycloak_user,
    user_id,
    user_proxy_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_no_member,
    project_budget_groups,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_no_member
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    budget = project_budget_groups.create(project_name, CLI_BUDGET_CATEGORIES)
    logger.info(
        "Assigning user (%s) to project (CLI budget pre-set, no premium budget)",
        user_id,
    )
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    sleep(30)

    # Phase 1 — only CLI budget pre-set: premium request falls back to CLI key
    logger.info(
        "Phase 1: user assigned after CLI-only budget — expecting premium spending on CLI key (alias=%s)",
        cli_alias,
    )
    logger.info("Sending premium request (only project CLI budget pre-set)")
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info("Waiting for project CLI key alias spending (alias=%s)", cli_alias)
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(cli_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    assert_that(lite_llm_budget_utils.get_customer_info(premium_customer_id), none())
    assert_that(lite_llm_budget_utils.get_customer_info(email), none())
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_CLI_BUDGET_ID}"),
        none(),
    )
    assert_that(
        lite_llm_budget_utils.get_key_spend_by_alias(platform_alias),
        equal_to(0),
        "Platform key of the minimal platform budget must not be charged.",
    )
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for cli spend in project_spend_tracking (project=%s)", project_name
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "cli"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(project_key_info["spend"]), 0.0001),
        "project_spend_tracking total_spend should match project cli key spend.",
    )

    # Phase 2 — project budget deleted: spending reverts to personal premium customer
    logger.info(
        "Phase 2: deleting project CLI budget — expecting premium spending to revert to personal"
    )
    project_budget_groups.delete(budget)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending premium request (project budget deleted)")
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info(
        "Waiting for personal premium spending (customer=%s)", premium_customer_id
    )
    customer = lite_llm_budget_utils.wait_for_spending(premium_customer_id)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_premium_budget_created_before_member_assigned_routes_chat_premium_spending_to_project_key(
    keycloak_user,
    user_id,
    user_premium_assistant,
    user_assistant_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_no_member,
    project_budget_groups,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_no_member
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")

    budget = project_budget_groups.create(project_name, PREMIUM_BUDGET_CATEGORIES)
    logger.info("Assigning user (%s) to project (premium budget pre-set)", user_id)
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    sleep(30)

    # Phase 1 — user joined with premium budget already active: chat routes to project premium key
    logger.info(
        "Phase 1: user assigned after premium budget — expecting project premium key spending for %s",
        premium_customer_id,
    )
    assistant = user_premium_assistant(project_name=project_name)
    logger.info("Sending chat premium request (project premium budget pre-set)")
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info(
        "Waiting for project premium key alias spending (alias=%s)", premium_alias
    )
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    assert_that(lite_llm_budget_utils.get_customer_info(premium_customer_id), none())
    assert_that(lite_llm_budget_utils.get_customer_info(email), none())
    assert_that(
        lite_llm_budget_utils.get_customer_info(f"{email}_{DEFAULT_CLI_BUDGET_ID}"),
        none(),
    )
    assert_that(
        lite_llm_budget_utils.get_key_spend_by_alias(platform_alias),
        equal_to(0),
        "Platform key of the minimal platform budget must not be charged.",
    )
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for premium_models spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "premium_models"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(project_key_info["spend"]), 0.0001),
        "project_spend_tracking total_spend should match project premium_models key spend.",
    )

    # Phase 2 — project budget deleted: spending reverts to personal premium customer
    logger.info(
        "Phase 2: deleting project premium budget — expecting premium spending to revert to personal"
    )
    project_budget_groups.delete(budget)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending chat premium request (project budget deleted)")
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info(
        "Waiting for personal premium spending (customer=%s)", premium_customer_id
    )
    customer = lite_llm_budget_utils.wait_for_spending(premium_customer_id)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_all_budgets_created_before_member_assigned_chat_premium_request_routes_to_premium_key(
    keycloak_user,
    user_id,
    user_premium_assistant,
    user_assistant_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_no_member_with_all_three_budgets,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name, _, _, _, platform_alias, cli_alias, premium_alias = (
        project_no_member_with_all_three_budgets
    )
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"

    logger.info("Assigning user (%s) to project (all 3 budgets pre-set)", user_id)
    admin_project_utils.assign_user_to_project(
        project_name, user_id, is_project_admin=False
    )
    sleep(30)

    assistant = user_premium_assistant(project_name=project_name)
    logger.info("Sending chat premium request — user joined with all 3 budgets active")
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    logger.info("Waiting for premium key spending (alias=%s)", premium_alias)
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))

    platform_key_info = lite_llm_budget_utils.get_key_info_by_alias(platform_alias)
    assert_that(platform_key_info, not_none())
    assert_that(float(platform_key_info["spend"]), equal_to(0))

    cli_key_info = lite_llm_budget_utils.get_key_info_by_alias(cli_alias)
    assert_that(cli_key_info, not_none())
    assert_that(float(cli_key_info["spend"]), equal_to(0))

    assert_that(lite_llm_budget_utils.get_customer_info(premium_customer_id), none())

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()
    logger.info(
        "Waiting for premium_models spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "premium_models"
    )
    assert_that(
        spends["total_spend"],
        close_to(float(project_key_info["spend"]), 0.0001),
        "project_spend_tracking total_spend should match project premium_models key spend.",
    )
