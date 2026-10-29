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

"""Tests for Skills integration with Assistants."""

import pytest
from hamcrest import assert_that, equal_to, greater_than, has_length, is_in

from codemie_test_harness.tests.test_data.skill_test_data import BULK_ATTACH_COUNT


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
@pytest.mark.assistant
def test_attach_skill_to_assistant(skill, assistant_factory, skill_utils):
    """Test attaching skill to assistant."""
    created_skill = skill()
    created_assistant = assistant_factory.create()

    # Verify no skills attached initially
    assistant_skills = skill_utils.get_assistant_skills(created_assistant.id)
    assert_that(assistant_skills, has_length(0))

    skill_utils.attach_skill_to_assistant(created_assistant.id, created_skill.id)

    # Verify attachment
    assistant_skills = skill_utils.get_assistant_skills(created_assistant.id)
    assert_that(len(assistant_skills), greater_than(0))

    # Verify the skill is in the list
    skill_ids = [skill.id for skill in assistant_skills]
    assert_that(created_skill.id in skill_ids, equal_to(True))


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
@pytest.mark.assistant
def test_detach_skill_from_assistant(skill, assistant_factory, skill_utils):
    """Test detaching skill from assistant."""
    created_skill = skill()
    created_assistant = assistant_factory.create()

    # Attach first
    skill_utils.attach_skill_to_assistant(created_assistant.id, created_skill.id)

    # Verify attachment
    skills_before = skill_utils.get_assistant_skills(created_assistant.id)
    skill_ids_before = [skill.id for skill in skills_before]
    assert_that(created_skill.id in skill_ids_before, equal_to(True))

    # Detach
    skill_utils.detach_skill_from_assistant(created_assistant.id, created_skill.id)

    # Verify detachment
    skills_after = skill_utils.get_assistant_skills(created_assistant.id)
    skill_ids_after = [skill.id for skill in skills_after]
    assert_that(created_skill.id not in skill_ids_after, equal_to(True))


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
@pytest.mark.assistant
def test_attach_multiple_skills_to_one_assistant(skill, assistant_factory, skill_utils):
    """Test attaching up to 10 skills to single assistant"""
    skills_count = 10
    created_assistant = assistant_factory.create()
    created_skills = []

    # Create and attach multiple skills
    for _ in range(skills_count):
        created_skill = skill()
        created_skills.append(created_skill)
        skill_utils.attach_skill_to_assistant(created_assistant.id, created_skill.id)

    # Verify all attached
    assistant_skills = skill_utils.get_assistant_skills(created_assistant.id)
    skill_ids = [skill.id for skill in assistant_skills]

    assert_that(len(assistant_skills), equal_to(skills_count))

    # Verify each skill is in the list
    for created_skill in created_skills:
        assert_that(created_skill.id in skill_ids, equal_to(True))


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
@pytest.mark.assistant
def test_bulk_attach_skill_to_assistants(skill, assistant_factory, skill_utils):
    """Test bulk attaching skill to multiple assistants."""
    created_skill = skill()

    # Create multiple assistants
    assistant_ids = []
    for _ in range(BULK_ATTACH_COUNT):
        asst = assistant_factory.create()
        assistant_ids.append(asst.id)

    # Bulk attach
    skill_utils.bulk_attach_skill(created_skill.id, assistant_ids)

    # Verify all assistants have the skill
    for assistant_id in assistant_ids:
        skills = skill_utils.get_assistant_skills(assistant_id)
        skill_ids = [skill.id for skill in skills]
        assert_that(created_skill.id in skill_ids, equal_to(True))

    # Get all assistants using this skill
    assistants = skill_utils.get_skill_assistants(created_skill.id)

    assert_that(len(assistants), equal_to(BULK_ATTACH_COUNT))


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
@pytest.mark.assistant
def test_get_skill_assistants(skill, assistant_factory, skill_utils):
    """Test getting all assistants using a skill."""
    created_skill = skill()
    created_assistant = assistant_factory.create()

    # Attach skill
    skill_utils.attach_skill_to_assistant(created_assistant.id, created_skill.id)

    # Get assistants using this skill
    assistants = skill_utils.get_skill_assistants(created_skill.id)

    assert_that(len(assistants), greater_than(0))


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
@pytest.mark.assistant
def test_detach_one_of_multiple_skills(skill, assistant_factory, skill_utils):
    """Test detaching one skill when multiple are attached."""
    # Create multiple skills
    skill1 = skill()
    skill2 = skill()
    skill3 = skill()

    created_assistant = assistant_factory.create()

    # Attach all skills
    skill_utils.attach_skill_to_assistant(created_assistant.id, skill1.id)
    skill_utils.attach_skill_to_assistant(created_assistant.id, skill2.id)
    skill_utils.attach_skill_to_assistant(created_assistant.id, skill3.id)

    # Detach only skill2
    skill_utils.detach_skill_from_assistant(created_assistant.id, skill2.id)

    # Verify skill2 is detached but others remain
    assistant_skills = skill_utils.get_assistant_skills(created_assistant.id)
    skill_ids = [skill.id for skill in assistant_skills]

    assert_that(skill1.id in skill_ids, equal_to(True))
    assert_that(skill2.id not in skill_ids, equal_to(True))
    assert_that(skill3.id in skill_ids, equal_to(True))


@pytest.mark.skill
@pytest.mark.api
@pytest.mark.assistant
def test_imported_skill_triggers_on_assistant_chat(
    assistant_factory, assistant_utils, skill_utils, import_skill_file_content
):
    """Test that imported MCP builder skill triggers when assistant is asked about MCP servers."""
    file_content, skill_name = import_skill_file_content

    # Import the skill
    imported_skill = skill_utils.import_skill(
        file_content=file_content,
        filename="mcp_builder.md",
    )

    # Create an assistant
    created_assistant = assistant_factory.create()

    # Attach the skill to the assistant
    skill_utils.attach_skill_to_assistant(created_assistant.id, imported_skill.id)

    # Ask the assistant to generate MCP server code
    prompt = "Generate code of simple mcp server example."
    response, triggered_tools = assistant_utils.ask_assistant(
        created_assistant,
        prompt,
        minimal_response=False,
    )

    # Verify the skill was triggered
    # Skills appear in triggered_tools as "skill" (generic)
    assert_that("skill", is_in(triggered_tools))
