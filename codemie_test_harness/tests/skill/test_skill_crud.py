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

"""Tests for Skills CRUD operations."""

import pytest
from hamcrest import assert_that, contains_string, equal_to, greater_than, not_none

from codemie_sdk.models.skill import SkillVisibility
from codemie_test_harness.tests.test_data.skill_test_data import (
    UPDATED_CONTENT,
    UPDATED_DESCRIPTION,
    UPDATED_SKILL_NAME,
    SKILL_CONTENT,
    SKILL_DESCRIPTION,
    SKILL_NAME,
)


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
@pytest.mark.sanity
def test_create_skill(skill):
    """Test creating a new skill."""
    created_skill = skill(
        skill_name=SKILL_NAME,
        description=SKILL_DESCRIPTION,
        content=SKILL_CONTENT,
    )

    assert_that(created_skill.name, equal_to(SKILL_NAME))
    assert_that(created_skill.description, equal_to(SKILL_DESCRIPTION))
    assert_that(created_skill.content, equal_to(SKILL_CONTENT))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_get_skill_by_id(skill, skill_utils):
    """Test retrieving skill by ID."""
    created_skill = skill()

    retrieved_skill = skill_utils.get_skill_by_id(created_skill.id)

    assert_that(retrieved_skill.id, equal_to(created_skill.id))
    assert_that(retrieved_skill.name, equal_to(created_skill.name))
    assert_that(retrieved_skill.description, equal_to(created_skill.description))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_list_skills(skill, skill_utils):
    """Test listing skills."""
    # Create a skill first
    skill()

    response = skill_utils.client.skills.list(per_page=10)

    assert_that(response.total, greater_than(0))
    assert_that(len(response.skills), greater_than(0))
    assert_that(response.page, equal_to(0))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_update_skill_all_fields(skill, skill_utils):
    """Test updating all skill fields at once."""
    created_skill = skill()

    updated_skill = skill_utils.update_skill(
        created_skill.id,
        name=UPDATED_SKILL_NAME,
        description=UPDATED_DESCRIPTION,
        content=UPDATED_CONTENT,
    )

    assert_that(updated_skill.name, equal_to(UPDATED_SKILL_NAME))
    assert_that(updated_skill.description, equal_to(UPDATED_DESCRIPTION))
    assert_that(updated_skill.content, equal_to(UPDATED_CONTENT))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_delete_skill(skill, skill_utils):
    """Test deleting a skill."""
    created_skill = skill()

    # Delete the skill
    skill_utils.delete_skill(created_skill)

    # Verify it's deleted (should raise error on get)
    with pytest.raises(Exception):
        skill_utils.get_skill_by_id(created_skill.id)


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_get_skill_by_name(skill, skill_utils):
    """Test retrieving skill by name."""
    created_skill = skill(skill_name=SKILL_NAME)

    retrieved_skill = skill_utils.get_skill_by_name(SKILL_NAME)

    assert_that(retrieved_skill, not_none())
    assert_that(retrieved_skill.name, equal_to(SKILL_NAME))
    assert_that(retrieved_skill.id, equal_to(created_skill.id))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_create_skill_with_visibility_user(skill):
    """Test creating skill with USER visibility."""
    created_skill = skill(visibility=SkillVisibility.PRIVATE)

    assert_that(created_skill.visibility, equal_to(SkillVisibility.PRIVATE))


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_skill_content_preserved(skill, skill_utils):
    """Test that skill Markdown content is preserved correctly."""
    content_with_formatting = """# Test Skill

## Section 1
Content with **bold** and *italic* text.

### Subsection
- List item 1
- List item 2

```python
# Code block
def example():
    return "test"
```

## Section 2
More content here.
"""

    created_skill = skill(content=content_with_formatting)
    retrieved_skill = skill_utils.get_skill_by_id(created_skill.id)

    assert_that(retrieved_skill.content, equal_to(content_with_formatting))
    assert_that(retrieved_skill.content, contains_string("# Test Skill"))
    assert_that(retrieved_skill.content, contains_string("```python"))
