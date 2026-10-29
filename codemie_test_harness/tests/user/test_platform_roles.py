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

import pytest
from hamcrest import assert_that, equal_to, is_not, empty


@pytest.mark.user
@pytest.mark.api
def test_default_user_cannot_get_admin_user_by_id(user_utils, default_user_utils):
    me = user_utils.get_about_me()
    status = default_user_utils.get_admin_user_status_code(me.user_id)

    assert_that(
        status,
        equal_to(403),
        "Default user should be denied access to admin user detail endpoint",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_default_user_cannot_update_user(user_utils, default_user_utils):
    me = user_utils.get_about_me()
    status = default_user_utils.update_admin_user_status_code(me.user_id, name="hacker")

    assert_that(
        status,
        equal_to(403),
        "Default user should be denied access to update user endpoint",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_default_user_cannot_deactivate_user(user_utils, default_user_utils):
    me = user_utils.get_about_me()
    status = default_user_utils.deactivate_user_status_code(me.user_id)

    assert_that(
        status,
        equal_to(403),
        "Default user should be denied access to deactivate user endpoint",
    )


@pytest.mark.user
@pytest.mark.api
def test_admin_user_can_list_users(user_utils):
    response = user_utils.list_admin_users()

    assert_that(
        response.data,
        is_not(empty()),
        "Admin user should receive a non-empty user list",
    )


@pytest.mark.user
@pytest.mark.api
def test_admin_user_can_get_user_by_id(user_utils):
    me = user_utils.get_about_me()
    status = user_utils.get_admin_user_status_code(me.user_id)

    assert_that(
        status,
        equal_to(200),
        "Admin user should be able to access admin user detail endpoint",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_admin_cannot_promote_user_to_admin(admin_only_user_utils, disposable_user):
    _, user_id, _ = disposable_user
    status = admin_only_user_utils.update_admin_user_status_code(user_id, is_admin=True)

    assert_that(
        status,
        equal_to(403),
        "Admin-only user should be denied when attempting to set is_admin flag (Maintainer-only operation)",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_admin_cannot_set_maintainer_flag(admin_only_user_utils, disposable_user):
    _, user_id, _ = disposable_user
    status = admin_only_user_utils.update_admin_user_status_code(
        user_id, is_maintainer=True
    )

    assert_that(
        status,
        equal_to(403),
        "Admin-only user should be denied when attempting to set is_maintainer flag (Maintainer-only operation)",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_maintainer_can_promote_user_to_admin(user_utils, disposable_user):
    _, user_id, _ = disposable_user
    user_utils.update_admin_user(user_id, is_admin=True)

    detail = user_utils.get_admin_user(user_id)
    assert_that(
        detail.is_admin,
        equal_to(True),
        "Maintainer should be able to promote a user to admin",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_maintainer_can_set_maintainer_flag(user_utils, disposable_user):
    _, user_id, _ = disposable_user
    user_utils.update_admin_user(user_id, is_maintainer=True)

    detail = user_utils.get_admin_user(user_id)
    assert_that(
        detail.is_maintainer,
        equal_to(True),
        "Maintainer should be able to set is_maintainer flag on another user",
    )
