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
UI Test Suite for Create Skill Feature - Creation and Scope Tests

This test suite implements UI automated tests for skill creation and scope management
following Page Object Model (POM) best practices.

Test Coverage:
- AC#1: Web form creation (tests 1-4)
- AC#2: Private vs Project scope (tests 8-11)
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.skills.skills_page import SkillsPage
from codemie_test_harness.tests.ui.pageobject.skills.create_edit_skill_page import (
    CreateEditSkillPage,
)
from codemie_test_harness.tests.ui.test_data.skill_test_data import (
    get_minimal_skill_data,
    get_full_skill_data,
    get_project_scope_skill_data,
)


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
def test_skills_page_elements_visibility(page):
    """
    Test #1: Verify Skills page loads with create/import buttons.

    AC#1: Web form creation - Verify main page elements.
    """
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Verify we are on the Skills page
    skills_page.should_be_on_skills_page()

    # Verify essential page elements
    skills_page.should_have_page_heading()
    skills_page.should_have_page_description()
    skills_page.should_have_create_button_visible()
    skills_page.should_have_tabs_visible()
    skills_page.should_have_filters_visible()


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
def test_create_skill_page_elements_visibility(page):
    """
    Test #2: Verify Create Skill form has all required fields.

    AC#1: Web form creation - Verify form structure.
    """
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    # Verify we are on Create Skill page
    create_page.should_be_on_create_skill_page()

    # Verify all form fields are visible
    create_page.should_have_all_form_fields_visible()

    # Verify action buttons
    create_page.should_have_action_buttons_visible()

    # Verify import/export buttons
    create_page.should_have_import_button_visible()
    create_page.should_have_download_button_visible()


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
def test_create_skill_via_web_form_minimal_fields(page):
    """
    Test #3: Create skill with name and instructions (happy path).

    AC#1: Web form creation - Minimal required fields.
    """
    #  Start from skills page to set correct navigation context
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Get test data
    test_data = get_minimal_skill_data()

    # Navigate to create page
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    # Create skill with minimal fields
    create_page.create_skill(
        name=test_data.name,
        description=test_data.description,
        instructions=test_data.instructions,
        shared=False,
    )

    # Apply Private scope filter
    skills_page.visibility_private_radio.click()

    # Verify skill appears in list
    skills_page.should_see_skill_with_name(test_data.name)


@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
def test_create_skill_via_web_form_all_fields(page):
    """
    Test #4: Create skill with all fields populated.

    AC#1: Web form creation - All fields including description and format.
    """
    #  Start from skills page to set correct navigation context
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Get comprehensive test data
    test_data = get_full_skill_data()

    # Navigate to create page
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    # Fill all form fields
    create_page.fill_name(test_data.name)
    create_page.fill_description(test_data.description)
    create_page.fill_instructions(test_data.instructions)
    create_page.toggle_shared(False)  # Private scope

    # Select categories if specified
    if test_data.categories:
        for category in test_data.categories:
            create_page.select_category(category)

    create_page.select_tool()
    create_page.click_save()

    # Verify skill appears in list
    skills_page.should_see_skill_with_name(test_data.name)


@pytest.mark.skill
@pytest.mark.ui
def test_skill_scope_toggle_private_and_project(page):
    """
    Test #8: Toggle between Private and Project scope.

    AC#2: Private vs Project scope - Toggle functionality.
    """
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    # Verify default is unchecked (Private)
    create_page.should_have_shared_unchecked()

    # Toggle to Project scope
    create_page.toggle_shared(True)
    create_page.should_have_shared_checked()

    # Toggle back to Private scope
    create_page.toggle_shared(False)
    create_page.should_have_shared_unchecked()


@pytest.mark.skill
@pytest.mark.ui
def test_create_skill_with_project_scope(page):
    """
    Test #10: Create skill with Project scope enabled.

    AC#2: Private vs Project scope - Create project-scoped skill.
    """
    #  Start from skills page to set correct navigation context
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Get project-scoped test data
    test_data = get_project_scope_skill_data()

    # Navigate and create skill with Project scope
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    create_page.create_skill(
        name=test_data.name,
        description=test_data.description,
        instructions=test_data.instructions,
        shared=True,  # Project scope
    )

    # Apply Project scope filter
    skills_page.visibility_project_radio.click()

    # Verify successful creation
    skills_page.should_see_skill_with_name(test_data.name)
