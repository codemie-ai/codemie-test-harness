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

"""Test data for Analytics UI tests."""

from dataclasses import dataclass
from enum import StrEnum


class CLIAnalyticsSection(StrEnum):
    """Sections of Analytics > CLI Analytics, valued by their button labels in the UI."""

    OVERVIEW = "Overview"
    USERS = "Users"
    REPOSITORIES = "Repositories"
    TOOLS_AND_MODELS = "Tools & Models"
    ACTIVITY = "Activity"
    EFFICIENCY = "Efficiency"
    COST = "Cost"
    SESSIONS = "Sessions"


@dataclass(frozen=True)
class InsightsTable:
    """A table widget of Analytics > Insights.

    ``title`` is the widget heading. ``name_column`` and ``count_column`` are the exact column
    headers the rows are ordered by: the count descending, then the name ascending. The count
    column also identifies the table, because the name column header is not unique on the page.
    """

    title: str
    name_column: str
    count_column: str


ASSISTANTS_CHATS_TABLE = InsightsTable(
    title="Assistants Chats", name_column="Assistant", count_column="Total Messages"
)
WORKFLOWS_TABLE = InsightsTable(
    title="Workflows", name_column="Workflow Name", count_column="Total Runs"
)

# Label of the first cell of the totals footer row.
INSIGHTS_FOOTER_LABEL = "Total"
