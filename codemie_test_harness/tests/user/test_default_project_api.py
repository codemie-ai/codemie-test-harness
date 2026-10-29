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

"""API tests for the per-user default project (foundation).

Without a stored default the backend REPORTS the personal project (else the first
project by name) as the default everywhere; the fallback is never persisted. So "no default" in
these tests means "the personal project is reported", and exactly one project is always marked.

Covers:
    TC-01  Set default on a member project; exactly one default; repeat call is idempotent
    TC-02  Switching the default replaces the previous one, which stays an ordinary membership
    TC-03  The personal project can be the default
    TC-04  Setting a default for a non-member / unknown project is rejected (404)
    TC-05  Removing the default membership falls back to the reported (personal) default
    TC-06  Bulk-removing the default membership falls back to the reported (personal) default
    TC-07  Removing a non-default membership keeps the default
    TC-08  Clearing a default; clearing a non-default is a no-op; clearing a non-member is 404
    TC-09  Admin and maintainer can set and clear the default
    TC-10  Project admin, auditor and plain user cannot set or clear the default
    TC-11  Auditor can read default-project markers
    TC-12  Admin user detail and users list expose the marker per project
    TC-13  The member's own profile shows the default and follows its changes
    TC-14  The user's project list keeps its order when defaults change
    TC-15  Defaults of different users in the same project are independent
    TC-16  A new default can be set after the previous default membership was removed
    TC-17  Setting a default for an unknown user is rejected (404)
"""

import pytest
from hamcrest import (
    assert_that,
    contains_exactly,
    equal_to,
    has_item,
    is_in,
    not_,
)

from codemie_test_harness.tests.utils.user_utils import UserUtils


@pytest.mark.user
@pytest.mark.api
@pytest.mark.smoke
def test_set_default_project_marks_exactly_one_default(
    user_utils, default_project_member
):
    """TC-01: setting a default marks that project only; repeating the call changes nothing."""
    member = default_project_member
    memberships_before = sorted(user_utils.get_user_project_names(member.user_id))

    user_utils.set_default_project(member.user_id, member.project_a)
    user_utils.set_default_project(member.user_id, member.project_a)

    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_a),
        "Exactly the selected project must be the user's default",
    )
    assert_that(
        sorted(user_utils.get_user_project_names(member.user_id)),
        equal_to(memberships_before),
        "Setting a default must not change memberships",
    )


@pytest.mark.user
@pytest.mark.api
def test_switching_default_project_replaces_previous_default(
    user_utils, default_project_member
):
    """TC-02: the new default replaces the old one; the old one stays an ordinary membership."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)

    user_utils.set_default_project(member.user_id, member.project_b)

    projects = {p.project_name: p for p in user_utils.get_user_projects(member.user_id)}
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_b),
        "The user must have exactly one default, the newly selected project",
    )
    assert_that(
        member.project_a,
        is_in(projects),
        "The previous default must remain a membership",
    )
    assert_that(
        projects[member.project_a].is_default,
        equal_to(False),
        "The previous default must lose the default flag",
    )


@pytest.mark.user
@pytest.mark.api
def test_personal_project_can_be_set_as_default(user_utils, default_project_member):
    """TC-03: the user's own personal project is a valid explicit default."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)

    user_utils.set_default_project(member.user_id, member.personal_project)

    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.personal_project),
        "The personal project must be accepted as the default",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.parametrize("case", ["non_member_project", "unknown_project"])
def test_set_default_project_rejected_for_invalid_project(
    request, user_utils, default_project_member, case
):
    """TC-04: a default that is not one of the user's memberships is rejected and nothing changes."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)
    if case == "non_member_project":
        project = request.getfixturevalue("temp_project")
    else:
        project = "autotest-unknown-project"

    status_code = user_utils.set_default_project_status_code(member.user_id, project)

    assert_that(status_code, equal_to(404), f"Request must be rejected ({case})")
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_a),
        "A rejected request must leave the existing default untouched",
    )


@pytest.mark.user
@pytest.mark.api
def test_removing_default_membership_falls_back_to_personal_project(
    user_utils, default_project_member
):
    """TC-05: deleting the membership that is the default falls back to the reported default."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)

    user_utils.remove_user_from_project(member.user_id, member.project_a)

    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.personal_project),
        "Without a stored default the personal project is reported as the default",
    )


