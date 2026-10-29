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

"""Default order of GET /v1/admin/users: A to Z by name, case-insensitive.

The name key falls back to the username when the name is empty; users with the same name are
ordered by email. Users are created per test (admin API on local-auth stands, auth server plus first login
elsewhere); the assertions only look at users found by the per-run search token.
"""

import pytest
from hamcrest import assert_that, contains_exactly

from codemie_test_harness.tests.test_data.admin_users_order_test_data import (
    UNNAMED_USERS_BY_USERNAME,
    default_order_scenarios,
)


@pytest.mark.user
@pytest.mark.parametrize(
    "scenario", default_order_scenarios, ids=lambda scenario: scenario.id
)
@pytest.mark.api
def test_list_admin_users_default_order_is_name_a_to_z(
    user_utils, ordered_users, scenario
):
    # @case admin-users-default-name-order_TC_001
    users = ordered_users(scenario)

    response = user_utils.list_admin_users(search=users.token)

    assert_that(
        [item.email for item in response.data],
        contains_exactly(*users.emails),
        "Without sort params the users must be ordered A to Z by name "
        "(username when the name is empty, then email)",
    )


@pytest.mark.user
@pytest.mark.api
def test_admin_client_list_users_returns_a_to_z(admin_utils, ordered_users):
    # @case admin-users-default-name-order_TC_004
    users = ordered_users(UNNAMED_USERS_BY_USERNAME)

    listed = admin_utils.list_users(search=users.token)

    assert_that(
        [item.username for item in listed],
        contains_exactly(*users.usernames),
        "client.admin.list_users must return users A to Z by username, ignoring case",
    )
