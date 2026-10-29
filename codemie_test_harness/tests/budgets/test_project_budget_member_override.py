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
from hamcrest import (
    assert_that,
    close_to,
    contains_string,
    equal_to,
    greater_than,
    none,
    not_none,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.budget_member_override_test_data import (
    DENIED_MUTATION_IDS,
    DENIED_MUTATIONS,
    MEMBER_OVERRIDE_MAX,
    MEMBER_OVERRIDE_SOFT,
    NO_PERMISSION_MESSAGE,
)
from codemie_test_harness.tests.test_data.budget_test_data import (
    ALL_BUDGET_CATEGORIES,
    budget_chat_prompt,
    CLI_BUDGET_CATEGORIES,
    CLI_CLIENT_HEADER,
    CLI_PROJECT_HEADER,
    MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE,
    PREMIUM_BUDGET_CATEGORIES,
    PREMIUM_MODEL,
    project_key_alias,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)

logger = logging.getLogger(__name__)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_overrides_platform_member_budget_routes_spending(
    user2_assistant,
    user2_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    lifecycle_project_with_platform_budget,
    admin_spend_tracking_utils,
):
    project_name, user2_id, budget_id, platform_alias = (
        lifecycle_project_with_platform_budget
    )
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    assistant = user2_assistant(project_name=project_name)
    try:
        # Phase 1 — no override: spending goes to both shared key and user customer
        logger.info("Phase 1: sending assistant request (no override)")
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info("Waiting for shared key spending (alias=%s)", platform_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info(
            "Waiting for user customer spending (customer=%s)", override_customer_id
        )
        user_customer = lite_llm_budget_utils.wait_for_spending(override_customer_id)
        assert_that(user_customer, not_none())
        assert_that(float(user_customer["spend"]), greater_than(0))
        assert_that(
            float(user_customer["spend"]),
            close_to(key_spend_phase1, 0.0001),
        )
        customer_spend_phase1 = float(user_customer["spend"])
        assert_that(
            user_customer.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(f"{budget_id}:shared"),
        )

        # Override assigned: verify customer has correct budget, limits, and preserved spend
        logger.info("Overriding user2 (%s) platform allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        override_budget_id = f"{budget_id}:user:{user2_id}"
        logger.info(
            "Waiting for override customer budget_id update (customer=%s)",
            override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_customer_budget_id(
            override_customer_id, override_budget_id
        )
        assert_that(override_customer, not_none())
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(override_budget_id),
        )
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("max_budget"),
            equal_to(40.0),
        )
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("soft_budget"),
            equal_to(20.0),
        )
        assert_that(
            float(override_customer["spend"]),
            close_to(customer_spend_phase1, 0.0001),
        )

        # Phase 2 — override active: both key and customer spending increase
        logger.info("Sending assistant request (override active)")
        sleep(60)
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info(
            "Waiting for override customer spending above phase1 (customer=%s)",
            override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_spending_above(
            override_customer_id, customer_spend_phase1
        )
        assert_that(override_customer, not_none())
        assert_that(
            float(override_customer["spend"]), greater_than(customer_spend_phase1)
        )
        logger.info(
            "Waiting for shared key spending above phase1 (alias=%s)", platform_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            platform_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
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
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project platform key spend.",
        )
    finally:
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        lite_llm_budget_utils.delete_project_budget_objects(budget_id, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_overrides_cli_member_budget_routes_spending(
    user2_proxy_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    default_llm,
    lifecycle_project_with_cli_budget,
    admin_spend_tracking_utils,
):
    project_name, user2_id, budget_id, cli_alias = lifecycle_project_with_cli_budget
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="cli", user_id=user2_id
    )
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}
    try:
        # Phase 1 — no override: spending goes to both shared key and user customer
        logger.info("Phase 1: sending CLI request (no override)")
        user2_proxy_utils.send_messages_request(
            model=default_llm.base_name,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info("Waiting for shared key spending (alias=%s)", cli_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(cli_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info(
            "Waiting for user customer spending (customer=%s)", override_customer_id
        )
        user_customer = lite_llm_budget_utils.wait_for_spending(override_customer_id)
        assert_that(user_customer, not_none())
        assert_that(float(user_customer["spend"]), greater_than(0))
        assert_that(
            float(user_customer["spend"]),
            close_to(key_spend_phase1, 0.0001),
        )
        customer_spend_phase1 = float(user_customer["spend"])
        assert_that(
            user_customer.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(f"{budget_id}:shared"),
        )

        # Override assigned: verify customer has correct budget, limits, and preserved spend
        logger.info("Overriding user2 (%s) CLI allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        override_budget_id = f"{budget_id}:user:{user2_id}"
        logger.info(
            "Waiting for override customer budget_id update (customer=%s)",
            override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_customer_budget_id(
            override_customer_id, override_budget_id
        )
        assert_that(override_customer, not_none())
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(override_budget_id),
        )
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("max_budget"),
            equal_to(40.0),
        )
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("soft_budget"),
            equal_to(20.0),
        )
        assert_that(
            float(override_customer["spend"]),
            close_to(customer_spend_phase1, 0.0001),
        )

        # Phase 2 — override active: both key and customer spending increase
        logger.info("Sending CLI request (override active)")
        sleep(60)
        user2_proxy_utils.send_messages_request(
            model=default_llm.base_name,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info(
            "Waiting for override customer spending above phase1 (customer=%s)",
            override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_spending_above(
            override_customer_id, customer_spend_phase1
        )
        assert_that(override_customer, not_none())
        assert_that(
            float(override_customer["spend"]), greater_than(customer_spend_phase1)
        )
        logger.info(
            "Waiting for shared key spending above phase1 (alias=%s)", cli_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            cli_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
        logger.info(
            "Waiting for cli spend in project_spend_tracking (project=%s)",
            project_name,
        )
        today = datetime.date.today()
        spends = admin_spend_tracking_utils.wait_for_project_spends(
            project_name, today, today, "cli"
        )
        assert_that(
            spends["total_spend"],
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project cli key spend.",
        )
    finally:
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        lite_llm_budget_utils.delete_project_budget_objects(budget_id, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_overrides_premium_member_budget_routes_spending(
    user2_proxy_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    lifecycle_project_with_premium_budget,
    admin_spend_tracking_utils,
):
    project_name, user2_id, budget_id, premium_alias = (
        lifecycle_project_with_premium_budget
    )
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}
    try:
        # Phase 1 — no override: spending goes to both shared key and user customer
        logger.info("Phase 1: sending premium request (no override)")
        user2_proxy_utils.send_messages_request(
            model=PREMIUM_MODEL,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info("Waiting for shared key spending (alias=%s)", premium_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info(
            "Waiting for user customer spending (customer=%s)", override_customer_id
        )
        user_customer = lite_llm_budget_utils.wait_for_spending(override_customer_id)
        assert_that(user_customer, not_none())
        assert_that(float(user_customer["spend"]), greater_than(0))
        assert_that(
            float(user_customer["spend"]),
            close_to(key_spend_phase1, 0.0001),
        )
        customer_spend_phase1 = float(user_customer["spend"])
        assert_that(
            user_customer.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(f"{budget_id}:shared"),
        )

        # Override assigned: verify customer has correct budget, limits, and preserved spend
        logger.info("Overriding user2 (%s) premium allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        override_budget_id = f"{budget_id}:user:{user2_id}"
        logger.info(
            "Waiting for override customer budget_id update (customer=%s)",
            override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_customer_budget_id(
            override_customer_id, override_budget_id
        )
        assert_that(override_customer, not_none())
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(override_budget_id),
        )
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("max_budget"),
            equal_to(40.0),
        )
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("soft_budget"),
            equal_to(20.0),
        )
        assert_that(
            float(override_customer["spend"]),
            close_to(customer_spend_phase1, 0.0001),
        )

        # Phase 2 — override active: both key and customer spending increase
        logger.info("Sending premium request (override active)")
        sleep(60)
        user2_proxy_utils.send_messages_request(
            model=PREMIUM_MODEL,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info(
            "Waiting for override customer spending above phase1 (customer=%s)",
            override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_spending_above(
            override_customer_id, customer_spend_phase1
        )
        assert_that(override_customer, not_none())
        assert_that(
            float(override_customer["spend"]), greater_than(customer_spend_phase1)
        )
        logger.info(
            "Waiting for shared key spending above phase1 (alias=%s)", premium_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            premium_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
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
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project premium_models key spend.",
        )
    finally:
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        lite_llm_budget_utils.delete_project_budget_objects(budget_id, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_clears_platform_member_override_reverts_spending_to_shared(
    lifecycle_project,
    project_budget_groups,
    user1_id,
    user2_assistant,
    user2_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, user2_id = lifecycle_project
    platform_alias = project_key_alias(project_name, "platform")
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    budget = project_budget_groups.create(
        project_name, name_prefix="autotest-clear-platform"
    )
    budget_id = budget.budget_ids["platform"]

    try:
        assistant = user2_assistant(project_name=project_name)

        # Phase 1 — override active: verify routing + rebalance
        logger.info("Phase 1: overriding user2 (%s) platform allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        logger.info("Waiting for override customer (customer=%s)", override_customer_id)
        lite_llm_budget_utils.wait_for_customer(override_customer_id)
        sleep(60)
        logger.info("Sending assistant request (override active)")
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info(
            "Waiting for override customer spending (customer=%s)", override_customer_id
        )
        override_customer = lite_llm_budget_utils.wait_for_spending(
            override_customer_id
        )
        assert_that(override_customer, not_none())
        assert_that(float(override_customer["spend"]), greater_than(0))
        override_spend_phase1 = float(override_customer["spend"])
        logger.info("Waiting for shared key spending (alias=%s)", platform_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info("Verifying budget allocations after override")
        budget_response = admin_project_budget_utils.get_budget(budget_id)
        allocations = {m["user_id"]: m for m in budget_response["member_allocations"]}
        assert_that(allocations[user2_id]["allocation_mode"], equal_to("fixed"))
        assert_that(allocations[user2_id]["allocated_max_budget"], equal_to(40.0))
        assert_that(allocations[user1_id]["allocated_max_budget"], equal_to(60.0))

        # Phase 2 — override cleared: spending reverts to shared key, allocations restored
        logger.info("Phase 2: clearing override for user2 (%s)", user2_id)
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        sleep(60)
        logger.info("Sending assistant request (override cleared)")
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info(
            "Waiting for override customer spending above phase1 (customer=%s)",
            override_customer_id,
        )
        current_override = lite_llm_budget_utils.wait_for_spending_above(
            override_customer_id, override_spend_phase1
        )
        assert_that(current_override, not_none())
        assert_that(
            float(current_override["spend"]), greater_than(override_spend_phase1)
        )
        logger.info(
            "Waiting for shared key spending above phase1 (alias=%s)", platform_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            platform_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))
        shared_budget_id = f"{budget_id}:shared"
        logger.info(
            "Waiting for override customer budget_id revert to shared (customer=%s)",
            override_customer_id,
        )
        current_override = lite_llm_budget_utils.wait_for_customer_budget_id(
            override_customer_id, shared_budget_id
        )
        assert_that(current_override, not_none())
        assert_that(
            current_override.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(shared_budget_id),
        )
        logger.info("Verifying budget allocations after clear")
        budget_response = admin_project_budget_utils.get_budget(budget_id)
        allocations = {m["user_id"]: m for m in budget_response["member_allocations"]}
        assert_that(allocations[user2_id]["allocation_mode"], equal_to("equal"))
        assert_that(allocations[user2_id]["allocated_max_budget"], equal_to(50.0))
        assert_that(allocations[user1_id]["allocated_max_budget"], equal_to(50.0))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
        logger.info(
            "Waiting for platform spend in project_spend_tracking (project=%s)",
            project_name,
        )

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()

        today = datetime.date.today()
        spends = admin_spend_tracking_utils.wait_for_project_spends(
            project_name, today, today, "platform"
        )
        assert_that(
            spends["total_spend"],
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project platform key spend.",
        )
    finally:
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_clears_cli_member_override_reverts_spending_to_shared(
    lifecycle_project,
    project_budget_groups,
    user1_id,
    user2_proxy_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    default_llm,
    admin_spend_tracking_utils,
):
    project_name, user2_id = lifecycle_project
    cli_alias = project_key_alias(project_name, "cli")
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="cli", user_id=user2_id
    )
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}
    budget = project_budget_groups.create(
        project_name, CLI_BUDGET_CATEGORIES, name_prefix="autotest-clear-cli"
    )
    budget_id = budget.budget_ids["cli"]

    try:
        # Phase 1 — override active: verify routing + rebalance
        logger.info("Phase 1: overriding user2 (%s) CLI allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        logger.info("Waiting for override customer (customer=%s)", override_customer_id)
        lite_llm_budget_utils.wait_for_customer(override_customer_id)
        sleep(60)
        logger.info("Sending CLI request (override active)")
        user2_proxy_utils.send_messages_request(
            model=default_llm.base_name,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info(
            "Waiting for override customer spending (customer=%s)", override_customer_id
        )
        override_customer = lite_llm_budget_utils.wait_for_spending(
            override_customer_id
        )
        assert_that(override_customer, not_none())
        assert_that(float(override_customer["spend"]), greater_than(0))
        override_spend_phase1 = float(override_customer["spend"])
        logger.info("Waiting for shared key spending (alias=%s)", cli_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(cli_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info("Verifying budget allocations after override")
        budget_response = admin_project_budget_utils.get_budget(budget_id)
        allocations = {m["user_id"]: m for m in budget_response["member_allocations"]}
        assert_that(allocations[user2_id]["allocation_mode"], equal_to("fixed"))
        assert_that(allocations[user2_id]["allocated_max_budget"], equal_to(40.0))
        assert_that(allocations[user1_id]["allocated_max_budget"], equal_to(60.0))

        # Phase 2 — override cleared: spending reverts to shared key, allocations restored
        logger.info("Phase 2: clearing override for user2 (%s)", user2_id)
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        sleep(60)
        logger.info("Sending CLI request (override cleared)")
        user2_proxy_utils.send_messages_request(
            model=default_llm.base_name,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info(
            "Waiting for override customer spending above phase1 (customer=%s)",
            override_customer_id,
        )
        current_override = lite_llm_budget_utils.wait_for_spending_above(
            override_customer_id, override_spend_phase1
        )
        assert_that(current_override, not_none())
        assert_that(
            float(current_override["spend"]), greater_than(override_spend_phase1)
        )
        logger.info(
            "Waiting for shared key spending above phase1 (alias=%s)", cli_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            cli_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))
        shared_budget_id = f"{budget_id}:shared"
        logger.info(
            "Waiting for override customer budget_id revert to shared (customer=%s)",
            override_customer_id,
        )
        current_override = lite_llm_budget_utils.wait_for_customer_budget_id(
            override_customer_id, shared_budget_id
        )
        assert_that(current_override, not_none())
        assert_that(
            current_override.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(shared_budget_id),
        )
        logger.info("Verifying budget allocations after clear")
        budget_response = admin_project_budget_utils.get_budget(budget_id)
        allocations = {m["user_id"]: m for m in budget_response["member_allocations"]}
        assert_that(allocations[user2_id]["allocation_mode"], equal_to("equal"))
        assert_that(allocations[user2_id]["allocated_max_budget"], equal_to(50.0))
        assert_that(allocations[user1_id]["allocated_max_budget"], equal_to(50.0))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
        logger.info(
            "Waiting for cli spend in project_spend_tracking (project=%s)",
            project_name,
        )
        today = datetime.date.today()
        spends = admin_spend_tracking_utils.wait_for_project_spends(
            project_name, today, today, "cli"
        )
        assert_that(
            spends["total_spend"],
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project cli key spend.",
        )
    finally:
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_clears_premium_member_override_reverts_spending_to_shared(
    lifecycle_project,
    project_budget_groups,
    user1_id,
    user2_proxy_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, user2_id = lifecycle_project
    premium_alias = project_key_alias(project_name, "premium_models")
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}
    budget = project_budget_groups.create(
        project_name, PREMIUM_BUDGET_CATEGORIES, name_prefix="autotest-clear-premium"
    )
    budget_id = budget.budget_ids["premium_models"]

    try:
        # Phase 1 — override active: verify routing + rebalance
        logger.info("Phase 1: overriding user2 (%s) premium allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        logger.info("Waiting for override customer (customer=%s)", override_customer_id)
        lite_llm_budget_utils.wait_for_customer(override_customer_id)
        sleep(60)
        logger.info("Sending premium request (override active)")
        user2_proxy_utils.send_messages_request(
            model=PREMIUM_MODEL,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info(
            "Waiting for override customer spending (customer=%s)", override_customer_id
        )
        override_customer = lite_llm_budget_utils.wait_for_spending(
            override_customer_id
        )
        assert_that(override_customer, not_none())
        assert_that(float(override_customer["spend"]), greater_than(0))
        override_spend_phase1 = float(override_customer["spend"])
        logger.info("Waiting for shared key spending (alias=%s)", premium_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info("Verifying budget allocations after override")
        budget_response = admin_project_budget_utils.get_budget(budget_id)
        allocations = {m["user_id"]: m for m in budget_response["member_allocations"]}
        assert_that(allocations[user2_id]["allocation_mode"], equal_to("fixed"))
        assert_that(allocations[user2_id]["allocated_max_budget"], equal_to(40.0))
        assert_that(allocations[user1_id]["allocated_max_budget"], equal_to(60.0))

        # Phase 2 — override cleared: spending reverts to shared key, allocations restored
        logger.info("Phase 2: clearing override for user2 (%s)", user2_id)
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        sleep(60)
        logger.info("Sending premium request (override cleared)")
        user2_proxy_utils.send_messages_request(
            model=PREMIUM_MODEL,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info(
            "Waiting for override customer spending above phase1 (customer=%s)",
            override_customer_id,
        )
        current_override = lite_llm_budget_utils.wait_for_spending_above(
            override_customer_id, override_spend_phase1
        )
        assert_that(current_override, not_none())
        assert_that(
            float(current_override["spend"]), greater_than(override_spend_phase1)
        )
        logger.info(
            "Waiting for shared key spending above phase1 (alias=%s)", premium_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            premium_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))
        shared_budget_id = f"{budget_id}:shared"
        logger.info(
            "Waiting for override customer budget_id revert to shared (customer=%s)",
            override_customer_id,
        )
        current_override = lite_llm_budget_utils.wait_for_customer_budget_id(
            override_customer_id, shared_budget_id
        )
        assert_that(current_override, not_none())
        assert_that(
            current_override.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(shared_budget_id),
        )
        logger.info("Verifying budget allocations after clear")
        budget_response = admin_project_budget_utils.get_budget(budget_id)
        allocations = {m["user_id"]: m for m in budget_response["member_allocations"]}
        assert_that(allocations[user2_id]["allocation_mode"], equal_to("equal"))
        assert_that(allocations[user2_id]["allocated_max_budget"], equal_to(50.0))
        assert_that(allocations[user1_id]["allocated_max_budget"], equal_to(50.0))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
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
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project premium_models key spend.",
        )
    finally:
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_cli_spending_falls_back_to_platform_member_override_when_no_cli_override(
    lifecycle_project,
    project_budget_groups,
    user2_proxy_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    default_llm,
    admin_spend_tracking_utils,
):
    project_name, user2_id = lifecycle_project
    platform_alias = project_key_alias(project_name, "platform")
    platform_override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    cli_override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="cli", user_id=user2_id
    )
    cli_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}
    budget = project_budget_groups.create(
        project_name, name_prefix="autotest-fallback-cli"
    )
    budget_id = budget.budget_ids["platform"]

    try:
        logger.info(
            "Overriding user2 (%s) platform allocation (no CLI override)", user2_id
        )
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        logger.info(
            "Waiting for platform override customer (customer=%s)",
            platform_override_customer_id,
        )
        lite_llm_budget_utils.wait_for_customer(platform_override_customer_id)

        # Phase 1 — first request: establish baseline spending
        sleep(60)
        logger.info("Phase 1: sending CLI request (platform-only override active)")
        user2_proxy_utils.send_messages_request(
            model=default_llm.base_name,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=cli_headers,
        ).raise_for_status()
        logger.info("Waiting for platform key spending (alias=%s)", platform_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info(
            "Waiting for platform override spending (customer=%s)",
            platform_override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_spending(
            platform_override_customer_id
        )
        assert_that(override_customer, not_none())
        assert_that(float(override_customer["spend"]), greater_than(0))
        assert_that(
            float(override_customer["spend"]),
            close_to(key_spend_phase1, 0.0001),
        )
        customer_spend_phase1 = float(override_customer["spend"])
        assert_that(
            lite_llm_budget_utils.get_customer_info(cli_override_customer_id), none()
        )

        # Phase 2 — second request: verify spending increases
        logger.info("Phase 2: sending CLI request (platform-only override active)")
        sleep(60)
        user2_proxy_utils.send_messages_request(
            model=default_llm.base_name,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=cli_headers,
        ).raise_for_status()
        logger.info(
            "Waiting for platform override spending above phase1 (customer=%s)",
            platform_override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_spending_above(
            platform_override_customer_id, customer_spend_phase1
        )
        assert_that(override_customer, not_none())
        assert_that(
            float(override_customer["spend"]), greater_than(customer_spend_phase1)
        )
        logger.info(
            "Waiting for platform key spending above phase1 (alias=%s)", platform_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            platform_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))
        assert_that(
            lite_llm_budget_utils.get_customer_info(cli_override_customer_id), none()
        )

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
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
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project platform key spend.",
        )
    finally:
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_premium_spending_falls_back_to_platform_member_override_when_no_premium_override(
    lifecycle_project,
    project_budget_groups,
    user2_proxy_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, user2_id = lifecycle_project
    platform_alias = project_key_alias(project_name, "platform")
    platform_override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    premium_override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}
    budget = project_budget_groups.create(
        project_name, name_prefix="autotest-fallback-premium"
    )
    budget_id = budget.budget_ids["platform"]

    try:
        logger.info(
            "Overriding user2 (%s) platform allocation (no premium override)", user2_id
        )
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        logger.info(
            "Waiting for platform override customer (customer=%s)",
            platform_override_customer_id,
        )
        lite_llm_budget_utils.wait_for_customer(platform_override_customer_id)

        # Phase 1 — first request: establish baseline spending
        sleep(60)
        logger.info("Phase 1: sending premium request (platform-only override active)")
        user2_proxy_utils.send_messages_request(
            model=PREMIUM_MODEL,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info("Waiting for platform key spending (alias=%s)", platform_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info(
            "Waiting for platform override spending (customer=%s)",
            platform_override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_spending(
            platform_override_customer_id
        )
        assert_that(override_customer, not_none())
        assert_that(float(override_customer["spend"]), greater_than(0))
        assert_that(
            float(override_customer["spend"]),
            close_to(key_spend_phase1, 0.0001),
        )
        customer_spend_phase1 = float(override_customer["spend"])
        assert_that(
            lite_llm_budget_utils.get_customer_info(premium_override_customer_id),
            none(),
        )

        # Phase 2 — second request: verify spending increases
        logger.info("Phase 2: sending premium request (platform-only override active)")
        sleep(60)
        user2_proxy_utils.send_messages_request(
            model=PREMIUM_MODEL,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info(
            "Waiting for platform override spending above phase1 (customer=%s)",
            platform_override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_spending_above(
            platform_override_customer_id, customer_spend_phase1
        )
        assert_that(override_customer, not_none())
        assert_that(
            float(override_customer["spend"]), greater_than(customer_spend_phase1)
        )
        logger.info(
            "Waiting for platform key spending above phase1 (alias=%s)", platform_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            platform_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))
        assert_that(
            lite_llm_budget_utils.get_customer_info(premium_override_customer_id),
            none(),
        )

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
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
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project platform key spend.",
        )
    finally:
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_platform_spending_routes_to_platform_member_override_when_all_overridden(
    lifecycle_project,
    project_budget_groups,
    user2_assistant,
    user2_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, user2_id = lifecycle_project
    platform_alias = project_key_alias(project_name, "platform")
    platform_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    cli_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="cli", user_id=user2_id
    )
    premium_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    budget = project_budget_groups.create(
        project_name, ALL_BUDGET_CATEGORIES, name_prefix="autotest-all-platform"
    )
    platform_budget_id = budget.budget_ids["platform"]
    cli_budget_id = budget.budget_ids["cli"]
    premium_budget_id = budget.budget_ids["premium_models"]

    try:
        logger.info("Overriding user2 (%s) on all 3 categories", user2_id)
        admin_project_budget_utils.override_member(
            platform_budget_id, user2_id, 40.0, 20.0
        )
        admin_project_budget_utils.override_member(cli_budget_id, user2_id, 40.0, 20.0)
        admin_project_budget_utils.override_member(
            premium_budget_id, user2_id, 40.0, 20.0
        )
        logger.info("Waiting for all 3 override customers")
        lite_llm_budget_utils.wait_for_customer(platform_override_id)
        lite_llm_budget_utils.wait_for_customer(cli_override_id)
        lite_llm_budget_utils.wait_for_customer(premium_override_id)

        # Phase 1 — first request: establish baseline spending
        sleep(60)
        logger.info("Phase 1: sending platform request (all 3 overrides active)")
        assistant = user2_assistant(project_name=project_name)
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info("Waiting for platform key spending (alias=%s)", platform_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info(
            "Waiting for platform override spending (customer=%s)", platform_override_id
        )
        platform_override = lite_llm_budget_utils.wait_for_spending(
            platform_override_id
        )
        assert_that(platform_override, not_none())
        assert_that(float(platform_override["spend"]), greater_than(0))
        assert_that(
            float(platform_override["spend"]),
            close_to(key_spend_phase1, 0.0001),
        )
        customer_spend_phase1 = float(platform_override["spend"])
        cli_override = lite_llm_budget_utils.get_customer_info(cli_override_id)
        assert_that(float(cli_override["spend"]), equal_to(0))
        premium_override = lite_llm_budget_utils.get_customer_info(premium_override_id)
        assert_that(float(premium_override["spend"]), equal_to(0))

        # Phase 2 — second request: verify spending increases
        logger.info("Phase 2: sending platform request (all 3 overrides active)")
        sleep(60)
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info(
            "Waiting for platform override spending above phase1 (customer=%s)",
            platform_override_id,
        )
        platform_override = lite_llm_budget_utils.wait_for_spending_above(
            platform_override_id, customer_spend_phase1
        )
        assert_that(platform_override, not_none())
        assert_that(
            float(platform_override["spend"]), greater_than(customer_spend_phase1)
        )
        logger.info(
            "Waiting for platform key spending above phase1 (alias=%s)", platform_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            platform_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))
        cli_override = lite_llm_budget_utils.get_customer_info(cli_override_id)
        assert_that(float(cli_override["spend"]), equal_to(0))
        premium_override = lite_llm_budget_utils.get_customer_info(premium_override_id)
        assert_that(float(premium_override["spend"]), equal_to(0))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
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
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project platform key spend.",
        )
    finally:
        for budget_id in (platform_budget_id, cli_budget_id, premium_budget_id):
            admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_cli_spending_routes_to_cli_member_override_when_all_overridden(
    lifecycle_project,
    project_budget_groups,
    user2_proxy_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    default_llm,
    admin_spend_tracking_utils,
):
    project_name, user2_id = lifecycle_project
    cli_alias = project_key_alias(project_name, "cli")
    platform_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    cli_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="cli", user_id=user2_id
    )
    premium_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    cli_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}
    budget = project_budget_groups.create(
        project_name, ALL_BUDGET_CATEGORIES, name_prefix="autotest-all-platform"
    )
    platform_budget_id = budget.budget_ids["platform"]
    cli_budget_id = budget.budget_ids["cli"]
    premium_budget_id = budget.budget_ids["premium_models"]

    try:
        logger.info("Overriding user2 (%s) on all 3 categories", user2_id)
        admin_project_budget_utils.override_member(
            platform_budget_id, user2_id, 40.0, 20.0
        )
        admin_project_budget_utils.override_member(cli_budget_id, user2_id, 40.0, 20.0)
        admin_project_budget_utils.override_member(
            premium_budget_id, user2_id, 40.0, 20.0
        )
        logger.info("Waiting for all 3 override customers")
        lite_llm_budget_utils.wait_for_customer(platform_override_id)
        lite_llm_budget_utils.wait_for_customer(cli_override_id)
        lite_llm_budget_utils.wait_for_customer(premium_override_id)

        # Phase 1 — first request: establish baseline spending
        sleep(60)
        logger.info("Phase 1: sending CLI request (all 3 overrides active)")
        user2_proxy_utils.send_messages_request(
            model=default_llm.base_name,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=cli_headers,
        ).raise_for_status()
        logger.info("Waiting for CLI key spending (alias=%s)", cli_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(cli_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info("Waiting for CLI override spending (customer=%s)", cli_override_id)
        cli_override = lite_llm_budget_utils.wait_for_spending(cli_override_id)
        assert_that(cli_override, not_none())
        assert_that(float(cli_override["spend"]), greater_than(0))
        assert_that(
            float(cli_override["spend"]),
            close_to(key_spend_phase1, 0.0001),
        )
        customer_spend_phase1 = float(cli_override["spend"])
        platform_override = lite_llm_budget_utils.get_customer_info(
            platform_override_id
        )
        assert_that(float(platform_override["spend"]), equal_to(0))
        premium_override = lite_llm_budget_utils.get_customer_info(premium_override_id)
        assert_that(float(premium_override["spend"]), equal_to(0))

        # Phase 2 — second request: verify spending increases
        logger.info("Phase 2: sending CLI request (all 3 overrides active)")
        sleep(60)
        user2_proxy_utils.send_messages_request(
            model=default_llm.base_name,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=cli_headers,
        ).raise_for_status()
        logger.info(
            "Waiting for CLI override spending above phase1 (customer=%s)",
            cli_override_id,
        )
        cli_override = lite_llm_budget_utils.wait_for_spending_above(
            cli_override_id, customer_spend_phase1
        )
        assert_that(cli_override, not_none())
        assert_that(float(cli_override["spend"]), greater_than(customer_spend_phase1))
        logger.info("Waiting for CLI key spending above phase1 (alias=%s)", cli_alias)
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            cli_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))
        platform_override = lite_llm_budget_utils.get_customer_info(
            platform_override_id
        )
        assert_that(float(platform_override["spend"]), equal_to(0))
        premium_override = lite_llm_budget_utils.get_customer_info(premium_override_id)
        assert_that(float(premium_override["spend"]), equal_to(0))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
        logger.info(
            "Waiting for cli spend in project_spend_tracking (project=%s)",
            project_name,
        )
        today = datetime.date.today()
        spends = admin_spend_tracking_utils.wait_for_project_spends(
            project_name, today, today, "cli"
        )
        assert_that(
            spends["total_spend"],
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project cli key spend.",
        )
    finally:
        for budget_id in (platform_budget_id, cli_budget_id, premium_budget_id):
            admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_premium_spending_routes_to_premium_member_override_when_all_overridden(
    lifecycle_project,
    project_budget_groups,
    user2_proxy_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, user2_id = lifecycle_project
    premium_alias = project_key_alias(project_name, "premium_models")
    platform_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    cli_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="cli", user_id=user2_id
    )
    premium_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}
    budget = project_budget_groups.create(
        project_name, ALL_BUDGET_CATEGORIES, name_prefix="autotest-all-platform"
    )
    platform_budget_id = budget.budget_ids["platform"]
    cli_budget_id = budget.budget_ids["cli"]
    premium_budget_id = budget.budget_ids["premium_models"]

    try:
        logger.info("Overriding user2 (%s) on all 3 categories", user2_id)
        admin_project_budget_utils.override_member(
            platform_budget_id, user2_id, 40.0, 20.0
        )
        admin_project_budget_utils.override_member(cli_budget_id, user2_id, 40.0, 20.0)
        admin_project_budget_utils.override_member(
            premium_budget_id, user2_id, 40.0, 20.0
        )
        logger.info("Waiting for all 3 override customers")
        lite_llm_budget_utils.wait_for_customer(platform_override_id)
        lite_llm_budget_utils.wait_for_customer(cli_override_id)
        lite_llm_budget_utils.wait_for_customer(premium_override_id)

        # Phase 1 — first request: establish baseline spending
        sleep(60)
        logger.info("Phase 1: sending premium request (all 3 overrides active)")
        user2_proxy_utils.send_messages_request(
            model=PREMIUM_MODEL,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info("Waiting for premium key spending (alias=%s)", premium_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info(
            "Waiting for premium override spending (customer=%s)", premium_override_id
        )
        premium_override = lite_llm_budget_utils.wait_for_spending(premium_override_id)
        assert_that(premium_override, not_none())
        assert_that(float(premium_override["spend"]), greater_than(0))
        assert_that(
            float(premium_override["spend"]),
            close_to(key_spend_phase1, 0.0001),
        )
        customer_spend_phase1 = float(premium_override["spend"])
        platform_override = lite_llm_budget_utils.get_customer_info(
            platform_override_id
        )
        assert_that(float(platform_override["spend"]), equal_to(0))
        cli_override = lite_llm_budget_utils.get_customer_info(cli_override_id)
        assert_that(float(cli_override["spend"]), equal_to(0))

        # Phase 2 — second request: verify spending increases
        logger.info("Phase 2: sending premium request (all 3 overrides active)")
        sleep(60)
        user2_proxy_utils.send_messages_request(
            model=PREMIUM_MODEL,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info(
            "Waiting for premium override spending above phase1 (customer=%s)",
            premium_override_id,
        )
        premium_override = lite_llm_budget_utils.wait_for_spending_above(
            premium_override_id, customer_spend_phase1
        )
        assert_that(premium_override, not_none())
        assert_that(
            float(premium_override["spend"]), greater_than(customer_spend_phase1)
        )
        logger.info(
            "Waiting for premium key spending above phase1 (alias=%s)", premium_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            premium_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))
        platform_override = lite_llm_budget_utils.get_customer_info(
            platform_override_id
        )
        assert_that(float(platform_override["spend"]), equal_to(0))
        cli_override = lite_llm_budget_utils.get_customer_info(cli_override_id)
        assert_that(float(cli_override["spend"]), equal_to(0))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
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
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project premium_models key spend.",
        )
    finally:
        for budget_id in (platform_budget_id, cli_budget_id, premium_budget_id):
            admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_litellm_key_overrides_platform_member_override(
    lifecycle_project,
    project_budget_groups,
    user2_assistant,
    user2_assistant_utils,
    user2_litellm_key,
    user2_litellm_integration,
    admin_project_budget_utils,
    lite_llm_budget_utils,
):
    project_name, user2_id = lifecycle_project
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    budget = project_budget_groups.create(
        project_name, name_prefix="autotest-key-platform"
    )
    budget_id = budget.budget_ids["platform"]

    try:
        logger.info("Overriding user2 (%s) platform allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        logger.info("Waiting for override customer (customer=%s)", override_customer_id)
        lite_llm_budget_utils.wait_for_customer(override_customer_id)

        sleep(60)
        logger.info("Sending platform request (override + personal LiteLLM key active)")
        assistant = user2_assistant(project_name=project_name)
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info("Waiting for LiteLLM key spending")
        key_info = lite_llm_budget_utils.wait_for_key_spending(user2_litellm_key)
        assert_that(key_info, not_none())
        assert_that(float(key_info["spend"]), greater_than(0))
        override_customer = lite_llm_budget_utils.get_customer_info(
            override_customer_id
        )
        assert_that(float(override_customer["spend"]), equal_to(0))
    finally:
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_litellm_key_overrides_cli_member_override(
    lifecycle_project,
    project_budget_groups,
    user2_proxy_utils,
    user2_litellm_key,
    user2_litellm_integration,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    default_llm,
):
    project_name, user2_id = lifecycle_project
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="cli", user_id=user2_id
    )
    cli_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}
    budget = project_budget_groups.create(
        project_name, CLI_BUDGET_CATEGORIES, name_prefix="autotest-key-cli"
    )
    budget_id = budget.budget_ids["cli"]

    try:
        logger.info("Overriding user2 (%s) CLI allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        logger.info("Waiting for override customer (customer=%s)", override_customer_id)
        lite_llm_budget_utils.wait_for_customer(override_customer_id)

        sleep(60)
        logger.info("Sending CLI request (override + personal LiteLLM key active)")
        user2_proxy_utils.send_messages_request(
            model=default_llm.base_name,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=cli_headers,
        ).raise_for_status()
        logger.info("Waiting for LiteLLM key spending")
        key_info = lite_llm_budget_utils.wait_for_key_spending(user2_litellm_key)
        assert_that(key_info, not_none())
        assert_that(float(key_info["spend"]), greater_than(0))
        override_customer = lite_llm_budget_utils.get_customer_info(
            override_customer_id
        )
        assert_that(float(override_customer["spend"]), equal_to(0))
    finally:
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_litellm_key_overrides_premium_member_override(
    lifecycle_project,
    project_budget_groups,
    user2_proxy_utils,
    user2_litellm_key,
    user2_litellm_integration,
    admin_project_budget_utils,
    lite_llm_budget_utils,
):
    project_name, user2_id = lifecycle_project
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    request_headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}
    budget = project_budget_groups.create(
        project_name, PREMIUM_BUDGET_CATEGORIES, name_prefix="autotest-key-premium"
    )
    budget_id = budget.budget_ids["premium_models"]

    try:
        logger.info("Overriding user2 (%s) premium allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        logger.info("Waiting for override customer (customer=%s)", override_customer_id)
        lite_llm_budget_utils.wait_for_customer(override_customer_id)

        sleep(60)
        logger.info("Sending premium request (override + personal LiteLLM key active)")
        user2_proxy_utils.send_messages_request(
            model=PREMIUM_MODEL,
            messages=[{"role": "user", "content": budget_chat_prompt()}],
            extra_headers=request_headers,
        ).raise_for_status()
        logger.info("Waiting for LiteLLM key spending")
        key_info = lite_llm_budget_utils.wait_for_key_spending(user2_litellm_key)
        assert_that(key_info, not_none())
        assert_that(float(key_info["spend"]), greater_than(0))
        override_customer = lite_llm_budget_utils.get_customer_info(
            override_customer_id
        )
        assert_that(float(override_customer["spend"]), equal_to(0))
    finally:
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_overrides_premium_member_budget_routes_spending_via_chat(
    user2_premium_assistant,
    user2_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    lifecycle_project_with_premium_budget,
    admin_spend_tracking_utils,
):
    project_name, user2_id, budget_id, premium_alias = (
        lifecycle_project_with_premium_budget
    )
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    assistant = user2_premium_assistant(project_name=project_name)
    try:
        # Phase 1 — no override: spending goes to both shared key and user customer
        logger.info("Phase 1: sending chat premium request (no override)")
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info("Waiting for shared key spending (alias=%s)", premium_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info(
            "Waiting for user customer spending (customer=%s)", override_customer_id
        )
        user_customer = lite_llm_budget_utils.wait_for_spending(override_customer_id)
        assert_that(user_customer, not_none())
        assert_that(float(user_customer["spend"]), greater_than(0))
        assert_that(
            float(user_customer["spend"]),
            close_to(key_spend_phase1, 0.0001),
        )
        customer_spend_phase1 = float(user_customer["spend"])
        assert_that(
            user_customer.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(f"{budget_id}:shared"),
        )

        # Override assigned: verify customer has correct budget, limits, and preserved spend
        logger.info("Overriding user2 (%s) premium allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        override_budget_id = f"{budget_id}:user:{user2_id}"
        logger.info(
            "Waiting for override customer budget_id update (customer=%s)",
            override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_customer_budget_id(
            override_customer_id, override_budget_id
        )
        assert_that(override_customer, not_none())
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(override_budget_id),
        )
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("max_budget"),
            equal_to(40.0),
        )
        assert_that(
            override_customer.get("litellm_budget_table", {}).get("soft_budget"),
            equal_to(20.0),
        )
        assert_that(
            float(override_customer["spend"]),
            close_to(customer_spend_phase1, 0.0001),
        )

        # Phase 2 — override active: both key and customer spending increase
        logger.info("Sending chat premium request (override active)")
        sleep(60)
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info(
            "Waiting for override customer spending above phase1 (customer=%s)",
            override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_spending_above(
            override_customer_id, customer_spend_phase1
        )
        assert_that(override_customer, not_none())
        assert_that(
            float(override_customer["spend"]), greater_than(customer_spend_phase1)
        )
        logger.info(
            "Waiting for shared key spending above phase1 (alias=%s)", premium_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            premium_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
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
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project premium_models key spend.",
        )
    finally:
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        lite_llm_budget_utils.delete_project_budget_objects(budget_id, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_admin_clears_premium_member_override_reverts_spending_to_shared_via_chat(
    lifecycle_project,
    project_budget_groups,
    user1_id,
    user2_premium_assistant,
    user2_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, user2_id = lifecycle_project
    premium_alias = project_key_alias(project_name, "premium_models")
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    budget = project_budget_groups.create(
        project_name,
        PREMIUM_BUDGET_CATEGORIES,
        name_prefix="autotest-clear-premium-chat",
    )
    budget_id = budget.budget_ids["premium_models"]

    try:
        assistant = user2_premium_assistant(project_name=project_name)

        # Phase 1 — override active: verify routing + rebalance
        logger.info("Phase 1: overriding user2 (%s) premium allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        logger.info("Waiting for override customer (customer=%s)", override_customer_id)
        lite_llm_budget_utils.wait_for_customer(override_customer_id)
        sleep(60)
        logger.info("Sending chat premium request (override active)")
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info(
            "Waiting for override customer spending (customer=%s)", override_customer_id
        )
        override_customer = lite_llm_budget_utils.wait_for_spending(
            override_customer_id
        )
        assert_that(override_customer, not_none())
        assert_that(float(override_customer["spend"]), greater_than(0))
        override_spend_phase1 = float(override_customer["spend"])
        logger.info("Waiting for shared key spending (alias=%s)", premium_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info("Verifying budget allocations after override")
        budget_response = admin_project_budget_utils.get_budget(budget_id)
        allocations = {m["user_id"]: m for m in budget_response["member_allocations"]}
        assert_that(allocations[user2_id]["allocation_mode"], equal_to("fixed"))
        assert_that(allocations[user2_id]["allocated_max_budget"], equal_to(40.0))
        assert_that(allocations[user1_id]["allocated_max_budget"], equal_to(60.0))

        # Phase 2 — override cleared: spending reverts to shared key, allocations restored
        logger.info("Phase 2: clearing override for user2 (%s)", user2_id)
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        sleep(60)
        logger.info("Sending chat premium request (override cleared)")
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info(
            "Waiting for override customer spending above phase1 (customer=%s)",
            override_customer_id,
        )
        current_override = lite_llm_budget_utils.wait_for_spending_above(
            override_customer_id, override_spend_phase1
        )
        assert_that(current_override, not_none())
        assert_that(
            float(current_override["spend"]), greater_than(override_spend_phase1)
        )
        logger.info(
            "Waiting for shared key spending above phase1 (alias=%s)", premium_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            premium_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))
        shared_budget_id = f"{budget_id}:shared"
        logger.info(
            "Waiting for override customer budget_id revert to shared (customer=%s)",
            override_customer_id,
        )
        current_override = lite_llm_budget_utils.wait_for_customer_budget_id(
            override_customer_id, shared_budget_id
        )
        assert_that(current_override, not_none())
        assert_that(
            current_override.get("litellm_budget_table", {}).get("budget_id"),
            equal_to(shared_budget_id),
        )
        logger.info("Verifying budget allocations after clear")
        budget_response = admin_project_budget_utils.get_budget(budget_id)
        allocations = {m["user_id"]: m for m in budget_response["member_allocations"]}
        assert_that(allocations[user2_id]["allocation_mode"], equal_to("equal"))
        assert_that(allocations[user2_id]["allocated_max_budget"], equal_to(50.0))
        assert_that(allocations[user1_id]["allocated_max_budget"], equal_to(50.0))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
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
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project premium_models key spend.",
        )
    finally:
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_premium_spending_falls_back_to_platform_member_override_via_chat(
    lifecycle_project,
    project_budget_groups,
    user2_premium_assistant,
    user2_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, user2_id = lifecycle_project
    platform_alias = project_key_alias(project_name, "platform")
    platform_override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    premium_override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    budget = project_budget_groups.create(
        project_name, name_prefix="autotest-fallback-premium-chat"
    )
    budget_id = budget.budget_ids["platform"]

    try:
        logger.info(
            "Overriding user2 (%s) platform allocation (no premium override)", user2_id
        )
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        logger.info(
            "Waiting for platform override customer (customer=%s)",
            platform_override_customer_id,
        )
        lite_llm_budget_utils.wait_for_customer(platform_override_customer_id)
        assistant = user2_premium_assistant(project_name=project_name)

        # Phase 1 — first request: establish baseline spending
        sleep(60)
        logger.info(
            "Phase 1: sending chat premium request (platform-only override active)"
        )
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info("Waiting for platform key spending (alias=%s)", platform_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(platform_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info(
            "Waiting for platform override spending (customer=%s)",
            platform_override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_spending(
            platform_override_customer_id
        )
        assert_that(override_customer, not_none())
        assert_that(float(override_customer["spend"]), greater_than(0))
        assert_that(
            float(override_customer["spend"]),
            close_to(key_spend_phase1, 0.0001),
        )
        customer_spend_phase1 = float(override_customer["spend"])
        assert_that(
            lite_llm_budget_utils.get_customer_info(premium_override_customer_id),
            none(),
        )

        # Phase 2 — second request: verify spending increases
        logger.info(
            "Phase 2: sending chat premium request (platform-only override active)"
        )
        sleep(60)
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info(
            "Waiting for platform override spending above phase1 (customer=%s)",
            platform_override_customer_id,
        )
        override_customer = lite_llm_budget_utils.wait_for_spending_above(
            platform_override_customer_id, customer_spend_phase1
        )
        assert_that(override_customer, not_none())
        assert_that(
            float(override_customer["spend"]), greater_than(customer_spend_phase1)
        )
        logger.info(
            "Waiting for platform key spending above phase1 (alias=%s)", platform_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            platform_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))
        assert_that(
            lite_llm_budget_utils.get_customer_info(premium_override_customer_id),
            none(),
        )

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
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
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project platform key spend.",
        )
    finally:
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_premium_spending_routes_to_premium_member_override_when_all_overridden_via_chat(
    lifecycle_project,
    project_budget_groups,
    user2_premium_assistant,
    user2_assistant_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    admin_spend_tracking_utils,
):
    project_name, user2_id = lifecycle_project
    premium_alias = project_key_alias(project_name, "premium_models")
    platform_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="platform", user_id=user2_id
    )
    cli_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="cli", user_id=user2_id
    )
    premium_override_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    budget = project_budget_groups.create(
        project_name, ALL_BUDGET_CATEGORIES, name_prefix="autotest-all-platform-chat"
    )
    platform_budget_id = budget.budget_ids["platform"]
    cli_budget_id = budget.budget_ids["cli"]
    premium_budget_id = budget.budget_ids["premium_models"]

    try:
        logger.info("Overriding user2 (%s) on all 3 categories", user2_id)
        admin_project_budget_utils.override_member(
            platform_budget_id, user2_id, 40.0, 20.0
        )
        admin_project_budget_utils.override_member(cli_budget_id, user2_id, 40.0, 20.0)
        admin_project_budget_utils.override_member(
            premium_budget_id, user2_id, 40.0, 20.0
        )
        logger.info("Waiting for all 3 override customers")
        lite_llm_budget_utils.wait_for_customer(platform_override_id)
        lite_llm_budget_utils.wait_for_customer(cli_override_id)
        lite_llm_budget_utils.wait_for_customer(premium_override_id)

        # Phase 1 — first request: establish baseline spending
        sleep(60)
        assistant = user2_premium_assistant(project_name=project_name)
        logger.info("Phase 1: sending chat premium request (all 3 overrides active)")
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info("Waiting for premium key spending (alias=%s)", premium_alias)
        shared_key = lite_llm_budget_utils.wait_for_key_alias_spending(premium_alias)
        assert_that(shared_key, not_none())
        assert_that(float(shared_key["spend"]), greater_than(0))
        key_spend_phase1 = float(shared_key["spend"])
        logger.info(
            "Waiting for premium override spending (customer=%s)", premium_override_id
        )
        premium_override = lite_llm_budget_utils.wait_for_spending(premium_override_id)
        assert_that(premium_override, not_none())
        assert_that(float(premium_override["spend"]), greater_than(0))
        assert_that(
            float(premium_override["spend"]),
            close_to(key_spend_phase1, 0.0001),
        )
        customer_spend_phase1 = float(premium_override["spend"])
        platform_override = lite_llm_budget_utils.get_customer_info(
            platform_override_id
        )
        assert_that(float(platform_override["spend"]), equal_to(0))
        cli_override = lite_llm_budget_utils.get_customer_info(cli_override_id)
        assert_that(float(cli_override["spend"]), equal_to(0))

        # Phase 2 — second request: verify spending increases
        logger.info("Phase 2: sending chat premium request (all 3 overrides active)")
        sleep(60)
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info(
            "Waiting for premium override spending above phase1 (customer=%s)",
            premium_override_id,
        )
        premium_override = lite_llm_budget_utils.wait_for_spending_above(
            premium_override_id, customer_spend_phase1
        )
        assert_that(premium_override, not_none())
        assert_that(
            float(premium_override["spend"]), greater_than(customer_spend_phase1)
        )
        logger.info(
            "Waiting for premium key spending above phase1 (alias=%s)", premium_alias
        )
        current_shared_key = lite_llm_budget_utils.wait_for_key_alias_spending_above(
            premium_alias, key_spend_phase1
        )
        assert_that(float(current_shared_key["spend"]), greater_than(key_spend_phase1))
        platform_override = lite_llm_budget_utils.get_customer_info(
            platform_override_id
        )
        assert_that(float(platform_override["spend"]), equal_to(0))
        cli_override = lite_llm_budget_utils.get_customer_info(cli_override_id)
        assert_that(float(cli_override["spend"]), equal_to(0))

        logger.info("Triggering spend collection")
        admin_spend_tracking_utils.collect_spends()
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
            close_to(float(current_shared_key["spend"]), 0.0001),
            "project_spend_tracking total_spend should match project premium_models key spend.",
        )
    finally:
        for budget_id in (platform_budget_id, cli_budget_id, premium_budget_id):
            admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_litellm_key_overrides_premium_member_override_via_chat(
    lifecycle_project,
    project_budget_groups,
    user2_premium_assistant,
    user2_assistant_utils,
    user2_litellm_key,
    user2_litellm_integration,
    admin_project_budget_utils,
    lite_llm_budget_utils,
):
    project_name, user2_id = lifecycle_project
    override_customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category="premium_models", user_id=user2_id
    )
    budget = project_budget_groups.create(
        project_name, PREMIUM_BUDGET_CATEGORIES, name_prefix="autotest-key-premium-chat"
    )
    budget_id = budget.budget_ids["premium_models"]

    try:
        logger.info("Overriding user2 (%s) premium allocation", user2_id)
        admin_project_budget_utils.override_member(budget_id, user2_id, 40.0, 20.0)
        logger.info("Waiting for override customer (customer=%s)", override_customer_id)
        lite_llm_budget_utils.wait_for_customer(override_customer_id)

        sleep(60)
        assistant = user2_premium_assistant(project_name=project_name)
        logger.info(
            "Sending chat premium request (override + personal LiteLLM key active)"
        )
        user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info("Waiting for LiteLLM key spending")
        key_info = lite_llm_budget_utils.wait_for_key_spending(user2_litellm_key)
        assert_that(key_info, not_none())
        assert_that(float(key_info["spend"]), greater_than(0))
        override_customer = lite_llm_budget_utils.get_customer_info(
            override_customer_id
        )
        assert_that(float(override_customer["spend"]), equal_to(0))
    finally:
        admin_project_budget_utils.clear_member_override(budget_id, user2_id)
        project_budget_groups.delete(budget, user2_id)


@pytest.mark.budget
@pytest.mark.api
def test_project_admin_overrides_and_clears_member_allocation(
    project_admin_override_ready,
):
    _, budget_id, pa_client, member_id, _ = project_admin_override_ready
    pa_budget_utils = AdminProjectBudgetUtils(pa_client)

    pa_budget_utils.override_member(
        budget_id, member_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
    )

    budget = pa_budget_utils.get_budget(budget_id)
    allocations = {m["user_id"]: m for m in budget["member_allocations"]}
    overridden = allocations[member_id]
    assert_that(overridden["allocation_mode"], equal_to("fixed"))
    assert_that(overridden["allocated_max_budget"], equal_to(MEMBER_OVERRIDE_MAX))
    assert_that(overridden["allocated_soft_budget"], equal_to(MEMBER_OVERRIDE_SOFT))
    total_allocated = sum(m["allocated_max_budget"] for m in allocations.values())
    assert_that(total_allocated, close_to(100.0, 0.01))

    pa_budget_utils.clear_member_override(budget_id, member_id)

    budget = pa_budget_utils.get_budget(budget_id)
    allocations = {m["user_id"]: m for m in budget["member_allocations"]}
    cleared = allocations[member_id]
    assert_that(cleared["allocation_mode"], equal_to("equal"))
    assert_that(
        cleared["allocated_max_budget"], close_to(100.0 / len(allocations), 0.01)
    )


@pytest.mark.budget
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize(
    "method_name, extra_args", DENIED_MUTATIONS, ids=DENIED_MUTATION_IDS
)
@pytest.mark.api
def test_unauthorized_actor_cannot_manage_member_allocation(
    unauthorized_override_actor,
    member_with_maintainer_override,
    admin_project_budget_utils,
    method_name,
    extra_args,
):
    budget_id, member_id, allocations_before = member_with_maintainer_override
    actor_budget_utils = AdminProjectBudgetUtils(unauthorized_override_actor)

    with pytest.raises(HTTPError) as exc_info:
        getattr(actor_budget_utils, method_name)(budget_id, member_id, *extra_args)

    assert_that(exc_info.value.response.status_code, equal_to(403))
    assert_that(exc_info.value.response.text, contains_string(NO_PERMISSION_MESSAGE))
    allocations_after = admin_project_budget_utils.get_budget(budget_id)[
        "member_allocations"
    ]
    assert_that(allocations_after, equal_to(allocations_before))
