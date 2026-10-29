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

"""Test data for Skills functionality tests."""

from codemie_test_harness.tests.utils.base_utils import get_random_name


def unique_slug() -> str:
    return get_random_name().replace("_", "-")


# Valid test data
# Skill names must be kebab-case (lowercase letters, numbers, and hyphens only)
SKILL_NAME = get_random_name().replace("_", "-")
SKILL_DESCRIPTION = "A test skill for automated testing"
SKILL_CONTENT = """# Test Skill

## Description
This is a test skill for automated testing.

## Usage
Use this skill to test the Skills API functionality.

## Examples
- Example 1: Demonstrate basic usage
- Example 2: Show advanced features
"""

# Import test data
IMPORT_MD_CONTENT = f"""---
name: imported-skill-{get_random_name().replace("_", "-")}
description: This skill was imported from a markdown file to test the import functionality
---

# Imported Skill

## Description
This skill was imported from a markdown file to test the import functionality.

## Implementation
Implementation details for the imported skill.

### Key Features
- Automatic parsing from markdown
- Preservation of formatting
- Support for code blocks

### Usage
```python
# Example usage
from skill import imported_skill
result = imported_skill.execute()
```

## Configuration
Configuration options for the imported skill.
"""
IMPORT_FILENAME = "test_skill.md"

# Bulk attach test data
BULK_ATTACH_COUNT = 3


def generate_boundary_content(length: int) -> str:
    """Generate valid skill content of exactly `length` characters for boundary tests."""
    header = "# Boundary Test\n\n"
    if length < len(header):
        raise ValueError(
            f"length {length} is shorter than the fixed header ({len(header)} chars)"
        )
    return header + "x" * (length - len(header))


# Updated skill data
UPDATED_SKILL_NAME = get_random_name().replace("_", "-")
UPDATED_DESCRIPTION = "Updated skill description for testing"
UPDATED_CONTENT = """# Updated Skill

## Description
This skill content has been updated to test the update functionality.

## Changes
- Change 1: Updated description
- Change 2: Modified content structure
- Change 3: Added new examples

## New Features
Features added in this update.
"""
