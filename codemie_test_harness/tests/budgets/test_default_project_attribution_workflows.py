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

"""E2E budget attribution for workflows.

Observation channel (same as the other budget tests): LiteLLM spend on the project keys
(``codemie:project:<name>:category:<category>``) and on the user's personal customers.
After each run exactly the expected source must have grown.

Covers:
    TC-30  Project workflow run by a member of a funded project, a member of an unfunded
           project and a non-member
    TC-31  Marketplace workflow: charged to the default project, otherwise personal
    TC-32  Workflow node running a saved marketplace assistant: charged as that assistant
    TC-33  Workflow node running a saved assistant of a member project: that project
           (the node workflows run without the result summary step, so the node is their
           only LLM call)
"""

import logging
from time import sleep

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.budget_test_data import (
    BUDGET_CACHE_DELAY,
    BUDGET_WORKFLOW_STATE,
    PLATFORM_BUDGET_CATEGORIES,
    budget_chat_prompt,
    project_key_alias,
)

logger = logging.getLogger(__name__)


# ── TC-30 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1800)
@pytest.mark.parametrize(
    "is_member, project_funded, has_default, expected_charged",
    [
        pytest.param(True, True, False, "workflow_project", id="member_funded"),
        pytest.param(
            True, False, True, "default_project", id="member_unfunded_with_default"
        ),
        pytest.param(
            False, True, True, "default_project", id="non_member_with_default"
        ),
    ],
)
def test_project_workflow_charge_follows_attribution_matrix(
    is_member,
    project_funded,
    has_default,
    expected_charged,
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user1_workflow,
    user2_workflow_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    workflow_project = budget_project_factory(
        PLATFORM_BUDGET_CATEGORIES if project_funded else None,
        (user2_id,) if is_member else (),
    )
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    workflow = user1_workflow(workflow_project)
    if has_default:
        user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "workflow_project": project_key_alias(workflow_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}

    logger.info(
        "Running a project workflow: member=%s, funded=%s, default set=%s, expecting %s",
        is_member,
        project_funded,
        has_default,
        expected_charged,
    )
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_workflow_utils.execute_workflow(
        workflow.id, BUDGET_WORKFLOW_STATE, user_input=budget_chat_prompt()
    )

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({expected_charged}),
        f"Spend must be charged to {expected_charged}",
    )


# ── TC-31 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.marketplace
@pytest.mark.timeout(1800)
@pytest.mark.parametrize(
    "is_member, has_default, expected_charged",
    [
        pytest.param(True, True, "default_project", id="member_with_default"),
        pytest.param(False, True, "default_project", id="non_member_with_default"),
        pytest.param(False, False, "personal", id="non_member_without_default"),
    ],
)
def test_marketplace_workflow_is_charged_to_default_project(
    is_member,
    has_default,
    expected_charged,
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user1_published_workflow,
    user2_workflow_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    workflow_project = budget_project_factory(
        PLATFORM_BUDGET_CATEGORIES, (user2_id,) if is_member else ()
    )
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    workflow = user1_published_workflow(workflow_project)
    if has_default:
        user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "workflow_project": project_key_alias(workflow_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}

    logger.info(
        "Running a marketplace workflow: member=%s, default set=%s, expecting %s",
        is_member,
        has_default,
        expected_charged,
    )
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_workflow_utils.execute_workflow(
        workflow.id, BUDGET_WORKFLOW_STATE, user_input=budget_chat_prompt()
    )

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({expected_charged}),
        f"Spend must be charged to {expected_charged}",
    )


# ── TC-32 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.marketplace
@pytest.mark.timeout(1800)
def test_workflow_node_with_marketplace_assistant_is_charged_to_default_project(
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user1_published_assistant,
    user1_workflow,
    user2_workflow_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    workflow_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    assistant_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, ())
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    assistant = user1_published_assistant(assistant_project)
    workflow = user1_workflow(workflow_project, assistant)
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "workflow_project": project_key_alias(workflow_project),
        "assistant_project": project_key_alias(assistant_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}

    logger.info("Running a workflow whose only node is a marketplace assistant")
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_workflow_utils.execute_workflow(
        workflow.id, BUDGET_WORKFLOW_STATE, user_input=budget_chat_prompt()
    )

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"default_project"}),
        "The node must be charged as the marketplace assistant is, to the default "
        "project, and neither to the workflow's nor to the assistant's project",
    )


# ── TC-33 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1800)
def test_workflow_node_with_member_project_assistant_is_charged_to_that_project(
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user1_assistant,
    user1_workflow,
    user2_workflow_utils,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    workflow_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    assistant_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    assistant = user1_assistant(project_name=assistant_project, shared=True)
    workflow = user1_workflow(workflow_project, assistant)
    user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "workflow_project": project_key_alias(workflow_project),
        "assistant_project": project_key_alias(assistant_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}

    logger.info(
        "Running a workflow whose only node is an assistant of a member project"
    )
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_workflow_utils.execute_workflow(
        workflow.id, BUDGET_WORKFLOW_STATE, user_input=budget_chat_prompt()
    )

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({"assistant_project"}),
        "The node must be charged as the assistant is, to the assistant's project, "
        "and neither to the workflow's project nor to the default project",
    )
