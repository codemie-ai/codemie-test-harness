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

"""Ceilings on the skill files placed in a workspace, and on the bundle path.

The ceilings are read from ``GET /v1/skills/config``, so the tests follow whatever the environment applies
(documented defaults: 100 files, 10485760 bytes per file, 52428800 bytes per skill in total).
A bundle over a ceiling is still accepted and the request still succeeds; the files are taken in path
order and the ones over the ceiling are left out.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_inanyorder,
    contains_string,
    equal_to,
    has_entries,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.skill_workspace_test_data import (
    INVALID_COMPANION_PATH_MESSAGE,
    MAX_BUNDLE_PATH_LENGTH,
    PATH_TOO_LONG_DETAILS,
    BundleFile,
    bundle_over_file_count_ceiling,
    bundle_over_file_size_ceiling,
    path_of_length,
    single_file_bundle,
)
from codemie_test_harness.tests.utils.skill_workspace_utils import (
    folder_paths,
    list_paths,
    send_message,
)


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.parametrize(
    "build_bundles",
    [bundle_over_file_count_ceiling, bundle_over_file_size_ceiling],
    ids=["file-count", "per-file-size"],
)
def test_files_over_a_ceiling_are_left_out_without_failing_the_request(
    client,
    assistant_utils,
    create_skill_with_bundle,
    create_skill_assistant,
    new_conversation,
    build_bundles,
):
    """A bundle one file over a ceiling still starts the conversation; only the files over it are missing."""
    limits = client.skills.get_config()
    uploaded, expected = build_bundles(limits)
    skill = create_skill_with_bundle(uploaded)
    assistant = create_skill_assistant(skills=[skill])
    conversation_id = new_conversation(assistant)

    send_message(assistant_utils, assistant, conversation_id)

    workspace = client.workspaces.get_by_conversation(conversation_id)
    assert_that(
        len(skill.companion_files),
        equal_to(len(uploaded)),
        "the bundle is stored whole",
    )
    assert_that(
        list_paths(client, workspace.id),
        contains_inanyorder(*folder_paths(skill, expected)),
        "files within the ceilings are placed in path order, the rest is left out",
    )


@pytest.mark.skill
@pytest.mark.workspace
@pytest.mark.api
def test_bundle_path_longer_than_the_limit_is_refused_at_upload(
    client, skill_utils, create_skill_with_bundle
):
    """A path of one character over the limit is refused with 400 and the skill keeps its files."""
    bundle = single_file_bundle()
    skill = create_skill_with_bundle(bundle)
    too_long = BundleFile(path_of_length(MAX_BUNDLE_PATH_LENGTH + 1), "content")

    with pytest.raises(HTTPError) as error:
        skill_utils.replace_skill_files(skill.id, [too_long.payload()])

    response = error.value.response
    assert_that(response.status_code, equal_to(400))
    assert_that(
        response.json()["error"],
        has_entries(message=INVALID_COMPANION_PATH_MESSAGE),
    )
    assert_that(
        response.json()["error"]["details"], contains_string(PATH_TOO_LONG_DETAILS)
    )
    assert_that(
        [file.path for file in client.skills.list_companion_files(skill.id)],
        contains_inanyorder(bundle[0].path),
        "a refused upload must not change the stored bundle",
    )
