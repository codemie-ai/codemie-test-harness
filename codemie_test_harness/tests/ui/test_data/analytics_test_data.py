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


# Em dash (U+2014): what a CLI Analytics Tool Success shows when there are no tool calls.
TOOL_SUCCESS_DASH = "—"


@dataclass(frozen=True)
class InsightsTable:
    """A table widget of Analytics > Insights.

    ``title`` is the widget heading. ``name_column`` and ``count_column`` are the exact column
    headers the rows are ordered by: the count descending, then the name ascending. The count
    column also identifies the table, because the name column header is not unique on the page.
    ``cost_column`` is set for a widget whose rows are ordered by that column instead.
    """

    title: str
    name_column: str
    count_column: str
    cost_column: str | None = None


ASSISTANTS_CHATS_COST_COLUMN = "Total Cost ($)"

# Located by its Total Messages column; its rows are ordered by Total Cost ($), see the cost check.
ASSISTANTS_CHATS_TABLE = InsightsTable(
    title="Assistants Chats",
    name_column="Assistant",
    count_column="Total Messages",
    cost_column=ASSISTANTS_CHATS_COST_COLUMN,
)
WORKFLOWS_TABLE = InsightsTable(
    title="Workflows", name_column="Workflow Name", count_column="Total Runs"
)

# Label of the first cell of the totals footer row.
INSIGHTS_FOOTER_LABEL = "Total"

# Runs the Insights activity fixture starts per assistant and per workflow: the counts differ, so
# the tables list rows with different message counts, run counts and costs.
INSIGHTS_SEEDED_RUN_COUNTS = (1, 2)
