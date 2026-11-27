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


"""Who may change 'enforce_member_spend_limits' through the API.

The Project Admin of a project may change it (the Edit Project screen relies on that); a plain
member of the project, the admin of a different project and a user unrelated to the project may
not: the call is rejected with 403 'Access denied' and the stored value stays as it was. Needs a
stand with real roles (not ENV=local, where every user is a global admin).
"""

import pytest
from hamcrest import assert_that, equal_to, is_
from requests import HTTPError

from codemie_test_harness.tests.ui.test_data.project_enforcement_test_data import (
    ACCESS_DENIED_MESSAGE,
)


def _stored(project_utils, project_name):
    return project_utils.get_project_detail(project_name).enforce_member_spend_limits


# @case project-admin-enforcement-switch-confirmation_TC_012
@pytest.mark.parametrize("new_value", [True, False], ids=["turn on", "turn off"])
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.api
def test_project_admin_changes_enforcement_through_api(
    roles_world, project_utils, new_value
):
    target = roles_world.target
    project_utils.set_enforce_member_spend_limits(target, not new_value)

    response = roles_world.clients["project_admin"].projects.update_project(
        project_name=target, enforce_member_spend_limits=new_value
    )

    assert_that(response.enforce_member_spend_limits, is_(new_value), "update response")
    assert_that(_stored(project_utils, target), is_(new_value), "stored value")


# @case project-admin-enforcement-switch-confirmation_TC_012
@pytest.mark.parametrize("caller", ["member", "other_project_admin", "unrelated_user"])
@pytest.mark.parametrize("new_value", [True, False], ids=["turn on", "turn off"])
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.api
def test_caller_without_rights_cannot_change_enforcement_through_api(
    roles_world, project_utils, caller, new_value
):
    target = roles_world.target
    project_utils.set_enforce_member_spend_limits(target, not new_value)

    with pytest.raises(HTTPError) as rejected:
        roles_world.clients[caller].projects.update_project(
            project_name=target, enforce_member_spend_limits=new_value
        )

    assert_that(
        rejected.value.response.status_code,
        equal_to(403),
        "the change is rejected with a permission error",
    )
    assert_that(
        rejected.value.response.json()["error"]["message"],
        equal_to(ACCESS_DENIED_MESSAGE),
        "the rejection names the missing access",
    )
    assert_that(
        _stored(project_utils, target), is_(not new_value), "nothing was changed"
    )
