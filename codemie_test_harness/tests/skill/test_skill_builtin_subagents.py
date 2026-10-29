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
Tests for skill enabled_builtin_subagents field.

Covers:
    TC-001  Skill enabled_builtin_subagents CRUD round-trip
    TC-002  Skill field edge cases and validation
    TC-009  _dedupe_builtin_subagents validator on create and update
    TC-010  SkillContributionsResolver + toolkit service subagent gating

Note on TC-010 scope:
    `enabled_builtin_subagents` contributions from skills are merged into the
    effective agent toolkit at *runtime*.  They are NOT written back to the
    assistant's DB row after a skill is attached.  TC-010 tests therefore verify:
    (a) the skill persists its own field correctly across create/update, and
    (b) attaching such a skill to an assistant succeeds (skill appears in
        assistant.skills[]) without altering the assistant's stored
        enabled_builtin_subagents (which is independently controlled).
"""

import time

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    is_,
    not_none,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name

BUILTIN_SUBAGENT_ID = "GENERAL_PURPOSE_SUBAGENT"

# Content must be at least 100 characters (server validation)
SKILL_CONTENT = (
    "# Test Skill\n\n## Description\n"
    "This skill is used for automated integration testing of the built-in subagent feature.\n"
    "It validates enabled_builtin_subagents persistence across create, update, and read operations."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _put_skill_subagents(skill_utils, skill_id: str, subagents: list):
    """Update skill's enabled_builtin_subagents via utils."""
    current = skill_utils.get_skill_by_id(skill_id)
    return skill_utils.update_skill(
        skill_id,
        name=current.name,
        description=current.description,
        content=current.content,
        visibility=current.visibility,
        categories=current.categories if current.categories else None,
        enabled_builtin_subagents=subagents,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TC-001  CRUD round-trip
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_skill_builtin_subagents_crud_roundtrip(raw_skill, skill_utils):
    """TC-001: Create with GENERAL_PURPOSE_SUBAGENT, read, update to [], read again."""
    created = raw_skill([BUILTIN_SUBAGENT_ID], content=SKILL_CONTENT)

    assert_that(created.enabled_builtin_subagents, not_none())
    assert_that(created.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))

    fetched = skill_utils.get_skill_by_id(created.id)
    assert_that(fetched.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))

    updated = _put_skill_subagents(skill_utils, created.id, [])
    assert_that(updated.enabled_builtin_subagents, equal_to([]))

    cleared = skill_utils.get_skill_by_id(created.id)
    assert_that(cleared.enabled_builtin_subagents, equal_to([]))


# ---------------------------------------------------------------------------
# TC-002  Edge cases and validation
# ---------------------------------------------------------------------------


@pytest.mark.skill
@pytest.mark.api
def test_skill_builtin_subagents_default_when_omitted(skill, skill_utils):
    """TC-002a: Omit enabled_builtin_subagents on create → defaults to []."""
    created_skill = skill()  # standard fixture — no enabled_builtin_subagents field

    fetched = skill_utils.get_skill_by_id(created_skill.id)
    assert_that(
        fetched.enabled_builtin_subagents,
        equal_to([]),
        "Field should default to empty list when omitted",
    )


@pytest.mark.skill
@pytest.mark.api
def test_skill_builtin_subagents_independent_values(raw_skill, skill_utils):
    """TC-002b: Two skills carry independent enabled_builtin_subagents values."""
    a = raw_skill([BUILTIN_SUBAGENT_ID], content=SKILL_CONTENT)
    b = raw_skill([], content=SKILL_CONTENT)

    fetched_a = skill_utils.get_skill_by_id(a.id)
    fetched_b = skill_utils.get_skill_by_id(b.id)

    assert_that(fetched_a.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))
    assert_that(fetched_b.enabled_builtin_subagents, equal_to([]))


@pytest.mark.skill
@pytest.mark.api
def test_skill_invalid_builtin_subagent_name_rejected(skill_utils):
    """TC-002c: Invalid subagent name in enabled_builtin_subagents → 422."""
    skill_name = get_random_name().replace("_", "-")
    with pytest.raises(Exception) as exc_info:
        skill_utils.send_create_skill_request(
            skill_name=skill_name,
            enabled_builtin_subagents=["INVALID_AGENT_XYZ"],
        )
    assert_that(
        hasattr(exc_info.value, "response"),
        is_(True),
        f"Exception has no response attribute: {exc_info.value!r}",
    )
    assert_that(
        exc_info.value.response.status_code,
        equal_to(422),
        "Server should reject unknown subagent name with HTTP 422",
    )


