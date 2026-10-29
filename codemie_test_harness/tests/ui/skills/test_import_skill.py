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
UI Test Suite for Import Skill Feature

This test suite implements UI automated tests for importing skills from markdown files
following Page Object Model (POM) best practices.

Test Coverage:
- AC#1: Markdown import functionality (tests 5-7)
- AC#4, AC#6: ZIP bundle import error shows user-friendly message
"""

import pytest
from pathlib import Path

from codemie_test_harness.tests.ui.pageobject.skills.skills_page import SkillsPage
from codemie_test_harness.tests.ui.pageobject.skills.create_edit_skill_page import (
    CreateEditSkillPage,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name

# Get path to test data files
TEST_DATA_DIR = (
    Path(__file__).parent.parent.parent / "ui" / "test_data" / "files" / "skills"
)
VALID_SKILL_FILE = str(TEST_DATA_DIR / "valid_skill.md")

# ZIP bundle with two .md files and no SKILL.md at root — triggers the backend's
# "must contain exactly one SKILL.md" validation (HTTP 400).
ZIP_BUNDLE_MULTI_MD = str(TEST_DATA_DIR / "bundle_two_md.zip")


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
def test_import_skill_from_markdown_and_verify_in_list(page):
    """
    Test #6-7: Import markdown file, verify form population, save, and verify in list.

    AC#1: Web form creation & Import - Complete import workflow with validation.

    This test combines:
    - Test #6: Verify markdown import populates form fields
    - Test #7: Verify imported skill appears in skills list
    """
    #  Start from skills page to set correct navigation context
    skills_page = SkillsPage(page)
    skills_page.navigate_to()

    # Navigate to Create Skill page
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    # Upload valid skill markdown file
    create_page.upload_skill_file(VALID_SKILL_FILE)

    # Verify form is populated with imported content
    create_page.should_have_name_populated()
    create_page.should_have_description_populated()
    create_page.should_have_instructions_populated()

    # Update the skill name to a unique value to avoid conflicts
    skill_name = create_page.get_skill_name()
    skill_name = skill_name + get_random_name().replace("_", "-")
    create_page.fill_name(skill_name)

    # Save the imported skill
    create_page.click_save()

    # Verify the skill appears in the skills list with correct name
    skills_page.should_see_skill_with_name(skill_name)


@pytest.mark.sanity
@pytest.mark.skill
@pytest.mark.ui
def test_import_zip_bundle_with_multiple_md_files_shows_friendly_error(page):
    """TC-001: ZIP bundle with multiple .md files shows a user-friendly error.

    AC#4: Invalid ZIP → user sees a clear validation message (not a raw HTTP error).
    AC#6: UI displays a user-friendly error message instead of a raw HTTP error.

    The MR (codemie-ui!1527) fixed a bug where uploading a ZIP bundle containing
    two .md files (and no SKILL.md at root) caused the UI to display the raw
    "HTTP error 400" string instead of the structured backend error message.
    """
    create_page = CreateEditSkillPage(page)
    create_page.navigate_to()

    # Upload a ZIP bundle with two competing .md files — no SKILL.md at root.
    create_page.upload_skill_file(ZIP_BUNDLE_MULTI_MD)

    # Assert the error toast shows a user-friendly message, not a raw HTTP error.
    create_page.should_see_import_error_toast()
