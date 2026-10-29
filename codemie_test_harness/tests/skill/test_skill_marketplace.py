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

"""Tests for Skills marketplace operations (publish/unpublish)."""

import random
import pytest
from codemie_sdk.models.skill import SkillVisibility
from hamcrest import assert_that, contains_string, equal_to, has_key

from codemie_test_harness.tests.test_data.skill_test_data import (
    SKILL_CONTENT,
    SKILL_DESCRIPTION,
    SKILL_NAME,
)


@pytest.fixture
def get_random_categories(skill_utils):
    """Fixture that returns a function to get random categories.

    Returns:
        Function that accepts count parameter and returns random category values
    """

    def _get_random_categories(count: int = 3):
        """Get random categories from available skill categories.

        Args:
            count: Number of random categories to return (default: 3)

        Returns:
            List of random category values
        """
        categories = skill_utils.list_categories()
        category_values = [cat.value for cat in categories]
        # Return up to 'count' random categories, or all if fewer available
        return random.sample(category_values, min(count, len(category_values)))

    return _get_random_categories


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_publish_skill(skill, skill_utils, get_random_categories):
    """Test publishing skill to marketplace."""
    created_skill = skill(
        skill_name=SKILL_NAME,
        description=SKILL_DESCRIPTION,
        content=SKILL_CONTENT,
    )

    categories = get_random_categories()
    response = skill_utils.publish_skill(created_skill.id, categories=categories)

    # Verify response message format
    assert_that(response, has_key("message"))
    assert_that(
        response["message"],
        contains_string(
            f"Skill {created_skill.id} published to marketplace successfully"
        ),
    )

    # Get the skill by ID and verify it has been published
    published_skill = skill_utils.get_skill_by_id(created_skill.id)

    # Verify visibility is now PUBLIC
    assert_that(published_skill.visibility, equal_to(SkillVisibility.PUBLIC))

    # Verify all categories were applied
    assert_that(set(published_skill.categories), equal_to(set(categories)))


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
@pytest.mark.enterprise
def test_unpublish_skill(skill, skill_utils, get_random_categories):
    """Test unpublishing skill from marketplace."""
    original_visibility = SkillVisibility.PRIVATE
    created_skill = skill(
        skill_name=SKILL_NAME,
        description=SKILL_DESCRIPTION,
        content=SKILL_CONTENT,
        visibility=original_visibility,
    )

    # Publish first
    categories = get_random_categories()
    skill_utils.publish_skill(created_skill.id, categories=categories)

    # Verify it was published
    published_skill = skill_utils.get_skill_by_id(created_skill.id)
    assert_that(published_skill.visibility, equal_to(SkillVisibility.PUBLIC))
    assert_that(set(published_skill.categories), equal_to(set(categories)))

    # Unpublish
    response = skill_utils.unpublish_skill(created_skill.id)

    # Verify response message format'
    assert_that(response, has_key("message"))
    assert_that(
        response["message"],
        contains_string(
            f"Skill {created_skill.id} unpublished from marketplace successfully"
        ),
    )

    # Get the skill by ID and verify it has been unpublished
    unpublished_skill = skill_utils.get_skill_by_id(created_skill.id)

    # Verify visibility reverted back to original
    assert_that(unpublished_skill.visibility, equal_to(original_visibility))


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
@pytest.mark.enterprise
def test_publish_skill_without_categories(skill, skill_utils):
    """Test publishing skill without explicit categories."""
    created_skill = skill(
        skill_name=SKILL_NAME,
        description=SKILL_DESCRIPTION,
        content=SKILL_CONTENT,
    )

    response = skill_utils.publish_skill(created_skill.id)

    # Verify response message format
    assert_that(response, has_key("message"))
    assert_that(
        response["message"],
        contains_string(
            f"Skill {created_skill.id} published to marketplace successfully"
        ),
    )

    # Get the skill by ID and verify it has been published
    published_skill = skill_utils.get_skill_by_id(created_skill.id)

    # Verify visibility is now PUBLIC
    assert_that(published_skill.visibility, equal_to(SkillVisibility.PUBLIC))

    # Verify all categories were applied
    assert_that(set(published_skill.categories), equal_to(set()))
