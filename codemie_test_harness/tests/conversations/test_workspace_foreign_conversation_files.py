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

"""A workspace is only readable by a user who can read the conversation it belongs to.

Creating a workspace accepts any conversation id, and the files a conversation holds are listed
in its workspace as references to the owner's stored uploads. Without a check on the conversation,
a user could create a workspace for another user's conversation id and read those uploads by path.

Expected behaviour:
- a user who cannot read the conversation gets HTTP 400 "Invalid workspace request" for the
  file content, the file download and the lookup of the workspace by conversation, and no bytes;
- the refusal reads like a missing workspace, so it does not reveal that the conversation exists;
- the owner keeps reading their own conversation file.

Account A (the default admin ``client``) owns the conversation; account B (``platform_user``)
has no READ on it.
"""

import uuid

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_item,
    is_not,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.workspace_conversation_files_test_data import (
    INVALID_WORKSPACE_REQUEST,
    NOT_FOUND_WORDING,
    READ_ENDPOINT_IDS,
    READ_ENDPOINTS,
    ConversationFile,
    new_file_name,
    new_marker,
)
from codemie_test_harness.tests.utils.workspace_file_utils import (
    workspace_path_of_upload,
)
from codemie_test_harness.tests.utils.workspace_script_utils import upload_text_file

SEED_PROMPT = "Reply with the single word OK. Do not call any tool."


def assert_looks_like_missing_workspace(response, conversation_file: ConversationFile):
    assert_that(response.status_code, equal_to(400), "the lookup fails with 400")
    assert_that(response.text, contains_string(INVALID_WORKSPACE_REQUEST))
    assert_that(response.text, contains_string(NOT_FOUND_WORDING))
    assert_that(
        response.text,
        is_not(contains_string(conversation_file.file_name)),
        "the response does not reveal the conversation's file",
    )


@pytest.fixture
def owner_conversation_file(
    client, assistant, assistant_utils, conversation_utils
) -> ConversationFile:
    """A conversation of account A holding one uploaded text file; deleted at teardown."""
    marker = new_marker()
    file_name = new_file_name()
    file_url = upload_text_file(client, file_name, marker)
    owner_assistant = assistant()
    conversation_id = conversation_utils.create_conversation(
        initial_assistant_id=owner_assistant.id, folder=""
    ).get("id")
    assistant_utils.ask_assistant(
        owner_assistant,
        SEED_PROMPT,
        file_urls=[file_url],
        conversation_id=conversation_id,
    )
    yield ConversationFile(
        conversation_id=conversation_id,
        file_name=file_name,
        file_path=workspace_path_of_upload(file_url),
        marker=marker,
    )
    try:
        conversation_utils.delete_conversation(conversation_id)
    except Exception:
        pass


@pytest.fixture
def owner_workspace(client, owner_conversation_file):
    """Account A's workspace of its conversation, once it lists the uploaded file."""
    workspace = client.workspaces.create(owner_conversation_file.conversation_id)
    paths = [item.path for item in client.workspaces.list_files(workspace.id)]
    assert_that(
        paths,
        has_item(owner_conversation_file.file_path),
        "the conversation file is listed in the owner's workspace",
    )
    return workspace


@pytest.fixture
def foreign_workspace(platform_user, owner_conversation_file):
    """Account B's workspace for account A's conversation id (create does not check READ)."""
    return platform_user.client.workspaces.create(
        owner_conversation_file.conversation_id
    )


@pytest.mark.workspace
@pytest.mark.conversations
@pytest.mark.api
@pytest.mark.parametrize("read", READ_ENDPOINTS, ids=READ_ENDPOINT_IDS)
def test_read_foreign_conversation_file_from_workspace_is_refused(
    platform_user, owner_conversation_file, owner_workspace, foreign_workspace, read
):
    """TC-001: account B's workspace for account A's conversation returns no bytes of A's file."""
    # @case workspace-foreign-conversation-files_TC_001
    with pytest.raises(HTTPError) as error:
        read(
            platform_user.client,
            foreign_workspace.id,
            owner_conversation_file.file_path,
        )

    response = error.value.response
    assert_that(response.status_code, equal_to(400), "the read is refused")
    assert_that(
        response.text,
        contains_string(INVALID_WORKSPACE_REQUEST),
        "the refusal is the workspace validation error",
    )
    assert_that(
        response.text,
        is_not(contains_string(owner_conversation_file.marker)),
        "the refusal does not carry the file content",
    )


@pytest.mark.workspace
@pytest.mark.conversations
@pytest.mark.api
def test_get_foreign_conversation_workspace_by_conversation_is_refused(
    platform_user, owner_conversation_file, foreign_workspace
):
    """TC-002: account B cannot open a workspace for a conversation it cannot read."""
    # @case workspace-foreign-conversation-files_TC_002
    with pytest.raises(HTTPError) as error:
        platform_user.client.workspaces.get_by_conversation(
            owner_conversation_file.conversation_id
        )

    assert_that(
        error.value.response.status_code, equal_to(400), "the lookup is refused"
    )
    assert_that(
        error.value.response.text,
        contains_string(INVALID_WORKSPACE_REQUEST),
        "the refusal is the workspace validation error",
    )


@pytest.mark.workspace
@pytest.mark.conversations
@pytest.mark.api
@pytest.mark.parametrize("read", READ_ENDPOINTS, ids=READ_ENDPOINT_IDS)
def test_owner_reads_own_conversation_file_from_workspace(
    client, owner_conversation_file, owner_workspace, read
):
    """TC-003 (regression guard): the owner still reads their own conversation file."""
    # @case workspace-foreign-conversation-files_TC_003
    content = read(client, owner_workspace.id, owner_conversation_file.file_path)

    assert_that(content, equal_to(owner_conversation_file.marker))


@pytest.mark.workspace
@pytest.mark.conversations
@pytest.mark.api
def test_refused_conversation_workspace_looks_like_a_missing_one(
    platform_user, owner_conversation_file, foreign_workspace
):
    """TC-004: the refusal for a conversation B cannot read matches the answer for an unknown one."""
    # @case workspace-foreign-conversation-files_TC_004
    with pytest.raises(HTTPError) as refused:
        platform_user.client.workspaces.get_by_conversation(
            owner_conversation_file.conversation_id
        )
    with pytest.raises(HTTPError) as missing:
        platform_user.client.workspaces.get_by_conversation(str(uuid.uuid4()))

    assert_that(
        refused.value.response.status_code,
        equal_to(missing.value.response.status_code),
        "both lookups fail with the same status",
    )
    assert_looks_like_missing_workspace(refused.value.response, owner_conversation_file)
    assert_looks_like_missing_workspace(missing.value.response, owner_conversation_file)
