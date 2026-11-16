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

"""E2E budget attribution when the chosen budget is exhausted.

An exhausted budget is not "unfunded": the request is blocked under a hard limit and
served with a warning under a soft limit, and in neither case is it rerouted to the
default project or to the personal budget, even though the default project is funded.

Observation channel (same as the other budget tests): LiteLLM spend on the project keys
(``codemie:project:<name>:category:<category>``) and on the user's personal customers.

Covers:
    TC-38  Hard limit on a web chat: blocked, the default project is not charged
    TC-39  Hard limit on a CLI request: HTTP 429, the default project is not charged
    TC-40  Soft limit on a web chat: served on the same project, the default project is
           not charged
"""

import logging
from time import sleep

import pytest
from hamcrest import assert_that, contains_string, equal_to, greater_than, is_not

from codemie_test_harness.tests.test_data.budget_test_data import (
    BUDGET_CACHE_DELAY,
    BUDGET_EXCEEDED_MESSAGE,
    BUDGET_EXCEEDED_STATUS,
    CLI_BUDGET_CATEGORIES,
    CLI_CLIENT_HEADER,
    CLI_PROJECT_HEADER,
    DEFAULT_CLI_BUDGET_ID,
    EXHAUSTIBLE_CLI_BUDGET,
    EXHAUSTIBLE_PLATFORM_BUDGET,
    MAX_EXHAUSTING_ATTEMPTS,
    PLATFORM_BUDGET_CATEGORIES,
    SOFT_LIMIT_BUDGET,
    SOFT_LIMIT_PLATFORM_BUDGET,
    budget_chat_prompt,
    budget_chat_prompt_bigger,
    project_key_alias,
)

logger = logging.getLogger(__name__)


# ── TC-38 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1800)
def test_exhausted_hard_limit_is_not_rerouted_to_default_project_on_web(
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user2_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    limited_project = budget_project_factory(EXHAUSTIBLE_PLATFORM_BUDGET, (user2_id,))
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "limited_project": project_key_alias(limited_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}
    assistant = user2_assistant(project_name=limited_project)

    logger.info("Chatting until the hard limit of the member project is used up")
    before = lite_llm_budget_utils.get_spends(keys, customers)
    reply = user2_assistant_utils.ask_until_text_in_reply(
        assistant,
        budget_chat_prompt_bigger,
        BUDGET_EXCEEDED_MESSAGE,
        MAX_EXHAUSTING_ATTEMPTS,
    )

    assert_that(
        reply,
        contains_string(f"codemie:project:{limited_project}:category:platform"),
        "The request must be blocked on the exhausted project",
    )
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"limited_project"}),
        "An exhausted budget must not be rerouted to the default project or to personal",
    )


# ── TC-39 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1800)
def test_exhausted_hard_limit_is_not_rerouted_to_default_project_on_cli(
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user2_proxy_utils,
    default_llm,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    limited_project = budget_project_factory(EXHAUSTIBLE_CLI_BUDGET, (user2_id,))
    default_project = budget_project_factory(CLI_BUDGET_CATEGORIES, (user2_id,))
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "limited_project": project_key_alias(limited_project, "cli"),
        "default_project": project_key_alias(default_project, "cli"),
    }
    customers = {
        "personal": email,
        "personal_cli": f"{email}_{DEFAULT_CLI_BUDGET_ID}",
    }

    logger.info(
        "Sending CLI requests until the hard limit of the member project is used up"
    )
    before = lite_llm_budget_utils.get_spends(keys, customers)
    response = user2_proxy_utils.send_messages_until_status(
        BUDGET_EXCEEDED_STATUS,
        MAX_EXHAUSTING_ATTEMPTS,
        lambda: [{"role": "user", "content": budget_chat_prompt_bigger()}],
        model=default_llm.base_name,
        max_tokens=1500,
        extra_headers={**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: limited_project},
    )

    assert_that(
        response.status_code,
        equal_to(BUDGET_EXCEEDED_STATUS),
        "The request must be blocked on the exhausted project",
    )
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"limited_project"}),
        "An exhausted budget must not be rerouted to the default project or to personal",
    )


# ── TC-40 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1800)
def test_soft_limit_is_not_rerouted_to_default_project(
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user2_assistant,
    user2_assistant_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    limited_project = budget_project_factory(SOFT_LIMIT_PLATFORM_BUDGET, (user2_id,))
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "limited_project": project_key_alias(limited_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}
    assistant = user2_assistant(project_name=limited_project)

    logger.info("Chatting past the soft limit of the member project")
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt_bigger())
    passed_soft_limit = lite_llm_budget_utils.wait_for_key_alias_spending_above(
        keys["limited_project"], SOFT_LIMIT_BUDGET
    )
    assert_that(
        float(passed_soft_limit["spend"]),
        greater_than(SOFT_LIMIT_BUDGET),
        "The first answer must pass the soft limit",
    )
    reply = user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    assert_that(
        reply,
        is_not(contains_string(BUDGET_EXCEEDED_MESSAGE)),
        "A request past the soft limit must still be served",
    )
    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"limited_project"}),
        "A request past the soft limit must stay on the same project",
    )
