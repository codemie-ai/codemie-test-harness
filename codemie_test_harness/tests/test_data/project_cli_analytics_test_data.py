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

"""Test data for the project-level `cli_analytics_enabled` API tests.

Roles are named by what they are (global_admin, maintainer, project_admin of the target project,
other_project_admin of the other project only, member of both, auditor who is a member of neither,
unrelated_user without membership), never by matrix codes.

Expected outcome of one visibility cell:
  PRESENT    2xx and the raw JSON contains the key with the value just written
  ABSENT     2xx and the key is not in the raw JSON (not null, not false)
  NOT_LISTED 200 list that does not contain the project at all
  <int>      exactly this HTTP status; the body is not inspected for the key
"""

import pytest

PRESENT = "present"
ABSENT = "absent"
NOT_LISTED = "not_listed"

ROLES = [
    "global_admin",
    "maintainer",
    "project_admin",
    "other_project_admin",
    "member",
    "auditor",
    "unrelated_user",
]
WRITER_ROLES = ["global_admin", "maintainer"]
NON_WRITER_ROLES = [
    "project_admin",
    "other_project_admin",
    "member",
    "auditor",
    "unrelated_user",
]

# route -> (HTTP route used by the helper, which project it reads, role -> expected outcome)
# "target" carries the state under test, "other" carries the opposite state, so a mixed-up
# project cannot pass.
VISIBILITY_MATRIX = {
    "list_target": (
        "list",
        "target",
        dict(
            zip(
                ROLES,
                [PRESENT, PRESENT, PRESENT, NOT_LISTED, ABSENT, ABSENT, NOT_LISTED],
            )
        ),
    ),
    "list_other": (
        "list",
        "other",
        dict(
            zip(
                ROLES,
                [PRESENT, PRESENT, NOT_LISTED, PRESENT, ABSENT, ABSENT, NOT_LISTED],
            )
        ),
    ),
    "detail": (
        "detail",
        "target",
        dict(zip(ROLES, [PRESENT, PRESENT, PRESENT, 404, ABSENT, ABSENT, 404])),
    ),
    "patch_response": (
        "patch_response",
        "target",
        dict(zip(ROLES, [PRESENT, PRESENT, PRESENT, 403, 403, 403, 403])),
    ),
    "legacy_application": (
        "legacy",
        "target",
        dict(zip(ROLES, [PRESENT, PRESENT, PRESENT, 403, ABSENT, 403, 403])),
    ),
}

STATE_IDS = {True: "flag_on", False: "flag_off"}

VISIBILITY_CASES = [
    pytest.param(
        route,
        which,
        role,
        state,
        expected[role],
        id=f"{label}-{role}-{STATE_IDS[state]}",
    )
    for label, (route, which, expected) in VISIBILITY_MATRIX.items()
    for role in ROLES
    for state in (True, False)
]

# (flag value before, value sent) of a PATCH that also changes the description
FIELD_VARIANTS = [
    pytest.param(False, True, id="set_true"),
    pytest.param(True, False, id="set_false"),
    pytest.param(True, None, id="explicit_null"),
    pytest.param(False, False, id="unchanged_value"),
]
