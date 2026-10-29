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

"""API tests for the validation of ServiceNow budget requests.

The tests of amounts share one project with a platform budget: a refused request must leave
that budget exactly as it was, so the project is never changed by a passing test.
"""

import pytest
from hamcrest import assert_that, equal_to, none
from requests import HTTPError

from codemie_test_harness.tests.test_data.servicenow_project_budget_test_data import (
    ADJUST,
    INVALID_BUDGET_PAYLOADS,
    INVALID_FIELD_OVERRIDES,
    PLATFORM_MUST_BE_POSITIVE_MESSAGE,
    PLATFORM_ONLY_GROUP,
    budget_request,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.servicenow_budget_utils import (
    amounts_close_to,
    error_body,
    group_amounts,
)


def assert_budget_unchanged(servicenow_budget_utils, project):
    groups = servicenow_budget_utils.active_budget_groups(project.name)
    assert_that(
        [group["group_id"] for group in groups],
        equal_to([project.group_id]),
        "A refused request must leave the project with its original budget group",
    )
    assert_that(
        group_amounts(groups[0]),
        amounts_close_to(
            {
                category: spec["max_budget"]
                for category, spec in PLATFORM_ONLY_GROUP.items()
            }
        ),
        "A refused request must not change the budget amounts",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.parametrize("payload", INVALID_BUDGET_PAYLOADS)
def test_invalid_budget_amounts_are_rejected_with_422_and_leave_budget_unchanged(
    servicenow_account, servicenow_budget_utils, validation_budget_project, payload
):
    # @case servicenow-project-budget-integration-api_TC_009
    request = budget_request(
        payload.action,
        codemie_project_name=validation_budget_project.name,
        amounts=payload.amounts,
    )

    with pytest.raises(HTTPError) as exc_info:
        servicenow_account.integration.submit_budget_request(request)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(422),
        "Invalid amounts must be refused as invalid input, not fail the server",
    )
    assert_budget_unchanged(servicenow_budget_utils, validation_budget_project)


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_adjust_leaving_platform_at_zero_returns_400_and_keeps_budget(
    servicenow_account, servicenow_budget_utils, validation_budget_project
):
    # @case servicenow-project-budget-integration-api_TC_009
    request = budget_request(
        ADJUST,
        codemie_project_name=validation_budget_project.name,
        amounts={"platform": 0.0},
    )

    with pytest.raises(HTTPError) as exc_info:
        servicenow_account.integration.submit_budget_request(request)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "An adjust that would leave platform at 0 must be refused",
    )
    assert_that(
        error_body(exc_info)["message"],
        equal_to(PLATFORM_MUST_BE_POSITIVE_MESSAGE),
        "The refusal must say the platform budget has to stay above 0",
    )
    assert_budget_unchanged(servicenow_budget_utils, validation_budget_project)


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.parametrize("overrides", INVALID_FIELD_OVERRIDES)
def test_invalid_request_fields_are_rejected_with_422_and_create_nothing(
    servicenow_account, servicenow_budget_utils, servicenow_cleanup, overrides
):
    # @case servicenow-project-budget-integration-api_TC_015
    project_name = servicenow_cleanup.track_project(get_random_name())
    request = budget_request(**{"codemie_project_name": project_name, **overrides})

    with pytest.raises(HTTPError) as exc_info:
        servicenow_account.integration.submit_budget_request(request)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(422),
        "A request with an invalid field must be refused as invalid input",
    )
    assert_that(
        servicenow_budget_utils.find_project(project_name),
        none(),
        "A request refused as invalid must not create the project",
    )
