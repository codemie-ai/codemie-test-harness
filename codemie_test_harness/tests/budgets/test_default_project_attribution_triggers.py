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

"""E2E budget attribution for webhook and scheduled triggers.

A trigger runs as the user who owns it, with that user's real project memberships and
default project, exactly as if the owner had run the assistant interactively.

Observation channel (same as the other budget tests): LiteLLM spend on the project keys
(``codemie:project:<name>:category:<category>``) and on the user's personal customers.
After each run exactly the expected source must have grown.

Covers:
    TC-37  A webhook and a scheduler of a user with a funded default project run a
           marketplace assistant of a project the user is not a member of (a trigger
           belongs to the project of its assistant): the owner's default project pays
    TC-43  The same triggers run an assistant of a funded project the owner is a member of:
           that project pays, which only happens when the owner's memberships are known
"""

import logging
from time import sleep

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.budget_test_data import (
    BUDGET_CACHE_DELAY,
    PLATFORM_BUDGET_CATEGORIES,
    SCHEDULED_RUN_CHARGE_TIMEOUT,
    project_key_alias,
)

logger = logging.getLogger(__name__)


# ── TC-37 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.marketplace
@pytest.mark.timeout(1800)
@pytest.mark.parametrize("trigger_name", ["webhook", "scheduler"])
def test_trigger_run_is_charged_as_owner(
    trigger_name,
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user1_published_assistant,
    user2_trigger,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    assistant_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, ())
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    assistant = user1_published_assistant(assistant_project)
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "assistant_project": project_key_alias(assistant_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}

    logger.info("Running a marketplace assistant from a %s of its owner", trigger_name)
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_trigger[trigger_name](assistant_project, assistant)

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(
            before, keys, customers, timeout=SCHEDULED_RUN_CHARGE_TIMEOUT
        ),
        equal_to({"default_project"}),
        "A trigger must be charged as its owner would be, to the owner's default "
        "project, never to the assistant's project",
    )


# ── TC-43 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1800)
@pytest.mark.parametrize("trigger_name", ["webhook", "scheduler"])
def test_trigger_run_uses_the_owners_project_membership(
    trigger_name,
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user1_assistant,
    user2_trigger,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    assistant_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    assistant = user1_assistant(project_name=assistant_project, shared=True)
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "assistant_project": project_key_alias(assistant_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}

    logger.info(
        "Running an assistant of the owner's member project from a %s", trigger_name
    )
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_trigger[trigger_name](assistant_project, assistant)

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(
            before, keys, customers, timeout=SCHEDULED_RUN_CHARGE_TIMEOUT
        ),
        equal_to({"assistant_project"}),
        "A trigger must use the owner's project memberships: a run without them would be "
        "charged to the default project instead",
    )
