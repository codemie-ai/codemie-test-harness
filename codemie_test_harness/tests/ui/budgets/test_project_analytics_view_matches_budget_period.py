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

"""UI test: "View analytics" opens with the project's current budget period (B3).

The Financial summary card's "Reset period" field (e.g. "30d") defines the
project's budget period. For a 30-day reset period, clicking "View analytics"
must open the Analytics page with the date range from the 1st of the current
month to today: start_date at 00:00 UTC on the 1st, end_date "to date" (now).

The button builds its dates from the project's budgets, which load after the
Overview tab renders. Until they load it falls back to ``time_period=last_30_days``
with no date params, so the test first waits for the Financial summary to show
the "30d" reset period. An earlier backend fix removed the symptom where the start
was the 2nd of the month (budget_reset_at - 30d).
"""

from datetime import datetime, timezone

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_view_analytics_opens_with_budget_period_date_range(page, project_admin_setup):
    project_name, _, _, _ = project_admin_setup
    now = datetime.now(timezone.utc)
    expected_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    details_page.should_show_reset_period("30d")

    analytics_page = details_page.click_view_analytics()
    analytics_page.should_show_date_range_matching_budget_period(expected_start)
