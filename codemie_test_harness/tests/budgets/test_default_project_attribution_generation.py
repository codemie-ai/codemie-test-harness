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

"""E2E budget attribution for AI generation and refinement requests.

These requests create no entity, so they are billed to no asset: the default project
pays, or the personal budget when there is no default.

Observation channel (same as the other budget tests): LiteLLM spend on the project keys
(``codemie:project:<name>:category:<category>``) and on the user's personal customers.
After each request exactly the expected source must have grown.

Covers:
    TC-36  Assistant generation, assistant prompt generation, assistant refinement,
           skill generation and skill refinement
"""

import logging
from time import sleep

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.budget_test_data import (
    BUDGET_CACHE_DELAY,
    GENERATION_REQUEST_NAMES,
    PLATFORM_BUDGET_CATEGORIES,
    project_key_alias,
)

logger = logging.getLogger(__name__)


# ── TC-36 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1500)
@pytest.mark.parametrize("request_name", GENERATION_REQUEST_NAMES)
@pytest.mark.parametrize(
    "has_default, expected_charged",
    [
        pytest.param(True, "default_project", id="with_default"),
        pytest.param(False, "personal", id="without_default"),
    ],
)
def test_ai_generation_is_charged_to_default_project(
    request_name,
    has_default,
    expected_charged,
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user2_generation_requests,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    other_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    if has_default:
        user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "default_project": project_key_alias(default_project),
        "other_project": project_key_alias(other_project),
    }
    customers = {"personal": email}

    logger.info(
        "Sending %s: default set=%s, expecting %s",
        request_name,
        has_default,
        expected_charged,
    )
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_generation_requests[request_name]()

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({expected_charged}),
        f"Spend must be charged to {expected_charged}, as no entity is involved",
    )
