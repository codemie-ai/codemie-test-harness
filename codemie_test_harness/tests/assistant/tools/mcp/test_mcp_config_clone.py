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

"""API tests for cloning a global MCP config (POST /v1/mcp-configs/{id}/clone).

Covers MCP config cloning: the clone is a separate record built from the submitted
payload, inherits visibility from the source, stays independent of it, and is
rejected for a duplicate name, an unknown source and a non-admin caller.

Clone, update and lookup by name go through ``McpConfigUtils``; a rejected clone
is read from the ``HTTPError`` response so the exact status and body are pinned.
"""

import uuid

import pytest
from codemie_sdk.models.mcp_config import (
    MCPConfigCreateRequest,
    MCPConfigUpdateRequest,
    MCPServerConfigData,
)
from hamcrest import (
    assert_that,
    contains_string,
    empty,
    equal_to,
    has_item,
    has_key,
    is_not,
)

from codemie_test_harness.tests.test_data.mcp_config_clone_test_data import (
    CLONE_DUPLICATE_NAME_MESSAGE,
    CLONE_EDITED_DESCRIPTION,
    CLONE_EDITED_URL,
    CLONE_UNKNOWN_SOURCE_DETAILS,
    EDITED_CATEGORIES,
    EDITED_DESCRIPTION,
    SOURCE_CATEGORIES,
    SOURCE_DESCRIPTION,
    SOURCE_EDITED_DESCRIPTION,
    SOURCE_EDITED_URL,
    mcp_clone_source_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.mcp_config_utils import McpConfigUtils


@pytest.fixture
def mcp_config_utils(client):
    return McpConfigUtils(client)


@pytest.fixture
def source_data():
    return mcp_clone_source_data()


def _create_source(client, data, is_public):
    return client.mcp_configs.create(
        MCPConfigCreateRequest(
            name=data.name,
            description=data.description,
            server_home_url=data.server_home_url,
            source_url=data.source_url,
            categories=data.categories,
            config=MCPServerConfigData(
                url=data.url, type=data.type, headers=data.headers
            ),
            is_public=is_public,
        )
    )


@pytest.fixture
def private_source(client, source_data):
    created = _create_source(client, source_data, is_public=False)
    yield created
    try:
        client.mcp_configs.delete(created.id)
    except Exception:
        pass


@pytest.fixture
def public_source(client, source_data):
    created = _create_source(client, source_data, is_public=True)
    yield created
    try:
        client.mcp_configs.delete(created.id)
    except Exception:
        pass


@pytest.fixture
def created_clone_ids(client):
    """Ids of clones made by a test; deleted on teardown even if the test fails."""
    ids = []
    yield ids
    for clone_id in ids:
        try:
            client.mcp_configs.delete(clone_id)
        except Exception:
            pass


@pytest.fixture
def source_and_clone(mcp_config_utils, private_source, source_data, created_clone_ids):
    clone = mcp_config_utils.clone(
        private_source.id, source_data.clone_payload(get_random_name())
    )
    created_clone_ids.append(clone.id)
    return private_source, clone


@pytest.mark.mcp
@pytest.mark.parametrize(
    "description, categories",
    [
        (SOURCE_DESCRIPTION, SOURCE_CATEGORIES),
        (EDITED_DESCRIPTION, EDITED_CATEGORIES),
    ],
    ids=["original_parameters", "edited_parameters"],
)
@pytest.mark.api
def test_clone_mcp_config_persists_payload_and_inherits_visibility(
    client,
    mcp_config_utils,
    public_source,
    source_data,
    created_clone_ids,
    description,
    categories,
):
    clone_name = get_random_name()

    clone = mcp_config_utils.clone(
        public_source.id,
        source_data.clone_payload(clone_name, description, categories),
    )

    created_clone_ids.append(clone.id)
    assert_that(clone.id, is_not(equal_to(public_source.id)))
    assert_that(clone.name, equal_to(clone_name))
    assert_that(clone.usage_count, equal_to(0), "usage counters are not copied")
    assert_that(clone.description, equal_to(description))
    assert_that(clone.categories, equal_to(categories))

    fetched = client.mcp_configs.get(clone.id)
    assert_that(fetched.description, equal_to(description))
    assert_that(fetched.categories, equal_to(categories))
    assert_that(fetched.config.url, equal_to(source_data.url))
    assert_that(
        fetched.is_public,
        equal_to(public_source.is_public),
        "is_public is copied from the source, not taken from the request",
    )
    assert_that(fetched.is_public, equal_to(True))
    assert_that(fetched.is_system, equal_to(public_source.is_system))


@pytest.mark.mcp
@pytest.mark.api
def test_edit_of_clone_and_source_are_independent(
    client, mcp_config_utils, source_and_clone, source_data
):
    source, clone = source_and_clone
    assert_that(clone.id, is_not(equal_to(source.id)))

    mcp_config_utils.update(
        clone.id,
        MCPConfigUpdateRequest(
            description=CLONE_EDITED_DESCRIPTION,
            config=source_data.config(url=CLONE_EDITED_URL),
        ),
    )

    source_after_clone_edit = client.mcp_configs.get(source.id)
    assert_that(source_after_clone_edit.description, equal_to(SOURCE_DESCRIPTION))
    assert_that(source_after_clone_edit.config.url, equal_to(source_data.url))

    mcp_config_utils.update(
        source.id,
        MCPConfigUpdateRequest(
            description=SOURCE_EDITED_DESCRIPTION,
            config=source_data.config(url=SOURCE_EDITED_URL),
        ),
    )

    clone_after_source_edit = client.mcp_configs.get(clone.id)
    assert_that(clone_after_source_edit.description, equal_to(CLONE_EDITED_DESCRIPTION))
    assert_that(clone_after_source_edit.config.url, equal_to(CLONE_EDITED_URL))

    source_final = client.mcp_configs.get(source.id)
    assert_that(source_final.description, equal_to(SOURCE_EDITED_DESCRIPTION))
    assert_that(source_final.config.url, equal_to(SOURCE_EDITED_URL))


@pytest.mark.mcp
@pytest.mark.parametrize(
    "source_key, name_key, status, error_field, expected_text",
    [
        ("existing", "source_name", 400, "message", CLONE_DUPLICATE_NAME_MESSAGE),
        ("unknown", "new_name", 404, "details", CLONE_UNKNOWN_SOURCE_DETAILS),
    ],
    ids=["duplicate_name", "unknown_source"],
)
@pytest.mark.api
def test_clone_mcp_config_rejects_invalid_request_and_creates_nothing(
    client,
    mcp_config_utils,
    private_source,
    source_data,
    source_key,
    name_key,
    status,
    error_field,
    expected_text,
):
    source_ids = {"existing": private_source.id, "unknown": str(uuid.uuid4())}
    names = {"source_name": source_data.name, "new_name": get_random_name()}
    attempted_name = names[name_key]
    source_listed = [c.id for c in mcp_config_utils.list_by_name(source_data.name)]
    assert_that(source_listed, has_item(private_source.id), "lookup must find source")
    rows_before = len(mcp_config_utils.list_by_name(attempted_name))

    response = mcp_config_utils.clone_rejected(
        source_ids[source_key], source_data.clone_payload(attempted_name)
    )

    assert_that(response.status_code, equal_to(status))
    assert_that(response.json()["error"][error_field], contains_string(expected_text))

    assert_that(
        len(mcp_config_utils.list_by_name(attempted_name)),
        equal_to(rows_before),
        "a rejected clone must not create a config",
    )
    source_after = client.mcp_configs.get(private_source.id)
    assert_that(source_after.description, equal_to(SOURCE_DESCRIPTION))
    assert_that(source_after.config.url, equal_to(source_data.url))


@pytest.mark.mcp
@pytest.mark.api
def test_clone_mcp_config_rejects_non_admin_caller_and_creates_nothing(
    client, mcp_config_utils, regular_client, private_source, source_data
):
    attempted_name = get_random_name()
    source_listed = [c.id for c in mcp_config_utils.list_by_name(source_data.name)]
    assert_that(source_listed, has_item(private_source.id), "lookup must find source")
    assert_that(mcp_config_utils.list_by_name(attempted_name), empty())

    response = McpConfigUtils(regular_client).clone_rejected(
        private_source.id, source_data.clone_payload(attempted_name)
    )

    assert_that(response.status_code, equal_to(403))
    assert_that(response.json(), has_key("error"))

    assert_that(
        mcp_config_utils.list_by_name(attempted_name),
        empty(),
        "no config may be created",
    )
    source_after = client.mcp_configs.get(private_source.id)
    assert_that(source_after.description, equal_to(SOURCE_DESCRIPTION))
    assert_that(source_after.config.url, equal_to(source_data.url))
