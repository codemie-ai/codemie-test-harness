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

"""Provisioning API: requests the backend refuses, and that a refusal changes nothing."""

import pytest
from hamcrest import assert_that, equal_to, is_
from requests import HTTPError

from codemie_sdk.models.provisioning import ProvisioningProjectBlock
from codemie_test_harness.cli.constants import PROVISIONING_FULL_CLIENT_KEYS
from codemie_test_harness.tests.test_data.budget_test_data import (
    PLATFORM_BUDGET_CATEGORIES,
)
from codemie_test_harness.tests.test_data.provisioning_test_data import (
    MALFORMED_SET_ROWS,
    REJECTED_NAME_ROWS,
    WRITE_CALLS,
    budget_request,
    change_reference,
)


@pytest.mark.parametrize("call", WRITE_CALLS)
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_write_call_without_change_reference_is_rejected_with_422(
    provisioning_full, provisioning_utils, call
):
    # @case provisioning-api-for-third-party_TC_007
    project_name = provisioning_utils.create_project(PLATFORM_BUDGET_CATEGORIES)
    state_before = provisioning_utils.state(project_name)

    with pytest.raises(HTTPError) as error:
        call(provisioning_full, project_name, None)

    assert_that(error.value.response.status_code, equal_to(422))
    assert_that(
        provisioning_utils.state(project_name),
        equal_to(state_before),
        "the rejected call left the budget unchanged",
    )


@pytest.mark.parametrize("names", REJECTED_NAME_ROWS)
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_with_invalid_name_is_rejected_with_400_and_creates_nothing(
    provisioning_full, provisioning_utils, names
):
    # @case provisioning-api-for-third-party_TC_009
    project_name = provisioning_utils.track_project(names.project_name())
    cost_center = provisioning_utils.track_cost_center(names.cost_center())

    with pytest.raises(HTTPError) as error:
        provisioning_full.set_budget(
            project_name,
            change_reference(),
            budget_request(
                {"platform": 100.0}, ProvisioningProjectBlock(cost_center=cost_center)
            ),
        )

    assert_that(error.value.response.status_code, equal_to(400))
    assert_that(provisioning_utils.project_exists(project_name), is_(False))
    assert_that(provisioning_utils.cost_center_exists(cost_center), is_(False))


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_naming_deleted_cost_center_is_rejected_with_409(
    provisioning_full, provisioning_utils, cost_center, cost_center_utils
):
    # @case provisioning-api-for-third-party_TC_009
    cost_center_name = provisioning_utils.new_cost_center_name()
    cost_center_utils.delete_cost_center(cost_center(name=cost_center_name))
    project_name = provisioning_utils.new_project_name()

    with pytest.raises(HTTPError) as error:
        provisioning_full.set_budget(
            project_name,
            change_reference(),
            budget_request(
                {"platform": 100.0},
                ProvisioningProjectBlock(cost_center=cost_center_name),
            ),
        )

    assert_that(error.value.response.status_code, equal_to(409))
    assert_that(provisioning_utils.project_exists(project_name), is_(False))


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_for_personal_project_is_rejected_with_403(
    provisioning_full, platform_user, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_009
    personal_project = platform_user.email
    state_before = provisioning_utils.state(personal_project)
    assert_that(
        state_before.exists,
        is_(True),
        "the personal project is visible to the state check, so the comparison below can fail",
    )

    with pytest.raises(HTTPError) as error:
        provisioning_full.set_budget(
            personal_project, change_reference(), budget_request({"platform": 100.0})
        )

    assert_that(error.value.response.status_code, equal_to(403))
    assert_that(
        provisioning_utils.state(personal_project),
        equal_to(state_before),
        "the personal project was not modified",
    )


@pytest.mark.parametrize("malformed", MALFORMED_SET_ROWS)
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_with_malformed_request_is_rejected_with_422(
    provisioning_full, provisioning_utils, malformed
):
    # @case provisioning-api-for-third-party_TC_025
    project_name = malformed.rename(provisioning_utils.new_project_name())

    with pytest.raises(HTTPError) as error:
        provisioning_full.set_budget(
            project_name, change_reference(), malformed.request
        )

    assert_that(error.value.response.status_code, equal_to(422))
    assert_that(
        provisioning_utils.project_exists(project_name),
        is_(False),
        "the rejected request created nothing",
    )