@pytest.mark.user
@pytest.mark.api
def test_bulk_removing_default_membership_falls_back_to_personal_project(
    user_utils, project_utils, default_project_member
):
    """TC-06: bulk removal of the default membership also falls back to the reported default."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)

    project_utils.bulk_remove_users_from_project(member.project_a, [member.user_id])

    assert_that(
        user_utils.get_user_project_names(member.user_id),
        not_(has_item(member.project_a)),
        "The user must be removed from the project",
    )
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.personal_project),
        "Without a stored default the personal project is reported as the default",
    )


@pytest.mark.user
@pytest.mark.api
def test_removing_non_default_membership_keeps_default(
    user_utils, default_project_member
):
    """TC-07: removing some other membership does not affect the default."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)

    user_utils.remove_user_from_project(member.user_id, member.project_b)

    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_a),
        "The default must survive removal of a different project",
    )


@pytest.mark.user
@pytest.mark.api
def test_clear_default_project(user_utils, default_project_member):
    """TC-08a: clearing unsets the default; clearing again, or a non-default project, is a no-op."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)

    user_utils.clear_default_project(member.user_id, member.project_a)
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.personal_project),
        "Clearing must fall back to the reported (personal) default",
    )

    user_utils.clear_default_project(member.user_id, member.project_a)
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.personal_project),
        "Clearing an already cleared default must be a no-op",
    )

    user_utils.set_default_project(member.user_id, member.project_a)
    user_utils.clear_default_project(member.user_id, member.project_b)
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_a),
        "Clearing a project that is not the default must not touch the real default",
    )


@pytest.mark.user
@pytest.mark.api
def test_clear_default_project_for_non_member_returns_404(
    user_utils, default_project_member, temp_project
):
    """TC-08b: clearing a project the user does not belong to is rejected."""
    status_code = user_utils.clear_default_project_status_code(
        default_project_member.user_id, temp_project
    )

    assert_that(status_code, equal_to(404), "Non-member project must be rejected")


@pytest.mark.user
@pytest.mark.api
@pytest.mark.parametrize("actor_utils", ["admin", "maintainer"], indirect=True)
def test_admin_and_maintainer_can_set_and_clear_default_project(
    user_utils, actor_utils, default_project_member
):
    """TC-09: roles that manage users can set and clear another user's default."""
    member = default_project_member

    actor_utils.set_default_project(member.user_id, member.project_a)
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_a),
        "Actor must be able to set the default",
    )

    actor_utils.clear_default_project(member.user_id, member.project_a)
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.personal_project),
        "Actor must be able to clear the default",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.parametrize(
    "actor_utils", ["project_admin", "auditor", "plain_user"], indirect=True
)
def test_roles_without_user_management_cannot_change_default_project(
    user_utils, actor_utils, default_project_member
):
    """TC-10: other roles are rejected for both set and clear, and the stored default is unchanged."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)

    set_status = actor_utils.set_default_project_status_code(
        member.user_id, member.project_b
    )
    clear_status = actor_utils.clear_default_project_status_code(
        member.user_id, member.project_a
    )

    assert_that(set_status, equal_to(403), "Setting the default must be forbidden")
    assert_that(clear_status, equal_to(403), "Clearing the default must be forbidden")
    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_a),
        "Rejected requests must not change the stored default",
    )


@pytest.mark.user
@pytest.mark.api
def test_auditor_can_see_default_project_marker(
    user_utils, auditor_client, default_project_member
):
    """TC-11: auditors can read the marker in projects, detail and list, though they cannot change it."""
    member = default_project_member
    auditor_utils = UserUtils(auditor_client)
    user_utils.set_default_project(member.user_id, member.project_a)

    assert_that(
        auditor_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_a),
        "Auditor must see the default in the user's projects",
    )
    assert_that(
        auditor_utils.get_default_project_names_from_detail(member.user_id),
        contains_exactly(member.project_a),
        "Auditor must see the default in the user details",
    )
    assert_that(
        auditor_utils.get_default_project_names_from_list(member.user_id, member.email),
        contains_exactly(member.project_a),
        "Auditor must see the default in the users list",
    )


@pytest.mark.user
@pytest.mark.api
def test_admin_user_detail_and_list_expose_default_project_marker(
    user_utils, default_project_member
):
    """TC-12: detail and list show the marker on the default project only; none when no default."""
    member = default_project_member

    assert_that(
        user_utils.get_default_project_names_from_detail(member.user_id),
        contains_exactly(member.personal_project),
        "No stored default: the personal project is marked in detail",
    )
    assert_that(
        user_utils.get_default_project_names_from_list(member.user_id, member.email),
        contains_exactly(member.personal_project),
        "No stored default: the personal project is marked in the list",
    )

    user_utils.set_default_project(member.user_id, member.project_a)

    assert_that(
        user_utils.get_default_project_names_from_detail(member.user_id),
        contains_exactly(member.project_a),
        "Default set: marker on that project in detail",
    )
    assert_that(
        user_utils.get_default_project_names_from_list(member.user_id, member.email),
        contains_exactly(member.project_a),
        "Default set: marker on that project in list",
    )


@pytest.mark.user
@pytest.mark.api
def test_member_profile_shows_default_project_and_follows_changes(
    user_utils, default_project_member
):
    """TC-13: the user's own /user profile shows the default and follows set, switch and removal."""
    member = default_project_member
    member_utils = UserUtils(member.client)

    assert_that(
        member_utils.get_default_project_names_from_profile(),
        contains_exactly(member.personal_project),
        "No stored default: the profile reports the personal project",
    )

    user_utils.set_default_project(member.user_id, member.project_a)
    assert_that(
        member_utils.get_default_project_names_from_profile(),
        contains_exactly(member.project_a),
        "Profile must show the new default",
    )

    user_utils.set_default_project(member.user_id, member.project_b)
    assert_that(
        member_utils.get_default_project_names_from_profile(),
        contains_exactly(member.project_b),
        "Profile must follow the switch",
    )

    user_utils.remove_user_from_project(member.user_id, member.project_b)
    assert_that(
        member_utils.get_default_project_names_from_profile(),
        contains_exactly(member.personal_project),
        "The default must fall back to the personal project with its membership",
    )


