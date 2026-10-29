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

"""API tests for the personal project budget guard.

Covers:
    TC-002  a maintainer's attempt to create a budget for their own personal project is
            rejected with 403 "Cannot create a budget for a personal project"

The maintainer is a user with the maintainer flag only; their personal project is named
after their email and is created together with the user.
"""

import pytest
from hamcrest import assert_that, contains_string, empty, equal_to
from requests import HTTPError

from codemie_test_harness.tests.test_data.personal_project_budget_test_data import (
    PERSONAL_PROJECT_BUDGET_MESSAGE,
    PERSONAL_PROJECT_TYPE,
)
from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)


@pytest.mark.project
@pytest.mark.api
def test_maintainer_create_budget_for_personal_project_returns_403(
    client, project_utils, maintainer_credentials, maintainer_client
):
    """
    project is rejected with 403 and the guard message, and no budget group is left behind.
    """
    personal_project, _ = maintainer_credentials
    assert_that(
        project_utils.get_project_detail(personal_project).project_type,
        equal_to(PERSONAL_PROJECT_TYPE),
        "Precondition: the maintainer's own project must be personal",
    )

    with pytest.raises(HTTPError) as exc_info:
        AdminProjectBudgetGroupUtils(maintainer_client).create_budget_group(
            personal_project
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        "Personal project budget create must be forbidden (404 would mean a missing project)",
    )
    assert_that(
        exc_info.value.response.json()["error"]["message"],
        contains_string(PERSONAL_PROJECT_BUDGET_MESSAGE),
        "Personal project budget rejection message",
    )
    assert_that(
        AdminProjectBudgetGroupUtils(client).list_by_project(personal_project),
        empty(),
        "A rejected create must not leave a budget group on the personal project",
    )
