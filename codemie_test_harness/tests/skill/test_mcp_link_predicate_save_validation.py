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

"""API tests for the skill save-time MCP link predicate (catalog + duplicate checks).

Skills share ``MCPAccessControlService.validate_on_save`` with assistants and
workflows: a link (enabled, carries ``mcp_config_id``, not ``use_custom_config``) is
checked against the catalog and for duplicates; a disabled or custom-config entry is
never checked, even with a dead ``mcp_config_id``.
"""

import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_test_harness.tests.test_data.mcp_link_test_data import (
    DUPLICATE_CATALOG_MESSAGE,
    catalog_unavailable_message,
    link_server,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.fixture
def dead_catalog_config_id(client, catalog_mcp_config):
    """A catalog config id that existed, then was deleted: resolves to no catalog entry."""
    config = catalog_mcp_config()
    client.mcp_configs.delete(config.id)
    return config.id


@pytest.mark.skill
@pytest.mark.mcp
@pytest.mark.api
@pytest.mark.parametrize(
    "enabled, use_custom_config",
    [
        pytest.param(False, False, id="disabled_dead_id_saves"),
        pytest.param(True, True, id="custom_config_dead_id_saves"),
    ],
)
def test_disabled_or_custom_config_dead_catalog_id_saves(
    skill, dead_catalog_config_id, enabled, use_custom_config
):
    # @case mcp-link-predicate-save-validation_TC_002
    server_name = get_random_name()
    server = link_server(
        name=server_name,
        mcp_config_id=dead_catalog_config_id,
        enabled=enabled,
        use_custom_config=use_custom_config,
    )

    created = skill(mcp_servers=[server])

    assert_that(len(created.mcp_servers), equal_to(1))
    stored = created.mcp_servers[0]
    assert_that(stored.mcp_config_id, equal_to(dead_catalog_config_id))
    assert_that(stored.enabled, equal_to(enabled))
    assert_that(stored.use_custom_config, equal_to(use_custom_config))


@pytest.mark.skill
@pytest.mark.mcp
@pytest.mark.api
def test_re_enabling_dead_catalog_id_entry_fails(
    skill, skill_utils, dead_catalog_config_id
):
    # @case mcp-link-predicate-save-validation_TC_002
    server_name = get_random_name()
    disabled_server = link_server(
        name=server_name, mcp_config_id=dead_catalog_config_id, enabled=False
    )
    created = skill(mcp_servers=[disabled_server])
    re_enabled_server = link_server(
        name=server_name, mcp_config_id=dead_catalog_config_id, enabled=True
    )

    with pytest.raises(HTTPError) as exc_info:
        skill_utils.update_skill(created.id, mcp_servers=[re_enabled_server])

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    assert_that(
        response.json()["error"]["message"],
        equal_to(catalog_unavailable_message(server_name)),
    )


@pytest.mark.skill
@pytest.mark.mcp
@pytest.mark.api
def test_duplicate_catalog_id_links_refused(skill_utils, catalog_mcp_config):
    # @case mcp-link-predicate-save-validation_TC_002
    config = catalog_mcp_config()
    first = link_server(mcp_config_id=config.id)
    second = link_server(mcp_config_id=config.id)

    with pytest.raises(HTTPError) as exc_info:
        skill_utils.create_skill(mcp_servers=[first, second])

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    assert_that(
        response.json()["error"]["message"], equal_to(DUPLICATE_CATALOG_MESSAGE)
    )
