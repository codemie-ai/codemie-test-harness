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
UI tests for skill built-in subagent toggle.

Covers:
    TC-018  UI skill subagent toggle — visibility, enable, disable, persistence
"""

import pytest
from hamcrest import assert_that, equal_to
from codemie_test_harness.tests.test_data.skill_test_data import (
    SKILL_CONTENT,
    SKILL_DESCRIPTION,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.ui.pageobject.skills.create_edit_skill_page import (
    CreateEditSkillPage,
)

BUILTIN_SUBAGENT_ID = "GENERAL_PURPOSE_SUBAGENT"


# ---------------------------------------------------------------------------
# TC-018  Toggle visibility, enable, disable, and persistence
# ---------------------------------------------------------------------------


@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_skill_subagent_toggle_visible(page, skill):
    """TC-018a: Built-in subagent toggle is visible on the skill settings page."""
    created_skill = skill(
        skill_name=get_random_name().replace("_", "-"),
        description=SKILL_DESCRIPTION,
        content=SKILL_CONTENT,
    )
    edit_page = CreateEditSkillPage(page)
    edit_page.navigate_to_edit(created_skill.id)
    edit_page.should_see_subagent_toggle()


@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_skill_subagent_toggle_enable_persist(page, skill, skill_utils):
    """TC-018b: Enable toggle → save → reload → toggle is ON and API returns the value."""
    created_skill = skill(
        skill_name=get_random_name().replace("_", "-"),
        description=SKILL_DESCRIPTION,
        content=SKILL_CONTENT,
    )

    edit_page = CreateEditSkillPage(page)
    edit_page.navigate_to_edit(created_skill.id)

    # Enable subagent spawning
    edit_page.toggle_subagent_spawning(enable=True)
    edit_page.click_save()

    # Reload and verify UI persists
    edit_page.navigate_to_edit(created_skill.id)
    edit_page.should_see_subagent_setting(value=True)

    # Also verify via SDK
    api_skill = skill_utils.get_skill_by_id(created_skill.id)
    assert_that(
        api_skill.enabled_builtin_subagents,
        equal_to([BUILTIN_SUBAGENT_ID]),
        "API should return enabled_builtin_subagents=[GENERAL_PURPOSE_SUBAGENT] after toggle ON",
    )


@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_skill_subagent_toggle_disable_persist(page, raw_skill, skill_utils):
    """TC-018c: Enable then disable toggle → save → reload → toggle is OFF and API reflects []."""
    created = raw_skill(
        [BUILTIN_SUBAGENT_ID], content=SKILL_CONTENT, description=SKILL_DESCRIPTION
    )
    skill_id = created.id

    edit_page = CreateEditSkillPage(page)
    edit_page.navigate_to_edit(skill_id)

    # Verify toggle is ON (pre-condition)
    edit_page.should_see_subagent_setting(value=True)

    # Disable subagent spawning
    edit_page.toggle_subagent_spawning(enable=False)
    edit_page.click_save()

    # Reload and verify UI reflects disabled state
    edit_page.navigate_to_edit(skill_id)
    edit_page.should_see_subagent_setting(value=False)

    # Also verify via SDK
    api_skill = skill_utils.get_skill_by_id(skill_id)
    assert_that(
        api_skill.enabled_builtin_subagents,
        equal_to([]),
        "API should return enabled_builtin_subagents=[] after toggle OFF",
    )
