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

"""CLI Analytics Tool Success per surface: a dash without tool calls, a percentage with them.

Each case is one user's single session in a project of its own: no tool calls, some of them
failed, and all of them failed (a real 0%, not "no data"). The dashboard is opened as the
harness admin, the user the sibling CLI Analytics UI tests view the page as.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.analytics.cli_analytics_page import (
    CLIAnalyticsPage,
)
from codemie_test_harness.tests.ui.test_data.analytics_test_data import (
    CLIAnalyticsSection,
)


@pytest.mark.cli_analytics
@pytest.mark.ui
def test_cli_analytics_overview_tool_success_follows_tool_calls(
    page, tool_success_scenario
):
    # @case cli-analytics-tool-success-follows-tool-calls_TC_001
    """Overview > Summary shows the Tool Success under TOOL CALLS as a dash only without tool calls."""
    case = tool_success_scenario.case
    dashboard = CLIAnalyticsPage(page).navigate_to()
    dashboard.filter_by_project(tool_success_scenario.project)

    dashboard.should_show_overview_tool_calls(case.tool_calls)  # repro:precondition
    dashboard.should_show_overview_tool_success(case.overview_success)  # repro:symptom


@pytest.mark.cli_analytics
@pytest.mark.ui
def test_cli_analytics_users_tool_success_follows_tool_calls(
    page, tool_success_scenario
):
    # @case cli-analytics-tool-success-follows-tool-calls_TC_002
    """Users > per-user detail shows TOOL SUCCESS as a dash only for a user without tool calls."""
    case = tool_success_scenario.case
    user = tool_success_scenario.user_email
    dashboard = CLIAnalyticsPage(page).navigate_to()
    dashboard.filter_by_project(tool_success_scenario.project)
    dashboard.open_section(CLIAnalyticsSection.USERS)

    dashboard.should_show_user_tool_calls(user, case.tool_calls)  # repro:precondition
    dashboard.should_show_user_tool_success(user, case.users_success)  # repro:symptom


@pytest.mark.cli_analytics
@pytest.mark.ui
def test_cli_analytics_user_modal_tool_success_follows_tool_calls(
    page, tool_success_scenario
):
    # @case cli-analytics-tool-success-follows-tool-calls_TC_003
    """The user modal Summary shows Tool Success as a dash only for a user without tool calls."""
    case = tool_success_scenario.case
    user = tool_success_scenario.user_email
    dashboard = CLIAnalyticsPage(page).navigate_to()
    dashboard.filter_by_project(tool_success_scenario.project)
    dashboard.open_section(CLIAnalyticsSection.USERS)
    dashboard.should_show_user_tool_calls(user, case.tool_calls)  # repro:precondition
    user_modal = dashboard.open_user_modal(user)

    user_modal.should_show_tool_success(case.users_success)  # repro:symptom
