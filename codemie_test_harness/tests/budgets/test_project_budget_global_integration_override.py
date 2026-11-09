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
import secrets
from time import sleep

import pytest
from hamcrest import assert_that, close_to, equal_to, greater_than, not_, not_none

from codemie_sdk.models.integration import CredentialTypes, CredentialValues

from codemie_test_harness.tests.test_data.budget_test_data import (
    ALL_BUDGET_CATEGORIES,
    budget_chat_prompt,
    BUDGET_CACHE_DELAY,
    DEFAULT_PLATFORM_BUDGET_ID,
    project_key_alias,
)
from codemie_test_harness.tests.utils.budget_usage_utils import wait_for_settled_spend

logger = logging.getLogger(__name__)

KNOWN_ISSUE = (
    "Spend incorrectly attributed to personal/project budget instead of global LiteLLM integration key"
)
MONEY_TOLERANCE = 0.0001


def assert_ledger_matches_litellm_once_the_global_integration_is_removed(
    *,
    global_key_spend,
    integration,
    user2_integration_utils,
    assistants,
    user2_assistant_utils,
    user2_email,
    user2_id,
    project1_name,
    project2_name,
    lite_llm_budget_utils,
    admin_project_utils,
):
    """Spend made without the global key reaches the ledger exactly as LiteLLM recorded it.

    The global key paid for everything chatted before, so the platform must not know about it.
    After the integration is removed the same chats are paid by the project keys and the
    personal customer. The ledger of each must then equal that LiteLLM spend, and neither may
    equal the spend of the global key, which would mean the earlier chats were counted too.
    """
    logger.info("Removing the global integration and chatting again in every context")
    user2_integration_utils.delete_integration_if_exists(integration)
    for assistant in assistants:
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    litellm_spends = {
        "project1": wait_for_settled_spend(
            lambda: lite_llm_budget_utils.get_key_spend_by_alias(
                project_key_alias(project1_name, "platform")
            )
        ),
        "project2": wait_for_settled_spend(
            lambda: lite_llm_budget_utils.get_key_spend_by_alias(
                project_key_alias(project2_name, "platform")
            )
        ),
        "personal": wait_for_settled_spend(
            lambda: float(
                (lite_llm_budget_utils.get_customer_info(user2_email) or {}).get(
                    "spend", 0
                )
            )
        ),
    }
    for context, spend in litellm_spends.items():
        assert_that(spend, greater_than(0), f"LiteLLM shows no {context} spend")

    ledger_project1 = admin_project_utils.wait_for_project_budget_spending_above(
        project1_name, "platform", litellm_spends["project1"] - MONEY_TOLERANCE
    )
    ledger_project2 = admin_project_utils.wait_for_project_budget_spending_above(
        project2_name, "platform", litellm_spends["project2"] - MONEY_TOLERANCE
    )
    ledger_personal = admin_project_utils.wait_for_member_budget_spending_above(
        DEFAULT_PLATFORM_BUDGET_ID,
        "platform",
        litellm_spends["personal"] - MONEY_TOLERANCE,
        user_id=user2_id,
    )
    ledger_spends = {
        "project1": None
        if ledger_project1 is None
        else ledger_project1.current_spending,
        "project2": None
        if ledger_project2 is None
        else ledger_project2.current_spending,
        "personal": None
        if ledger_personal is None
        else ledger_personal.current_spending,
    }
    for context, litellm_spend in litellm_spends.items():
        assert_that(ledger_spends[context], not_none(), f"No {context} ledger figure")
        assert_that(
            ledger_spends[context],
            close_to(litellm_spend, MONEY_TOLERANCE),
            f"The {context} ledger spend must equal the LiteLLM spend made without the "
            "global key; it differs, so spend of the global key was tracked on the platform",
        )
        assert_that(
            litellm_spend,
            not_(close_to(global_key_spend, MONEY_TOLERANCE)),
            f"The {context} LiteLLM spend must differ from the global key's spend",
        )
        assert_that(
            ledger_spends[context],
            not_(close_to(global_key_spend, MONEY_TOLERANCE)),
            f"The {context} ledger spend must differ from the global key's spend",
        )


@pytest.fixture(scope="function")
def user2_project1(admin_project_utils, user1_project_utils, user2_client):
    uid = secrets.token_hex(4)
    project_name = f"autotest-project-{uid}"
    user1_project_utils.create_project(
        name=project_name, description="Autotest global-integration owner project"
    )
    admin_project_utils.enable_member_budget_tracking(project_name)
    user2_id = user2_client.users.about_me().user_id
    user1_project_utils.assign_user_to_project(
        project_name, user2_id, is_project_admin=False
    )
    sleep(30)
    yield project_name
    admin_project_utils.delete_project_cascade(project_name)


