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

"""Auditor role — Analytics API access tests (API only).

Covers:
  TC-003  Auditor can access all analytics endpoints (API, parameterised)
  TC-015  Auditor can access all leaderboard sub-endpoints (API, parameterised regression)
  TC-016  Auditor analytics users endpoint returns full platform user list (API, regression)

UI analytics tests live in tests/ui/auditor/test_auditor_analytics_ui.py.
"""

import pytest
from hamcrest import assert_that, equal_to, greater_than, is_not, none

from codemie_test_harness.tests.test_data.auditor_test_data import (
    ANALYTICS_TABULAR_ENDPOINTS,
)
from codemie_sdk.models.analytics import UsersListResponse

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


# All analytics methods exercised by TC-003
ALL_ANALYTICS_ENDPOINTS = [
    "get_summaries",
    "get_cli_summary",
] + ANALYTICS_TABULAR_ENDPOINTS


# ── TC-003 ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("method_name", ALL_ANALYTICS_ENDPOINTS)
@pytest.mark.auditor
@pytest.mark.api
def test_auditor_can_access_analytics_endpoint(method_name, auditor_analytics_utils):
    """TC-003: Auditor receives non-null data from each analytics endpoint.

    AC-3: All analytics API endpoints are accessible with auditor credentials and return
    valid response objects.
    """
    result = getattr(auditor_analytics_utils, method_name)()
    assert_that(
        result,
        is_not(none()),
        f"Auditor analytics endpoint '{method_name}' must return a non-null response",
    )


LEADERBOARD_ENDPOINTS = [
    "get_leaderboard_summary",
    "get_leaderboard_scores",
    "get_leaderboard_tiers",
    "get_leaderboard_top_performers",
    "get_leaderboard_dimensions",
    "get_leaderboard_entries",
    "get_leaderboard_seasons",
    "get_leaderboard_framework",
]


# ── TC-015 ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("method_name", LEADERBOARD_ENDPOINTS)
@pytest.mark.auditor
@pytest.mark.api
def test_auditor_can_access_leaderboard_endpoint(method_name, auditor_analytics_utils):
    """TC-015 [Regression]: Auditor receives a non-error response from each leaderboard sub-endpoint.

    AC-1, AC-3: All /v1/analytics/leaderboard/* endpoints must be accessible to an
    auditor user — a 403 indicates a backend regression in the auditor permissions
    middleware.
    """
    result = getattr(auditor_analytics_utils, method_name)()
    assert_that(
        result,
        is_not(none()),
        f"Leaderboard endpoint '{method_name}' must return a non-null response to auditor",
    )


# ── TC-016 ────────────────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_analytics_users_returns_all_platform_users(auditor_analytics_utils):
    """TC-016 [Regression]: Auditor analytics/users endpoint returns the full user list.

    AC-2, AC-3: The cross-user filter bug is not regressed — the auditor must receive all
    platform users, not only their own account.  At minimum there must be > 1 user.
    """
    result: UsersListResponse = auditor_analytics_utils.get_users(
        time_period="last_30_days"
    )
    users = result.data.users
    assert_that(
        len(users),
        greater_than(1),
        "Auditor must see all platform users, not only their own account",
    )
    # AC-3: Verify cross-user scope — the regular (non-auditor) user must appear in
    # the list, proving data is not filtered to the auditor's own activity.
    regular_fullname = CredentialsManager.get_parameter("TEST_USER_FULL_NAME")
    found_regular_user = any(regular_fullname in u.name for u in users)
    assert_that(
        found_regular_user,
        equal_to(True),
        f"Auditor analytics users list must include '{regular_fullname}' "
        "(cross-user scope — not filtered to auditor's own account)",
    )
