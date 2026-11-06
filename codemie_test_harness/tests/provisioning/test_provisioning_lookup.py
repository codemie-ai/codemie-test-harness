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

"""Provisioning API: looking up the projects of people (GET /v1/provisioning/projects)."""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.cli.constants import KEY_PROVISIONING_READ_TOKEN
from codemie_test_harness.tests.test_data.provisioning_test_data import unknown_email
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.budget
@pytest.mark.requires_setting(KEY_PROVISIONING_READ_TOKEN)
@pytest.mark.api
def test_lookup_returns_union_of_shared_projects_sorted_by_name(
    provisioning_read,
    non_admin_user,
    disposable_user,
    user_utils,
    provisioning_utils,
):
    # @case provisioning-api-for-third-party_TC_006
    first_email, first_id, _ = non_admin_user
    second_email, second_id, _ = disposable_user
    base = get_random_name()
    first_only = provisioning_utils.create_project(name=f"{base}-b")
    second_only = provisioning_utils.create_project(name=f"{base}-a")
    shared = provisioning_utils.create_project(name=f"{base}-c")
    user_utils.assign_user_to_project(first_id, first_only)
    user_utils.assign_user_to_project(second_id, second_only)
    user_utils.assign_user_to_project(first_id, shared)
    user_utils.assign_user_to_project(second_id, shared)

    projects = provisioning_read.list_projects(
        [first_email, unknown_email(), second_email]
    )

    assert_that(
        [project.project_name for project in projects],
        equal_to([second_only, first_only, shared]),
        "distinct shared projects of both users sorted by name, without their "
        "personal projects and without anything for the unknown email",
    )
