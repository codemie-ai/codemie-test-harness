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
from hamcrest import assert_that, equal_to, has_item
from requests import HTTPError

from codemie_test_harness.cli.constants import (
    PROVISIONING_FULL_CLIENT_KEYS,
    PROVISIONING_READ_CLIENT_KEYS,
)
from codemie_test_harness.tests.test_data.provisioning_test_data import (
    LOOKUP_REJECTED_ROWS,
    unknown_email,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_READ_CLIENT_KEYS)
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
    first_only = provisioning_utils.create_project(
        name=f"{base}-b", display_name=f"Display of {base}-b"
    )
    second_only = provisioning_utils.create_project(name=f"{base}-a")
    shared = provisioning_utils.create_project(
        name=f"{base}-c", display_name=f"Display of {base}-c"
    )
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
    assert_that(
        {project.project_name: project.display_name for project in projects},
        equal_to(
            {
                second_only: None,
                first_only: f"Display of {base}-b",
                shared: f"Display of {base}-c",
            }
        ),
        "each project carries its display name, null when it has none",
    )


@pytest.mark.parametrize("member_emails", LOOKUP_REJECTED_ROWS)
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_READ_CLIENT_KEYS)
@pytest.mark.api
def test_lookup_without_a_valid_member_email_is_rejected_with_422(
    provisioning_read, member_emails
):
    # @case provisioning-api-for-third-party_TC_006
    with pytest.raises(HTTPError) as error:
        provisioning_read.list_projects(member_emails)

    assert_that(error.value.response.status_code, equal_to(422))


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_READ_CLIENT_KEYS)
@pytest.mark.api
def test_lookup_of_emails_matching_no_user_returns_an_empty_list(provisioning_read):
    # @case provisioning-api-for-third-party_TC_006
    projects = provisioning_read.list_projects([unknown_email(), unknown_email()])

    assert_that(projects, equal_to([]))


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_READ_CLIENT_KEYS)
@pytest.mark.api
def test_lookup_matches_member_email_in_any_letter_case(
    provisioning_read, non_admin_user, user_utils, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_006
    member_email, member_id, _ = non_admin_user
    project_name = provisioning_utils.create_project()
    user_utils.assign_user_to_project(member_id, project_name)

    projects = provisioning_read.list_projects([member_email.upper()])

    assert_that(
        [project.project_name for project in projects],
        equal_to([project_name]),
        "the upper-case email finds the same user and project as the stored one",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(
    *PROVISIONING_READ_CLIENT_KEYS, *PROVISIONING_FULL_CLIENT_KEYS
)
@pytest.mark.api
def test_lookup_skips_the_email_of_a_registered_client(
    provisioning_read,
    provisioning_client_email,
    provisioning_client_user_id,
    non_admin_user,
    user_utils,
    provisioning_utils,
):
    # @case provisioning-api-for-third-party_TC_006
    member_email, member_id, _ = non_admin_user
    project_name = provisioning_utils.create_project()
    user_utils.assign_user_to_project(member_id, project_name)
    user_utils.assign_user_to_project(
        provisioning_client_user_id, project_name, is_project_admin=True
    )
    assert_that(
        provisioning_utils.member_ids(project_name),
        has_item(provisioning_client_user_id),
        "the registered client's user is a member of the project",
    )

    member_projects = provisioning_read.list_projects([member_email])
    client_projects = provisioning_read.list_projects([provisioning_client_email])

    assert_that(
        [project.project_name for project in member_projects],
        equal_to([project_name]),
        "the ordinary member's email finds the project",
    )
    assert_that(
        client_projects,
        equal_to([]),
        "the registered client's email finds nothing although it is a member of the project",
    )