@pytest.fixture(scope="function")
def user2_project1_with_platform_budget(user2_project1, project_budget_groups):
    project_budget_groups.create(user2_project1)
    sleep(BUDGET_CACHE_DELAY)
    return user2_project1


@pytest.fixture(scope="function")
def lifecycle_project2_with_all_three_budgets(lifecycle_project, project_budget_groups):
    project_name, user2_id = lifecycle_project
    project_budget_groups.create(
        project_name, ALL_BUDGET_CATEGORIES, name_prefix="autotest-proj-all3"
    )
    sleep(BUDGET_CACHE_DELAY)
    return project_name, user2_id


@pytest.fixture(scope="function")
def user2_global_integration_project1(
    user2_litellm_key, user2_integration_utils, user2_project1_with_platform_budget
):
    integration = user2_integration_utils.create_user_integration(
        CredentialTypes.LITE_LLM,
        [CredentialValues(key="api_key", value=user2_litellm_key)],
        project_name=user2_project1_with_platform_budget,
        is_global=True,
    )
    yield integration
    if integration:
        user2_integration_utils.delete_integration_if_exists(integration)


@pytest.fixture(scope="function")
def user2_assistants(default_llm, user2_assistant_utils):
    created = []

    def _create(project_name: str):
        assistant = user2_assistant_utils.create_assistant(
            llm_model_type=default_llm.base_name,
            project_name=project_name,
        )
        created.append(assistant)
        return assistant

    yield _create

    for assistant in created:
        user2_assistant_utils.delete_assistant(assistant)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
