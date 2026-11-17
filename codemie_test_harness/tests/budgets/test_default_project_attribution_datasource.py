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

"""E2E budget attribution for datasource indexing.

Observation channel (same as the other budget tests): LiteLLM spend on the project keys
(``codemie:project:<name>:category:<category>``) and on the user's personal customers.
After the indexing exactly the expected source must have grown.

Covers:
    TC-35  Indexing started by a member of a funded project, and by an admin who is not a
           member of the datasource's project
"""

import logging
from time import sleep

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.budget_test_data import (
    BUDGET_CACHE_DELAY,
    PLATFORM_BUDGET_CATEGORIES,
    project_key_alias,
)

logger = logging.getLogger(__name__)


# ── TC-35 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1800)
@pytest.mark.parametrize(
    "is_member, has_default, expected_charged",
    [
        pytest.param(True, False, "datasource_project", id="member_funded"),
        pytest.param(False, True, "default_project", id="non_member_with_default"),
    ],
)
def test_datasource_indexing_charge_follows_attribution_matrix(
    is_member,
    has_default,
    expected_charged,
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user2_file_datasource,
    lite_llm_budget_utils,
):
    email, _ = keycloak_user_2
    datasource_project = budget_project_factory(
        PLATFORM_BUDGET_CATEGORIES, (user2_id,) if is_member else ()
    )
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    if has_default:
        user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    keys = {
        "datasource_project": project_key_alias(datasource_project),
        "default_project": project_key_alias(default_project),
    }
    customers = {"personal": email}

    logger.info(
        "Indexing a file datasource: member=%s, default set=%s, expecting %s",
        is_member,
        has_default,
        expected_charged,
    )
    before = lite_llm_budget_utils.get_spends(keys, customers)
    user2_file_datasource(datasource_project)

    assert_that(
        lite_llm_budget_utils.wait_for_charged_sources(before, keys, customers),
        equal_to({expected_charged}),
        f"Spend must be charged to {expected_charged}",
    )
