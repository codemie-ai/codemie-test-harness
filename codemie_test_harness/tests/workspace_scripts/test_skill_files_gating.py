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

"""When skill bundle files are NOT placed in the conversation workspace.

The workspace is opened ahead of the request and given a note, so that an empty skill folder list is read
from a workspace that demonstrably lists its files. Each skill that carries a bundle is checked to have
stored it, so the absence of skill files is caused by the condition under test and by nothing else.
"""

import pytest
from hamcrest import assert_that, contains_inanyorder, equal_to

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.skill_workspace_test_data import (
    two_file_bundle,
)
from codemie_test_harness.tests.utils.skill_workspace_utils import (
    list_paths,
    send_message,
)

NOTE_PATH = "notes/user-note.txt"
NOTE_CONTENT = "a note written before the first request"


def open_workspace_with_note(client, conversation_id: str):
    workspace = client.workspaces.create(conversation_id)
    client.workspaces.write_file(workspace.id, NOTE_PATH, NOTE_CONTENT)
    return workspace


def stored_paths(skill) -> list[str]:
    return [file.path for file in skill.companion_files]


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.parametrize(
    "skill_bundles",
    [[], [[]]],
    ids=["no-skills", "skill-without-files"],
)
def test_assistant_without_skill_files_leaves_workspace_unchanged(
    client,
    assistant_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
    skill_bundles,
):
    """No skills, or skills with no files: the workspace holds only what the user put there."""
    skills = [create_skill_with_bundle(bundle) for bundle in skill_bundles]
    assistant = create_skill_assistant(skills=skills)
    conversation_id = new_conversation(assistant)
    workspace = open_workspace_with_note(client, conversation_id)

    send_message(assistant_utils, assistant, conversation_id)

    assert_that(
        list_paths(client, workspace.id),
        contains_inanyorder(NOTE_PATH),
        "no skill folder may appear",
    )


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_names",
    [(), (AgentWorkspaceTool.LIST_WORKSPACE_FILES.value,)],
    ids=["no-workspace-toolkit", "workspace-toolkit-without-script-tool"],
)
def test_skill_files_are_not_placed_without_workspace_script_capability(
    client,
    assistant_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
    tool_names,
):
    """Without the workspace toolkit or without its script tool the skill's files stay out of the workspace."""
    bundle = two_file_bundle()
    skill = create_skill_with_bundle(bundle)
    assistant = create_skill_assistant(skills=[skill], tool_names=tool_names)
    conversation_id = new_conversation(assistant)
    workspace = open_workspace_with_note(client, conversation_id)

    send_message(assistant_utils, assistant, conversation_id)

    assert_that(
        stored_paths(skill),
        contains_inanyorder(*[file.path for file in bundle]),
        "the skill must really carry its bundle",
    )
    assert_that(
        list_paths(client, workspace.id),
        contains_inanyorder(NOTE_PATH),
        "no skill folder may appear",
    )


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_skill_files_are_not_placed_when_script_bridge_is_switched_off(
    client,
    assistant_utils,
    script_bridge_disabled,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
):
    """A fully equipped assistant gets no skill files while the environment-wide switch is off."""
    bundle = two_file_bundle()
    skill = create_skill_with_bundle(bundle)
    assistant = create_skill_assistant(skills=[skill])
    conversation_id = new_conversation(assistant)
    workspace = open_workspace_with_note(client, conversation_id)

    send_message(assistant_utils, assistant, conversation_id)

    assert_that(len(stored_paths(skill)), equal_to(len(bundle)))
    assert_that(
        list_paths(client, workspace.id),
        contains_inanyorder(NOTE_PATH),
        "no skill folder may appear",
    )
