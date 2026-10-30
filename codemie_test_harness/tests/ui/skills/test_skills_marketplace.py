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
UI Test Suite for Skills Marketplace Feature

This test suite implements UI automated tests for the Skills Marketplace
following Page Object Model (POM) best practices.

Test Coverage:
- AC#3: Marketplace functionality (tests 13-21)
- Test: Publish to Marketplace via 3-dot menu
- Test: Marketplace filtering (Categories, Created By)
- Test: Marketplace search
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.skills.skills_page import SkillsPage
from codemie_test_harness.tests.ui.pageobject.skills.skills_marketplace_page import (
    SkillsMarketplacePage,
)
from codemie_test_harness.tests.ui.pageobject.skills.create_edit_skill_page import (
    CreateEditSkillPage,
)
from codemie_test_harness.tests.ui.test_data.skill_test_data import (
    get_full_skill_data,
)


@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_skills_marketplace_page_elements_visibility(page):
    """
    Test #13: Verify Marketplace page loads with browse UI.

    AC#3: Marketplace - Page structure and navigation.
    """
    # Navigate to Skills page first
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Switch to Marketplace tab
    skills_page.switch_to_marketplace_tab()

    # Verify on Marketplace page
    marketplace_page = SkillsMarketplacePage(page)
    marketplace_page.should_be_on_marketplace_page()

    # Verify marketplace elements are visible
    marketplace_page.should_have_marketplace_elements_visible()
    marketplace_page.should_have_filters_visible()

    # Verify marketplace displays skills cards
    marketplace_page.should_display_skills()

    # Verify skills count is greater than 0
    marketplace_page.should_have_skill_count_number()

    # Verify skill card elements are visible
    marketplace_page.should_have_skill_card_elements_visible()


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_publish_private_skill_to_marketplace(page):
    """
    Test #17: Publish a private skill to marketplace via 3-dot menu.

    AC#3: Marketplace - Publish workflow from skill card menu.
    """
    # Navigate to skills list
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Create a private skill
    test_data = get_full_skill_data()
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    create_page.create_skill(
        name=test_data.name,
        description=test_data.description,
        instructions=test_data.instructions,
        categories=test_data.categories,
        shared=False,
    )

    # Search for the newly created skill
    skills_page.should_see_skill_with_name(test_data.name)

    # Verify Publish to Marketplace button is visible in 3-dot menu
    skills_page.should_have_publish_button_in_menu(test_data.name)

    skills_page.close_skill_card_menu()

    # Click publish from 3-dot menu
    skills_page.publish_skill_to_marketplace(test_data.name)

    # Confirm publish dialog
    skills_page.publish_confirm_dialog_should_be_visible()
    skills_page.confirm_publish()

    # Navigate to marketplace
    marketplace_page = SkillsMarketplacePage(page)
    marketplace_page.navigate_to()

    # Search for the published skill in marketplace
    marketplace_page.search_skills(test_data.name)

    # Verify published skill appears in marketplace
    marketplace_page.should_see_skill_in_marketplace(test_data.name)


@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_marketplace_filter_by_category(page):
    """
    Test #19: Filter marketplace skills by category.

    AC#3: Marketplace - Categories filter.
    """
    # Navigate to skills list
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Create a private skill
    test_data = get_full_skill_data()
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    create_page.create_skill(
        name=test_data.name,
        description=test_data.description,
        instructions=test_data.instructions,
        categories=test_data.categories,
        shared=False,
    )

    # Click publish from 3-dot menu
    skills_page.publish_skill_to_marketplace(test_data.name)

    # Confirm publish dialog
    skills_page.confirm_publish()

    # Navigate to marketplace
    marketplace_page = SkillsMarketplacePage(page)
    marketplace_page.navigate_to()

    # Filter by category
    marketplace_page.filter_by_category(test_data.categories[0])

    # Search for the published skill in marketplace
    marketplace_page.search_skills(test_data.name)

    # Verify filtered skill appears
    marketplace_page.should_see_skill_in_marketplace(test_data.name)


@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_marketplace_filter_by_created(page):
    """
    Test #20: Filter marketplace skills by Created By.

    AC#3: Marketplace - Created By filter.
    """
    # Navigate to skills list
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Create a private skill
    test_data = get_full_skill_data()
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    create_page.create_skill(
        name=test_data.name,
        description=test_data.description,
        instructions=test_data.instructions,
        categories=test_data.categories,
        shared=False,
    )

    # Click publish from 3-dot menu
    skills_page.publish_skill_to_marketplace(test_data.name)

    # Confirm publish dialog
    skills_page.confirm_publish()

    # Navigate to marketplace
    marketplace_page = SkillsMarketplacePage(page)
    marketplace_page.navigate_to()

    # Filter by created by me
    marketplace_page.filter_by_created_by_me(True)

    # Search for the published skill in marketplace
    marketplace_page.search_skills(test_data.name)

    # Verify filtered skill appears
    marketplace_page.should_see_skill_in_marketplace(test_data.name)


@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_marketplace_search_skills_by_name(page):
    """
    Test #21: Search skills in marketplace.

    AC#3: Marketplace - Search functionality.
    """
    # Navigate to skills list
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Create a private skill
    test_data = get_full_skill_data()
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    create_page.create_skill(
        name=test_data.name,
        description=test_data.description,
        instructions=test_data.instructions,
        categories=test_data.categories,
        shared=False,
    )

    # Click publish from 3-dot menu
    skills_page.publish_skill_to_marketplace(test_data.name)

    # Confirm publish dialog
    skills_page.confirm_publish()

    # Navigate to marketplace
    marketplace_page = SkillsMarketplacePage(page)
    marketplace_page.navigate_to()

    # Search for skill by name
    marketplace_page.search_skills(test_data.name)

    # Verify published skill appears
    marketplace_page.should_see_skill_in_marketplace(test_data.name)
