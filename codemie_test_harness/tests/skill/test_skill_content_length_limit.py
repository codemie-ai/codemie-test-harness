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

"""Tests for the configurable skill content length limit."""

import pytest
from requests.exceptions import HTTPError

from hamcrest import assert_that, equal_to, not_none

from codemie_test_harness.tests.test_data.skill_test_data import (
    SKILL_DESCRIPTION,
    generate_boundary_content,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_response,
)


@pytest.fixture
def skill_content_limit_manager(client):
    """Clear any pre-existing SKILL_MAX_CONTENT_LENGTH config before the test so the
    environment starts from the system default. Delete the key and clean up created
    skills on teardown to leave the system in its default state."""
    # Setup: remove any custom config value so the system falls back to its built-in default.
    client.dynamic_config.delete("SKILL_MAX_CONTENT_LENGTH")

    skill_ids_to_clean: list = []

    class Manager:
        def register_skill(self, skill_id: str) -> None:
            skill_ids_to_clean.append(skill_id)

    yield Manager()

    # Teardown: delete the key (restores built-in default) and remove created skills.
    client.dynamic_config.delete("SKILL_MAX_CONTENT_LENGTH")
    for skill_id in skill_ids_to_clean:
        client.skills.delete(skill_id)


@pytest.mark.not_for_parallel_run
@pytest.mark.skill
@pytest.mark.api
def test_full_content_length_limit_lifecycle(
    client, skill_utils, skill_content_limit_manager
):
    manager = skill_content_limit_manager

    # Step 1 (AC2): Fixture cleared any custom config; verify built-in default is 30000.
    default_config = client.skills.get_config()
    assert_that(
        default_config.max_content_length,
        equal_to(30000),
        "AC2: built-in default limit must equal legacy hardcoded value (30000) when no config key is set",
    )

    # Step 2: Set limit to 5000.
    client.dynamic_config.set("SKILL_MAX_CONTENT_LENGTH", 5000)

    # Step 3: Verify limit is live.
    config = client.skills.get_config()
    assert_that(
        config.max_content_length,
        equal_to(5000),
        "Step 3: max_content_length must be 5000 after setting it",
    )

    # Step 4: Create skill over limit — must fail with 4xx and name the effective limit.
    with pytest.raises(HTTPError) as exc_info:
        skill_utils.create_skill(
            skill_name=get_random_name().replace("_", "-"),
            description=SKILL_DESCRIPTION,
            content=generate_boundary_content(5001),
        )
    assert_response(
        exc_info.value.response,
        422,
        "Value error, Skill content must not exceed 5000 characters (was 5001).",
    )

    # Step 5: Create skill at limit — must succeed.
    skill_name = get_random_name().replace("_", "-")
    created = skill_utils.create_skill(
        skill_name=skill_name,
        description=SKILL_DESCRIPTION,
        content=generate_boundary_content(5000),
    )
    assert_that(created, not_none(), "Step 5: skill at limit must be created")
    skill_id = created.id
    manager.register_skill(skill_id)

    # Step 6: GET skill — content stored intact.
    fetched = client.skills.get(skill_id)
    assert_that(
        len(fetched.content),
        equal_to(5000),
        "Step 6: content length must be exactly 5000 chars",
    )

    # Step 7: Reduce limit to 2000.
    client.dynamic_config.set("SKILL_MAX_CONTENT_LENGTH", 2000)

    # Step 8: GET skill — existing content readable, not truncated.
    fetched_after_reduce = client.skills.get(skill_id)
    assert_that(
        len(fetched_after_reduce.content),
        equal_to(5000),
        "Step 8: existing 5000-char content must not be truncated after limit reduction to 2000",
    )

    # Step 9: Edit skill over new limit — must fail with 4xx and name the new limit.
    with pytest.raises(HTTPError) as exc_info:
        skill_utils.update_skill(skill_id, content=generate_boundary_content(2001))
    assert_response(
        exc_info.value.response,
        422,
        "Value error, Skill content must not exceed 2000 characters (was 2001).",
    )

    # Step 10: Edit skill at new limit — must succeed.
    updated = skill_utils.update_skill(
        skill_id, content=generate_boundary_content(2000)
    )
    assert_that(
        updated, not_none(), "Step 10: edit at new limit (2000 chars) must succeed"
    )
