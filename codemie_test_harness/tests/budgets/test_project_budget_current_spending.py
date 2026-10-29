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
import secrets
from time import sleep

import pytest
from hamcrest import assert_that, close_to, greater_than, not_none

from codemie_test_harness.tests.utils.project_utils import ProjectUtils
from codemie_test_harness.tests.test_data.budget_test_data import (
    budget_chat_prompt,
    BUDGET_CACHE_DELAY,
    CLI_CLIENT_HEADER,
    CLI_PROJECT_HEADER,
    PREMIUM_MODEL,
    project_key_alias,
)

logger = logging.getLogger(__name__)

_SPENDING_PROPAGATION_WAIT = 600


@pytest.fixture(scope="function")
def two_user_project_with_platform_budget(
    user1_client,
    user2_client,
    admin_project_utils,
    project_budget_groups,
    lite_llm_budget_utils,
):
    uid = secrets.token_hex(4)
    project_name = f"autotest-project-{uid}"
    user1_project_utils = ProjectUtils(user1_client)
    user1_id = user1_client.users.about_me().user_id
    user2_id = user2_client.users.about_me().user_id
    alias = project_key_alias(project_name, "platform")

    user1_project_utils.create_project(
        name=project_name, description="Autotest 2-user spending project"
    )
    user1_project_utils.enable_member_budget_tracking(project_name)
    user1_project_utils.assign_user_to_project(
        project_name, user2_id, is_project_admin=False
    )
    budget = project_budget_groups.create(
        project_name, name_prefix="autotest-2usr-platform"
    )
    sleep(BUDGET_CACHE_DELAY)

    yield project_name, budget.budget_ids["platform"], alias, user1_id, user2_id

    try:
        project_budget_groups.delete(budget)
    except Exception as e:
        logger.warning(f"Failed to delete budget group {budget.group_id}: {e}")
    for category in ("platform", "cli", "premium_models"):
        try:
            lite_llm_budget_utils.delete_key_by_alias(
                project_key_alias(project_name, category)
            )
        except Exception as e:
            logger.warning(
                f"Failed to delete LiteLLM key for project {project_name} "
                f"category {category}: {e}"
            )
    admin_project_utils.delete_project_cascade(project_name)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_platform_spending_reflected_in_project_list_budgets(
    keycloak_user,
    user_assistant,
    user_assistant_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_with_platform_budget,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name, budget_id, alias = project_with_platform_budget

    logger.info("Sending platform request (user=%s, project=%s)", email, project_name)
    assistant = user_assistant(project_name=project_name)
    user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    logger.info("Waiting for platform key spending (alias=%s)", alias)
    key_info = lite_llm_budget_utils.wait_for_key_alias_spending(alias)
    assert_that(key_info, not_none(), "LiteLLM platform key spending not recorded.")
    key_spend = float(key_info["spend"])
    assert_that(key_spend, greater_than(0))

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()

    logger.info("Waiting for current_spending to propagate to projects API (platform)")
    platform_budget = admin_project_utils.wait_for_project_budget_spending(
        project_name, "platform", timeout=_SPENDING_PROPAGATION_WAIT
    )
    assert_that(
        platform_budget,
        not_none(),
        "Platform budget spending did not propagate within timeout.",
    )
    assert_that(
        float(platform_budget.current_spending),
        close_to(key_spend, 0.0001),
        "Platform budget current_spending should match LiteLLM key spend.",
    )

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
        close_to(key_spend, 0.0001),
        "project_spend_tracking total_spend should match LiteLLM platform key spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_cli_spending_reflected_in_project_list_budgets(
    keycloak_user,
    default_llm,
    user_proxy_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_with_cli_budget,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name, budget_id, alias = project_with_cli_budget
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    logger.info("Sending CLI request (user=%s, project=%s)", email, project_name)
    user_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()

    logger.info("Waiting for CLI key spending (alias=%s)", alias)
    key_info = lite_llm_budget_utils.wait_for_key_alias_spending(alias)
    assert_that(key_info, not_none(), "LiteLLM CLI key spending not recorded.")
    key_spend = float(key_info["spend"])
    assert_that(key_spend, greater_than(0))

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()

    logger.info("Waiting for current_spending to propagate to projects API (cli)")
    cli_budget = admin_project_utils.wait_for_project_budget_spending(
        project_name, "cli", timeout=_SPENDING_PROPAGATION_WAIT
    )
    assert_that(
        cli_budget,
        not_none(),
        "CLI budget spending did not propagate within timeout.",
    )
    assert_that(
        float(cli_budget.current_spending),
        close_to(key_spend, 0.0001),
        "CLI budget current_spending should match LiteLLM key spend.",
    )

    logger.info(
        "Waiting for CLI spend in project_spend_tracking (project=%s)", project_name
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "cli"
    )
    assert_that(
        spends["total_spend"],
        close_to(key_spend, 0.0001),
        "project_spend_tracking total_spend should match LiteLLM CLI key spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_premium_spending_reflected_in_project_list_budgets(
    keycloak_user,
    user_proxy_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    project_with_premium_budget,
    admin_spend_tracking_utils,
):
    email, _ = keycloak_user
    project_name, budget_id, alias = project_with_premium_budget
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    logger.info(
        "Sending premium model request (user=%s, project=%s)", email, project_name
    )
    user_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()

    logger.info("Waiting for premium key spending (alias=%s)", alias)
    key_info = lite_llm_budget_utils.wait_for_key_alias_spending(alias)
    assert_that(key_info, not_none(), "LiteLLM premium key spending not recorded.")
    key_spend = float(key_info["spend"])
    assert_that(key_spend, greater_than(0))

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()

    logger.info(
        "Waiting for current_spending to propagate to projects API (premium_models)"
    )
    premium_budget = admin_project_utils.wait_for_project_budget_spending(
        project_name, "premium_models", timeout=_SPENDING_PROPAGATION_WAIT
    )
    assert_that(
        premium_budget,
        not_none(),
        "Premium budget spending did not propagate within timeout.",
    )
    assert_that(
        float(premium_budget.current_spending),
        close_to(key_spend, 0.0001),
        "Premium budget current_spending should match LiteLLM key spend.",
    )

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
        close_to(key_spend, 0.0001),
        "project_spend_tracking total_spend should match LiteLLM premium key spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_two_user_platform_spending_sums_in_project_list_budgets(
    keycloak_user_1,
    keycloak_user_2,
    user1_assistant,
    user2_assistant,
    user1_assistant_utils,
    user2_assistant_utils,
    admin_project_utils,
    lite_llm_budget_utils,
    two_user_project_with_platform_budget,
    admin_spend_tracking_utils,
):
    project_name, budget_id, alias, user1_id, user2_id = (
        two_user_project_with_platform_budget
    )
    email1, _ = keycloak_user_1
    email2, _ = keycloak_user_2

    logger.info(
        "User1 (%s) sending platform request to project '%s'", email1, project_name
    )
    assistant1 = user1_assistant(project_name=project_name)
    user1_assistant_utils.ask_assistant(assistant1, budget_chat_prompt())

    logger.info("Waiting for user1 key spending (alias=%s)", alias)
    key_info_after_user1 = lite_llm_budget_utils.wait_for_key_alias_spending(alias)
    assert_that(
        key_info_after_user1,
        not_none(),
        "LiteLLM key spending after user1 not recorded.",
    )
    spend_after_user1 = float(key_info_after_user1["spend"])
    assert_that(spend_after_user1, greater_than(0))

    logger.info(
        "User2 (%s) sending platform request to project '%s'", email2, project_name
    )
    assistant2 = user2_assistant(project_name=project_name)
    user2_assistant_utils.ask_assistant(assistant2, budget_chat_prompt())

    logger.info("Waiting for user2 spending to be added to key (alias=%s)", alias)
    key_info_final = lite_llm_budget_utils.wait_for_key_alias_spending_above(
        alias, spend_after_user1
    )
    assert_that(
        key_info_final, not_none(), "LiteLLM key spending after user2 not recorded."
    )
    total_key_spend = float(key_info_final["spend"])
    assert_that(total_key_spend, greater_than(spend_after_user1))

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends()

    logger.info(
        "Waiting for current_spending to propagate to projects API (platform, 2 users)"
    )
    platform_budget = admin_project_utils.wait_for_project_budget_spending(
        project_name, "platform", timeout=_SPENDING_PROPAGATION_WAIT
    )
    assert_that(
        platform_budget,
        not_none(),
        "Platform budget spending did not propagate within timeout.",
    )
    assert_that(
        float(platform_budget.current_spending),
        close_to(total_key_spend, 0.0001),
        "Platform budget current_spending should match the sum of both users' spending.",
    )

    logger.info(
        "Waiting for platform spend in project_spend_tracking (project=%s, 2 users)",
        project_name,
    )
    today = datetime.date.today()
    spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "platform"
    )
    assert_that(
        spends["total_spend"],
        close_to(total_key_spend, 0.0001),
        "project_spend_tracking total_spend should match sum of both users' platform spending.",
    )
