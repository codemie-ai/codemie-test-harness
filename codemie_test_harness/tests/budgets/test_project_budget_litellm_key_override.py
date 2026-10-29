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
from hamcrest import assert_that, greater_than, none, not_none, equal_to

from codemie_sdk.models.integration import CredentialTypes, CredentialValues

from codemie_test_harness.tests.test_data.budget_test_data import (
    budget_chat_prompt,
    CLI_CLIENT_HEADER,
    CLI_PROJECT_HEADER,
    DEFAULT_CLI_BUDGET_ID,
    DEFAULT_PREMIUM_BUDGET_ID,
    PREMIUM_MODEL,
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def user2_litellm_project_integration(
    user2_litellm_key, user2_integration_utils, lifecycle_project
):
    project_name, _ = lifecycle_project
    integration = user2_integration_utils.create_user_integration(
        CredentialTypes.LITE_LLM,
        [CredentialValues(key="api_key", value=user2_litellm_key)],
        project_name=project_name,
    )
    yield integration
    if integration:
        user2_integration_utils.delete_integration(integration)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
def test_litellm_key_overrides_project_platform_budget(
    keycloak_user_2,
    user2_litellm_key,
    user2_litellm_project_integration,
    user2_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
    lifecycle_project_with_platform_budget,
):
    user2_email, _ = keycloak_user_2
    project_name, _, _, platform_alias = lifecycle_project_with_platform_budget

    assistant = user2_assistant(project_name=project_name)
    logger.info(
        "Sending assistant request in project '%s' with personal LiteLLM key integration (id=%s) — project platform key should remain empty",
        project_name,
        user2_litellm_project_integration.id,
    )
    user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info("Waiting for personal LiteLLM key spending")
    key_info = lite_llm_budget_utils.wait_for_key_spending(user2_litellm_key)
    assert_that(key_info, not_none())
    assert_that(float(key_info["spend"]), greater_than(0))
    assert_that(
        float(lite_llm_budget_utils.get_key_info_by_alias(platform_alias)["spend"]),
        equal_to(0),
    )
    assert_that(lite_llm_budget_utils.get_customer_info(user2_email), none())


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
def test_litellm_key_overrides_project_cli_budget(
    keycloak_user_2,
    user2_proxy_utils,
    user2_litellm_key,
    user2_litellm_integration,
    lite_llm_budget_utils,
    default_llm,
    lifecycle_project_with_cli_budget,
):
    user2_email, _ = keycloak_user_2
    project_name, _, _, cli_alias = lifecycle_project_with_cli_budget
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    logger.info(
        "Sending CLI request via personal LiteLLM key (integration=%s) — project CLI key should remain empty",
        user2_litellm_integration.id,
    )
    user2_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
        integration_id=user2_litellm_integration.id,
    ).raise_for_status()
    logger.info("Waiting for personal LiteLLM key spending")
    key_info = lite_llm_budget_utils.wait_for_key_spending(user2_litellm_key)
    assert_that(key_info, not_none())
    assert_that(float(key_info["spend"]), greater_than(0))
    assert_that(
        float(lite_llm_budget_utils.get_key_info_by_alias(cli_alias)["spend"]),
        equal_to(0),
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(
            f"{user2_email}_{DEFAULT_CLI_BUDGET_ID}"
        ),
        none(),
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
def test_litellm_key_overrides_project_premium_budget(
    keycloak_user_2,
    user2_proxy_utils,
    user2_litellm_key,
    user2_litellm_integration,
    lite_llm_budget_utils,
    lifecycle_project_with_premium_budget,
):
    user2_email, _ = keycloak_user_2
    project_name, _, _, premium_alias = lifecycle_project_with_premium_budget
    request_headers = {CLI_PROJECT_HEADER: project_name}

    logger.info(
        "Sending premium request via personal LiteLLM key (integration=%s) — project premium key should remain empty",
        user2_litellm_integration.id,
    )
    user2_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
        integration_id=user2_litellm_integration.id,
    ).raise_for_status()
    logger.info("Waiting for personal LiteLLM key spending")
    key_info = lite_llm_budget_utils.wait_for_key_spending(user2_litellm_key)
    assert_that(key_info, not_none())
    assert_that(float(key_info["spend"]), greater_than(0))
    assert_that(
        float(lite_llm_budget_utils.get_key_info_by_alias(premium_alias)["spend"]),
        equal_to(0),
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(
            f"{user2_email}_{DEFAULT_PREMIUM_BUDGET_ID}"
        ),
        none(),
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
def test_litellm_key_overrides_project_premium_budget_via_chat(
    keycloak_user_2,
    user2_litellm_key,
    user2_litellm_project_integration,
    user2_premium_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
    lifecycle_project_with_premium_budget,
):
    user2_email, _ = keycloak_user_2
    project_name, _, _, premium_alias = lifecycle_project_with_premium_budget

    assistant = user2_premium_assistant(project_name=project_name)
    logger.info(
        "Sending chat premium request in project '%s' with personal LiteLLM key integration (id=%s) — project premium key should remain empty",
        project_name,
        user2_litellm_project_integration.id,
    )
    user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
    logger.info("Waiting for personal LiteLLM key spending")
    key_info = lite_llm_budget_utils.wait_for_key_spending(user2_litellm_key)
    assert_that(key_info, not_none())
    assert_that(float(key_info["spend"]), greater_than(0))
    assert_that(
        float(lite_llm_budget_utils.get_key_info_by_alias(premium_alias)["spend"]),
        equal_to(0),
    )
    assert_that(
        lite_llm_budget_utils.get_customer_info(
            f"{user2_email}_{DEFAULT_PREMIUM_BUDGET_ID}"
        ),
        none(),
    )
