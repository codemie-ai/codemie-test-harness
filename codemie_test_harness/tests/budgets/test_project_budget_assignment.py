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
def test_admin_creates_platform_project_budget_routes_spending_from_personal(
    keycloak_user,
    user_id,
    user_assistant,
    user_assistant_utils,
    lite_llm_budget_utils,
    project_setup,
    project_budget_groups,
    default_llm,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_setup
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")

    # Phase 1 — no project budget: spending goes to personal
    logger.info(
        "Phase 1: no project budget — expecting personal spending for %s", email
    )
    assistant = user_assistant(project_name=project_name)
    logger.info("Sending assistant request (no project budget)")
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info("Waiting for personal spending (user=%s)", email)
    customer = lite_llm_budget_utils.wait_for_spending(email)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))
    personal_spend_after_phase1 = float(customer["spend"])
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(platform_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    # Phase 2 — project budget created: spending goes to project key
    logger.info(
        "Phase 2: creating project platform budget — expecting spending on project key (alias=%s)",
        platform_alias,
    )
    budget = project_budget_groups.create(project_name)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending assistant request (project platform budget active)")
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info(
        "Waiting for project platform key alias spending (alias=%s)", platform_alias
    )
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    current_personal = lite_llm_budget_utils.get_customer_info(email)
    assert_that(
        float(current_personal["spend"]),
        close_to(personal_spend_after_phase1, 0.0001),
    )
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

    # Phase 3 — project budget deleted: spending reverts to personal
    logger.info(
        "Phase 3: deleting project budget — expecting spending to revert to personal"
    )
    project_budget_groups.delete(budget)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending assistant request (project budget deleted)")
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info(
        "Waiting for personal spending to exceed %.6f", personal_spend_after_phase1
    )
    customer = lite_llm_budget_utils.wait_for_spending_above(
        email, personal_spend_after_phase1
    )
    assert_that(float(customer["spend"]), greater_than(personal_spend_after_phase1))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_creates_cli_project_budget_routes_spending_from_personal(
    keycloak_user,
    user_proxy_utils,
    lite_llm_budget_utils,
    project_setup,
    project_budget_groups,
    default_llm,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_setup
    cli_customer_id = f"{email}_{DEFAULT_CLI_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    # Phase 1 — no project budget: spending goes to personal CLI customer
    logger.info(
        "Phase 1: no project CLI budget — expecting personal CLI spending for %s",
        cli_customer_id,
    )
    logger.info("Sending CLI request (no project budget)")
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info("Waiting for personal CLI spending (customer=%s)", cli_customer_id)
    customer = lite_llm_budget_utils.wait_for_spending(cli_customer_id)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))
    personal_cli_spend_after_phase1 = float(customer["spend"])
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(platform_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    # Phase 2 — project budget created: spending goes to project CLI key
    logger.info(
        "Phase 2: creating project CLI budget — expecting spending on project CLI key (alias=%s)",
        cli_alias,
    )
    budget = project_budget_groups.create(project_name, CLI_BUDGET_CATEGORIES)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending CLI request (project CLI budget active)")
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info("Waiting for project CLI key alias spending (alias=%s)", cli_alias)
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(cli_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    current_cli = lite_llm_budget_utils.get_customer_info(cli_customer_id)
    assert_that(
        float(current_cli["spend"]),
        close_to(personal_cli_spend_after_phase1, 0.0001),
    )
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
    admin_spend_tracking_utils.collect_spends()
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

    # Phase 3 — project budget deleted: spending reverts to personal CLI customer
    logger.info(
        "Phase 3: deleting project CLI budget — expecting CLI spending to revert to personal"
    )
    project_budget_groups.delete(budget)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending CLI request (project budget deleted)")
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info(
        "Waiting for personal CLI spending to exceed %.6f",
        personal_cli_spend_after_phase1,
    )
    customer = lite_llm_budget_utils.wait_for_spending_above(
        cli_customer_id, personal_cli_spend_after_phase1
    )
    assert_that(float(customer["spend"]), greater_than(personal_cli_spend_after_phase1))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_creates_premium_project_budget_routes_spending_from_personal(
    keycloak_user,
    user_proxy_utils,
    lite_llm_budget_utils,
    project_setup,
    project_budget_groups,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_setup
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    # Phase 1 — no project budget: spending goes to personal premium customer
    logger.info(
        "Phase 1: no project premium budget — expecting personal premium spending for %s",
        premium_customer_id,
    )
    logger.info("Sending premium request (no project budget)")
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
    personal_premium_spend_after_phase1 = float(customer["spend"])
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(platform_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    # Phase 2 — project budget created: spending goes to project premium key
    logger.info(
        "Phase 2: creating project premium budget — expecting spending on project premium key (alias=%s)",
        premium_alias,
    )
    budget = project_budget_groups.create(project_name, PREMIUM_BUDGET_CATEGORIES)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending premium request (project premium budget active)")
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
    current_premium = lite_llm_budget_utils.get_customer_info(premium_customer_id)
    assert_that(
        float(current_premium["spend"]),
        close_to(personal_premium_spend_after_phase1, 0.0001),
    )
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

    # Phase 3 — project budget deleted: spending reverts to personal premium customer
    logger.info(
        "Phase 3: deleting project premium budget — expecting premium spending to revert to personal"
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
        "Waiting for personal premium spending to exceed %.6f",
        personal_premium_spend_after_phase1,
    )
    customer = lite_llm_budget_utils.wait_for_spending_above(
        premium_customer_id, personal_premium_spend_after_phase1
    )
    assert_that(
        float(customer["spend"]), greater_than(personal_premium_spend_after_phase1)
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_all_project_budgets_created_platform_request_routes_to_platform_key(
    keycloak_user,
    user_assistant,
    user_assistant_utils,
    lite_llm_budget_utils,
    project_with_all_three_budgets,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name, _, _, _, platform_alias, cli_alias, premium_alias = (
        project_with_all_three_budgets
    )

    assistant = user_assistant(project_name=project_name)
    logger.info(
        "Sending assistant (platform) request with all 3 project budgets active"
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
def test_all_project_budgets_created_cli_request_routes_to_cli_key(
    keycloak_user,
    user_proxy_utils,
    lite_llm_budget_utils,
    default_llm,
    project_with_all_three_budgets,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name, _, _, _, platform_alias, cli_alias, premium_alias = (
        project_with_all_three_budgets
    )
    cli_customer_id = f"{email}_{DEFAULT_CLI_BUDGET_ID}"
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    logger.info("Sending CLI request with all 3 project budgets active")
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
def test_all_project_budgets_created_premium_request_routes_to_premium_key(
    keycloak_user,
    user_proxy_utils,
    lite_llm_budget_utils,
    project_with_all_three_budgets,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name, _, _, _, platform_alias, cli_alias, premium_alias = (
        project_with_all_three_budgets
    )
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    logger.info("Sending premium request with all 3 project budgets active")
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
def test_admin_creates_platform_project_budget_routes_cli_spending_from_personal(
    keycloak_user,
    user_proxy_utils,
    lite_llm_budget_utils,
    project_setup,
    project_budget_groups,
    default_llm,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_setup
    cli_customer_id = f"{email}_{DEFAULT_CLI_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    # Phase 1 — no project budget: spending goes to personal CLI customer
    logger.info(
        "Phase 1: no project budget — expecting personal CLI spending for %s",
        cli_customer_id,
    )
    logger.info("Sending CLI request (no project budget)")
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info("Waiting for personal CLI spending (customer=%s)", cli_customer_id)
    customer = lite_llm_budget_utils.wait_for_spending(cli_customer_id)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))
    personal_cli_spend_after_phase1 = float(customer["spend"])
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(platform_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    # Phase 2 — only platform budget created: CLI spending falls back to project platform key
    logger.info(
        "Phase 2: creating project platform budget (no CLI budget) — expecting CLI spending on platform key (alias=%s)",
        platform_alias,
    )
    budget = project_budget_groups.create(project_name)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending CLI request (only project platform budget active)")
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
    current_cli = lite_llm_budget_utils.get_customer_info(cli_customer_id)
    assert_that(
        float(current_cli["spend"]),
        close_to(personal_cli_spend_after_phase1, 0.0001),
    )
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

    # Phase 3 — project budget deleted: spending reverts to personal CLI customer
    logger.info(
        "Phase 3: deleting project platform budget — expecting CLI spending to revert to personal"
    )
    project_budget_groups.delete(budget)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending CLI request (project budget deleted)")
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info(
        "Waiting for personal CLI spending to exceed %.6f",
        personal_cli_spend_after_phase1,
    )
    customer = lite_llm_budget_utils.wait_for_spending_above(
        cli_customer_id, personal_cli_spend_after_phase1
    )
    assert_that(float(customer["spend"]), greater_than(personal_cli_spend_after_phase1))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_creates_platform_project_budget_routes_premium_spending_from_personal(
    keycloak_user,
    user_proxy_utils,
    lite_llm_budget_utils,
    project_setup,
    project_budget_groups,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_setup
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    # Phase 1 — no project budget: spending goes to personal premium customer
    logger.info(
        "Phase 1: no project budget — expecting personal premium spending for %s",
        premium_customer_id,
    )
    logger.info("Sending premium request (no project budget)")
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
    personal_premium_spend_after_phase1 = float(customer["spend"])
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(platform_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    # Phase 2 — only platform budget created: premium spending falls back to project platform key
    logger.info(
        "Phase 2: creating project platform budget (no premium budget) — expecting premium spending on platform key (alias=%s)",
        platform_alias,
    )
    budget = project_budget_groups.create(project_name)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending premium request (only project platform budget active)")
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
    current_premium = lite_llm_budget_utils.get_customer_info(premium_customer_id)
    assert_that(
        float(current_premium["spend"]),
        close_to(personal_premium_spend_after_phase1, 0.0001),
    )
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

    # Phase 3 — project budget deleted: spending reverts to personal premium customer
    logger.info(
        "Phase 3: deleting project platform budget — expecting premium spending to revert to personal"
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
        "Waiting for personal premium spending to exceed %.6f",
        personal_premium_spend_after_phase1,
    )
    customer = lite_llm_budget_utils.wait_for_spending_above(
        premium_customer_id, personal_premium_spend_after_phase1
    )
    assert_that(
        float(customer["spend"]), greater_than(personal_premium_spend_after_phase1)
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_creates_cli_project_budget_routes_premium_spending_from_personal(
    keycloak_user,
    user_proxy_utils,
    lite_llm_budget_utils,
    project_setup,
    project_budget_groups,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_setup
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    # Phase 1 — no project budget: spending goes to personal premium customer
    logger.info(
        "Phase 1: no project budget — expecting personal premium spending for %s",
        premium_customer_id,
    )
    logger.info("Sending premium request (no project budget)")
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
    personal_premium_spend_after_phase1 = float(customer["spend"])
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(platform_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    # Phase 2 — only CLI budget created: premium spending falls back to project CLI key
    logger.info(
        "Phase 2: creating project CLI budget (no premium budget) — expecting premium spending on CLI key (alias=%s)",
        cli_alias,
    )
    budget = project_budget_groups.create(project_name, CLI_BUDGET_CATEGORIES)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending premium request (only project CLI budget active)")
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info("Waiting for project CLI key alias spending (alias=%s)", cli_alias)
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(cli_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    current_premium = lite_llm_budget_utils.get_customer_info(premium_customer_id)
    assert_that(
        float(current_premium["spend"]),
        close_to(personal_premium_spend_after_phase1, 0.0001),
    )
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

    # Phase 3 — CLI budget deleted: spending reverts to personal premium customer
    logger.info(
        "Phase 3: deleting project CLI budget — expecting premium spending to revert to personal"
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
        "Waiting for personal premium spending to exceed %.6f",
        personal_premium_spend_after_phase1,
    )
    customer = lite_llm_budget_utils.wait_for_spending_above(
        premium_customer_id, personal_premium_spend_after_phase1
    )
    assert_that(
        float(customer["spend"]), greater_than(personal_premium_spend_after_phase1)
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_creates_premium_project_budget_routes_chat_premium_spending_from_personal(
    keycloak_user,
    user_premium_assistant,
    user_assistant_utils,
    lite_llm_budget_utils,
    project_setup,
    project_budget_groups,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name = project_setup
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")

    # Phase 1 — no project budget: spending goes to personal premium customer
    logger.info(
        "Phase 1: no project premium budget — expecting personal premium spending for %s",
        premium_customer_id,
    )
    assistant = user_premium_assistant(project_name=project_name)
    logger.info("Sending chat premium request (no project budget)")
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info(
        "Waiting for personal premium spending (customer=%s)", premium_customer_id
    )
    customer = lite_llm_budget_utils.wait_for_spending(premium_customer_id)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))
    personal_premium_spend_after_phase1 = float(customer["spend"])
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(platform_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())
    assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

    # Phase 2 — project budget created: spending goes to project premium key
    logger.info(
        "Phase 2: creating project premium budget — expecting spending on project premium key (alias=%s)",
        premium_alias,
    )
    budget = project_budget_groups.create(project_name, PREMIUM_BUDGET_CATEGORIES)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending chat premium request (project premium budget active)")
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info(
        "Waiting for project premium key alias spending (alias=%s)", premium_alias
    )
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    current_premium = lite_llm_budget_utils.get_customer_info(premium_customer_id)
    assert_that(
        float(current_premium["spend"]),
        close_to(personal_premium_spend_after_phase1, 0.0001),
    )
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

    # Phase 3 — project budget deleted: spending reverts to personal premium customer
    logger.info(
        "Phase 3: deleting project premium budget — expecting premium spending to revert to personal"
    )
    project_budget_groups.delete(budget)
    sleep(BUDGET_CACHE_DELAY)
    logger.info("Sending chat premium request (project budget deleted)")
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info(
        "Waiting for personal premium spending to exceed %.6f",
        personal_premium_spend_after_phase1,
    )
    customer = lite_llm_budget_utils.wait_for_spending_above(
        premium_customer_id, personal_premium_spend_after_phase1
    )
    assert_that(
        float(customer["spend"]), greater_than(personal_premium_spend_after_phase1)
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_all_project_budgets_created_chat_premium_request_routes_to_premium_key(
    keycloak_user,
    user_premium_assistant,
    user_assistant_utils,
    lite_llm_budget_utils,
    project_with_all_three_budgets,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name, _, _, _, platform_alias, cli_alias, premium_alias = (
        project_with_all_three_budgets
    )
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"

    assistant = user_premium_assistant(project_name=project_name)
    logger.info("Sending chat premium request with all 3 project budgets active")
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
