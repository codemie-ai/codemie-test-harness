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

"""Skill files in a workspace are the conversation's own copy by reference.

Edits and deletions stay in the conversation that made them, a skill update or deletion does not reach
conversations that already hold the skill's files, and a skill's stored file is downloadable only
through a live file of the requester's own workspace.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_inanyorder,
    contains_string,
    equal_to,
    is_,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.skill_workspace_test_data import (
    BundleFile,
    bundle_file,
    single_file_bundle,
    three_file_bundle,
)
from codemie_test_harness.tests.utils.skill_workspace_utils import (
    folder_paths,
    list_paths,
    send_message,
    skill_blob_token,
    skill_folder,
)

EDITED_CONTENT = "edited in one conversation only"
NEW_FILE_CONTENT = "created in one conversation only"
UPDATED_CONTENT = "skill file content after the skill was updated"


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
def test_changes_in_skill_folder_stay_in_their_conversation(
    client,
    assistant_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
):
    """Edit, add and delete in conversation A: A keeps them, conversation B and the skill are untouched."""
    bundle = three_file_bundle()
    skill = create_skill_with_bundle(bundle)
    assistant = create_skill_assistant(skills=[skill])
    conversation_a = new_conversation(assistant)
    conversation_b = new_conversation(assistant)
    send_message(assistant_utils, assistant, conversation_a)
    send_message(assistant_utils, assistant, conversation_b)
    workspace_a = client.workspaces.get_by_conversation(conversation_a)
    workspace_b = client.workspaces.get_by_conversation(conversation_b)
    edited_path, deleted_path, kept_path = folder_paths(skill, bundle)
    added_path = f"{skill_folder(skill)}/extra/new-file.txt"

    client.workspaces.write_file(workspace_a.id, edited_path, EDITED_CONTENT)
    client.workspaces.write_file(workspace_a.id, added_path, NEW_FILE_CONTENT)
    deletion = client.workspaces.delete_file(workspace_a.id, deleted_path)
    send_message(assistant_utils, assistant, conversation_a)

    assert_that(deletion.deleted, is_(True))
    assert_that(
        list_paths(client, workspace_a.id),
        contains_inanyorder(edited_path, kept_path, added_path),
        "conversation A keeps its new file and the deleted file is not brought back",
    )
    assert_that(
        client.workspaces.read_file(workspace_a.id, edited_path).content,
        equal_to(EDITED_CONTENT),
    )
    assert_that(
        list_paths(client, workspace_b.id),
        contains_inanyorder(*folder_paths(skill, bundle)),
        "conversation B still holds every original file",
    )
    assert_that(
        client.workspaces.read_file(workspace_b.id, edited_path).content,
        equal_to(bundle[0].content),
    )
    assert_that(
        client.skills.get_companion_file(skill.id, bundle[0].path).content,
        equal_to(bundle[0].content),
        "the skill's own file must not change",
    )


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
def test_running_conversation_keeps_skill_content_after_skill_update(
    client,
    assistant_utils,
    skill_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
):
    """A skill update reaches new conversations only; the open one keeps what it was started with."""
    bundle = [bundle_file("docs/changing.md"), bundle_file("docs/stable.md")]
    added_file = bundle_file("docs/added-later.md")
    updated_file = BundleFile(bundle[0].path, UPDATED_CONTENT)
    skill = create_skill_with_bundle(bundle)
    assistant = create_skill_assistant(skills=[skill])
    conversation_a = new_conversation(assistant)
    send_message(assistant_utils, assistant, conversation_a)
    workspace_a = client.workspaces.get_by_conversation(conversation_a)
    changing_path = folder_paths(skill, bundle)[0]

    skill_utils.replace_skill_files(
        skill.id,
        [file.payload() for file in (updated_file, bundle[1], added_file)],
    )
    send_message(assistant_utils, assistant, conversation_a)
    conversation_b = new_conversation(assistant)
    send_message(assistant_utils, assistant, conversation_b)
    workspace_b = client.workspaces.get_by_conversation(conversation_b)

    assert_that(
        client.workspaces.read_file(workspace_a.id, changing_path).content,
        equal_to(bundle[0].content),
        "the open conversation keeps the content it was started with",
    )
    assert_that(
        list_paths(client, workspace_a.id),
        contains_inanyorder(*folder_paths(skill, bundle)),
        "a file added to the skill later does not appear in the open conversation",
    )
    assert_that(
        client.workspaces.read_file(workspace_b.id, changing_path).content,
        equal_to(UPDATED_CONTENT),
        "a new conversation gets the updated content",
    )
    assert_that(
        list_paths(client, workspace_b.id),
        contains_inanyorder(
            *folder_paths(skill, [updated_file, bundle[1], added_file])
        ),
        "a new conversation gets the added file",
    )


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
def test_workspace_still_reads_its_files_after_skill_is_updated_and_deleted(
    client,
    assistant_utils,
    skill_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
):
    """Update then delete the skill: the seeded file is still readable with its original content."""
    bundle = single_file_bundle()
    skill = create_skill_with_bundle(bundle)
    assistant = create_skill_assistant(skills=[skill])
    conversation_id = new_conversation(assistant)
    send_message(assistant_utils, assistant, conversation_id)
    workspace = client.workspaces.get_by_conversation(conversation_id)
    seeded_path = folder_paths(skill, bundle)[0]

    skill_utils.replace_skill_files(
        skill.id, [BundleFile(bundle[0].path, UPDATED_CONTENT).payload()]
    )
    skill_utils.delete_skill_by_id(skill.id)

    assert_that(
        client.workspaces.read_file(workspace.id, seeded_path).content,
        equal_to(bundle[0].content),
        "the workspace keeps the content it was seeded with",
    )


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
def test_skill_file_is_downloadable_only_through_live_file_of_own_workspace(
    client,
    regular_client,
    assistant_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
):
    """The owner of the workspace can download the skill file by token; another user and the owner after deletion cannot."""
    bundle = single_file_bundle()
    skill = create_skill_with_bundle(bundle)
    assistant = create_skill_assistant(skills=[skill])
    conversation_id = new_conversation(assistant)
    send_message(assistant_utils, assistant, conversation_id)
    workspace = client.workspaces.get_by_conversation(conversation_id)
    token = skill_blob_token(skill.id, bundle[0].path, bundle[0].content)

    downloaded = client.files.get_file(token)

    assert_that(downloaded.decode("utf-8"), equal_to(bundle[0].content))
    with pytest.raises(HTTPError) as other_user_error:
        regular_client.files.get_file(token)
    assert_that(other_user_error.value.response.status_code, equal_to(404))

    client.workspaces.delete_file(workspace.id, folder_paths(skill, bundle)[0])

    with pytest.raises(HTTPError) as after_deletion_error:
        client.files.get_file(token)
    assert_that(after_deletion_error.value.response.status_code, equal_to(404))
    assert_that(
        after_deletion_error.value.response.json()["error"]["message"],
        contains_string("File not found"),
    )
