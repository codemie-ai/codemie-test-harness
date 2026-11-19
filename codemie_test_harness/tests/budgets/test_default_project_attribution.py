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
    TC-14  Marketplace assistant is charged to the user's default project whether or not the user
           is a member of the assistant's project; without an assigned default the default is the
           personal project, so the personal budget pays
    TC-15  A flow not bound to a project asset is charged to the default project of a multi-project user
    TC-16  Multi-project user without a default: the charged destination is the same every time
    TC-17  Default project without a budget: all spend goes to the personal budgets
    TC-18  Proxy / CLI: default project when no project is sent; a funded member project named
           in the request is charged instead of the default
    TC-19  Lifecycle: changing the default moves new spend only; removing the default membership
           stops charging that project
    TC-20  Personal assistant: charged to the assigned default project
    TC-21  Member project without a budget: charged to the funded default project
    TC-22  Shared project assistant used by a non-member: the assistant's project is never
           charged; default project, otherwise personal
    TC-23  Marketplace assistant published from the user's own personal project
    TC-24  CLI request naming a member project that has no budget: charged to the default
           project
    TC-25  CLI request naming a project the user is not a member of: rejected for a regular
           user; header ignored and default project charged for an admin
    TC-26  Sub-assistant of an orchestrator: charged as that assistant, not as the orchestrator
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
    budget_math_prompt,
    budget_skill_description,
    project_key_alias,
)
from codemie_test_harness.tests.utils.proxy_utils import ProxyUtils

logger = logging.getLogger(__name__)


# ── TC-14 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.marketplace
@pytest.mark.timeout(1500)
@pytest.mark.parametrize(
    "is_member, has_default, default_budget, expected_charged",
    [
        pytest.param(
            False,
            True,
            PLATFORM_BUDGET_CATEGORIES,
            "default_project",
            id="non_member_with_default",
        ),
        pytest.param(
            True,
            True,
            PLATFORM_BUDGET_CATEGORIES,
            "default_project",
            id="member_with_other_default",
        ),
        pytest.param(
            True,
            False,
            PLATFORM_BUDGET_CATEGORIES,
            "personal",
            id="member_without_default",
        ),
        pytest.param(
            False,
            False,
            PLATFORM_BUDGET_CATEGORIES,
            "personal",
            id="non_member_without_default",
        ),
        pytest.param(
            False,
            True,
            None,
            "personal",
            id="non_member_with_unfunded_default",
        ),
    ],
)
def test_marketplace_assistant_charge_follows_membership_then_default(
    is_member,
    has_default,
    default_budget,
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
    default_project = budget_project_factory(default_budget, (user2_id,))
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
        "Asking the marketplace assistant: member=%s, default set=%s, default funded=%s, "
        "expecting %s",
        is_member,
        has_default,
        default_budget is not None,
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
        "A project the user is a member of and that is funded must be charged instead of the default project when the request names it",
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


# ── TC-20 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1500)
def test_personal_assistant_is_charged_to_assigned_default_project(
    keycloak_user_2,
    user2_id,
    user_utils,
    user2_assistant,
    user2_assistant_utils,
    budget_project_factory,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {"default_project": project_key_alias(default_project)}
    customers = {"personal": email}
    assistant = user2_assistant(project_name=email)

    logger.info("Asking an assistant of the user's personal project, default is a team")
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"default_project"}),
        "A personal assistant must be charged to the assigned default project",
    )


# ── TC-21 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1500)
def test_member_project_without_budget_falls_back_to_funded_default_project(
    keycloak_user_2,
    user2_id,
    user_utils,
    user2_assistant,
    user2_assistant_utils,
    budget_project_factory,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    unfunded_project = budget_project_factory(None, (user2_id,))
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "default_project": project_key_alias(default_project),
        "unfunded_project": project_key_alias(unfunded_project),
    }
    customers = {"personal": email}
    assistant = user2_assistant(project_name=unfunded_project)

    logger.info("Asking an assistant of a member project that has no budget")
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"default_project"}),
        "A project without a budget must fall back to the funded default project, "
        "not to the personal budget",
    )


