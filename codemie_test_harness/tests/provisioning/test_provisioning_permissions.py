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

"""Provisioning API: which callers may use which route."""

import pytest
from hamcrest import assert_that, contains_string, equal_to, is_
from requests import HTTPError

from codemie_test_harness.cli.constants import (
    PROVISIONING_BUDGETS_CLIENT_KEYS,
    PROVISIONING_FULL_CLIENT_KEYS,
    PROVISIONING_READ_CLIENT_KEYS,
)
from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.test_data.budget_test_data import (
    PLATFORM_BUDGET_CATEGORIES,
)
from codemie_test_harness.tests.test_data.provisioning_test_data import (
    BUDGET_ONLY_ALLOWED_ROWS,
    BUDGET_ONLY_COST_CENTER,
    BUDGET_ONLY_FORBIDDEN_ROWS,
    CLIENT_LOCKED_MESSAGE,
    LOCKED_OUT_ROWS,
    MISSING_PERMISSION_ROWS,
    NON_REGISTERED_ROWS,
    change_reference,
)
from codemie_test_harness.tests.utils.user_utils import UserUtils


@pytest.mark.parametrize(("call", "expected_status"), BUDGET_ONLY_ALLOWED_ROWS)
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_BUDGETS_CLIENT_KEYS)
@pytest.mark.api
def test_budget_only_client_manages_budget_of_existing_project(
    provisioning_budgets, provisioning_utils, call, expected_status
):
    # @case provisioning-api-for-third-party_TC_015
    project_name = provisioning_utils.create_project(PLATFORM_BUDGET_CATEGORIES)

    result = call(provisioning_budgets, project_name, change_reference())

    assert_that(result.status_code, equal_to(expected_status))


@pytest.mark.parametrize(("setup_project", "call"), BUDGET_ONLY_FORBIDDEN_ROWS)
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_BUDGETS_CLIENT_KEYS)
@pytest.mark.api
def test_budget_only_client_cannot_create_project_or_send_cost_center_or_admins(
    provisioning_budgets, provisioning_utils, setup_project, call
):
    # @case provisioning-api-for-third-party_TC_016
    project_name = setup_project(provisioning_utils)
    provisioning_utils.track_cost_center(BUDGET_ONLY_COST_CENTER)
    state_before = provisioning_utils.state(project_name)

    with pytest.raises(HTTPError) as error:
        call(provisioning_budgets, project_name, change_reference())

    assert_that(error.value.response.status_code, equal_to(403))
    assert_that(
        provisioning_utils.state(project_name),
        equal_to(state_before),
        "the refused call changed nothing on the project",
    )
    assert_that(
        provisioning_utils.cost_center_exists(BUDGET_ONLY_COST_CENTER),
        is_(False),
        "the refused call did not create the cost center",
    )


@pytest.mark.parametrize(
    ("service_fixture", "call", "permission"), MISSING_PERMISSION_ROWS
)
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(
    *PROVISIONING_FULL_CLIENT_KEYS, *PROVISIONING_READ_CLIENT_KEYS
)
@pytest.mark.api
def test_client_without_the_needed_permission_gets_403(
    request, provisioning_utils, service_fixture, call, permission
):
    # @case provisioning-api-for-third-party_TC_017
    service = request.getfixturevalue(service_fixture)
    project_name = provisioning_utils.new_project_name()

    with pytest.raises(HTTPError) as error:
        call(service, project_name, change_reference())

    assert_that(error.value.response.status_code, equal_to(403))
    assert_that(
        UserUtils.error_text(error.value),
        contains_string(f"does not hold the permission {permission}"),
    )
    assert_that(provisioning_utils.project_exists(project_name), is_(False))


@pytest.mark.parametrize("call_outside_provisioning", LOCKED_OUT_ROWS)
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_registered_client_is_refused_outside_the_provisioning_api(
    provisioning_full_token, call_outside_provisioning
):
    # @case provisioning-api-for-third-party_TC_018
    with pytest.raises(HTTPError) as error:
        call_outside_provisioning(API_DOMAIN, provisioning_full_token, VERIFY_SSL)

    assert_that(error.value.response.status_code, equal_to(403))
    assert_that(
        UserUtils.error_text(error.value), contains_string(CLIENT_LOCKED_MESSAGE)
    )


@pytest.mark.parametrize(("caller_fixture", "call"), NON_REGISTERED_ROWS)
@pytest.mark.budget
@pytest.mark.enterprise
# A configured client login marks a stand prepared for the provisioning API (it is mounted only when enabled).
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_non_registered_callers_including_admins_get_403_on_provisioning_routes(
    request, provisioning_utils, caller_fixture, call
):
    # @case provisioning-api-for-third-party_TC_019
    caller = request.getfixturevalue(caller_fixture)
    project_name = provisioning_utils.new_project_name()

    with pytest.raises(HTTPError) as error:
        call(caller.provisioning, project_name, change_reference())

    assert_that(error.value.response.status_code, equal_to(403))
    assert_that(
        provisioning_utils.project_exists(project_name),
        is_(False),
        "the refused call created no project",
    )
