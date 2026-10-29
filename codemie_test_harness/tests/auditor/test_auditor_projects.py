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

"""Auditor role — Projects API access and write-denial tests.

Covers:
  TC-004  Auditor can access project data via API (API leg)
  TC-010  Auditor project write requests denied at API layer (API)

UI tests (sidebar, project list) live in tests/ui/auditor/test_auditor_administration_ui.py.
"""

import pytest
from hamcrest import assert_that, equal_to, greater_than, is_not, none

from codemie_test_harness.tests.utils.analytics_utils import AnalyticsUtils


# ── TC-004 — spending data leg (AC-6) ─────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_can_view_projects_spending_data(auditor_client):
    """TC-004 (API, AC-6): Auditor can see project spending data via analytics endpoint.

    AC-6: Auditors must see 'all projects on the platform including spending data'.
    The analytics projects-spending endpoint exposes cost data per project; an auditor
    must receive a non-empty payload — not a 403 or empty list.
    """
    analytics = AnalyticsUtils(auditor_client)
    result = analytics.get_projects_spending()
    assert_that(
        result,
        is_not(none()),
        "Auditor projects spending response must not be None",
    )
    # TabularResponse carries rows under .data.rows or .rows — verify a payload exists.
    rows = None
    if hasattr(result, "data") and result.data is not None:
        rows = getattr(result.data, "rows", None)
    if rows is None:
        rows = getattr(result, "rows", None)
    if rows is None and isinstance(result, dict):
        rows = (result.get("data") or {}).get("rows") or result.get("rows")
    assert_that(
        rows is not None,
        equal_to(True),
        "Auditor projects spending response must contain a 'rows' field",
    )


# ── TC-004 — API leg ──────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_can_list_projects_via_api(auditor_project_utils):
    """TC-004 (API): Auditor can call GET /projects and receive a non-empty list.

    AC-5, AC-6: The projects endpoint is accessible to auditors and returns the full
    platform project list.
    """
    result = auditor_project_utils.list_projects(per_page=50)
    assert_that(
        result,
        is_not(none()),
        "Auditor project list must not be None",
    )
    items = getattr(result, "items", None) or getattr(result, "data", None)
    if items is None and isinstance(result, dict):
        items = result.get("items") or result.get("data")
    assert_that(
        items,
        is_not(none()),
        "Auditor project list response must contain items",
    )
    assert_that(
        len(items),
        greater_than(0),
        "Auditor must receive at least one project from the projects endpoint",
    )


# ── TC-010 ────────────────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_edit_project_returns_403(
    auditor_test_project, auditor_write_check_utils
):
    """TC-010: Auditor PATCH /projects/{name} returns HTTP 403.

    AC-7: The auditor role does not carry write permissions for projects.
    """
    status = auditor_write_check_utils.attempt_edit_project(auditor_test_project)
    assert_that(
        status,
        equal_to(403),
        "Auditor project edit must be denied with HTTP 403",
    )


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_delete_project_returns_404(
    auditor_test_project, auditor_write_check_utils
):
    """TC-010: Auditor DELETE /projects/{name} returns HTTP 404.

    AC-7: The auditor role does not carry write permissions for projects.
    """
    status = auditor_write_check_utils.attempt_delete_project(auditor_test_project)
    assert_that(
        status,
        equal_to(404),
        "Auditor project delete must be denied with HTTP 404",
    )


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_add_project_member_returns_404(
    auditor_test_project, auditor_test_user_id, auditor_write_check_utils
):
    """TC-010: Auditor POST /projects/{name}/members returns HTTP 404.

    AC-7: The auditor role does not carry member-management permissions.
    """
    status = auditor_write_check_utils.attempt_add_project_member(
        auditor_test_project, auditor_test_user_id
    )
    assert_that(
        status,
        equal_to(404),
        "Auditor add-project-member must be denied with HTTP 404",
    )
