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

"""Provisioning API: cancelling a project budget (DELETE /v1/provisioning/projects/{name}/budget)."""

import pytest
from hamcrest import assert_that, equal_to, is_, none
from requests import HTTPError

from codemie_test_harness.cli.constants import PROVISIONING_FULL_CLIENT_KEYS
from codemie_test_harness.tests.test_data.provisioning_test_data import (
    CANCEL_EXISTING_PROJECT_ROWS,
    change_reference,
)


@pytest.mark.parametrize("setup_project", CANCEL_EXISTING_PROJECT_ROWS)
@pytest.mark.budget
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_cancel_budget_answers_204_and_leaves_no_budget(
    provisioning_full, provisioning_utils, setup_project
):
    # @case provisioning-api-for-third-party_TC_005
    project_name = setup_project(provisioning_utils)

    result = provisioning_full.cancel_budget(project_name, change_reference())

    assert_that(result.status_code, equal_to(204), "cancel answers 204")
    assert_that(result.budget, none(), "cancel has no body")
    assert_that(provisioning_utils.project_exists(project_name), is_(True))
    assert_that(
        provisioning_utils.active_budget_group(project_name),
        none(),
        "the project has no budget after the cancel",
    )


@pytest.mark.budget
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_cancel_budget_of_missing_project_answers_404_and_creates_nothing(
    provisioning_full, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_005
    project_name = provisioning_utils.new_project_name()

    with pytest.raises(HTTPError) as error:
        provisioning_full.cancel_budget(project_name, change_reference())

    assert_that(error.value.response.status_code, equal_to(404))
    assert_that(
        provisioning_utils.project_exists(project_name),
        is_(False),
        "the cancel did not create the project",
    )
