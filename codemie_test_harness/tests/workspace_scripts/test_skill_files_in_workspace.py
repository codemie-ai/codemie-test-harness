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

"""Skill bundle files in the conversation workspace.

When an assistant with the workspace toolkit and the script tool handles a request, the files of every
attached skill appear in the conversation's workspace under ``skills/<skill-name>-<first 8 chars of
skill id>/``. The files are placed before the assistant answers, so the prompts only need the request
to succeed; the assertions read the workspace through the API.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_inanyorder,
    contains_string,
    empty,
    ends_with,
    equal_to,
    has_item,
    is_,
    is_not,
)

from codemie_test_harness.tests.test_data.skill_workspace_test_data import (
    SCRIPT_BUNDLE_PATH,
    SHARED_BUNDLE_PATH,
    bundle_file,
    script_bundle,
    single_file_bundle,
    two_file_bundle,
)
from codemie_test_harness.tests.utils.skill_workspace_utils import (
    folder_paths,
    list_paths,
    send_message,
    send_messages_in_parallel,
    skill_folder,
)
from codemie_test_harness.tests.utils.workspace_script_utils import random_marker

PREEXISTING_CONTENT = "written by the user before the first request"


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
def test_skill_bundle_files_appear_in_workspace_under_skill_folder(
    client,
    assistant_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
):
    """Every bundle file lands in the skill's folder, SKILL.md does not, and an existing file is kept."""
    bundle = two_file_bundle()
    skill = create_skill_with_bundle(bundle)
    assistant = create_skill_assistant(skills=[skill])
    conversation_id = new_conversation(assistant)
    seeded_path, contested_path = folder_paths(skill, bundle)
    workspace = client.workspaces.create(conversation_id)
    client.workspaces.write_file(workspace.id, contested_path, PREEXISTING_CONTENT)

    send_message(assistant_utils, assistant, conversation_id)

    paths = list_paths(client, workspace.id)
    assert_that(
        paths,
        contains_inanyorder(*folder_paths(skill, bundle)),
        "workspace must hold exactly the bundle files, each once, under the skill folder",
    )
    assert_that(paths, is_not(has_item(ends_with("SKILL.md"))))
    assert_that(
        client.workspaces.read_file(workspace.id, seeded_path).content,
        equal_to(bundle[0].content),
        "seeded file must carry the bundle file's content",
    )
    assert_that(
        client.workspaces.read_file(workspace.id, contested_path).content,
        equal_to(PREEXISTING_CONTENT),
        "a file that already existed at a bundle path must not be overwritten",
    )


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.parametrize(
    "same_name", [False, True], ids=["different-names", "same-name"]
)
def test_two_skills_with_the_same_file_path_get_their_own_folders(
    client,
    regular_client,
    assistant_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
    same_name,
):
    """Same relative path in two skills: each file sits in its own skill's folder, neither overwrites the other.

    A skill name is unique per user and project, so the same-name pair is made by two users."""
    first_bundle = single_file_bundle(SHARED_BUNDLE_PATH)
    second_bundle = single_file_bundle(SHARED_BUNDLE_PATH)
    first_skill = create_skill_with_bundle(first_bundle)
    second_skill = create_skill_with_bundle(
        second_bundle,
        name=first_skill.name if same_name else None,
        owner=regular_client if same_name else None,
    )
    assistant = create_skill_assistant(skills=[first_skill, second_skill])
    conversation_id = new_conversation(assistant)

    send_message(assistant_utils, assistant, conversation_id)

    workspace = client.workspaces.get_by_conversation(conversation_id)
    first_path = folder_paths(first_skill, first_bundle)[0]
    second_path = folder_paths(second_skill, second_bundle)[0]
    assert_that(
        skill_folder(second_skill),
        is_not(equal_to(skill_folder(first_skill))),
        "each skill must get its own folder",
    )
    assert_that(
        list_paths(client, workspace.id),
        contains_inanyorder(first_path, second_path),
        "both skills' files must be placed",
    )
    assert_that(
        client.workspaces.read_file(workspace.id, first_path).content,
        equal_to(first_bundle[0].content),
    )
    assert_that(
        client.workspaces.read_file(workspace.id, second_path).content,
        equal_to(second_bundle[0].content),
    )


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
def test_script_from_skill_bundle_runs_like_any_workspace_script(
    client,
    assistant_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
):
    """The seeded script runs from the skill folder and reads the file next to it, with no warnings."""
    marker = random_marker()
    skill = create_skill_with_bundle(script_bundle(marker))
    assistant = create_skill_assistant(skills=[skill])
    conversation_id = new_conversation(assistant)
    send_message(assistant_utils, assistant, conversation_id)
    workspace = client.workspaces.get_by_conversation(conversation_id)

    result = client.workspaces.execute_script(
        workspace.id, f"{skill_folder(skill)}/{SCRIPT_BUNDLE_PATH}"
    )

    assert_that(result.output, contains_string(f"RESULT-{marker}-DATA-{marker}"))
    assert_that(result.warnings, is_(empty()), "no workspace file may be skipped")


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
def test_workspace_has_no_skill_files_until_first_request_and_later_skill_is_added_once(
    client,
    assistant_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
    skill_utils,
):
    """Opening the workspace places nothing; the first request does; a skill attached later is added once."""
    first_bundle = two_file_bundle()
    second_bundle = [bundle_file("tools/second.py")]
    first_skill = create_skill_with_bundle(first_bundle)
    second_skill = create_skill_with_bundle(second_bundle)
    assistant = create_skill_assistant(skills=[first_skill])
    conversation_id = new_conversation(assistant)
    workspace = client.workspaces.create(conversation_id)

    assert_that(
        list_paths(client, workspace.id),
        is_(empty()),
        "an opened workspace must hold no skill files before the first request",
    )

    send_message(assistant_utils, assistant, conversation_id)
    assert_that(
        list_paths(client, workspace.id),
        contains_inanyorder(*folder_paths(first_skill, first_bundle)),
    )

    skill_utils.attach_skill_to_assistant(assistant.id, second_skill.id)
    send_message(assistant_utils, assistant, conversation_id)
    assert_that(
        list_paths(client, workspace.id),
        contains_inanyorder(
            *folder_paths(first_skill, first_bundle),
            *folder_paths(second_skill, second_bundle),
        ),
        "the new skill's files are added and the first skill's files are not repeated",
    )


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
def test_parallel_requests_place_skill_files_exactly_once(
    client,
    assistant_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
):
    """Two requests at the same moment in one new conversation leave each bundle file once."""
    bundle = two_file_bundle()
    skill = create_skill_with_bundle(bundle)
    assistant = create_skill_assistant(skills=[skill])
    conversation_id = new_conversation(assistant)

    # A failed request raises while the results are collected, so reaching the listing means both succeeded.
    send_messages_in_parallel(assistant_utils, assistant, conversation_id, 2)

    workspace = client.workspaces.get_by_conversation(conversation_id)
    assert_that(
        list_paths(client, workspace.id),
        contains_inanyorder(*folder_paths(skill, bundle)),
        "each bundle file must appear exactly once",
    )
