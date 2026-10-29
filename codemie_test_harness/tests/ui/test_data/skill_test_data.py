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
Test data factory for Skills UI tests.

Provides test data structures and factory functions for creating
skills with various configurations.
"""

import random
import string
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List


def get_random_skill_name(prefix: str = "test-skill") -> str:
    """
    Generate a random skill name (kebab-case, no underscores).

    Skills require kebab-case format and don't allow underscores.
    """
    random_suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
    return f"{prefix}-{random_suffix}"


@dataclass
class SkillTestData:
    """Test data structure for a skill."""

    name: str
    description: str
    instructions: str
    scope: str  # "private" or "project"
    categories: List[str] = None  # Category name (e.g., "Testing", "Development")


def get_minimal_skill_data() -> SkillTestData:
    """
    Get test data for a minimal skill (name + instructions only).

    Returns:
        SkillTestData with minimal required fields (instructions >100 chars)
    """
    return SkillTestData(
        name=get_random_skill_name("test-skill"),
        description="Test skill for automated testing",
        instructions="""# Test Skill

## Description
This is a test skill for automated testing of the Skills functionality.

## Usage
Use this skill to verify that skill creation works correctly through the UI.

## Examples
- Example 1: Demonstrate basic skill usage
- Example 2: Test skill integration with assistants
""",
        scope="private",
    )


def get_full_skill_data() -> SkillTestData:
    """
    Get test data for a skill with all fields populated.

    Returns:
        SkillTestData with all fields
    """
    return SkillTestData(
        name=get_random_skill_name("full-test-skill"),
        description="Comprehensive test skill with all fields populated for testing purposes",
        instructions="""# Comprehensive Test Skill

## Purpose
This is a comprehensive test skill for validating the Skills feature with all available fields.

## Context
Use this skill when testing the Skills functionality in automated UI tests with full field coverage.

## Instructions
1. Follow user instructions carefully and precisely
2. Provide clear and concise responses with proper formatting
3. Use proper markdown formatting in all outputs
4. Validate input before processing

## Examples
- Example 1: When asked about testing, explain the testing approach and methodology
- Example 2: When asked about automation, describe automation benefits and best practices
- Example 3: Demonstrate proper error handling and edge case management

## Configuration
Configuration options and parameters for this skill.
""",
        scope="private",
        categories=["Testing"],
    )


def get_project_scope_skill_data() -> SkillTestData:
    """
    Get test data for a project-scoped skill.

    Returns:
        SkillTestData configured for project scope
    """
    return SkillTestData(
        name=get_random_skill_name("project-skill"),
        description="Project-scoped skill for testing shared functionality",
        instructions="""# Project Skill

## Description
This skill is shared with the project to test project-level skill functionality.

## Usage
Use this skill to verify project scope and sharing capabilities.

## Features
- Shared across project members
- Available to all project assistants
- Centralized skill management

## Examples
- Example 1: Test project-wide skill access
- Example 2: Verify skill sharing works correctly
""",
        scope="project",
    )


BUNDLE_FILE_NAME_TEMPLATE = "bundle_file_{index:04d}.txt"

_BUNDLE_SKILL_MD = """---
name: bundle-warning-skill
description: Skill archive built by an automated test to check the bundle file count warning
---

# Bundle Warning Skill

## Purpose
This archive carries a number of small companion files so that the skill editor can be checked
against the limit on the number of files an assistant workspace receives.

## Instructions
1. Read the companion files only when the task asks for them
2. Answer briefly and do not call any tool unless asked
"""


def bundle_file_name(index: int) -> str:
    """Name of the ``index``-th companion file in an archive made by ``build_skill_bundle_archive``."""
    return BUNDLE_FILE_NAME_TEMPLATE.format(index=index)


def build_skill_bundle_archive(directory: Path, companion_file_count: int) -> Path:
    """Write a skill archive: ``SKILL.md`` plus ``companion_file_count`` tiny companion files; return its path."""
    archive_path = directory / f"skill_bundle_{companion_file_count}_files.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("SKILL.md", _BUNDLE_SKILL_MD)
        for index in range(companion_file_count):
            archive.writestr(bundle_file_name(index), f"companion file {index}")
    return archive_path
