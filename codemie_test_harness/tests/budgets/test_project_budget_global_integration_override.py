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
from hamcrest import assert_that, equal_to, greater_than, has_length, not_none

from codemie_sdk.models.integration import CredentialTypes, CredentialValues

from codemie_test_harness.tests.test_data.budget_test_data import (
    ALL_BUDGET_CATEGORIES,
    budget_chat_prompt,
    BUDGET_CACHE_DELAY,
    project_key_alias,
)

logger = logging.getLogger(__name__)


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
        user2_integration_utils.delete_integration(integration)


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
def test_global_integration_owned_by_regular_project_overrides_all_chat_contexts(
    keycloak_user_2,
    user2_project1_with_platform_budget,
    lifecycle_project2_with_all_three_budgets,
    user2_litellm_key,
    user2_global_integration_project1,
    user2_assistants,
    user2_assistant_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    user2_email, _ = keycloak_user_2
    project1_name = user2_project1_with_platform_budget
    project2_name, _ = lifecycle_project2_with_all_three_budgets
    today = datetime.date.today()

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

    logger.info("Running blocking collect to confirm no DB rows are produced")
    admin_spend_tracking_utils.collect_spends()

    # spend_subject_type="key" collection was removed (commit
    # 9c86cc862), so a global integration's raw LiteLLM key spend is currently
    # invisible to project_spend_tracking for every project involved — we assert
    # absence here rather than checking key spend values in our DB.
    spends_project1 = admin_spend_tracking_utils.get_project_spends(
        project1_name, today, today
    )
    assert_that(
        spends_project1["total_spend"],
        equal_to(0),
        "Expected no tracked spend for the owning project via global integration key.",
    )
    assert_that(
        spends_project1["rows"],
        has_length(0),
        "Expected zero spend rows for the owning project via global integration key.",
    )

    spends_project2 = admin_spend_tracking_utils.get_project_spends(
        project2_name, today, today
    )
    assert_that(
        spends_project2["total_spend"],
        equal_to(0),
        "Expected no tracked spend for the other regular project via global integration key.",
    )
    assert_that(
        spends_project2["rows"],
        has_length(0),
        "Expected zero spend rows for the other regular project via global integration key.",
    )

    spends_personal = admin_spend_tracking_utils.get_project_spends(
        user2_email, today, today
    )
    assert_that(
        spends_personal["total_spend"],
        equal_to(0),
        "Expected no tracked spend for the personal project via global integration key.",
    )
    assert_that(
        spends_personal["rows"],
        has_length(0),
        "Expected zero spend rows for the personal project via global integration key.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_global_integration_owned_by_personal_project_overrides_all_chat_contexts(
    keycloak_user_2,
    user2_project1_with_platform_budget,
    lifecycle_project2_with_all_three_budgets,
    user2_litellm_key,
    user2_litellm_integration,
    user2_assistants,
    user2_assistant_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    user2_email, _ = keycloak_user_2
    project1_name = user2_project1_with_platform_budget
    project2_name, _ = lifecycle_project2_with_all_three_budgets
    today = datetime.date.today()

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

    logger.info("Running blocking collect to confirm no DB rows are produced")
    admin_spend_tracking_utils.collect_spends()

    # spend_subject_type="key" collection was removed (commit
    # 9c86cc862), so a global integration's raw LiteLLM key spend is currently
    # invisible to project_spend_tracking for every project involved — we assert
    # absence here rather than checking key spend values in our DB.
    spends_project1 = admin_spend_tracking_utils.get_project_spends(
        project1_name, today, today
    )
    assert_that(
        spends_project1["total_spend"],
        equal_to(0),
        "Expected no tracked spend for a regular project via global integration key.",
    )
    assert_that(
        spends_project1["rows"],
        has_length(0),
        "Expected zero spend rows for a regular project via global integration key.",
    )

    spends_project2 = admin_spend_tracking_utils.get_project_spends(
        project2_name, today, today
    )
    assert_that(
        spends_project2["total_spend"],
        equal_to(0),
        "Expected no tracked spend for the other regular project via global integration key.",
    )
    assert_that(
        spends_project2["rows"],
        has_length(0),
        "Expected zero spend rows for the other regular project via global integration key.",
    )

    spends_personal = admin_spend_tracking_utils.get_project_spends(
        user2_email, today, today
    )
    assert_that(
        spends_personal["total_spend"],
        equal_to(0),
        "Expected no tracked spend for the owning personal project via global integration key.",
    )
    assert_that(
        spends_personal["rows"],
        has_length(0),
        "Expected zero spend rows for the owning personal project via global integration key.",
    )