# ---------------------------------------------------------------------------
# TC-009  Deduplication validator
# ---------------------------------------------------------------------------


@pytest.mark.skill
@pytest.mark.api
def test_skill_builtin_subagents_deduplication_on_create(raw_skill):
    """TC-009a: Duplicate entries in create payload are deduplicated."""
    created = raw_skill(
        [BUILTIN_SUBAGENT_ID, BUILTIN_SUBAGENT_ID], content=SKILL_CONTENT
    )

    assert_that(
        created.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        "Duplicate entries should be collapsed to a single entry",
    )


@pytest.mark.skill
@pytest.mark.api
def test_skill_builtin_subagents_deduplication_on_update(skill, skill_utils):
    """TC-009b: Duplicate entries sent in update are deduplicated."""
    created_skill = skill()

    updated = _put_skill_subagents(
        skill_utils,
        created_skill.id,
        [BUILTIN_SUBAGENT_ID, BUILTIN_SUBAGENT_ID, BUILTIN_SUBAGENT_ID],
    )
    assert_that(
        updated.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        "Three duplicate entries should be collapsed to one",
    )

    fetched = skill_utils.get_skill_by_id(created_skill.id)
    assert_that(fetched.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))


# ---------------------------------------------------------------------------
# TC-010  SkillContributionsResolver: skill-level persistence and attachment
# ---------------------------------------------------------------------------


@pytest.mark.skill
@pytest.mark.api
def test_skill_builtin_subagent_gating_enabled(raw_skill, skill_utils):
    """TC-010a: Skill with GENERAL_PURPOSE_SUBAGENT persists the field correctly."""
    created = raw_skill([BUILTIN_SUBAGENT_ID], content=SKILL_CONTENT)

    assert_that(
        created.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        "Skill should store enabled value immediately on create",
    )

    fetched = skill_utils.get_skill_by_id(created.id)
    assert_that(fetched.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))

    updated = _put_skill_subagents(skill_utils, created.id, [])
    assert_that(updated.enabled_builtin_subagents, equal_to([]))

    re_enabled = _put_skill_subagents(skill_utils, created.id, [BUILTIN_SUBAGENT_ID])
    assert_that(re_enabled.enabled_builtin_subagents, equal_to([BUILTIN_SUBAGENT_ID]))


@pytest.mark.skill
@pytest.mark.assistant
@pytest.mark.api
def test_skill_builtin_subagent_attachment_succeeds(
    raw_skill, raw_assistant, skill_utils, assistant_utils
):
    """TC-010b: Skill with GENERAL_PURPOSE_SUBAGENT can be attached to an assistant."""
    created_skill = raw_skill([BUILTIN_SUBAGENT_ID], content=SKILL_CONTENT)
    asst_id = raw_assistant(
        description="TC-010 test assistant",
        system_prompt="Test assistant for skill attachment",
    )

    skill_utils.attach_skill_to_assistant(asst_id, created_skill.id)
    time.sleep(1)

    attached_skills = skill_utils.get_assistant_skills(asst_id)
    skill_ids_attached = [s.id for s in attached_skills]
    assert_that(
        created_skill.id in skill_ids_attached,
        is_(True),
        "Attached skill should appear in assistant.skills[]",
    )

    asst_data = assistant_utils.get_assistant_by_id(asst_id)
    assert_that(
        asst_data.enabled_builtin_subagents,
        equal_to([]),
        "Assistant DB-level field must not change when a skill is attached",
    )

    skill_data = skill_utils.get_skill_by_id(created_skill.id)
    assert_that(
        skill_data.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        "Skill's own field must remain unchanged after attachment",
    )


@pytest.mark.skill
@pytest.mark.api
def test_skill_builtin_subagent_gating_disabled(raw_skill, skill_utils):
    """TC-010c: Skill with enabled_builtin_subagents=[] persists empty field correctly."""
    created = raw_skill([], content=SKILL_CONTENT)

    assert_that(created.enabled_builtin_subagents, equal_to([]))

    fetched = skill_utils.get_skill_by_id(created.id)
    assert_that(fetched.enabled_builtin_subagents, equal_to([]))
