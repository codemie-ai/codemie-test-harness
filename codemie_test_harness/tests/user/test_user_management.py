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

import json

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    only_contains,
    greater_than_or_equal_to,
    has_item,
    has_property,
    instance_of,
    is_not,
    less_than_or_equal_to,
    not_,
    empty,
)

from codemie_sdk.models.user import (
    AdminUserProject,
    CodeMieUserDetail,
    PaginatedUserListResponse,
)


@pytest.mark.user
@pytest.mark.api
def test_list_admin_users_returns_paginated_response(user_utils):
    response = user_utils.list_admin_users()

    assert_that(
        response,
        instance_of(PaginatedUserListResponse),
        "Response should be a PaginatedUserListResponse",
    )
    assert_that(
        response.data,
        is_not(empty()),
        "User list should contain at least one user",
    )
    assert_that(
        response.pagination.total,
        greater_than_or_equal_to(1),
        "Pagination total should be at least 1",
    )
    assert_that(
        response.pagination.page,
        equal_to(0),
        "Default page should be 0",
    )
    assert_that(
        response.pagination.per_page,
        equal_to(20),
        "Default per_page should be 20",
    )


@pytest.mark.user
@pytest.mark.api
def test_list_admin_users_respects_pagination_parameters(user_utils):
    response = user_utils.list_admin_users(page=0, per_page=10)

    assert_that(
        response.pagination.per_page,
        equal_to(10),
        "per_page should match requested value",
    )
    assert_that(
        len(response.data),
        less_than_or_equal_to(10),
        "Result count should not exceed per_page",
    )


@pytest.mark.user
@pytest.mark.api
def test_list_admin_users_search_returns_matching_users(user_utils):
    me = user_utils.get_about_me()
    response = user_utils.list_admin_users(search=me.email)

    assert_that(
        response.data,
        is_not(empty()),
        "Search by current user email should return at least one result",
    )
    found_emails = [item.email for item in response.data]
    assert_that(
        found_emails,
        has_item(me.email),
        "Search results should include the user with the searched email",
    )


@pytest.mark.user
@pytest.mark.api
def test_list_admin_users_search_by_username(user_utils):
    me = user_utils.get_about_me()
    users = user_utils.list_all_admin_users(search=me.username)

    assert_that(
        users,
        is_not(empty()),
        "Search by username should return at least one result",
    )
    found_usernames = [item.username for item in users]
    assert_that(
        found_usernames,
        has_item(me.username),
        "Search results should include the user with the searched username",
    )


