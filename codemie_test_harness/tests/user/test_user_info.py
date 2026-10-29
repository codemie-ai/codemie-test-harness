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

import os

import pytest
from codemie_sdk.models.user import User, UserData
from hamcrest import (
    assert_that,
    instance_of,
    is_not,
    all_of,
    has_property,
)

from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


@pytest.mark.user
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.sanity
def test_about_me(user_utils):
    user = user_utils.get_about_me()

    assert_that(
        user,
        all_of(
            instance_of(User),
            has_property("user_id", is_not(None)),
            has_property("name", os.getenv("TEST_USER_FULL_NAME")),
            has_property(
                "username",
                "admin"
                if EnvironmentResolver.is_localhost()
                else os.getenv("AUTH_USERNAME"),
            ),
            has_property("email", is_not(None)),
            has_property("is_admin", is_not(None)),
            has_property("applications", instance_of(list)),
            has_property("applications_admin", instance_of(list)),
            has_property("knowledge_bases", instance_of(list)),
        ),
        "User profile should have all required properties with correct types",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.sanity
def test_get_user_data(user_utils):
    user_data = user_utils.get_user_data()

    assert_that(
        user_data,
        all_of(
            instance_of(UserData),
            has_property("user_id", is_not(None)),
        ),
        "User data should be valid UserData instance with user_id",
    )
