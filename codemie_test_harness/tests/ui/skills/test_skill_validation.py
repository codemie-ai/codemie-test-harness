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
UI Test Suite for Skill Validation

This test suite implements UI automated tests for skill format validation
following Page Object Model (POM) best practices.

Test Coverage:
- Create Skill page Fields format validation
"""

import pytest
from codemie_test_harness.tests.ui.pageobject.skills.create_edit_skill_page import (
    CreateEditSkillPage,
)


@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_skill_required_fields_validation(page):
    """
    Test #30: Required fields validation
    """
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    create_page.click_create()

    create_page.should_have_required_name_error()
    create_page.should_have_required_description_error()
    create_page.should_have_required_instructions_error()


@pytest.mark.skill
@pytest.mark.ui
@pytest.mark.prod_regression
def test_skill_fields_format_validation(page):
    """
    Test: Fields Format validation.
    """
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    # Name field: Name must be kebab-case (lowercase letters, numbers, and hyphens only)
    create_page.fill_name("Invalid Name With Spaces")

    # Description field: Description must be at least 10 characters
    create_page.fill_description("short")

    # Instructions field: Instructions must be at least 100 characters
    create_page.fill_instructions("Too short instructions")

    # Try to save
    create_page.click_save()

    # Verify format validation errors
    create_page.should_have_name_format_error()
    create_page.should_have_description_length_error()
    create_page.should_have_instructions_length_error()