@pytest.mark.user
@pytest.mark.api
def test_get_admin_user_by_id_returns_full_details(user_utils):
    me = user_utils.get_about_me()
    detail = user_utils.get_admin_user(me.user_id)

    assert_that(
        detail, instance_of(CodeMieUserDetail), "Response should be CodeMieUserDetail"
    )
    assert_that(detail.id, equal_to(me.user_id), "User ID should match")
    assert_that(detail.email, equal_to(me.email), "Email should match current user")
    assert_that(
        detail.username, equal_to(me.username), "Username should match current user"
    )
    assert_that(
        detail.projects,
        instance_of(list),
        "Projects field should be a list",
    )
    assert_that(
        detail.knowledge_bases,
        instance_of(list),
        "Knowledge bases field should be a list",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_update_admin_user_name_persists(updated_user):
    _, new_name, updated = updated_user

    assert_that(
        updated.name,
        equal_to(new_name),
        "Updated name should be reflected in user details",
    )


@pytest.mark.user
@pytest.mark.api
def test_get_user_project_memberships_returns_list(user_utils):
    me = user_utils.get_about_me()
    projects = user_utils.get_user_projects(me.user_id)

    assert_that(
        projects,
        instance_of(list),
        "Project memberships should be returned as a list",
    )
    assert_that(
        projects,
        only_contains(instance_of(AdminUserProject)),
        "Each membership should be an AdminUserProject",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_assign_and_remove_user_from_project(user_utils, temp_project):
    me = user_utils.get_about_me()

    user_utils.assign_user_to_project(me.user_id, temp_project)
    project_names_after_assign = user_utils.get_user_project_names(me.user_id)
    assert_that(
        project_names_after_assign,
        has_item(temp_project),
        "User should be assigned to the project",
    )

    user_utils.remove_user_from_project(me.user_id, temp_project)
    project_names_after_remove = user_utils.get_user_project_names(me.user_id)
    assert_that(
        project_names_after_remove,
        not_(has_item(temp_project)),
        "User should no longer be in the project after removal",
    )


@pytest.mark.user
@pytest.mark.api
def test_get_admin_user_with_nonexistent_id_returns_404(user_utils):
    status_code = user_utils.get_admin_user_status_code("nonexistent-user-id-000000")

    assert_that(status_code, equal_to(404), "Non-existent user ID should return 404")


@pytest.mark.user
@pytest.mark.api
def test_list_admin_users_with_invalid_filters_returns_400(user_utils):
    status_code = user_utils.list_admin_users_status_code(filters="not-valid-json{{{")

    assert_that(
        status_code,
        equal_to(400),
        "Invalid JSON in filters parameter should return 400",
    )


@pytest.mark.user
@pytest.mark.api
def test_list_admin_users_filter_is_active_returns_only_active_users(user_utils):
    response = user_utils.list_admin_users(filters=json.dumps({"is_active": True}))

    assert_that(
        response.data,
        is_not(empty()),
        "Filter by is_active=true should return at least one user",
    )
    assert_that(
        response.data,
        only_contains(has_property("is_active", True)),
        "All returned users should be active",
    )


@pytest.mark.user
@pytest.mark.api
def test_list_admin_users_filter_platform_role_admin_returns_only_admins(user_utils):
    response = user_utils.list_admin_users(
        filters=json.dumps({"platform_role": "admin"})
    )

    assert_that(
        response.data,
        is_not(empty()),
        "Filter by platform_role=admin should return at least one user",
    )
    assert_that(
        response.data,
        only_contains(has_property("is_admin", True)),
        "All returned users should have is_admin=True",
    )


@pytest.mark.user
@pytest.mark.api
def test_list_admin_users_filter_user_type_returns_valid_response(user_utils):
    response = user_utils.list_admin_users(filters=json.dumps({"user_type": "regular"}))

    assert_that(
        response,
        instance_of(PaginatedUserListResponse),
        "Filter by user_type should return a valid paginated response",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_list_admin_users_filter_projects_returns_assigned_user(
    user_utils, temp_project_with_me
):
    me, project_name = temp_project_with_me

    response = user_utils.list_admin_users(
        filters=json.dumps({"projects": [project_name]})
    )

    found_emails = [item.email for item in response.data]
    assert_that(
        found_emails,
        has_item(me.email),
        "Filtering by project should include the assigned user",
    )


@pytest.mark.user
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_update_user_project_role_sets_project_admin(user_utils, temp_project):
    me = user_utils.get_about_me()
    user_utils.assign_user_to_project(me.user_id, temp_project, is_project_admin=False)

    user_utils.update_user_project_role(me.user_id, temp_project, is_project_admin=True)

    projects = user_utils.get_user_projects(me.user_id)
    matched = [p for p in projects if p.project_name == temp_project]
    assert_that(
        matched, is_not(empty()), "User should still be a member of the project"
    )
    assert_that(
        matched[0].is_project_admin,
        equal_to(True),
        "User should now be a project admin",
    )

    user_utils.remove_user_from_project(me.user_id, temp_project)


@pytest.mark.user
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_deactivate_user_sets_inactive(user_utils, disposable_user):
    _, user_id, _ = disposable_user

    user_utils.deactivate_user(user_id)

    detail = user_utils.get_admin_user(user_id)
    assert_that(
        detail.is_active,
        equal_to(False),
        "Deactivated user should have is_active=False",
    )


@pytest.mark.user
@pytest.mark.api
def test_admin_user_has_required_permissions(user_utils):
    me = user_utils.get_about_me()

    assert_that(
        me.is_admin,
        equal_to(True),
        "Test user must have admin privileges to access admin endpoints",
    )
    detail = user_utils.get_admin_user(me.user_id)
    assert_that(
        detail.is_admin,
        equal_to(True),
        "Admin detail endpoint should confirm is_admin flag for admin user",
    )