@pytest.mark.user
@pytest.mark.api
def test_user_projects_keep_their_order_when_defaults_change(
    user_utils, default_project_member
):
    """TC-14: the order of a multi-project user's projects is stable, also after rows are rewritten."""
    member = default_project_member
    order_before = user_utils.get_user_project_names(member.user_id)

    user_utils.set_default_project(member.user_id, member.project_b)
    user_utils.set_default_project(member.user_id, member.project_a)
    user_utils.clear_default_project(member.user_id, member.project_a)
    order_after = user_utils.get_user_project_names(member.user_id)

    assert_that(
        order_after,
        equal_to(order_before),
        "Rewriting default flags must not reorder the projects",
    )
    first, second = sorted([member.project_a, member.project_b])
    assert_that(
        order_after.index(first) < order_after.index(second),
        equal_to(True),
        "Projects must be listed in name order relative to each other",
    )


@pytest.mark.user
@pytest.mark.api
def test_defaults_of_different_users_in_one_project_are_independent(
    user_utils, default_project_member, disposable_user
):
    """TC-15: two users can both have the same project as default."""
    member = default_project_member
    _, other_user_id, _ = disposable_user
    user_utils.assign_user_to_project(other_user_id, member.project_a)

    user_utils.set_default_project(member.user_id, member.project_a)
    user_utils.set_default_project(other_user_id, member.project_a)

    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_a),
        "First user must keep the default",
    )
    assert_that(
        user_utils.get_default_project_names(other_user_id),
        contains_exactly(member.project_a),
        "Second user must have the same project as default",
    )


@pytest.mark.user
@pytest.mark.api
def test_default_project_can_be_set_again_after_default_membership_removed(
    user_utils, default_project_member
):
    """TC-16: after the default membership is removed, another project can become the default."""
    member = default_project_member
    user_utils.set_default_project(member.user_id, member.project_a)
    user_utils.remove_user_from_project(member.user_id, member.project_a)

    user_utils.set_default_project(member.user_id, member.project_b)

    assert_that(
        user_utils.get_default_project_names(member.user_id),
        contains_exactly(member.project_b),
        "A new default must be accepted after the old one disappeared",
    )


@pytest.mark.user
@pytest.mark.api
def test_set_default_project_for_unknown_user_returns_404(
    user_utils, default_project_member
):
    """TC-17: an unknown user id is rejected."""
    status_code = user_utils.set_default_project_status_code(
        "nonexistent-user-id-000000", default_project_member.project_a
    )

    assert_that(status_code, equal_to(404), "Unknown user must be rejected")
