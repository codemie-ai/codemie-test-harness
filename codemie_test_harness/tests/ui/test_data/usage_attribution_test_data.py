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

"""Test data for the Analytics > Usage Attribution UI tests.

Labels are the ones the UI ships (the 'Chargeback Potential' tile and column, the period and date
filters only, the People columns and filters), not the older wording of the requirements.
"""

from dataclasses import dataclass
from enum import StrEnum

import pytest


class SubTab(StrEnum):
    """Sub-tabs of the Usage Attribution tab, valued by their button labels."""

    OVERVIEW = "Overview"
    PEOPLE = "People"
    HOW_IT_WORKS = "How It Works"


TAB_NAME = "Usage Attribution"

# Tabs the Usage Attribution tab is placed after, when the user has them.
TABS_BEFORE_USAGE_ATTRIBUTION = (
    "Insights",
    "CLI Insights",
    "CLI Analytics",
    "Leaderboard",
)

# The tab filters by period and dates only; the note takes the place of the Project and Users filters.
FILTER_SECTIONS_SHOWN = ("Time Period", "Start Date", "End Date")
FILTER_SECTIONS_HIDDEN = ("Project", "Users")
FILTER_NOTE = "No project or user filter on this tab"

SUMMARY_TILES = (
    "Total Spend",
    "Web Platform",
    "CLI",
    "Charged Back",
    "CLI Production",
    "CLI Experiments",
    "Chargeback Potential",
    "CLI Unclassified",
)
MONEY_WIDGETS = (
    "Where the Money Goes",
    "Who Pays",
    "CLI Spend by Category",
)
BREAKDOWN_WIDGETS = (
    "CLI Spend Paid From Personal Budgets, by Country",
    "CLI Spend Paid From Personal Budgets, by Job Title Group",
)

HOW_IT_WORKS_TILES = (
    "Coverage",
    "CLI Unclassified",
    "Allocated by Person",
    "Not in Total",
)
HOW_IT_WORKS_SECTIONS = (
    "This Analysis",
    "What CodeMie Records",
    "How Repositories Are Identified",
    "How Repositories Are Grouped",
    "Evidence Used for CLI Categories",
)


@dataclass(frozen=True)
class TableSpec:
    """A table of the tab: where it is, its shipped labels and the API call a scope change triggers."""

    sub_tab: SubTab
    aria_label: str
    columns: tuple[str, ...]
    search_placeholder: str
    options_select: str
    """Accessible name of the select that switches the scope or the filter."""
    option_patterns: tuple[str, ...]
    """Regular expressions for the option labels; the counts and the amounts depend on the data."""
    all_rows_option: str
    """Regular expression for the option that lists every row."""
    endpoint: str
    all_rows_query: str
    """Query parameter the list endpoint receives once every row is listed."""


SHARED_PROJECTS_TABLE = TableSpec(
    sub_tab=SubTab.OVERVIEW,
    aria_label="Shared projects without a budget",
    columns=(
        "Project",
        "Used Via",
        "Chargeback Potential",
        "Web Platform",
        "CLI",
        "% of Total Spend",
        "People",
        "CLI Production",
    ),
    search_placeholder="Search projects…",
    options_select="Projects to show",
    option_patterns=(
        r"^Over \$[\d,]+ per 30 days \(\d+\)$",
        r"^All \(\d+\)$",
    ),
    all_rows_option=r"^All \(\d+\)$",
    endpoint="shared-projects",
    all_rows_query="scope=all",
)
REPOSITORY_GROUPS_TABLE = TableSpec(
    sub_tab=SubTab.OVERVIEW,
    aria_label="Repository groups in personal projects",
    columns=(
        "Repository Group",
        "Grouped By",
        "Repositories",
        "People",
        "Chargeback Potential",
        "CLI Spend",
        "% of Total Spend",
        "CLI Production",
    ),
    search_placeholder="Search repositories…",
    options_select="Repository groups to show",
    option_patterns=(
        r"^Over \$[\d,]+ per 30 days \(\d+\)$",
        r"^All groups \(\d+\)$",
    ),
    all_rows_option=r"^All groups \(\d+\)$",
    endpoint="repository-groups",
    all_rows_query="scope=all",
)
PEOPLE_TABLE = TableSpec(
    sub_tab=SubTab.PEOPLE,
    aria_label="People",
    columns=(
        "User",
        "Total Spend",
        "Charged Back",
        "Production",
        "Learning & Experiments",
        "Other",
        "Production Days",
        "Works In",
    ),
    search_placeholder="Search users…",
    options_select="Filter people",
    option_patterns=(
        r"^Chargeback candidates \(\d+\)$",
        r"^All people \(\d+\)$",
        r"^Production on a personal budget \(\d+\)$",
        r"^Learning & experiments over \$[\d,]+ per 30 days \(\d+\)$",
        r"^In a shared project without a budget \(\d+\)$",
        r"^Web Platform over \$[\d,]+ per 30 days \(\d+\)$",
    ),
    all_rows_option=r"^All people \(\d+\)$",
    endpoint="people",
    all_rows_query="filter=all",
)

TABLES = [
    pytest.param(SHARED_PROJECTS_TABLE, id="shared-projects"),
    pytest.param(REPOSITORY_GROUPS_TABLE, id="repository-groups"),
    pytest.param(PEOPLE_TABLE, id="people"),
]


@dataclass(frozen=True)
class PopupSpec:
    """The popup that opens from the first row of a table."""

    table: TableSpec
    header_prefix: str
    """Text before the row name in the popup header."""
    tiles: tuple[str, ...]
    sections: tuple[str, ...]


SHARED_PROJECT_POPUP = PopupSpec(
    table=SHARED_PROJECTS_TABLE,
    header_prefix="",
    tiles=("Chargeback Potential", "Web Platform", "CLI", "People"),
    sections=(
        "Models",
        "Coding agents",
        "People",
        "CLI repositories in this project",
    ),
)
REPOSITORY_GROUP_POPUP = PopupSpec(
    table=REPOSITORY_GROUPS_TABLE,
    header_prefix="Repository group: ",
    tiles=("Chargeback Potential", "CLI Spend", "CLI Production", "People"),
    sections=(
        "Why these repositories are one group",
        "CLI spend by category",
        "Repositories and how they were identified",
        "Models",
        "Coding agents",
        "CodeMie projects used",
        "People",
    ),
)
PERSON_POPUP = PopupSpec(
    table=PEOPLE_TABLE,
    header_prefix="User: ",
    tiles=(
        "Total Spend",
        "Web Platform",
        "CLI",
        "Charged Back",
        "Personal Budget: Production",
        "Personal Budget: Learning & Experiments",
        "Net Lines Added",
        "Main Repository",
    ),
    sections=(
        "CodeMie projects",
        "Models",
        "Coding agents",
        "Repositories",
        "Sessions by category",
        "Why these categories",
        "Recent sessions",
    ),
)

POPUPS = [
    pytest.param(SHARED_PROJECT_POPUP, id="shared-project"),
    pytest.param(REPOSITORY_GROUP_POPUP, id="repository-group"),
    pytest.param(PERSON_POPUP, id="person"),
]
