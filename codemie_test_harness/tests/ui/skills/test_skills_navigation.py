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
UI Test Suite for Skills Navigation

This test suite implements UI automated tests for skills navigation and filtering
following Page Object Model (POM) best practices.

Test Coverage:
- AC#2: Filtering by scope (test 12)
- AC#6: Navigation (tests 34-36)
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.components import Menu
from codemie_test_harness.tests.ui.pageobject.skills.skills_page import SkillsPage
from codemie_test_harness.tests.ui.test_data.skill_test_data import (
    get_minimal_skill_data,
)


@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
def test_skills_navigation_from_main_menu(page):
    """
    Test #34: Navigate to Skills page from main menu.

    AC#6: UI/Backend/Navigation - Main menu navigation.
    """
    # Click on Skills menu item in sidebar
    main_menu = Menu(page)
    main_menu.navigate_to_skills()

    # Verify navigation to Skills page
    skills_page = SkillsPage(page)
    skills_page.should_be_on_skills_page()

    # Verify page elements loaded
    skills_page.should_have_page_heading()
    skills_page.should_have_create_button_visible()


@pytest.mark.skill
@pytest.mark.ui
def test_create_skill_back_button_returns_to_list(page):
    """
    Test #35: Back button returns to skills list.

    AC#6: UI/Backend/Navigation - Back button functionality.
    """
    # Navigate to skills list
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Click Create Skill
    create_page = skills_page.click_create_skill()

    # Verify on Create Skill page
    create_page.should_be_on_create_skill_page()

    # Click Back button
    create_page.click_back()

    # Verify returned to skills list
    skills_page.should_be_on_skills_page()


@pytest.mark.skill
@pytest.mark.ui
def test_create_skill_cancel_returns_to_list(page):
    """
    Test #36: Cancel button returns to skills list.

    AC#6: UI/Backend/Navigation - Cancel button functionality.
    """
    # Navigate to skills list
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Click Create Skill
    create_page = skills_page.click_create_skill()

    # Verify on Create Skill page
    create_page.should_be_on_create_skill_page()

    # Fill some fields (simulate user input)
    test_data = get_minimal_skill_data()
    create_page.fill_name(test_data.name)
    create_page.fill_description(test_data.description)

    # Click Cancel button
    create_page.click_cancel()

    # Verify returned to skills list
    skills_page.should_be_on_skills_page()

    # Verify skill was not created (should not appear in list)
    skills_page.should_not_see_skill_with_name(test_data.name)
