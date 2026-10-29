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

import pytest
from hamcrest import assert_that, contains_string, equal_to, greater_than, not_none

from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.test_data.budget_test_data import (
    budget_chat_prompt,
    budget_chat_prompt_bigger,
    project_key_alias,
)

logger = logging.getLogger(__name__)

_INITIAL_MAX_BUDGET = 1.0
_INITIAL_SOFT_BUDGET = 0.5
_UPDATED_MAX_BUDGET = 0.2
_UPDATED_SOFT_BUDGET = 0.1
_MAX_CHAT_ATTEMPTS = 5
_BUDGET_EXCEEDED_MSG = "Your LLM usage budget has been exceeded"


@pytest.fixture(scope="function")
def project_with_1usd_platform_budget(
    admin_project_utils,
    user2_client,
    project_budget_groups,
    lite_llm_budget_utils,
):
    uid = secrets.token_hex(4)
    project_name = f"autotest-project-{uid}"
    admin_project_utils.create_project(
        name=project_name, description="Autotest shared key budget project"
    )
    user2_id = user2_client.users.about_me().user_id
    admin_project_utils.assign_user_to_project(
        project_name, user2_id, is_project_admin=False
    )
    platform_alias = project_key_alias(project_name, "platform")
    budget = project_budget_groups.create(
        project_name,
        {
            "platform": {
                "max_budget": _INITIAL_MAX_BUDGET,
                "soft_budget": _INITIAL_SOFT_BUDGET,
            }
        },
        name_prefix="autotest-sharedkey",
    )
    yield (
        project_name,
        user2_id,
        budget.budget_ids["platform"],
        platform_alias,
        budget.group_id,
    )
    try:
        project_budget_groups.delete(budget, user2_id)
    except Exception as e:
        logger.warning(f"Failed to delete budget group {budget.group_id}: {e}")
    for category in ("platform", "cli", "premium_models"):
        try:
            alias = project_key_alias(project_name, category)
            lite_llm_budget_utils.delete_key_by_alias(alias)
        except Exception as e:
            logger.warning(f"Failed to delete LiteLLM key for alias {alias}: {e}")
    admin_project_utils.delete_project_cascade(project_name)


