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

"""Structural assertions for SonarQube / SonarCloud issue-search responses.

Sonar test data previously hardcoded a full `/api/issues/search` response -
metric totals, issue keys, line numbers, hashes, dates - captured from one
scan of one project at one point in time. That broke every time the
referenced project was rescanned or its code changed, because none of those
values are stable.

Unlike the other datasources (Jira, Confluence, xWiki, ServiceNow, ...),
there is no seed project to freeze here: the SonarQube project is the live
codemie codebase under active development, and the SonarCloud project is a
third-party GitHub repo we do not control. So instead of pinning a project,
Sonar tests assert on the *shape* of the response: the fields that must be
present, their types, and the enum values Sonar documents for them - never
the exact counts, keys or dates a particular scan happened to produce.
"""

import json
from typing import Optional

from hamcrest import (
    all_of,
    assert_that,
    greater_than_or_equal_to,
    has_entries,
    instance_of,
    is_in,
    less_than_or_equal_to,
    matches_regexp,
)

# https://docs.sonarsource.com/sonarqube-server/latest/user-guide/issues/
ISSUE_TYPES = {"CODE_SMELL", "BUG", "VULNERABILITY", "SECURITY_HOTSPOT"}
SEVERITIES = {"INFO", "MINOR", "MAJOR", "CRITICAL", "BLOCKER"}
STATUSES = {
    "OPEN",
    "CONFIRMED",
    "REOPENED",
    "RESOLVED",
    "CLOSED",
    "TO_REVIEW",
    "REVIEWED",
}

RULE_PATTERN = r"^[\w-]+:\S+$"
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}$"


def _issue_matcher(expected_type: str):
    return has_entries(
        {
            "key": instance_of(str),
            "rule": matches_regexp(RULE_PATTERN),
            "severity": is_in(sorted(SEVERITIES)),
            "component": instance_of(str),
            "project": instance_of(str),
            "status": is_in(sorted(STATUSES)),
            "message": instance_of(str),
            "type": expected_type,
            "creationDate": matches_regexp(DATE_PATTERN),
            "updateDate": matches_regexp(DATE_PATTERN),
        }
    )


def assert_issue_search_response(
    response: str, expected_type: str = "CODE_SMELL", max_issues: Optional[int] = 1
) -> None:
    """Assert a `/api/issues/search` response has the expected shape.

    Checks the presence, type, and (where Sonar defines one) allowed enum
    value of each field, instead of comparing against a hardcoded snapshot
    that only ever matched one scan of one project.
    """
    assert expected_type in ISSUE_TYPES, f"Unknown Sonar issue type: {expected_type}"

    payload = json.loads(response)
    assert_that(
        payload,
        has_entries(
            {
                "total": all_of(instance_of(int), greater_than_or_equal_to(0)),
                "p": instance_of(int),
                "ps": instance_of(int),
                "paging": has_entries(
                    {
                        "pageIndex": instance_of(int),
                        "pageSize": instance_of(int),
                        "total": all_of(instance_of(int), greater_than_or_equal_to(0)),
                    }
                ),
                "effortTotal": all_of(instance_of(int), greater_than_or_equal_to(0)),
                "issues": instance_of(list),
                "components": instance_of(list),
            }
        ),
    )

    issues = payload["issues"]
    if max_issues is not None:
        assert_that(len(issues), less_than_or_equal_to(max_issues))
    for issue in issues:
        assert_that(issue, _issue_matcher(expected_type))
