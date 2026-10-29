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

import pytest
from hamcrest import assert_that, close_to, not_none

from codemie_test_harness.tests.test_data.budget_test_data import budget_chat_prompt

logger = logging.getLogger(__name__)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_updating_budget_description_does_not_reset_spending(
    user_assistant,
    user_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    project_with_platform_budget,
    admin_spend_tracking_utils,
):
    project_name, budget_id, platform_alias = project_with_platform_budget
    created_assistant = user_assistant(project_name=project_name)
    logger.info("Sending request to accumulate spending (alias=%s)", platform_alias)
    user_assistant_utils.ask_assistant(created_assistant, budget_chat_prompt())
    key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    spend_before = float(key_info["spend"])
    logger.info("Spend before update: %.6f", spend_before)

    logger.info("Updating budget description (budget_id=%s)", budget_id)
    group_id = admin_project_budget_utils.get_group_id_for_project(project_name)
    admin_project_budget_utils.update_budget_group_category(
        group_id, "platform", description="Updated description"
    )

    key_info_after = lite_llm_budget_utils.get_key_info_by_alias(platform_alias)
    assert_that(key_info_after, not_none())
    assert_that(
        float(key_info_after["spend"]),
        close_to(spend_before, 0.0001),
        "Spending was reset after updating budget description.",
    )

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
        close_to(spend_before, 0.0001),
        "project_spend_tracking total_spend should match platform key spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_updating_budget_name_does_not_reset_spending(
    user_assistant,
    user_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    project_with_platform_budget,
    admin_spend_tracking_utils,
):
    project_name, budget_id, platform_alias = project_with_platform_budget
    created_assistant = user_assistant(project_name=project_name)
    logger.info("Sending request to accumulate spending (alias=%s)", platform_alias)
    user_assistant_utils.ask_assistant(created_assistant, budget_chat_prompt())
    key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    spend_before = float(key_info["spend"])
    logger.info("Spend before update: %.6f", spend_before)

    logger.info("Updating budget name (budget_id=%s)", budget_id)
    group_id = admin_project_budget_utils.get_group_id_for_project(project_name)
    admin_project_budget_utils.update_budget_group_category(
        group_id, "platform", name=f"Updated name {secrets.token_hex(4)}"
    )

    key_info_after = lite_llm_budget_utils.get_key_info_by_alias(platform_alias)
    assert_that(key_info_after, not_none())
    assert_that(
        float(key_info_after["spend"]),
        close_to(spend_before, 0.0001),
        "Spending was reset after updating budget name.",
    )

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
        close_to(spend_before, 0.0001),
        "project_spend_tracking total_spend should match platform key spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_updating_budget_soft_limit_does_not_reset_spending(
    user_assistant,
    user_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    project_with_platform_budget,
    admin_spend_tracking_utils,
):
    project_name, budget_id, platform_alias = project_with_platform_budget
    created_assistant = user_assistant(project_name=project_name)
    logger.info("Sending request to accumulate spending (alias=%s)", platform_alias)
    user_assistant_utils.ask_assistant(created_assistant, budget_chat_prompt())
    key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    spend_before = float(key_info["spend"])
    logger.info("Spend before update: %.6f", spend_before)

    logger.info("Updating budget soft limit (budget_id=%s)", budget_id)
    group_id = admin_project_budget_utils.get_group_id_for_project(project_name)
    admin_project_budget_utils.update_budget_group_category(
        group_id, "platform", soft_budget=60.0
    )

    key_info_after = lite_llm_budget_utils.get_key_info_by_alias(platform_alias)
    assert_that(key_info_after, not_none())
    assert_that(
        float(key_info_after["spend"]),
        close_to(spend_before, 0.0001),
        "Spending was reset after updating budget soft limit.",
    )

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
        close_to(spend_before, 0.0001),
        "project_spend_tracking total_spend should match platform key spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_updating_budget_hard_limit_does_not_reset_spending(
    user_assistant,
    user_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    project_with_platform_budget,
    admin_spend_tracking_utils,
):
    project_name, budget_id, platform_alias = project_with_platform_budget
    created_assistant = user_assistant(project_name=project_name)
    logger.info("Sending request to accumulate spending (alias=%s)", platform_alias)
    user_assistant_utils.ask_assistant(created_assistant, budget_chat_prompt())
    key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    spend_before = float(key_info["spend"])
    logger.info("Spend before update: %.6f", spend_before)

    logger.info("Updating budget hard limit (budget_id=%s)", budget_id)
    group_id = admin_project_budget_utils.get_group_id_for_project(project_name)
    admin_project_budget_utils.update_budget_group_category(
        group_id, "platform", max_budget=200.0
    )

    key_info_after = lite_llm_budget_utils.get_key_info_by_alias(platform_alias)
    assert_that(key_info_after, not_none())
    assert_that(
        float(key_info_after["spend"]),
        close_to(spend_before, 0.0001),
        "Spending was reset after updating budget hard limit.",
    )

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
        close_to(spend_before, 0.0001),
        "project_spend_tracking total_spend should match platform key spend.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_updating_budget_reset_period_does_not_reset_spending(
    user_assistant,
    user_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    project_with_platform_budget,
    admin_spend_tracking_utils,
):
    project_name, budget_id, platform_alias = project_with_platform_budget
    created_assistant = user_assistant(project_name=project_name)
    logger.info("Sending request to accumulate spending (alias=%s)", platform_alias)
    user_assistant_utils.ask_assistant(created_assistant, budget_chat_prompt())
    key_info = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
    spend_before = float(key_info["spend"])
    logger.info("Spend before update: %.6f", spend_before)

    logger.info("Updating budget reset period (budget_id=%s)", budget_id)
    group_id = admin_project_budget_utils.get_group_id_for_project(project_name)
    admin_project_budget_utils.update_budget_group_category(
        group_id, "platform", budget_duration="60d"
    )

    key_info_after = lite_llm_budget_utils.get_key_info_by_alias(platform_alias)
    assert_that(key_info_after, not_none())
    assert_that(
        float(key_info_after["spend"]),
        close_to(spend_before, 0.0001),
        "Spending was reset after updating budget reset period.",
    )

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
        close_to(spend_before, 0.0001),
        "project_spend_tracking total_spend should match platform key spend.",
    )
