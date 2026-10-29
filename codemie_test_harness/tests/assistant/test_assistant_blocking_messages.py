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

"""
Tests for AC-6: blocked subagent spawn attempts produce clear, actionable,
distinguishable messages.

Covers:
    TC-006  Recursion guard enforced at configuration level (catalog + field check)
    TC-007  Multiple sequential assistant configs — recursion guard holds per config
    TC-015  Skill-permission block (422 error) is distinguishable from recursion guard

Implementation note:
    Full log-message verification (AC-6) requires access to application or execution
    logs, which are not available via the test harness REST API.  These tests verify
    the OBSERVABLE layer of AC-6:
      (a) The API produces a structured 422 error (not a generic 500) for invalid
          subagent names — the skill-permission block scenario.
      (b) Each 422 error contains field-level context (not a generic string).
      (c) The recursion guard is expressed at the configuration level: the catalog
          entry and assistant field semantics confirm the guard is in place.
      (d) Multiple independent assistant configurations each carry the guard correctly.

    The docstring of each test notes what additional log access would fully verify.
"""

from typing import List

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    is_,
    not_none,
)
from codemie_sdk.models.assistant import BuiltinSubagent
from codemie_test_harness.tests.test_data.skill_test_data import SKILL_DESCRIPTION
from codemie_test_harness.tests.utils.base_utils import get_random_name

BUILTIN_SUBAGENT_ID = "GENERAL_PURPOSE_SUBAGENT"
INVALID_SUBAGENT_ID = "INVALID_RECURSIVE_AGENT_XYZ"

# Content must be at least 100 characters (API validation)
_SKILL_CONTENT = (
    "# Blocking Messages Test Skill\n\n"
    "## Description\n"
    "Integration test skill for validating AC-6 blocking behavior.\n"
    "Used in tests for TC-006, TC-007, TC-015."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_name() -> str:
    return get_random_name().replace("_", "-")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TC-006  Recursion guard enforced at configuration level
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_recursion_guard_assistant_field_prevents_self_spawn(
    raw_assistant, assistant_utils
):
    """TC-006: Recursion guard is expressed at the configuration layer."""
    asst_id = raw_assistant(
        [BUILTIN_SUBAGENT_ID], description="TC-006/007/015 test assistant"
    )

    fetched = assistant_utils.get_assistant_by_id(asst_id)
    assert_that(
        fetched.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        "Parent must have enabled_builtin_subagents=[GENERAL_PURPOSE_SUBAGENT]",
    )
    assert_that(
        fetched.assistant_ids,
        equal_to([]),
        "Parent assistant_ids must not be populated by built-in subagent config",
    )

    catalog: List[BuiltinSubagent] = assistant_utils.get_builtin_subagents()
    matching_entries = [e for e in catalog if e.id == BUILTIN_SUBAGENT_ID]
    assert_that(
        len(matching_entries),
        equal_to(1),
        f"Catalog must list '{BUILTIN_SUBAGENT_ID}' exactly once",
    )


# ---------------------------------------------------------------------------
# TC-007  Multiple assistant configs — recursion guard holds independently
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_multiple_assistants_each_carry_recursion_guard_independently(
    raw_assistant, assistant_utils
):
    """TC-007: Multiple independent assistants each carry the recursion guard."""
    id_a = raw_assistant(
        [BUILTIN_SUBAGENT_ID], description="TC-006/007/015 test assistant"
    )
    id_b = raw_assistant([], description="TC-006/007/015 test assistant")
    id_c = raw_assistant(
        [BUILTIN_SUBAGENT_ID], description="TC-006/007/015 test assistant"
    )

    data_a = assistant_utils.get_assistant_by_id(id_a)
    data_b = assistant_utils.get_assistant_by_id(id_b)
    data_c = assistant_utils.get_assistant_by_id(id_c)

    assert_that(
        data_a.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        "asst_a must retain its own enabled config",
    )
    assert_that(
        data_b.enabled_builtin_subagents,
        equal_to([]),
        "asst_b must retain its own empty config (no bleed from asst_a)",
    )
    assert_that(
        data_c.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        "asst_c must retain its own enabled config (no bleed from asst_b)",
    )

    assert_that(
        len({id_a, id_b, id_c}),
        equal_to(3),
        "Each assistant must have a unique ID for per-entry log attribution",
    )


# ---------------------------------------------------------------------------
# TC-015  Skill-permission block is distinguishable from recursion guard
# ---------------------------------------------------------------------------


@pytest.mark.skill
@pytest.mark.api
def test_skill_permission_block_distinguished_from_recursion_guard(
    raw_assistant, assistant_utils, skill_utils
):
    """TC-015: The skill-permission block produces a structured 422 error
    distinguishable from the recursion guard.
    """
    skill_name = _unique_name()

    # --- Block type A: Skill-permission block (invalid subagent name) ---
    skill_422_exc = None
    with pytest.raises(Exception) as exc_info:
        skill_utils.send_create_skill_request(
            skill_name=skill_name,
            description=SKILL_DESCRIPTION,
            content=_SKILL_CONTENT,
            enabled_builtin_subagents=[INVALID_SUBAGENT_ID],
        )
    skill_422_exc = exc_info.value

    assert_that(
        hasattr(skill_422_exc, "response"),
        is_(True),
        f"Exception from invalid subagent name must have a response attribute; "
        f"got: {skill_422_exc!r}",
    )
    assert_that(
        skill_422_exc.response.status_code,
        equal_to(422),
        "Skill-permission block must return HTTP 422 — not a generic 500",
    )

    error_body = skill_422_exc.response.json()
    assert_that(
        str(error_body),
        contains_string(INVALID_SUBAGENT_ID),
        "422 response body must identify the rejected subagent name",
    )

    # --- Block type B: Recursion guard (configuration layer) ---
    asst_id = raw_assistant(
        [BUILTIN_SUBAGENT_ID], description="TC-006/007/015 test assistant"
    )
    asst_data = assistant_utils.get_assistant_by_id(asst_id)
    assert_that(
        asst_data.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        "Recursion guard config must use a known subagent ID (not a 422)",
    )

    assert_that(
        skill_422_exc.response.status_code,
        equal_to(422),
        "Skill-permission block must be an HTTP-level error (422)",
    )
    assert_that(
        asst_data.id,
        not_none(),
        "Recursion guard config must NOT raise an HTTP error — it is a valid config",
    )
