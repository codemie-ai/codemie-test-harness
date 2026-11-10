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

"""Provisioning API: what a registered client's own account looks like after its calls."""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.cli.constants import PROVISIONING_FULL_CLIENT_KEYS
from codemie_test_harness.tests.test_data.provisioning_test_data import (
    budget_request,
    change_reference,
)


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_registered_client_gets_no_personal_project_from_its_calls(
    provisioning_full,
    provisioning_client_id,
    provisioning_client_user_id,
    non_admin_user,
    provisioning_utils,
):
    # @case provisioning-api-for-third-party_TC_028
    member_email, member_id, _ = non_admin_user
    assert_that(
        provisioning_utils.personal_projects(member_id, member_email),
        equal_to([member_email]),
        "the check sees the personal project of an ordinary user",
    )
    project_name = provisioning_utils.new_project_name()

    provisioning_full.set_budget(
        project_name, change_reference(), budget_request({"platform": 100.0})
    )

    assert_that(
        provisioning_utils.personal_projects(
            provisioning_client_user_id, provisioning_client_id
        ),
        equal_to([]),
        "the client has no personal project after its calls",
    )

    provisioning_full.adjust_budget(
        project_name, change_reference(), budget_request({"platform": 110.0})
    )

    assert_that(
        provisioning_utils.personal_projects(
            provisioning_client_user_id, provisioning_client_id
        ),
        equal_to([]),
        "none appears after one more call",
    )
