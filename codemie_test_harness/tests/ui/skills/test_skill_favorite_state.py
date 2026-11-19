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


import pytest

from codemie_test_harness.tests.ui.pageobject.skills.skills_page import SkillsPage


# @case skills-and-workflows-favorite-state_TC_001
@pytest.mark.skill
@pytest.mark.ui
def test_skill_favorite_star_stays_filled_after_reload(page, skill_to_favorite):
    """A favorited skill keeps a filled star after the Skills list is reloaded.

    The test runs as its own fresh user, so its favorites are private to it.
    """
    skills_page = SkillsPage(page)
    skills_page.should_see_skill_with_name(skill_to_favorite.name)
    skills_page.should_show_skill_not_favorited(skill_to_favorite.name)

    skills_page.favorite_skill(skill_to_favorite.name)
    skills_page.should_show_skill_favorited(skill_to_favorite.name)

    skills_page.refresh_page()
    skills_page.should_see_skill_card(skill_to_favorite.name)
    skills_page.should_show_skill_favorited(skill_to_favorite.name)
