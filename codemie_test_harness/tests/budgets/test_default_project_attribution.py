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

"""E2E budget attribution by default project.

Observation channel (same as the other budget tests): LiteLLM spend on the project keys
(``codemie:project:<name>:category:<category>``) and on the user's personal customers.
After each request exactly the expected source must have grown.

Covers:
    TC-14  Marketplace assistant: non-member+default -> default; member+default -> assistant's
           project; member, no default -> assistant's project; non-member, no default -> personal
    TC-15  A flow not bound to a project asset is charged to the default project of a multi-project user
    TC-16  Multi-project user without a default: the charged destination is the same every time
    TC-17  Default project without a budget: all spend goes to the personal budgets
    TC-18  Proxy / CLI: default project when no project is sent; explicit project always wins
    TC-19  Lifecycle: changing the default moves new spend only; removing the default membership
           stops charging that project
"""

import logging
from time import sleep

import pytest
from hamcrest import (
    assert_that,
    close_to,
    contains_exactly,
    equal_to,
    has_length,
    none,
)

from codemie_test_harness.tests.test_data.budget_test_data import (
    BUDGET_CACHE_DELAY,
    CLI_BUDGET_CATEGORIES,
    CLI_CLIENT_HEADER,
    CLI_PROJECT_HEADER,
    DEFAULT_CLI_BUDGET_ID,
    PLATFORM_BUDGET_CATEGORIES,
    budget_chat_prompt,
    budget_skill_description,
    project_key_alias,
)

logger = logging.getLogger(__name__)


# ── TC-14 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.marketplace
@pytest.mark.timeout(1500)
@pytest.mark.parametrize(
    "is_member, has_default, expected_charged",
    [
        pytest.param(False, True, "default_project", id="non_member_with_default"),
        pytest.param(True, True, "assistant_project", id="member_with_other_default"),
        pytest.param(True, False, "assistant_project", id="member_without_default"),
        pytest.param(False, False, "personal", id="non_member_without_default"),
    ],
)
def test_marketplace_assistant_charge_follows_membership_then_default(
    is_member,
    has_default,
    expected_charged,
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user1_published_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    assistant_project = budget_project_factory(
        PLATFORM_BUDGET_CATEGORIES, (user2_id,) if is_member else ()
    )
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    assistant = user1_published_assistant(assistant_project)
    if has_default:
        user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "assistant_project": project_key_alias(assistant_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}

    logger.info(
        "Asking the marketplace assistant: member=%s, default set=%s, expecting %s",
        is_member,
        has_default,
        expected_charged,
    )
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({expected_charged}),
        f"Spend must be charged to {expected_charged}",
    )


# ── TC-15 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1500)
def test_unbound_flow_is_charged_to_default_project(
    keycloak_user_2,
    user2_id,
    user_utils,
    user2_skills_utils,
    budget_project_factory,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    other_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "default_project": project_key_alias(default_project),
        "other_project": project_key_alias(other_project),
    }
    customers = {"personal": email}

    logger.info("Generating skill instructions as a multi-project user with a default")
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_skills_utils.generate_instructions(budget_skill_description())

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"default_project"}),
        "Spend must go to the default project, not to another membership or the personal budget",
    )


# ── TC-16 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1500)
def test_unbound_flow_without_default_is_charged_to_same_destination_every_time(
    keycloak_user_2,
    user2_id,
    user2_skills_utils,
    budget_project_factory,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    project_one = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    project_two = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "project_one": project_key_alias(project_one),
        "project_two": project_key_alias(project_two),
    }
    customers = {"personal": email}

    destinations = []
    for attempt in range(1, 3):
        logger.info(
            "Request %s: generating skill instructions without a default", attempt
        )
        before = lite_llm_budget_utils.get_spends(keys, customers)
        user2_skills_utils.generate_instructions(budget_skill_description())
        destinations.append(
            lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers)
        )

    logger.info("Charged destinations across requests: %s", destinations)
    assert_that(destinations[0], has_length(1), "Exactly one destination is charged")
    assert_that(
        destinations,
        equal_to([destinations[0]] * 2),
        "The charged destination must be identical on every request",
    )
    assert_that(
        destinations[0],
        equal_to({"personal"}),
        "Without a default project the charge must resolve to the personal budget",
    )


