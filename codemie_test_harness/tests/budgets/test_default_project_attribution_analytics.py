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

"""E2E check of the analytics of a charged request.

The project the analytics show for a request is the project whose budget was charged,
not the project the asset belongs to.

Covers:
    TC-41  A marketplace assistant of a project the user is not a member of: the analytics
           show the default project, or the personal project when there is no default
"""

import logging
from time import sleep

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.budget_test_data import (
    BUDGET_CACHE_DELAY,
    PLATFORM_BUDGET_CATEGORIES,
    budget_chat_prompt,
)

logger = logging.getLogger(__name__)


# ── TC-41 ──────────────────────────────────────────────────────────────────────


@pytest.mark.budget
@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.marketplace
@pytest.mark.timeout(1800)
@pytest.mark.parametrize(
    "has_default, expected_charged",
    [
        pytest.param(True, "default_project", id="with_default"),
        pytest.param(False, "personal", id="without_default"),
    ],
)
def test_analytics_shows_the_project_that_was_charged(
    has_default,
    expected_charged,
    keycloak_user_2,
    user2_id,
    user_utils,
    budget_project_factory,
    user1_published_assistant,
    user2_assistant_utils,
    analytics_utils,
):
    email, _ = keycloak_user_2
    assistant_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, ())
    default_project = budget_project_factory(PLATFORM_BUDGET_CATEGORIES, (user2_id,))
    assistant = user1_published_assistant(assistant_project)
    if has_default:
        user_utils.set_default_project(user2_id, default_project)
    sleep(BUDGET_CACHE_DELAY)
    charged_projects = {"default_project": default_project, "personal": email}
    charged_project = charged_projects[expected_charged]

    logger.info(
        "Asking a marketplace assistant as a non-member: default set=%s, expecting %s",
        has_default,
        charged_project,
    )
    user2_assistant_utils.ask_assistant(assistant, budget_chat_prompt())

    assert_that(
        analytics_utils.wait_for_projects_with_spend(
            [assistant_project, default_project, email], charged_project, user2_id
        ),
        equal_to({charged_project}),
        "The analytics must show only the project whose budget was charged",
    )