# ── TC-22 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1500)
@pytest.mark.parametrize(
    "has_default, expected_charged",
    [
        pytest.param(True, "default_project", id="with_default"),
        pytest.param(False, "personal", id="without_default"),
    ],
)
def test_shared_assistant_non_member_is_charged_to_default_project_not_asset_project(
    has_default,
    expected_charged,
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user1_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    asset_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, ())
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    assistant = user1_assistant(project_name=asset_project, shared=True)
    if has_default:
        user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "asset_project": project_key_alias(asset_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}

    logger.info(
        "Asking a shared assistant as a non-member: default set=%s, expecting %s",
        has_default,
        expected_charged,
    )
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({expected_charged}),
        f"Spend must be charged to {expected_charged}, never to the assistant's project",
    )


# ── TC-23 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.marketplace
@pytest.mark.timeout(1500)
@pytest.mark.parametrize(
    "has_default, expected_charged",
    [
        pytest.param(True, "default_project", id="with_default"),
        pytest.param(False, "personal", id="without_default"),
    ],
)
def test_marketplace_assistant_from_personal_project_is_charged_to_default_project(
    has_default,
    expected_charged,
    keycloak_user_1,
    user1_id,
    user_utils,
    budget_project_factory,
    user1_published_assistant,
    user1_assistant_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_1
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES)
    assistant = user1_published_assistant(email)
    if has_default:
        user_utils.set_default_project(user1_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {"default_project": project_key_alias(default_project)}
    customers = {"personal": email}

    logger.info(
        "Owner asks their published assistant from the personal project: "
        "default set=%s, expecting %s",
        has_default,
        expected_charged,
    )
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user1_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({expected_charged}),
        f"Spend must be charged to {expected_charged}",
    )


# ── TC-24 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1800)
def test_cli_unfunded_member_project_falls_back_to_default_project(
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
    unfunded_project = budget_project_factory(None, (user2_id,))
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "default_project": project_key_alias(default_project, "cli"),
        "unfunded_project": project_key_alias(unfunded_project, "cli"),
    }
    customers = {
        "personal": email,
        "personal_cli": f"{email}_{DEFAULT_CLI_BUDGET_ID}",
    }

    logger.info("CLI request naming a member project that has no budget")
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers={**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: unfunded_project},
    ).raise_for_status()

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"default_project"}),
        "A member project without a budget must fall back to the funded default "
        "project, not to the personal CLI budget",
    )


# ── TC-25 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1200)
def test_cli_non_member_project_header_is_rejected_for_regular_user(
    platform_user,
    default_llm,
    budget_project_factory,
):
    project = budget_project_factory(CLI_BUDGET_CATEGORIES, ())
    proxy_utils = ProxyUtils(platform_user.client)

    logger.info("Regular user names a project they are not a member of")
    response = proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers={**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project},
    )

    assert_that(
        response.status_code,
        equal_to(403),
        "A regular user must not be able to name a project they cannot use",
    )


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1800)
def test_cli_non_member_project_header_is_ignored_for_admin(
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
    named_project = budget_project_factory(CLI_BUDGET_CATEGORIES, ())
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "default_project": project_key_alias(default_project, "cli"),
        "named_project": project_key_alias(named_project, "cli"),
    }
    customers = {
        "personal": email,
        "personal_cli": f"{email}_{DEFAULT_CLI_BUDGET_ID}",
    }

    logger.info("Admin names a project they are not a member of")
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=[{"role": "user", "content": budget_chat_prompt()}],
        extra_headers={**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: named_project},
    ).raise_for_status()

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"default_project"}),
        "The named project must be ignored and the default project charged",
    )


# ── TC-26 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.marketplace
@pytest.mark.timeout(1800)
def test_sub_assistant_is_charged_by_its_own_attribution_row(
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user1_published_assistant,
    user1_orchestrator,
    user2_assistant_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    orchestrator_project = budget_project_factory(
        PLATFORM_BUDGET_CATEGORIES, (user2_id,)
    )
    sub_assistant_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, ())
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    sub_assistant = user1_published_assistant(sub_assistant_project)
    orchestrator = user1_orchestrator(orchestrator_project, sub_assistant, "math")
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "orchestrator_project": project_key_alias(orchestrator_project),
        "sub_assistant_project": project_key_alias(sub_assistant_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}

    logger.info(
        "Asking a math question that the orchestrator hands to its sub-assistant"
    )
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_assistant_utils.ask_assistant(orchestrator, budget_math_prompt(), stream=True)

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"orchestrator_project", "default_project"}),
        "The orchestrator must be charged to its own project and the marketplace "
        "sub-assistant to the default project, never to the sub-assistant's project",
    )
