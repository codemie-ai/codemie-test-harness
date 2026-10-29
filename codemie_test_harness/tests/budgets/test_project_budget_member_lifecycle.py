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
from hamcrest import assert_that, close_to, greater_than, none, not_none

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
def test_project_member_spending_follows_budget_and_membership_lifecycle(
    keycloak_user_1,
    keycloak_user_2,
    user1_project_utils,
    user1_assistant,
    user1_assistant_utils,
    user2_assistant_utils,
    lite_llm_budget_utils,
    lifecycle_project,
    project_budget_groups,
    admin_spend_tracking_utils,
):
    user2_email, _ = keycloak_user_2
    project_name, user2_id = lifecycle_project
    platform_alias = project_key_alias(project_name, "platform")
    cli_alias = project_key_alias(project_name, "cli")
    premium_alias = project_key_alias(project_name, "premium_models")

    logger.info("Creating assistant in project '%s'", project_name)
    assistant = user1_assistant(project_name=project_name)

    try:
        # Phase 1 — member, no project budget: spending goes to User 2 personal
        logger.info(
            "Phase 1: member, no project budget — expecting personal spending for %s",
            user2_email,
        )
        logger.info("Sending assistant request as User 2 (no project budget)")
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info("Waiting for personal spending (user=%s)", user2_email)
        customer = lite_llm_budget_utils.wait_for_spending(user2_email)
        assert_that(customer, not_none())
        assert_that(float(customer["spend"]), greater_than(0))
        personal_spend_after_phase1 = float(customer["spend"])
        assert_that(lite_llm_budget_utils.get_key_info_by_alias(platform_alias), none())
        assert_that(lite_llm_budget_utils.get_key_info_by_alias(cli_alias), none())
        assert_that(lite_llm_budget_utils.get_key_info_by_alias(premium_alias), none())

        # Phase 2 — project budget created: spending goes to project platform key
        logger.info(
            "Phase 2: creating project platform budget — expecting spending on project key (alias=%s)",
            platform_alias,
        )
        project_budget_groups.create(project_name)
        sleep(BUDGET_CACHE_DELAY)
        logger.info("Sending assistant request as User 2 (project budget active)")
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info(
            "Waiting for project platform key alias spending (alias=%s)", platform_alias
        )
        project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(
            platform_alias
        )
        assert_that(project_key_info, not_none())
        assert_that(float(project_key_info["spend"]), greater_than(0))
        project_spend_after_phase2 = float(project_key_info["spend"])
        current_personal = lite_llm_budget_utils.get_customer_info(user2_email)

        # if spend collect will be triggered after user unassignment, DB will not contain record
        # with spend_subject_type as member_budget only project_budget. By default,
        # admin_spend_tracking_utils.wait_for_project_spends returns records excluding project_budget,
        # to not duplicate total spends.

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
            close_to(project_spend_after_phase2, 0.0001),
            "project_spend_tracking total_spend should match project platform key spend.",
        )

        assert_that(
            float(current_personal["spend"]),
            close_to(personal_spend_after_phase1, 0.0001),
        )
        assert_that(
            lite_llm_budget_utils.get_customer_info(
                f"{user2_email}_{DEFAULT_CLI_BUDGET_ID}"
            ),
            none(),
        )
        assert_that(
            lite_llm_budget_utils.get_customer_info(
                f"{user2_email}_{DEFAULT_PREMIUM_BUDGET_ID}"
            ),
            none(),
        )

        # Phase 3 — User 2 unassigned, assistant published to marketplace
        logger.info(
            "Phase 3: removing User 2 from project and publishing assistant — expecting personal spending"
        )
        user1_project_utils.remove_user_from_project(project_name, user2_id)
        logger.info("User 2 removed from project, publishing assistant to marketplace")
        user1_assistant_utils.publish_assistant_to_marketplace(
            assistant.id, categories=["quality-assurance"], ignore_recommendations=True
        )
        sleep(60)
        logger.info(
            "Sending assistant request as User 2 (non-member, assistant in marketplace)"
        )
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info(
            "Waiting for personal spending to exceed %.6f", personal_spend_after_phase1
        )
        customer = lite_llm_budget_utils.wait_for_spending_above(
            user2_email, personal_spend_after_phase1
        )
        assert_that(float(customer["spend"]), greater_than(personal_spend_after_phase1))
        final_project_key = lite_llm_budget_utils.get_key_info_by_alias(platform_alias)
        assert_that(
            float(final_project_key["spend"]),
            close_to(project_spend_after_phase2, 0.0001),
        )

        # Checking that project budget remains same as in Phase 2

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
            close_to(project_spend_after_phase2, 0.0001),
            "project_spend_tracking total_spend should match project platform key spend.",
        )

    finally:
        user1_assistant_utils.unpublish_assistant_from_marketplace(assistant.id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_cli_spending_reverts_to_personal_after_project_unassignment(
    keycloak_user_2,
    user2_proxy_utils,
    user1_project_utils,
    lite_llm_budget_utils,
    lifecycle_project,
    project_budget_groups,
    default_llm,
    admin_spend_tracking_utils,
):
    user2_email, _ = keycloak_user_2
    project_name, user2_id = lifecycle_project
    cli_customer_id = f"{user2_email}_{DEFAULT_CLI_BUDGET_ID}"
    cli_alias = project_key_alias(project_name, "cli")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    logger.info(
        "Phase 1: no CLI project budget — expecting personal CLI spending for %s",
        cli_customer_id,
    )
    logger.info("Sending CLI request as User 2 (no project budget)")
    user2_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info("Waiting for personal CLI spending (customer=%s)", cli_customer_id)
    customer = lite_llm_budget_utils.wait_for_spending(cli_customer_id)
    assert_that(customer, not_none())
    assert_that(float(customer["spend"]), greater_than(0))
    personal_cli_spend_after_phase1 = float(customer["spend"])

    logger.info(
        "Phase 2: creating project CLI budget — expecting spending on project CLI key (alias=%s)",
        cli_alias,
    )
    project_budget_groups.create(project_name, CLI_BUDGET_CATEGORIES)
    sleep(BUDGET_CACHE_DELAY)

    # User 2 is member: spending goes to project CLI key
    logger.info("Sending CLI request as User 2 (project budget active)")
    user2_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info("Waiting for project CLI key alias spending (alias=%s)", cli_alias)
    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(cli_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    project_spend_before_unassign = float(project_key_info["spend"])

    # Regression: User 2 is removed here with spend still uncollected
    # (no collect_spends() call before removal). The flush-before-delete fix must
    # capture this member's terminal spend as a member_budget row inline during
    # removal, otherwise the nightly collector's later join would silently lose it
    # once the allocation is soft-deleted.
    logger.info(
        "Phase 3: removing User 2 from project with spend still uncollected — expecting CLI spending to revert to personal"
    )
    user1_project_utils.remove_user_from_project(project_name, user2_id)
    sleep(60)
    logger.info("Sending CLI request as User 2 (non-member, project header still sent)")
    user2_proxy_utils.send_messages_request(
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
    final_project_key = lite_llm_budget_utils.get_key_info_by_alias(cli_alias)
    assert_that(
        float(final_project_key["spend"]),
        close_to(project_spend_before_unassign, 0.0001),
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends()
    logger.info(
        "Waiting for cli member_budget spend in project_spend_tracking (project=%s)",
        project_name,
    )
    today = datetime.date.today()
    member_spends = admin_spend_tracking_utils.wait_for_project_spends(
        project_name, today, today, "cli", spend_subject_type="member_budget"
    )
    assert_that(
        member_spends["total_spend"],
        close_to(project_spend_before_unassign, 0.0001),
        "member_budget total_spend should still match the CLI spend "
        "captured before removal, even though it was collected only after the user "
        "was removed from the project.",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_premium_spending_reverts_to_personal_after_project_unassignment(
    keycloak_user_2,
    user2_proxy_utils,
    user1_project_utils,
    lite_llm_budget_utils,
    lifecycle_project,
    project_budget_groups,
    admin_spend_tracking_utils,
):
    user2_email, _ = keycloak_user_2
    project_name, user2_id = lifecycle_project
    premium_customer_id = f"{user2_email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    premium_alias = project_key_alias(project_name, "premium_models")
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}

    logger.info(
        "Phase 1: no premium project budget — expecting personal premium spending for %s",
        premium_customer_id,
    )
    logger.info("Sending premium request as User 2 (no project budget)")
    user2_proxy_utils.send_messages_request(
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

    logger.info(
        "Phase 2: creating project premium budget — expecting spending on project premium key (alias=%s)",
        premium_alias,
    )
    project_budget_groups.create(project_name, PREMIUM_BUDGET_CATEGORIES)
    sleep(BUDGET_CACHE_DELAY)

    # User 2 is member: spending goes to project premium key
    logger.info("Sending premium request as User 2 (project budget active)")
    user2_proxy_utils.send_messages_request(
        model=PREMIUM_MODEL,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=request_headers,
    ).raise_for_status()
    logger.info(
        "Waiting for project premium key alias spending (alias=%s)", premium_alias
    )

    logger.info("Triggering spend collection")
    admin_spend_tracking_utils.collect_spends_nowait()

    project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
    assert_that(project_key_info, not_none())
    assert_that(float(project_key_info["spend"]), greater_than(0))
    project_spend_before_unassign = float(project_key_info["spend"])

    # if spend collect will be triggered after user unassignment, DB will not contain record
    # with spend_subject_type as member_budget only project_budget. By default,
    # admin_spend_tracking_utils.wait_for_project_spends returns records excluding project_budget,
    # to not duplicate total spends.
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
        close_to(project_spend_before_unassign, 0.0001),
        "project_spend_tracking total_spend should match project premium_models key spend.",
    )

    # Unassign User 2: spending reverts to personal premium customer (project header still sent)
    logger.info(
        "Phase 3: removing User 2 from project — expecting premium spending to revert to personal"
    )
    user1_project_utils.remove_user_from_project(project_name, user2_id)
    sleep(60)
    logger.info(
        "Sending premium request as User 2 (non-member, project header still sent)"
    )
    user2_proxy_utils.send_messages_request(
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
        float(customer["spend"]),
        greater_than(personal_premium_spend_after_phase1),
    )
    final_project_key = lite_llm_budget_utils.get_key_info_by_alias(premium_alias)
    assert_that(
        float(final_project_key["spend"]),
        close_to(project_spend_before_unassign, 0.0001),
    )

    # Checking that project budget remains same as in Phase 2

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
        close_to(project_spend_before_unassign, 0.0001),
        "project_spend_tracking total_spend should match project premium_models key spend.",
    )
