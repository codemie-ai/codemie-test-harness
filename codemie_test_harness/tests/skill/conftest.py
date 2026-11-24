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

"""Fixtures for Skills tests."""

import os
import re
import pytest

from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.skill_utils import SkillsUtils


@pytest.fixture
def import_skill_file_content():
    """Fixture that provides MCP builder skill file content with randomized skill name.

    Returns:
        tuple: (file_content, skill_name) where file_content is the modified markdown
               with a unique skill name in the YAML frontmatter
    """
    # Path to test data directory
    test_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "test_data", "files", "skills"
    )

    # Read the mcp_builder.md file
    mcp_builder_file = os.path.join(test_data_dir, "mcp_builder.md")
    with open(mcp_builder_file, "r", encoding="utf-8") as f:
        file_content = f.read()

    # Replace the skill name in YAML frontmatter with a random name
    random_suffix = get_random_name().replace("_", "-")
    skill_name = f"mcp-builder-{random_suffix}"
    file_content = re.sub(
        r"(name:\s+)([^\n]+)",
        rf"\1{skill_name}",
        file_content,
        count=1,
    )

    return file_content, skill_name


@pytest.fixture
def skill_project(project):
    """Name of a fresh project created by the harness admin; removed after the test."""
    return project().name


@pytest.fixture
def other_skill_project(project):
    """Name of a second fresh project created by the harness admin; removed after the test."""
    return project().name


@pytest.fixture
def non_member_skill_utils(platform_user):
    """SkillsUtils for a platform_user who belongs to no project created for the test."""
    return SkillsUtils(platform_user.client)


@pytest.fixture
def member_skill_utils(platform_user, user_utils, skill_project):
    """SkillsUtils for a platform_user assigned to skill_project as a plain member.

    The client is a fresh login made after the assignment, so a backend that caches the
    user's projects per token cannot hold the list from before it.
    """
    user_utils.assign_user_to_project(
        platform_user.user_id, skill_project, is_project_admin=False
    )
    yield SkillsUtils(
        get_client(username=platform_user.email, password=platform_user.password)
    )
    try:
        user_utils.remove_user_from_project(platform_user.user_id, skill_project)
    except Exception:
        pass


@pytest.fixture
def created_skill_ids(skill_utils):
    """List collecting ids of skills a test created outside the `skill` factory; deleted after."""
    ids = []
    yield ids
    for skill_id in ids:
        try:
            skill_utils.delete_skill_by_id(skill_id)
        except Exception:
            pass
