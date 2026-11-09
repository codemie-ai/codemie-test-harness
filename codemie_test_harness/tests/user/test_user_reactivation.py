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

"""API tests for deactivating and reactivating users through the admin user routes.

Every test works on a disposable user (or a disposable admin / maintainer), never on the shared
accounts, so a regression in the self-action or rank rules cannot lock the stand.
"""

import json

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_item,
    has_properties,
    is_not,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.user_status_test_data import (
    ACCOUNT_DEACTIVATED_MESSAGE,
    DEACTIVATE,
    REACTIVATE,
    REACTIVATE_VIA_UPDATE_MESSAGE,
    REACTIVATION_REJECTIONS,
    STATUS_ACTIONS,
    USER_DEACTIVATED_MESSAGE,
    USER_IS_DEACTIVATED_MESSAGE,
    ReactivationRejection,
    unknown_user_id,
)
from codemie_test_harness.tests.utils.user_utils import UserUtils


def _project_roles(detail):
    """project name -> is_project_admin for the projects of an admin user detail."""
    return {p.name: p.is_project_admin for p in detail.projects}


@pytest.mark.user
@pytest.mark.api
def test_reactivate_restores_active_user_with_roles_and_projects(
    user_utils, disposable_project_member
):
    # @case platform-admins-deactivate-reactivate-users_TC_001
    _, user_id, _, project = disposable_project_member
    user_utils.update_admin_user(user_id, is_admin=True)
    before = user_utils.get_admin_user(user_id)
    user_utils.deactivate_user(user_id)

    reactivated = user_utils.reactivate_user(user_id)
    detail = user_utils.get_admin_user(user_id)

    assert_that(
        _project_roles(before),
        has_item(project),
        "Precondition: the user must be a member of the project before deactivation",
    )
    for source, state in (
        ("reactivate response", reactivated),
        ("admin detail", detail),
    ):
        assert_that(
            state.is_active, equal_to(True), f"{source}: user must be active again"
        )
        assert_that(
            state.is_admin,
            equal_to(before.is_admin),
            f"{source}: the admin flag must survive deactivation",
        )
        assert_that(
            state.is_maintainer,
            equal_to(before.is_maintainer),
            f"{source}: the maintainer flag must survive deactivation",
        )
        assert_that(
            _project_roles(state),
            equal_to(_project_roles(before)),
            f"{source}: project memberships and roles must be unchanged",
        )


