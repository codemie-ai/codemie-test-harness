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

"""API tests for file-download authorization.

GET /v1/files/{file_name} used to serve any file to anyone who could build its
URL: the token is an unsigned, base64-encoded [mime_type, owner, name] triplet
and the handler trusted the client-supplied owner without any ownership check
(IDOR / cross-user file disclosure).

Expected behaviour after the fix:
- a requester can download a file only if they own it, or hold a valid grant
  (the file belongs to a conversation shared via a share token);
- forged / tampered tokens are rejected;
- the public "Share chat" flow keeps working, but only for files that belong
  to the shared conversation.

Uses the shared `non_admin_user` fixture (developer role only) as the attacker
(account B) and the default admin `client` as the file owner (account A).
"""

import base64
import uuid
from dataclasses import dataclass

import pytest
from hamcrest import assert_that, contains_string, equal_to, is_not
from requests import HTTPError

from codemie_test_harness.tests.utils.base_utils import get_random_name


@dataclass
class OwnerFile:
    file_url: str
    marker: str
    name: str
    mime_type: str = "text/plain"


def _serialize_token(*parts: str) -> str:
    """Build a file token the same way the backend's StringSerializer does."""
    raw = "".join(f"{len(part)}~{part}" for part in parts)
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


def _download(client, file_token: str, share_token: str | None = None) -> str:
    return client.files.get_file(file_token, share_token=share_token).decode(
        "utf-8", errors="replace"
    )


def _assert_download_denied(
    client, file_token: str, marker: str, share_token: str | None = None
):
    with pytest.raises(HTTPError) as exc_info:
        content = _download(client, file_token, share_token)
        pytest.fail(f"File was served to an unauthorized requester: {content!r}")

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Unauthorized file download must be rejected with 404",
    )
    assert_that(
        exc_info.value.response.text,
        is_not(contains_string(marker)),
        "Denial response must not leak the file content",
    )


@pytest.fixture
def owner_file(client, assistant_utils, tmp_path) -> OwnerFile:
    """A private file uploaded by account A (the default admin client)."""
    marker = f"private payload {uuid.uuid4()}"
    name = f"idor_{get_random_name()}.txt"
    path = tmp_path / name
    path.write_text(marker)
    file_url = assistant_utils.upload_file_to_chat(path)["file_url"]
    return OwnerFile(file_url=file_url, marker=marker, name=name)


@pytest.fixture
def shared_conversation(
    assistant, assistant_utils, conversation_utils, owner_file, tmp_path
):
    """A conversation of account A that has `owner_file` attached and is shared.

    Also uploads a second, never-attached file that must stay private.
    Returns (share_token, unshared_file).
    """
    assistant_obj = assistant()
    assistant_utils.ask_assistant(
        assistant_obj,
        f"Reply with OK. {get_random_name()}",
        file_urls=[owner_file.file_url],
    )
    conversation_id = conversation_utils.get_conversation_by_assistant_id(
        assistant_obj.id
    )[0].id
    share_token = conversation_utils.share_conversation(conversation_id).token

    marker = f"unshared payload {uuid.uuid4()}"
    name = f"idor_unshared_{get_random_name()}.txt"
    path = tmp_path / name
    path.write_text(marker)
    unshared_url = assistant_utils.upload_file_to_chat(path)["file_url"]

    return share_token, OwnerFile(file_url=unshared_url, marker=marker, name=name)


@pytest.mark.smoke
@pytest.mark.conversations
@pytest.mark.api
def test_download_file_by_owner_returns_content(client, owner_file):
    """TC-01 (regression guard): the file owner keeps read access to their own file."""
    content = _download(client, owner_file.file_url)

    assert_that(content, equal_to(owner_file.marker))


@pytest.mark.smoke
@pytest.mark.conversations
@pytest.mark.api
def test_download_foreign_file_by_other_user_is_denied(non_admin_user, owner_file):
    """TC-02: account B must not read account A's private file by reusing its URL —
    the exact cross-user disclosure from the ticket's steps to reproduce."""
    _email, _member_id, member_client = non_admin_user

    _assert_download_denied(member_client, owner_file.file_url, owner_file.marker)


@pytest.mark.smoke
@pytest.mark.conversations
@pytest.mark.api
def test_download_file_with_forged_token_is_denied(client, non_admin_user, owner_file):
    """TC-03: a token fabricated from a known owner user-id + filename must not
    grant access, even though the encoding itself is unsigned and forgeable."""
    _email, _member_id, member_client = non_admin_user
    owner_id = client.users.about_me().user_id
    forged = _serialize_token(owner_file.mime_type, owner_id, owner_file.name)

    _assert_download_denied(member_client, forged, owner_file.marker)


@pytest.mark.smoke
@pytest.mark.conversations
@pytest.mark.api
def test_download_file_with_path_traversal_token_is_denied(
    client, non_admin_user, owner_file
):
    """TC-04: a token whose owner is the attacker's own id but whose name climbs
    into the victim's directory must not bypass the ownership rule."""
    _email, member_id, member_client = non_admin_user
    owner_id = client.users.about_me().user_id
    traversal = _serialize_token(
        owner_file.mime_type, member_id, f"../{owner_id}/{owner_file.name}"
    )

    _assert_download_denied(member_client, traversal, owner_file.marker)


@pytest.mark.smoke
@pytest.mark.conversations
@pytest.mark.api
def test_download_file_with_malformed_token_returns_bad_request(non_admin_user):
    """TC-05: an undecodable token is a client error, not a 500."""
    _email, _member_id, member_client = non_admin_user

    with pytest.raises(HTTPError) as exc_info:
        _download(member_client, "!!not-a-valid-token!!")

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "Undecodable file token must be rejected with 400, not 500",
    )


@pytest.mark.smoke
@pytest.mark.conversations
@pytest.mark.api
def test_download_shared_file_with_share_token_returns_content(
    non_admin_user, owner_file, shared_conversation
):
    """TC-06 (regression guard): the public "Share chat" flow keeps working — a
    recipient can render a file of the shared conversation using the share token."""
    _email, _member_id, member_client = non_admin_user
    share_token, _unshared = shared_conversation

    content = _download(member_client, owner_file.file_url, share_token=share_token)

    assert_that(content, equal_to(owner_file.marker))


@pytest.mark.smoke
@pytest.mark.conversations
@pytest.mark.api
def test_download_shared_file_without_share_token_is_denied(
    non_admin_user, owner_file, shared_conversation
):
    """TC-07: sharing a conversation must not make its files public — without the
    share token the recipient is still denied."""
    _email, _member_id, member_client = non_admin_user

    _assert_download_denied(member_client, owner_file.file_url, owner_file.marker)


@pytest.mark.smoke
@pytest.mark.conversations
@pytest.mark.api
def test_download_unshared_file_with_share_token_is_denied(
    non_admin_user, shared_conversation
):
    """TC-08: a valid share token is scoped to the shared conversation — it must
    not unlock another private file of the same owner."""
    _email, _member_id, member_client = non_admin_user
    share_token, unshared_file = shared_conversation

    _assert_download_denied(
        member_client,
        unshared_file.file_url,
        unshared_file.marker,
        share_token=share_token,
    )
