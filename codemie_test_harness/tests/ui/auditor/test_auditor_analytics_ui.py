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

"""Auditor role — Analytics UI tests.

Covers:
  TC-001  Auditor sees all Analytics sections (UI)
  TC-002  Auditor analytics user filter spans all platform users (UI)

API analytics tests live in tests/auditor/test_auditor_analytics.py.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.analytics.analytics_page import (
    AnalyticsPage,
)
from codemie_test_harness.tests.ui.test_data.auditor_test_data import (
    AUDITOR_ANALYTICS_TABS,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


# ── TC-001 ────────────────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_sees_all_analytics_sections(page):
    """TC-001: Auditor can view all Analytics sections.

    AC-1: Auditor can see Insights, Leaderboard, CLI Insights tabs.
    """
    analytics = AnalyticsPage(page)
    analytics.navigate_to()
    analytics.should_see_analytics_sections(AUDITOR_ANALYTICS_TABS)


# ── TC-002 ────────────────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.ui
def test_auditor_analytics_user_filter_spans_all_users(page):
    """TC-002: Auditor USERS filter in Analytics shows users other than the auditor.

    AC-2: The user filter dropdown exposes all platform users, not just the auditor's own
    account.  At minimum, the regular test user should appear in the dropdown.
    """
    other_user = CredentialsManager.get_parameter("TEST_USER_FULL_NAME")
    analytics = AnalyticsPage(page)
    analytics.navigate_to()
    analytics.should_see_all_users_in_filter(other_user)