@pytest.mark.xfail(reason=KNOWN_ISSUE)
def test_global_integration_owned_by_regular_project_overrides_all_chat_contexts(
    keycloak_user_2,
    user2_project1_with_platform_budget,
    lifecycle_project2_with_all_three_budgets,
    user2_litellm_key,
    user2_global_integration_project1,
    user2_assistants,
    user2_assistant_utils,
    lite_llm_budget_utils,
    admin_project_utils,
    user2_integration_utils,
):
    user2_email, _ = keycloak_user_2
    project1_name = user2_project1_with_platform_budget
    project2_name, user2_id = lifecycle_project2_with_all_three_budgets

    logger.info(
        "Global integration (id=%s) owned by regular project '%s' (platform budget) — "
        "chatting under the owning project, a different regular project '%s' "
        "(platform+cli+premium budgets), and the personal project",
        user2_global_integration_project1.id,
        project1_name,
        project2_name,
    )
    assistant_project1 = user2_assistants(project_name=project1_name)
    user2_assistant_utils.ask_assistant(assistant_project1, budget_chat_prompt())

    assistant_project2 = user2_assistants(project_name=project2_name)
    user2_assistant_utils.ask_assistant(assistant_project2, budget_chat_prompt())

    assistant_personal = user2_assistants(project_name=user2_email)
    user2_assistant_utils.ask_assistant(assistant_personal, budget_chat_prompt())

    logger.info("Waiting for personal LiteLLM key spending")
    key_info = lite_llm_budget_utils.wait_for_key_spending(user2_litellm_key)
    assert_that(key_info, not_none())
    assert_that(float(key_info["spend"]), greater_than(0))

    logger.info(
        "Verifying project-owned budget keys stayed unused (global key overrides them)"
    )
    platform_alias_project1 = project_key_alias(project1_name, "platform")
    assert_that(
        float(
            lite_llm_budget_utils.get_key_info_by_alias(platform_alias_project1)[
                "spend"
            ]
        ),
        equal_to(0),
        "Project1's platform budget key must remain unused when a global key overrides it.",
    )
    platform_alias_project2 = project_key_alias(project2_name, "platform")
    cli_alias_project2 = project_key_alias(project2_name, "cli")
    premium_alias_project2 = project_key_alias(project2_name, "premium_models")
    assert_that(
        float(
            lite_llm_budget_utils.get_key_info_by_alias(platform_alias_project2)[
                "spend"
            ]
        ),
        equal_to(0),
        "Project2's platform budget key must remain unused when a global key overrides it.",
    )
    assert_that(
        float(lite_llm_budget_utils.get_key_info_by_alias(cli_alias_project2)["spend"]),
        equal_to(0),
        "Project2's cli budget key must remain unused when a global key overrides it.",
    )
    assert_that(
        float(
            lite_llm_budget_utils.get_key_info_by_alias(premium_alias_project2)["spend"]
        ),
        equal_to(0),
        "Project2's premium_models budget key must remain unused when a global key overrides it.",
    )

    global_key_spend = wait_for_settled_spend(
        lambda: float(lite_llm_budget_utils.get_key_info(user2_litellm_key)["spend"])
    )
    assert_ledger_matches_litellm_once_the_global_integration_is_removed(
        global_key_spend=global_key_spend,
        integration=user2_global_integration_project1,
        user2_integration_utils=user2_integration_utils,
        assistants=[assistant_project1, assistant_project2, assistant_personal],
        user2_assistant_utils=user2_assistant_utils,
        user2_email=user2_email,
        user2_id=user2_id,
        project1_name=project1_name,
        project2_name=project2_name,
        lite_llm_budget_utils=lite_llm_budget_utils,
        admin_project_utils=admin_project_utils,
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
@pytest.mark.xfail(reason=KNOWN_ISSUE)
def test_global_integration_owned_by_personal_project_overrides_all_chat_contexts(
    keycloak_user_2,
    user2_project1_with_platform_budget,
    lifecycle_project2_with_all_three_budgets,
    user2_litellm_key,
    user2_litellm_integration,
    user2_assistants,
    user2_assistant_utils,
    lite_llm_budget_utils,
    admin_project_utils,
    user2_integration_utils,
):
    user2_email, _ = keycloak_user_2
    project1_name = user2_project1_with_platform_budget
    project2_name, user2_id = lifecycle_project2_with_all_three_budgets

    logger.info(
        "Global integration (id=%s) owned by personal project '%s' — chatting under "
        "the personal project, regular project '%s' (platform budget), and regular "
        "project '%s' (platform+cli+premium budgets)",
        user2_litellm_integration.id,
        user2_email,
        project1_name,
        project2_name,
    )
    assistant_project1 = user2_assistants(project_name=project1_name)
    user2_assistant_utils.ask_assistant(assistant_project1, budget_chat_prompt())

    assistant_project2 = user2_assistants(project_name=project2_name)
    user2_assistant_utils.ask_assistant(assistant_project2, budget_chat_prompt())

    assistant_personal = user2_assistants(project_name=user2_email)
    user2_assistant_utils.ask_assistant(assistant_personal, budget_chat_prompt())

    logger.info("Waiting for personal LiteLLM key spending")
    key_info = lite_llm_budget_utils.wait_for_key_spending(user2_litellm_key)
    assert_that(key_info, not_none())
    assert_that(float(key_info["spend"]), greater_than(0))

    logger.info(
        "Verifying project-owned budget keys stayed unused (global key overrides them)"
    )
    platform_alias_project1 = project_key_alias(project1_name, "platform")
    assert_that(
        float(
            lite_llm_budget_utils.get_key_info_by_alias(platform_alias_project1)[
                "spend"
            ]
        ),
        equal_to(0),
        "Project1's platform budget key must remain unused when a global key overrides it.",
    )
    platform_alias_project2 = project_key_alias(project2_name, "platform")
    cli_alias_project2 = project_key_alias(project2_name, "cli")
    premium_alias_project2 = project_key_alias(project2_name, "premium_models")
    assert_that(
        float(
            lite_llm_budget_utils.get_key_info_by_alias(platform_alias_project2)[
                "spend"
            ]
        ),
        equal_to(0),
        "Project2's platform budget key must remain unused when a global key overrides it.",
    )
    assert_that(
        float(lite_llm_budget_utils.get_key_info_by_alias(cli_alias_project2)["spend"]),
        equal_to(0),
        "Project2's cli budget key must remain unused when a global key overrides it.",
    )
    assert_that(
        float(
            lite_llm_budget_utils.get_key_info_by_alias(premium_alias_project2)["spend"]
        ),
        equal_to(0),
        "Project2's premium_models budget key must remain unused when a global key overrides it.",
    )

    global_key_spend = wait_for_settled_spend(
        lambda: float(lite_llm_budget_utils.get_key_info(user2_litellm_key)["spend"])
    )
    assert_ledger_matches_litellm_once_the_global_integration_is_removed(
        global_key_spend=global_key_spend,
        integration=user2_litellm_integration,
        user2_integration_utils=user2_integration_utils,
        assistants=[assistant_project1, assistant_project2, assistant_personal],
        user2_assistant_utils=user2_assistant_utils,
        user2_email=user2_email,
        user2_id=user2_id,
        project1_name=project1_name,
        project2_name=project2_name,
        lite_llm_budget_utils=lite_llm_budget_utils,
        admin_project_utils=admin_project_utils,
    )