@pytest.fixture(scope="function")
def project_with_1usd_platform_budget_user_added_after(
    admin_project_utils,
    user2_client,
    project_budget_groups,
    lite_llm_budget_utils,
):
    uid = secrets.token_hex(4)
    project_name = f"autotest-project-{uid}"
    admin_project_utils.create_project(
        name=project_name, description="Autotest shared key budget project"
    )
    platform_alias = project_key_alias(project_name, "platform")
    budget = project_budget_groups.create(
        project_name,
        {
            "platform": {
                "max_budget": _INITIAL_MAX_BUDGET,
                "soft_budget": _INITIAL_SOFT_BUDGET,
            }
        },
        name_prefix="autotest-sharedkey",
    )
    user2_id = user2_client.users.about_me().user_id
    admin_project_utils.assign_user_to_project(
        project_name, user2_id, is_project_admin=False
    )
    yield (
        project_name,
        user2_id,
        budget.budget_ids["platform"],
        platform_alias,
        budget.group_id,
    )
    try:
        project_budget_groups.delete(budget, user2_id)
    except Exception as e:
        logger.warning(f"Failed to delete budget group {budget.group_id}: {e}")
    for category in ("platform", "cli", "premium_models"):
        try:
            alias = project_key_alias(project_name, category)
            lite_llm_budget_utils.delete_key_by_alias(alias)
        except Exception as e:
            logger.warning(f"Failed to delete LiteLLM key for alias {alias}: {e}")
    admin_project_utils.delete_project_cascade(project_name)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_platform_budget_shared_key_max_budget_reflected_and_enforced_user_added_before_budget(
    project_with_1usd_platform_budget,
    admin_project_budget_utils,
    user2_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
):
    project_name, user2_id, budget_id, platform_alias, group_id = (
        project_with_1usd_platform_budget
    )
    shared_budget_id = f"{budget_id}:shared"

    # Phase 1: shared key and shared budget max_budget must equal the full project budget
    logger.info(
        "Phase 1: verifying key and shared budget max_budget=%.2f for project '%s'",
        _INITIAL_MAX_BUDGET,
        project_name,
    )
    key_info = lite_llm_budget_utils.get_key_info_by_alias(platform_alias)
    assert_that(key_info, not_none())
    assert_that(float(key_info["max_budget"]), equal_to(_INITIAL_MAX_BUDGET))
    budget_info = lite_llm_budget_utils.get_budget_info(shared_budget_id)
    assert_that(budget_info, not_none())
    assert_that(float(budget_info["max_budget"]), equal_to(_INITIAL_MAX_BUDGET))

    # Phase 2: create assistant and send one chat request
    logger.info("Phase 2: creating assistant and sending first chat request")
    assistant = user2_assistant(
        project_name=project_name, llm_model=ModelTypes.GPT_5_6_SOL_2026_07_09
    )
    user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    # Phase 3: spend is non-zero; key and shared budget max_budget must remain unchanged
    logger.info(
        "Phase 3: waiting for spend, verifying key and shared budget max_budget still %.2f",
        _INITIAL_MAX_BUDGET,
    )
    key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    assert_that(key_info, not_none())
    assert_that(float(key_info["spend"]), greater_than(0))
    assert_that(float(key_info["max_budget"]), equal_to(_INITIAL_MAX_BUDGET))
    budget_info = lite_llm_budget_utils.get_budget_info(shared_budget_id)
    assert_that(budget_info, not_none())
    assert_that(float(budget_info["max_budget"]), equal_to(_INITIAL_MAX_BUDGET))

    # Phase 4: lower the project budget
    logger.info(
        "Phase 4: updating project budget to max_budget=%.2f", _UPDATED_MAX_BUDGET
    )
    admin_project_budget_utils.update_budget_group_category(
        group_id,
        "platform",
        max_budget=_UPDATED_MAX_BUDGET,
        soft_budget=_UPDATED_SOFT_BUDGET,
    )

    # Phase 5: key and shared budget max_budget must propagate to the new value
    logger.info(
        "Phase 5: waiting for key and shared budget max_budget to update to %.2f",
        _UPDATED_MAX_BUDGET,
    )
    key_info = lite_llm_budget_utils.wait_for_key_alias_max_budget(
        platform_alias, _UPDATED_MAX_BUDGET
    )
    assert_that(key_info, not_none())
    assert_that(float(key_info["max_budget"]), equal_to(_UPDATED_MAX_BUDGET))
    budget_info = lite_llm_budget_utils.wait_for_budget_max_budget(
        shared_budget_id,
        _UPDATED_MAX_BUDGET,
    )
    assert_that(budget_info, not_none())
    assert_that(float(budget_info["max_budget"]), equal_to(_UPDATED_MAX_BUDGET))

    # Phase 6: exhaust the reduced budget by sending multiple larger requests
    logger.info(
        "Phase 6: sending chat requests to exceed the %.2f budget", _UPDATED_MAX_BUDGET
    )
    generated = ""
    for attempt in range(_MAX_CHAT_ATTEMPTS):
        generated = user2_assistant_utils.ask_assistant(
            assistant, budget_chat_prompt_bigger()
        )
        logger.info("Attempt %d response preview: %s", attempt + 1, generated[:120])
        if _BUDGET_EXCEEDED_MSG in generated:
            break

    # Phase 7: assert the budget-exceeded error is present in the assistant response
    logger.info("Phase 7: asserting budget-exceeded error in assistant response")
    assert_that(
        generated,
        contains_string(
            "Your LLM usage budget has been exceeded."
            " Please contact your administrator to increase the limit."
            f"\nBudget has been exceeded! Key=codemie:project:{project_name}:category:platform"
        ),
    )
    assert_that(generated, contains_string(f"Max budget: {_UPDATED_MAX_BUDGET}"))


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_platform_budget_shared_key_max_budget_reflected_and_enforced_user_added_after_budget(
    project_with_1usd_platform_budget_user_added_after,
    admin_project_budget_utils,
    user2_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
):
    project_name, user2_id, budget_id, platform_alias, group_id = (
        project_with_1usd_platform_budget_user_added_after
    )
    shared_budget_id = f"{budget_id}:shared"

    # Phase 1: shared key and shared budget max_budget must equal the full project budget
    logger.info(
        "Phase 1: verifying key and shared budget max_budget=%.2f for project '%s'",
        _INITIAL_MAX_BUDGET,
        project_name,
    )
    key_info = lite_llm_budget_utils.get_key_info_by_alias(platform_alias)
    assert_that(key_info, not_none())
    assert_that(float(key_info["max_budget"]), equal_to(_INITIAL_MAX_BUDGET))
    budget_info = lite_llm_budget_utils.get_budget_info(shared_budget_id)
    assert_that(budget_info, not_none())
    assert_that(float(budget_info["max_budget"]), equal_to(_INITIAL_MAX_BUDGET))

    # Phase 2: create assistant and send one chat request
    logger.info("Phase 2: creating assistant and sending first chat request")
    assistant = user2_assistant(
        project_name=project_name, llm_model=ModelTypes.GPT_5_6_SOL_2026_07_09
    )
    user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    # Phase 3: spend is non-zero; key and shared budget max_budget must remain unchanged
    logger.info(
        "Phase 3: waiting for spend, verifying key and shared budget max_budget still %.2f",
        _INITIAL_MAX_BUDGET,
    )
    key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    assert_that(key_info, not_none())
    assert_that(float(key_info["spend"]), greater_than(0))
    assert_that(float(key_info["max_budget"]), equal_to(_INITIAL_MAX_BUDGET))
    budget_info = lite_llm_budget_utils.get_budget_info(shared_budget_id)
    assert_that(budget_info, not_none())
    assert_that(float(budget_info["max_budget"]), equal_to(_INITIAL_MAX_BUDGET))

    # Phase 4: lower the project budget
    logger.info(
        "Phase 4: updating project budget to max_budget=%.2f", _UPDATED_MAX_BUDGET
    )
    admin_project_budget_utils.update_budget_group_category(
        group_id,
        "platform",
        max_budget=_UPDATED_MAX_BUDGET,
        soft_budget=_UPDATED_SOFT_BUDGET,
    )

    # Phase 5: key and shared budget max_budget must propagate to the new value
    logger.info(
        "Phase 5: waiting for key and shared budget max_budget to update to %.2f",
        _UPDATED_MAX_BUDGET,
    )
    key_info = lite_llm_budget_utils.wait_for_key_alias_max_budget(
        platform_alias, _UPDATED_MAX_BUDGET
    )
    assert_that(key_info, not_none())
    assert_that(float(key_info["max_budget"]), equal_to(_UPDATED_MAX_BUDGET))
    budget_info = lite_llm_budget_utils.wait_for_budget_max_budget(
        shared_budget_id,
        _UPDATED_MAX_BUDGET,
    )
    assert_that(budget_info, not_none())
    assert_that(float(budget_info["max_budget"]), equal_to(_UPDATED_MAX_BUDGET))

    # Phase 6: exhaust the reduced budget by sending multiple larger requests
    logger.info(
        "Phase 6: sending chat requests to exceed the %.2f budget", _UPDATED_MAX_BUDGET
    )
    generated = ""
    for attempt in range(_MAX_CHAT_ATTEMPTS):
        generated = user2_assistant_utils.ask_assistant(
            assistant, budget_chat_prompt_bigger()
        )
        logger.info("Attempt %d response preview: %s", attempt + 1, generated[:120])
        if _BUDGET_EXCEEDED_MSG in generated:
            break

    # Phase 7: assert the budget-exceeded error is present in the assistant response
    logger.info("Phase 7: asserting budget-exceeded error in assistant response")
    assert_that(
        generated,
        contains_string(
            "Your LLM usage budget has been exceeded."
            " Please contact your administrator to increase the limit."
            f"\nBudget has been exceeded! Key=codemie:project:{project_name}:category:platform"
        ),
    )
    assert_that(generated, contains_string(f"Max budget: {_UPDATED_MAX_BUDGET}"))
