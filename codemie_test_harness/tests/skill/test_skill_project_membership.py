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

"""Project membership is required to create, import or move a skill into a project."""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_item,
    is_not,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.skill_test_data import (
    SKILL_CONTENT,
    SKILL_DESCRIPTION,
    unique_slug,
)
from codemie_test_harness.tests.utils.user_utils import UserUtils

PERMISSION_DENIED = "Permission denied"


# @case skill-project-membership_TC_001
@pytest.mark.skill
@pytest.mark.project
@pytest.mark.api
def test_create_skill_in_project_as_non_member_is_forbidden(
    non_member_skill_utils, skill_utils, skill_project
):
    """A user outside the project gets 403 and no skill is stored."""
    skill_name = unique_slug()

    with pytest.raises(HTTPError) as exc_info:
        non_member_skill_utils.send_create_skill_request(
            skill_name=skill_name, project_name=skill_project
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        "Creating a skill in a project the caller does not belong to must be forbidden",
    )
    error_text = UserUtils.error_text(exc_info.value)
    assert_that(error_text, contains_string(PERMISSION_DENIED))
    assert_that(error_text, contains_string(skill_project))
    assert_that(
        skill_utils.list_project_skill_names(skill_project),
        is_not(has_item(skill_name)),
        "A denied create must not leave a skill behind",
    )


# @case skill-project-membership_TC_002
@pytest.mark.skill
@pytest.mark.project
@pytest.mark.api
def test_import_skill_into_project_as_non_member_is_forbidden(
    non_member_skill_utils, skill_utils, skill_project, import_skill_file_content
):
    """A user outside the project gets 403 when importing a valid skill file."""
    file_content, skill_name = import_skill_file_content

    with pytest.raises(HTTPError) as exc_info:
        non_member_skill_utils.send_import_skill_request(
            file_content=file_content,
            filename="mcp_builder.md",
            project_name=skill_project,
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        "Importing a skill into a project the caller does not belong to must be forbidden",
    )
    assert_that(
        UserUtils.error_text(exc_info.value), contains_string(PERMISSION_DENIED)
    )
    assert_that(
        skill_utils.list_project_skill_names(skill_project),
        is_not(has_item(skill_name)),
        "A denied import must not leave a skill behind",
    )


# @case skill-project-membership_TC_003
@pytest.mark.skill
@pytest.mark.project
@pytest.mark.api
def test_create_skill_in_project_as_plain_member_succeeds(
    member_skill_utils, skill_project, created_skill_ids
):
    """A plain member (not project admin) can still create a skill in the project."""
    skill_name = unique_slug()

    response, _ = member_skill_utils.send_create_skill_request(
        skill_name=skill_name, project_name=skill_project
    )
    created_skill_ids.append(response.id)

    assert_that(response.name, equal_to(skill_name))
    assert_that(response.project, equal_to(skill_project))
    assert_that(response.description, equal_to(SKILL_DESCRIPTION))
    assert_that(response.content, equal_to(SKILL_CONTENT))


# @case skill-project-membership_TC_005
@pytest.mark.skill
@pytest.mark.project
@pytest.mark.api
def test_move_skill_to_project_as_non_member_is_forbidden(
    member_skill_utils,
    skill_utils,
    skill_project,
    other_skill_project,
    created_skill_ids,
):
    """A member of the first project only cannot move their skill into the second."""
    skill, _ = member_skill_utils.send_create_skill_request(project_name=skill_project)
    created_skill_ids.append(skill.id)

    with pytest.raises(HTTPError) as exc_info:
        member_skill_utils.send_move_skill_request(skill.id, other_skill_project)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        "Moving a skill into a project the caller does not belong to must be forbidden",
    )
    assert_that(
        UserUtils.error_text(exc_info.value), contains_string(PERMISSION_DENIED)
    )
    assert_that(
        skill_utils.get_skill_by_id(skill.id).project,
        equal_to(skill_project),
        "A denied move must leave the skill in its original project",
    )
