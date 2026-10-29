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

"""Workspace paths owned by the script runtime.

A single write or delete of the bridge folder or the runtime SDK file at the workspace root is refused in
every spelling (case, Unicode look-alikes). The same names deeper in the tree are ordinary, and reading or
listing is never restricted.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_items,
    is_,
    is_not,
    empty,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.skill_workspace_test_data import (
    NESTED_RESERVED_NAMES,
    RESERVED_PATH_ERROR,
    RESERVED_PATHS,
    ROOT_RESERVED_READ_PATH,
)
from codemie_test_harness.tests.utils.skill_workspace_utils import list_paths

RESERVED_IDS = [reserved.spelling for reserved in RESERVED_PATHS]


@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.parametrize("reserved", RESERVED_PATHS, ids=RESERVED_IDS)
def test_write_to_reserved_path_is_refused(client, empty_workspace, reserved):
    """Writing a runtime-owned path is a 400 'reserved' error and nothing is stored."""
    with pytest.raises(HTTPError) as error:
        client.workspaces.write_file(empty_workspace.id, reserved.path, "content")

    response = error.value.response
    assert_that(response.status_code, equal_to(400))
    assert_that(
        response.json()["error"]["details"], contains_string(RESERVED_PATH_ERROR)
    )
    assert_that(list_paths(client, empty_workspace.id), is_(empty()))


@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.parametrize("reserved", RESERVED_PATHS, ids=RESERVED_IDS)
def test_delete_of_reserved_path_is_refused(client, empty_workspace, reserved):
    """Deleting a runtime-owned path is a 400 'reserved' error, not a 'file not found' answer."""
    with pytest.raises(HTTPError) as error:
        client.workspaces.delete_file(empty_workspace.id, reserved.path)

    response = error.value.response
    assert_that(response.status_code, equal_to(400))
    assert_that(
        response.json()["error"]["details"], contains_string(RESERVED_PATH_ERROR)
    )


@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.parametrize(
    "nested_path", NESTED_RESERVED_NAMES, ids=["in-skills-folder", "in-subfolder"]
)
def test_reserved_name_below_the_root_is_an_ordinary_file(
    client, empty_workspace, nested_path
):
    """The same name one level down is written and read back like any file."""
    written = client.workspaces.write_file(empty_workspace.id, nested_path, "nested")

    assert_that(written.path, equal_to(nested_path))
    assert_that(
        client.workspaces.read_file(empty_workspace.id, nested_path).content,
        equal_to("nested"),
    )


@pytest.mark.workspace
@pytest.mark.api
def test_reading_and_listing_are_not_restricted_for_reserved_names(
    client, empty_workspace
):
    """Reading a root reserved path answers 'not found' (not 'reserved'), and listing works."""
    for_listing = NESTED_RESERVED_NAMES[0]
    client.workspaces.write_file(empty_workspace.id, for_listing, "nested")

    with pytest.raises(HTTPError) as error:
        client.workspaces.read_file(empty_workspace.id, ROOT_RESERVED_READ_PATH)

    details = error.value.response.json()["error"]["details"]
    assert_that(details, contains_string("not found"))
    assert_that(details, is_not(contains_string("reserved")))
    assert_that(list_paths(client, empty_workspace.id), has_items(for_listing))