@pytest.mark.user
@pytest.mark.api
def test_deactivated_user_is_denied_access_until_reactivated(
    user_utils, disposable_user, disposable_user_utils
):
    # @case platform-admins-deactivate-reactivate-users_TC_002
    _, user_id, _ = disposable_user

    message = user_utils.deactivate_user_message(user_id)
    with pytest.raises(HTTPError) as denied:
        disposable_user_utils.get_about_me()
    user_utils.reactivate_user(user_id)
    restored = disposable_user_utils.get_about_me()

    assert_that(
        message,
        equal_to(USER_DEACTIVATED_MESSAGE),
        "Deactivation must answer with its confirmation message",
    )
    assert_that(
        denied.value.response.status_code,
        equal_to(401),
        "A deactivated user must be refused with 401",
    )
    # Live-observed text; the local-IdP text ("Authentication failed" / "User is not active") does not hold on this stand.
    assert_that(
        UserUtils.error_text(denied.value),
        contains_string(ACCOUNT_DEACTIVATED_MESSAGE),
        "The 401 must say the account is deactivated",
    )
    assert_that(
        restored.user_id,
        equal_to(user_id),
        "After reactivation the same user must be authenticated again",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.parametrize(
    "rejection",
    REACTIVATION_REJECTIONS,
    ids=[r.label for r in REACTIVATION_REJECTIONS],
)
def test_reactivate_is_rejected_for_active_user(
    user_utils, disposable_user, rejection: ReactivationRejection
):
    # @case platform-admins-deactivate-reactivate-users_TC_003
    _, active_user_id, _ = disposable_user

    with pytest.raises(HTTPError) as rejected:
        user_utils.reactivate_user(rejection.target_id(active_user_id))

    assert_that(
        rejected.value.response.status_code,
        equal_to(rejection.expected_status),
        f"Reactivating the {rejection.label} must be refused with {rejection.expected_status}",
    )
    assert_that(
        UserUtils.error_text(rejected.value),
        contains_string(rejection.message),
        "The error must carry the expected message",
    )


@pytest.mark.user
@pytest.mark.api
def test_reactivate_is_rejected_for_unknown_user(user_utils):
    # @case platform-admins-deactivate-reactivate-users_TC_003
    with pytest.raises(HTTPError) as rejected:
        user_utils.reactivate_user(unknown_user_id())

    assert_that(
        rejected.value.response.status_code,
        equal_to(404),
        "Reactivating an unknown user must be refused with 404",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.parametrize("action", STATUS_ACTIONS, ids=[a.name for a in STATUS_ACTIONS])
def test_admin_cannot_change_own_status(
    user_utils, admin_client, promoted_admin_user, action
):
    # @case platform-admins-deactivate-reactivate-users_TC_006
    _, admin_id, _ = promoted_admin_user

    with pytest.raises(HTTPError) as refused:
        action.perform(UserUtils(admin_client), admin_id)

    assert_that(
        refused.value.response.status_code,
        equal_to(403),
        f"An admin must not be able to {action.name} their own account",
    )
    assert_that(
        UserUtils.error_text(refused.value),
        contains_string(f"You cannot {action.name} your own account"),
        "The refusal must name the rule",
    )
    assert_that(
        user_utils.get_admin_user(admin_id).is_active,
        equal_to(True),
        "The admin account must stay active",
    )


@pytest.mark.user
@pytest.mark.api
def test_admin_only_actor_cannot_deactivate_maintainer(
    user_utils, admin_client, maintainer_client
):
    # @case platform-admins-deactivate-reactivate-users_TC_007
    maintainer_id = maintainer_client.users.about_me().user_id

    with pytest.raises(HTTPError) as refused:
        DEACTIVATE.perform(UserUtils(admin_client), maintainer_id)

    assert_that(
        refused.value.response.status_code,
        equal_to(403),
        "An admin who is not a maintainer must not deactivate a maintainer",
    )
    assert_that(
        UserUtils.error_text(refused.value),
        contains_string("Only maintainers can deactivate a maintainer"),
        "The refusal must name the rank rule",
    )
    assert_that(
        user_utils.get_admin_user(maintainer_id).is_active,
        equal_to(True),
        "The maintainer must stay active",
    )


@pytest.mark.user
@pytest.mark.api
def test_admin_only_actor_cannot_reactivate_maintainer(
    user_utils, admin_client, maintainer_client
):
    # @case platform-admins-deactivate-reactivate-users_TC_007
    maintainer_id = maintainer_client.users.about_me().user_id
    user_utils.deactivate_user(maintainer_id)

    with pytest.raises(HTTPError) as refused:
        REACTIVATE.perform(UserUtils(admin_client), maintainer_id)

    assert_that(
        refused.value.response.status_code,
        equal_to(403),
        "An admin who is not a maintainer must not reactivate a maintainer",
    )
    assert_that(
        UserUtils.error_text(refused.value),
        contains_string("Only maintainers can reactivate a maintainer"),
        "The refusal must name the rank rule",
    )
    assert_that(
        user_utils.get_admin_user(maintainer_id).is_active,
        equal_to(False),
        "The maintainer must stay deactivated",
    )


@pytest.mark.user
@pytest.mark.api
def test_update_with_is_active_true_is_refused(user_utils, deactivated_user):
    # @case platform-admins-deactivate-reactivate-users_TC_008
    _, user_id, _ = deactivated_user

    with pytest.raises(HTTPError) as refused:
        user_utils.update_admin_user(user_id, is_active=True)

    assert_that(
        refused.value.response.status_code,
        equal_to(400),
        "Reactivation through the update route must be refused with 400",
    )
    assert_that(
        UserUtils.error_text(refused.value),
        contains_string(REACTIVATE_VIA_UPDATE_MESSAGE),
        "The refusal must point to the reactivate route",
    )
    assert_that(
        user_utils.get_admin_user(user_id).is_active,
        equal_to(False),
        "The user must stay deactivated",
    )


@pytest.mark.user
@pytest.mark.api
def test_platform_role_grant_on_deactivated_user_is_refused(
    user_utils, deactivated_user
):
    # @case platform-admins-deactivate-reactivate-users_TC_009
    _, user_id, _ = deactivated_user
    admin_flag_before = user_utils.get_admin_user(user_id).is_admin

    with pytest.raises(HTTPError) as refused:
        user_utils.update_admin_user(user_id, is_admin=True)

    assert_that(
        refused.value.response.status_code,
        equal_to(409),
        "Granting a platform role to a deactivated user must be refused with 409",
    )
    assert_that(
        UserUtils.error_text(refused.value),
        contains_string(USER_IS_DEACTIVATED_MESSAGE),
        "The refusal must say the user is deactivated",
    )
    assert_that(
        user_utils.get_admin_user(user_id).is_admin,
        equal_to(admin_flag_before),
        "The admin flag must not change",
    )


@pytest.mark.user
@pytest.mark.api
def test_project_access_grant_to_deactivated_user_is_refused_and_removal_allowed(
    user_utils, disposable_project_member
):
    # @case platform-admins-deactivate-reactivate-users_TC_018
    _, user_id, _, project = disposable_project_member
    user_utils.deactivate_user(user_id)

    with pytest.raises(HTTPError) as refused:
        user_utils.assign_user_to_project(user_id, project)
    user_utils.remove_user_from_project(user_id, project)

    assert_that(
        refused.value.response.status_code,
        equal_to(409),
        "Granting project access to a deactivated user must be refused with 409",
    )
    assert_that(
        UserUtils.error_text(refused.value),
        contains_string(USER_IS_DEACTIVATED_MESSAGE),
        "The refusal must say the user is deactivated",
    )
    assert_that(
        user_utils.get_user_project_names(user_id),
        is_not(has_item(project)),
        "Removing the deactivated user from the project must still work",
    )


@pytest.mark.user
@pytest.mark.api
def test_project_admin_listing_does_not_show_deactivated_users(
    user_utils, default_project_member, project_admin_client
):
    # @case platform-admins-deactivate-reactivate-users_TC_019
    member = default_project_member
    user_utils.deactivate_user(member.user_id)
    inactive_filter = json.dumps({"is_active": False})

    seen_by_admin = user_utils.list_admin_users(
        search=member.email, filters=inactive_filter
    )
    seen_by_project_admin = UserUtils(project_admin_client).list_admin_users(
        search=member.email, filters=inactive_filter
    )

    assert_that(
        seen_by_admin.data,
        has_item(has_properties(id=member.user_id, is_active=False)),
        "Control: a platform admin must see the deactivated user",
    )
    assert_that(
        [u.id for u in seen_by_project_admin.data],
        is_not(has_item(member.user_id)),
        "A project admin must not see the deactivated user",
    )
    assert_that(
        [u.is_active for u in seen_by_project_admin.data],
        is_not(has_item(False)),
        "A project admin must only be shown active users",
    )
