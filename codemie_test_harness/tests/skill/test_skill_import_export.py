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

"""Tests for Skills import and export operations."""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    instance_of,
    is_not,
    not_none,
    starts_with,
)

from codemie_test_harness.tests.test_data.skill_test_data import (
    IMPORT_FILENAME,
    IMPORT_MD_CONTENT,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_import_skill_from_md(skill_utils, import_skill_file_content):
    """Test importing skill from markdown file."""
    file_content, skill_name = import_skill_file_content

    imported_skill = skill_utils.import_skill(
        file_content=file_content,
        filename="mcp_builder.md",
    )

    assert_that(imported_skill.id, not_none())
    assert_that(imported_skill.name, not_none())
    assert_that(imported_skill.content, contains_string("MCP Server Development Guide"))
    assert_that(imported_skill.content, contains_string("Model Context Protocol"))


@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_import_skill_preserves_formatting(skill_utils):
    """Test that imported skill preserves markdown formatting."""
    markdown_content = f"""---
    name: test-skill-formatting-{get_random_name().replace("_", "-")}
    description: A test skill to verify formatting preservation
    ---
    
    # Test Skill
    
    ## Features
    - Feature 1
    - Feature 2
    
    ### Code Example
    ```python
    def example():
        return "test"
    ```
    
    ## Configuration
    Configuration details here.
    """

    imported_skill = skill_utils.import_skill(
        file_content=markdown_content,
        filename="test_formatting.md",
    )

    assert_that(imported_skill.content, contains_string("# Test Skill"))
    assert_that(imported_skill.content, contains_string("```python"))
    assert_that(imported_skill.content, contains_string("- Feature 1"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_export_skill(skill, skill_utils):
    """Test exporting a skill."""
    created_skill = skill()

    exported_data = skill_utils.export_skill(created_skill.id)

    # Verify exported data is a non-empty string
    assert_that(exported_data, instance_of(str))
    assert_that(exported_data, is_not(""))

    # Verify it contains YAML frontmatter
    assert_that(exported_data, starts_with("---"))

    # Verify it contains the skill content
    assert_that(exported_data, contains_string(created_skill.name))
    assert_that(exported_data, contains_string(created_skill.description))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_import_and_export_roundtrip(skill_utils):
    """Test importing a skill and then exporting it."""
    # Import skill
    imported_skill = skill_utils.import_skill(
        file_content=IMPORT_MD_CONTENT,
        filename=IMPORT_FILENAME,
    )

    # Export the imported skill
    exported_data = skill_utils.export_skill(imported_skill.id)

    # Verify exported data is a non-empty string
    assert_that(exported_data, instance_of(str))
    assert_that(exported_data, is_not(""))

    # Verify it contains YAML frontmatter
    assert_that(exported_data, starts_with("---"))

    # Verify exported content matches imported content structure
    assert_that(exported_data, contains_string(imported_skill.name))
    assert_that(exported_data, contains_string("Imported Skill"))
    assert_that(exported_data, contains_string("Implementation details"))
