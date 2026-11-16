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

"""API tests for who may download an assistant's uploaded icon.

Covers the fix that makes an uploaded icon downloadable by any user who can
read the assistant (not only the uploader), without widening access beyond
that: a user with no read access to the assistant must still be refused.
"""

import pytest
from hamcrest import assert_that, equal_to, not_none
from requests import HTTPError

from codemie_sdk.models.assistant import AssistantUpdateRequest

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.utils.base_utils import assert_response
from codemie_test_harness.tests.utils.constants import FILES_PATH


@pytest.mark.assistant
@pytest.mark.api
def test_shared_assistant_icon_downloads_for_member_not_for_outsider(
    client, assistant_factory, platform_user, unrelated_client, user_utils
):
    """@case uploaded-assistant-icons-are-visible_TC_001"""
    icon_bytes = (FILES_PATH / "test.png").read_bytes()
    uploaded = client.files.bulk_upload([FILES_PATH / "test.png"])
    uploaded_icon_url = uploaded.files[0].file_url

    # user A: create the assistant, share it with the project, then set the uploaded
    # image as its icon_url (localization happens on update, same as on create).
    assistant = assistant_factory.create(shared=True)
    full_assistant = client.assistants.get(assistant.id)
    update_request = AssistantUpdateRequest(
        name=full_assistant.name,
        description=full_assistant.description,
        shared=True,
        system_prompt=full_assistant.system_prompt,
        project=full_assistant.project,
        llm_model_type=full_assistant.llm_model_type,
        icon_url=uploaded_icon_url,
    )
    client.assistants.update(assistant.id, update_request)

    # The update localizes the icon into an entity-owned copy; re-read the assistant
    # to get the token Rule F actually serves, not the raw upload reference.
    icon_token = client.assistants.get(assistant.id).icon_url
    assert_that(
        icon_token,
        not_none(),
        "assistant should have an icon_url after the update sets one",
    )

    owner_bytes = client.files.get_file(icon_token)
    assert_that(
        owner_bytes,
        equal_to(icon_bytes),
        "the uploader should be able to download their own assistant's icon",
    )

    # user B: a plain project member who did not upload the icon.
    member_id, member_client = platform_user.user_id, platform_user.client
    user_utils.assign_user_to_project(member_id, PROJECT)

    member_bytes = member_client.files.get_file(icon_token)
    assert_that(
        member_bytes,
        equal_to(icon_bytes),
        "a project member who can read the shared assistant must download the same "
        "bytes that were uploaded as its icon (AC-1: no 404 for a viewer who can "
        "read the assistant)",
    )

    # user C: no read access to the assistant at all.
    with pytest.raises(HTTPError) as exc_info:
        unrelated_client.files.get_file(icon_token)
    assert_response(
        exc_info.value.response,
        404,
    )
