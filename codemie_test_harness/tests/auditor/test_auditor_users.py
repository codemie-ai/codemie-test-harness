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

"""Auditor role — Users API access and write-denial tests.

Covers:
  TC-005  Auditor can access user data via API (API leg)
  TC-011  Auditor user write requests denied at API layer (API)

UI tests (sidebar, user list, user details) live in tests/ui/auditor/test_auditor_administration_ui.py.
"""

import pytest
from hamcrest import assert_that, equal_to, greater_than, is_not, none

# ── TC-005 — API leg ──────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_can_list_users_via_api(auditor_user_utils):
    """TC-005 (API): Auditor can call GET /admin/users and receive a non-empty list.

    AC-8, AC-9: The admin users endpoint is accessible to auditors and returns all
    platform users.
    """
    result = auditor_user_utils.list_admin_users(per_page=50)
    assert_that(result, is_not(none()), "Auditor user list must not be None")
    data = getattr(result, "data", None)
    if data is None and isinstance(result, dict):
        data = result.get("data") or result.get("items")
    assert_that(data, is_not(none()), "Auditor user list response must contain data")
    assert_that(
        len(data),
        greater_than(0),
        "Auditor must receive at least one user from the admin users endpoint",
    )


# ── TC-011 ────────────────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_create_user_returns_403(auditor_write_check_utils):
    """TC-011: Auditor POST /admin/users returns HTTP 403.

    AC-10: The auditor role does not carry write permissions for users.
    """
    status = auditor_write_check_utils.attempt_create_user()
    assert_that(
        status, equal_to(403), "Auditor user create must be denied with HTTP 403"
    )


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_edit_user_returns_403(auditor_test_user_id, auditor_write_check_utils):
    """TC-011: Auditor PUT /admin/users/{id} returns HTTP 403.

    AC-10: The auditor role does not carry write permissions for users.
    """
    status = auditor_write_check_utils.attempt_edit_user(auditor_test_user_id)
    assert_that(status, equal_to(403), "Auditor user edit must be denied with HTTP 403")


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_deactivate_user_returns_403(
    auditor_test_user_id, auditor_write_check_utils
):
    """TC-011: Auditor POST /admin/users/{id}/deactivate returns HTTP 403.

    AC-10: The auditor role does not carry deactivation permissions.
    """
    status = auditor_write_check_utils.attempt_deactivate_user(auditor_test_user_id)
    assert_that(
        status, equal_to(403), "Auditor deactivate-user must be denied with HTTP 403"
    )


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_change_user_role_returns_403(
    auditor_test_user_id, auditor_write_check_utils
):
    """TC-011: Auditor PATCH /admin/users/{id}/role returns HTTP 403.

    AC-10: The auditor role does not carry role-management permissions.
    """
    status = auditor_write_check_utils.attempt_change_user_role(auditor_test_user_id)
    assert_that(
        status, equal_to(403), "Auditor change-user-role must be denied with HTTP 403"
    )