# ── TC-17 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1200)
def test_default_project_without_budget_falls_back_to_personal_budget(
    keycloak_user_2,
    user2_id,
    user_utils,
    user2_skills_utils,
    user2_proxy_utils,
    default_llm,
    budget_project_factory,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    default_project = budget_project_factory(None, (user2_id,))
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    customers = {
        "personal": email,
        "personal_cli": f"{email}_{DEFAULT_CLI_BUDGET_ID}",
    }

    logger.info("Phase 1: unbound flow, default project has no budget")
    before = lite_llm_budget_utils.get_spends({}, customers)
    user2_skills_utils.generate_instructions(budget_skill_description())
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, {}, customers),
        equal_to({"personal"}),
        "A flow not bound to a project must fall back to the personal budget",
    )

    logger.info("Phase 2: CLI request, default project has no budget")
    before = lite_llm_budget_utils.get_spends({}, customers)
    user2_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=CLI_CLIENT_HEADER,
    ).raise_for_status()
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, {}, customers),
        equal_to({"personal_cli"}),
        "A CLI request must fall back to the personal CLI budget",
    )

    assert_that(
        lite_llm_budget_utils.get_key_info_by_alias(
            project_key_alias(default_project, "platform")
        ),
        none(),
        "No project platform key may exist for a project without a budget",
    )
    assert_that(
        lite_llm_budget_utils.get_key_info_by_alias(
            project_key_alias(default_project, "cli")
        ),
        none(),
        "No project cli key may exist for a project without a budget",
    )


# ── TC-18 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1800)
def test_cli_request_uses_default_project_unless_project_is_explicit(
    keycloak_user_2,
    user2_id,
    user_utils,
    user2_proxy_utils,
    default_llm,
    budget_project_factory,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    default_project = budget_project_factory(CLI_BUDGET_CATEGORIES, (user2_id,))
    explicit_project = budget_project_factory(CLI_BUDGET_CATEGORIES, (user2_id,))
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "default_project": project_key_alias(default_project, "cli"),
        "explicit_project": project_key_alias(explicit_project, "cli"),
    }
    customers = {
        "personal": email,
        "personal_cli": f"{email}_{DEFAULT_CLI_BUDGET_ID}",
    }

    logger.info("Phase 1: CLI request without a project header")
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers=CLI_CLIENT_HEADER,
    ).raise_for_status()
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"default_project"}),
        "Without a project header the default project must be charged",
    )

    logger.info("Phase 2: CLI request with an explicit project header")
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers={**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: explicit_project},
    ).raise_for_status()
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"explicit_project"}),
        "An explicitly requested project must be charged regardless of the default",
    )


# ── TC-19 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(2400)
def test_changing_and_removing_default_project_moves_only_new_spend(
    keycloak_user_2,
    user2_id,
    user_utils,
    user1_project_utils,
    user2_skills_utils,
    budget_project_factory,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    first_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    second_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    user_utils.set_default_project(user2_id, first_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "first_project": project_key_alias(first_project),
        "second_project": project_key_alias(second_project),
    }
    customers = {"personal": email}

    logger.info("Phase 1: the initial default project is charged")
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_skills_utils.generate_instructions(budget_skill_description())
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"first_project"}),
        "The initial default project must be charged",
    )

    spend_of_first_project = lite_llm_budget_utils.get_spends(keys, customers)[
        "first_project"
    ]
    logger.info("Phase 2: default changed, new spend must follow")
    user_utils.set_default_project(user2_id, second_project)
    sleep(BUDGET_CACHE_DELAY)
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_skills_utils.generate_instructions(budget_skill_description())
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"second_project"}),
        "After the change new spend must go to the new default project",
    )
    assert_that(
        lite_llm_budget_utils.get_spends(keys, customers)["first_project"],
        close_to(spend_of_first_project, 0.0001),
        "Previously recorded spend must not be moved",
    )

    logger.info(
        "Phase 3: default membership removed, only the reported personal default remains"
    )
    user1_project_utils.remove_user_from_project(second_project, user2_id)
    sleep(BUDGET_CACHE_DELAY)
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_skills_utils.generate_instructions(budget_skill_description())
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"personal"}),
        "With no default project the removed default must not be charged; spend is personal",
    )
    assert_that(
        user_utils.get_default_project_names(user2_id),
        contains_exactly(email),
        "Without a stored default the personal project is reported as the default",
    )
