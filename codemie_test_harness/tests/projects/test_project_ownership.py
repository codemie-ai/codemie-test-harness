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

"""API tests for project ownership transfer.

Covers PUT /v1/projects/{projectName}/ownership:
    TC-003  the new owner is returned and persisted
    TC-004  an unauthorized caller is rejected with 404 "Project not found"
    TC-005  existing members, their roles and the previous owner's membership survive
    TC-006  a new owner who is not a member is added as project admin
    TC-007  a missing target user is rejected with 404
    TC-008  a personal project is rejected with 403

The activity event of a transfer (TC-009) is covered in tests/activity.

`ownership_project` hands ownership back on teardown, so every user fixture a test needs
is requested before it (users must still exist when the project is cleaned up).
"""

import pytest
from hamcrest import (
    assert_that,
    contains_inanyorder,
    contains_string,
    equal_to,
    has_item,
    has_properties,
    is_not,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.project_ownership_test_data import (
    PERSONAL_PROJECT_UPDATE_MESSAGE,
    PROJECT_NOT_FOUND_MESSAGE,
    get_nonexistent_user_id,
    get_transfer_message,
)
from codemie_test_harness.tests.utils.project_utils import ProjectUtils


def _member_roles(project_utils, project_name):
    """(user_id, is_project_admin) of every member, read from project detail."""
    return [
        (member.user_id, member.is_project_admin)
        for member in project_utils.get_project_detail(project_name).members
    ]


@pytest.mark.project
@pytest.mark.api
def test_transfer_ownership_persists_new_owner(
    project_utils, non_admin_user, ownership_project
):
    """
    detail, read in a separate request, reports the same owner.
    """
    _, new_owner_id, _ = non_admin_user

    response = project_utils.transfer_ownership(ownership_project.name, new_owner_id)

    assert_that(response.name, equal_to(ownership_project.name), "Project name")
    assert_that(
        response.created_by, equal_to(new_owner_id), "Response must name the new owner"
    )
    assert_that(
        response.message,
        equal_to(get_transfer_message(ownership_project.name, new_owner_id)),
        "Transfer message",
    )
    assert_that(
        project_utils.get_project_detail(ownership_project.name).created_by,
        equal_to(new_owner_id),
        "The new owner must be persisted",
    )


@pytest.mark.project
@pytest.mark.api
def test_transfer_ownership_by_unauthorized_user_returns_404(
    project_utils, non_admin_user, ownership_project
):
    """
    does not exist (existence hiding) and the owner stays unchanged.
    """
    _, member_id, member_client = non_admin_user

    with pytest.raises(HTTPError) as exc_info:
        ProjectUtils(member_client).transfer_ownership(
            ownership_project.name, member_id
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Unauthorized caller must get 404, not 403",
    )
    assert_that(
        exc_info.value.response.json()["error"]["message"],
        equal_to(PROJECT_NOT_FOUND_MESSAGE),
        "Unauthorized caller must get the project-not-found message",
    )
    assert_that(
        project_utils.get_project_detail(ownership_project.name).created_by,
        equal_to(ownership_project.created_by),
        "A rejected transfer must not change the owner",
    )


@pytest.mark.project
@pytest.mark.api
def test_transfer_ownership_keeps_members_and_previous_owner(
    project_utils, non_admin_user, extra_platform_user, ownership_project
):
    """
    removed, every role is unchanged and the previous owner stays a project member.
    """
    _, admin_member_id, _ = non_admin_user
    _, plain_member_id = extra_platform_user
    project_utils.assign_user_to_project(
        ownership_project.name, admin_member_id, is_project_admin=True
    )
    project_utils.assign_user_to_project(
        ownership_project.name, plain_member_id, is_project_admin=False
    )
    before = _member_roles(project_utils, ownership_project.name)
    assert_that(
        before,
        has_item((ownership_project.created_by, True)),
        "Setup: the creator must be a project admin before the transfer",
    )
    assert_that(
        before,
        has_item((plain_member_id, False)),
        "Setup: the new owner must be a plain member before the transfer",
    )

    project_utils.transfer_ownership(ownership_project.name, plain_member_id)

    assert_that(
        project_utils.get_project_detail(ownership_project.name).created_by,
        equal_to(plain_member_id),
        "The transfer must have taken effect",
    )
    assert_that(
        _member_roles(project_utils, ownership_project.name),
        contains_inanyorder(*before),
        "Members, their roles and the previous owner's membership must be unchanged",
    )


@pytest.mark.project
@pytest.mark.api
def test_transfer_ownership_to_non_member_adds_new_owner_as_project_admin(
    project_utils, non_admin_user, ownership_project
):
    """
    as a project admin.
    """
    _, new_owner_id, _ = non_admin_user
    assert_that(
        [
            m.user_id
            for m in project_utils.get_project_detail(ownership_project.name).members
        ],
        is_not(has_item(new_owner_id)),
        "Setup: the new owner must not be a member yet",
    )

    project_utils.transfer_ownership(ownership_project.name, new_owner_id)

    assert_that(
        project_utils.get_project_detail(ownership_project.name).members,
        has_item(has_properties(user_id=new_owner_id, is_project_admin=True)),
        "The new owner must be listed as project admin",
    )


@pytest.mark.project
@pytest.mark.api
def test_transfer_ownership_to_missing_user_returns_404(
    project_utils, ownership_project
):
    """
    404 and the owner stays unchanged.
    """
    with pytest.raises(HTTPError) as exc_info:
        project_utils.transfer_ownership(
            ownership_project.name, get_nonexistent_user_id()
        )

    assert_that(
        exc_info.value.response.status_code, equal_to(404), "Missing target user"
    )
    assert_that(
        exc_info.value.response.json()["error"]["message"],
        equal_to(PROJECT_NOT_FOUND_MESSAGE),
        "Missing target user gets the generic project-not-found message",
    )
    assert_that(
        project_utils.get_project_detail(ownership_project.name).created_by,
        equal_to(ownership_project.created_by),
        "A rejected transfer must not change the owner",
    )


@pytest.mark.project
@pytest.mark.api
def test_transfer_ownership_of_personal_project_returns_403(
    project_utils, non_admin_user
):
    """
    request is rejected with 403 and the owner stays unchanged.
    """
    email, member_id, _ = non_admin_user
    owner_before = project_utils.get_project_detail(email).created_by

    with pytest.raises(HTTPError) as exc_info:
        project_utils.transfer_ownership(email, member_id)

    assert_that(exc_info.value.response.status_code, equal_to(403), "Personal project")
    assert_that(
        exc_info.value.response.json()["error"]["message"],
        contains_string(PERSONAL_PROJECT_UPDATE_MESSAGE),
        "Personal project rejection message",
    )
    assert_that(
        project_utils.get_project_detail(email).created_by,
        equal_to(owner_before),
        "A rejected transfer must not change the owner",
    )
