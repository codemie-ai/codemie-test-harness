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


"""Shared fixtures for skills UI tests."""

import pytest

from codemie_test_harness.tests.ui.pageobject.skills.skills_page import SkillsPage


@pytest.fixture
def skill_to_favorite(page, skill):
    """Create a skill through the API and undo its favorite state after the test.

    The favorite is stored in the user's preferences, not on the skill, so deleting
    the skill does not clear it. Teardown opens the Skills list and removes the
    favorite through the UI when the test left it set; it runs before the ``skill``
    factory deletes the skill.
    """
    created_skill = skill()
    yield created_skill
    try:
        SkillsPage(page).unfavorite_skill_if_favorited(created_skill.name)
    except Exception:
        pass
