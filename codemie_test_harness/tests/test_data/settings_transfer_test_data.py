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

"""Test data for POST /v1/settings/transfer (move/copy project integrations).

Parametrize rows for TC-03, TC-07, TC-08, TC-09 and the ``type_of_integration`` /
``list`` filter rows (TC-10, TC-11, TC-13).
"""

import pytest

from codemie_sdk.models.integration import (
    IntegrationType,
    TransferMode,
    TypeOfIntegration,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name

# TC-03 -- empty source project, both modes return 200 with zero counts.
transfer_mode_test_data = [
    pytest.param(TransferMode.MOVE.value, id="mode_move"),
    pytest.param(TransferMode.COPY.value, id="mode_copy"),
]

# TC-07 -- invalid payload rows, all expected 422.
# Each row is (source_project_name_override, target_project_name_override, mode_override,
# same_project, expected_message) where an override of None means "use this test's own valid,
# randomly named project", "" means a literal blank string, and same_project=True means the
# target override is ignored and the real source project name is reused as the target too.
#
# expected_message is the exact pydantic/FastAPI validation `msg` for the four request-schema
# rows (mode missing/unsupported, blank name) and the exact service-layer `details` string for
# the same-project row -- confirmed against the live POST /v1/settings/transfer response bodies:
#   missing_mode            -> {"error": {"details": [{"msg": "Field required", ...}]}}
#   unsupported_mode         -> {"error": {"details": [{"msg": "Input should be 'move' or 'copy'", ...}]}}
#   blank_*_project_name     -> {"error": {"details": [{"msg": "String should have at least 1 character", ...}]}}
#   same_source_and_target   -> {"error": {"details": "Source and target projects must be different."}}
invalid_transfer_payload_test_data = [
    pytest.param(None, None, None, False, "Field required", id="missing_mode"),
    pytest.param(
        None,
        None,
        "teleport",
        False,
        "Input should be 'move' or 'copy'",
        id="unsupported_mode",
    ),
    pytest.param(
        "",
        None,
        "move",
        False,
        "String should have at least 1 character",
        id="blank_source_project_name",
    ),
    pytest.param(
        None,
        "",
        "move",
        False,
        "String should have at least 1 character",
        id="blank_target_project_name",
    ),
    pytest.param(
        None,
        None,
        "move",
        True,
        "Source and target projects must be different.",
        id="same_source_and_target_project",
    ),
]

# TC-08 -- nonexistent project on one side, checked independently of the other.
missing_project_side_test_data = [
    pytest.param("source", id="source_project_missing"),
    pytest.param("target", id="target_project_missing"),
]

# TC-09 -- caller role vs. expected outcome for the admin-or-maintainer-only guard.
transfer_role_test_data = [
    pytest.param("plain_member", 403, id="plain_member_denied"),
    pytest.param("maintainer", 200, id="maintainer_allowed"),
    pytest.param("admin", 200, id="admin_allowed"),
]

# TC-10 -- (type_of_integration payload, scopes whose integrations must be moved).
# The source project is seeded with 2 PROJECT and 2 USER integrations and `list` is omitted, so
# every integration of a selected scope must move. `None` omits the whole field (backward-compatible
# default: both scopes); the partial object omits `project_integrations`, which defaults to False.
transfer_type_filter_test_data = [
    pytest.param(
        {"user_integrations": True, "project_integrations": False},
        (IntegrationType.USER,),
        id="user_only",
    ),
    pytest.param(
        {"user_integrations": False, "project_integrations": True},
        (IntegrationType.PROJECT,),
        id="project_only",
    ),
    pytest.param(
        {"user_integrations": True, "project_integrations": True},
        (IntegrationType.PROJECT, IntegrationType.USER),
        id="both_explicit",
    ),
    pytest.param(
        None,
        (IntegrationType.PROJECT, IntegrationType.USER),
        id="field_omitted",
    ),
    pytest.param(
        TypeOfIntegration(user_integrations=True),
        (IntegrationType.USER,),
        id="partial_object_user_only",
    ),
]

# TC-11 -- (type_of_integration payload, integrations named in `list` as (scope, index into the
# seeded rows of that scope)). The source project is seeded with 2 PROJECT and 1 USER integration.
transfer_list_selection_test_data = [
    pytest.param(
        {"user_integrations": True, "project_integrations": True},
        ((IntegrationType.PROJECT, 0), (IntegrationType.USER, 0)),
        id="mixed_types_subset",
    ),
    pytest.param(
        {"user_integrations": False, "project_integrations": True},
        ((IntegrationType.PROJECT, 1),),
        id="single_project_alias",
    ),
]

# TC-13 -- (type_of_integration payload, builder of the `list` to send from the seeded rows,
# fragment expected in error details). The builder returns None to omit `list`. The source project
# is seeded with 1 PROJECT and 1 USER integration; every row expects 422.
transfer_invalid_filter_test_data = [
    pytest.param(
        {"user_integrations": False, "project_integrations": False},
        lambda seeded: None,
        "At least one integration type must be selected.",
        id="both_flags_false",
    ),
    pytest.param(
        {"user_integrations": True, "project_integrations": True},
        lambda seeded: [],
        "The integration list must not be empty",
        id="empty_list",
    ),
    pytest.param(
        {"user_integrations": False, "project_integrations": True},
        lambda seeded: [seeded[IntegrationType.USER][0].alias],
        "not of the requested type",
        id="type_mismatch",
    ),
    pytest.param(
        {"user_integrations": True, "project_integrations": True},
        lambda seeded: [get_random_name()],
        "were not found in project",
        id="unknown_alias",
    ),
]
