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

"""Tests for the preconfigured azure-devops-work-item-fields Skill's
field-reference table content."""

import pytest
from hamcrest import assert_that, equal_to

# The 18 of the 21 ticket-listed field names that have a verifiable
# correspondence in the shipped table: either the row's own Display Name
# (for "Acceptance Criteria", which the ticket lists with its real ADO
# spacing) or the last dot-segment of the row's REST Reference Name (for
# the rest, which the ticket lists condensed/without spaces, e.g.
# "AreaPath" for the "Area Path" row's `System.AreaPath`).
GROUNDED_TICKET_FIELDS = [
    "Id",
    "Title",
    "Description",
    "Tags",
    "Priority",
    "AreaPath",
    "IterationPath",
    "TeamProject",
    "WorkItemType",
    "State",
    "CreatedBy",
    "CreatedDate",
    "AssignedTo",
    "ChangedDate",
    "SystemInfo",
    "ReproSteps",
    "Severity",
    "Acceptance Criteria",
]

ACCEPTANCE_CRITERIA_DISPLAY_NAME = "Acceptance Criteria"
ACCEPTANCE_CRITERIA_REST_NAME = "Microsoft.VSTS.Common.AcceptanceCriteria"


def _parse_field_table(content: str) -> dict:
    """Parse the skill content's '| Display Name | REST Reference Name |'
    markdown table into {display_name: rest_reference_name}, skipping the
    header and separator rows."""
    rows = {}
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        display_name, rest_name = cells
        if display_name == "Display Name":
            continue
        rows[display_name] = rest_name.strip("`")
    return rows


def _table_header(content: str) -> list:
    """Return the markdown table's header cells (the first '|'-led line)."""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("|") and "---" not in line:
            return [cell.strip() for cell in line.strip("|").split("|")]
    return []


@pytest.mark.skill
@pytest.mark.ado
@pytest.mark.api
def test_ado_field_reference_skill_table_has_two_columns_and_covers_builtin_fields(
    ado_field_reference_skill,
):
    """Covers extend-context-for-ado-tools_TC_001: the preconfigured
    azure-devops-work-item-fields Skill's content is a two-column table
    (Display Name, REST Reference Name) with no type column, covering the
    ticket's built-in fields, and mapping "Acceptance Criteria" to
    Microsoft.VSTS.Common.AcceptanceCriteria.
    """
    # @case extend-context-for-ado-tools_TC_001
    content = ado_field_reference_skill.content
    assert_that(bool(content), equal_to(True))

    header = _table_header(content)
    assert_that(header, equal_to(["Display Name", "REST Reference Name"]))

    rows = _parse_field_table(content)
    display_names = set(rows.keys())
    rest_suffixes = {rest.rsplit(".", 1)[-1] for rest in rows.values()}

    for field in GROUNDED_TICKET_FIELDS:
        assert_that(
            field in display_names or field in rest_suffixes,
            equal_to(True),
            f"Expected ticket field '{field}' to appear as a row "
            "(by Display Name or REST Reference Name) in the shipped "
            "field-reference table",
        )

    assert_that(
        rows.get(ACCEPTANCE_CRITERIA_DISPLAY_NAME),
        equal_to(ACCEPTANCE_CRITERIA_REST_NAME),
    )
