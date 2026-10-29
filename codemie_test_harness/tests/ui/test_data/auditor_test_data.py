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

"""UI test data constants for auditor role tests."""

# Analytics tab labels as they appear in the UI
ANALYTICS_TAB_INSIGHTS = "Insights"
ANALYTICS_TAB_CLI_INSIGHTS = "CLI Insights"
ANALYTICS_TAB_LEADERBOARD = "Leaderboard"
# All three analytics tabs the auditor should see
AUDITOR_ANALYTICS_TABS = [
    ANALYTICS_TAB_INSIGHTS,
    ANALYTICS_TAB_LEADERBOARD,
    ANALYTICS_TAB_CLI_INSIGHTS,
]

# Settings sidebar item labels (as shown in browser)
SIDEBAR_ITEM_BUDGETS = "Budgets management"
SIDEBAR_ITEM_PROJECTS = "Projects management"
SIDEBAR_ITEM_USERS = "Users management"
