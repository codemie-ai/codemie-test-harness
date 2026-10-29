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

import pytest
from hamcrest import assert_that, equal_to

from codemie_sdk.models.mcp_config import MCPConfigCreateRequest, MCPServerConfigData
from codemie_test_harness.tests.test_data.mcp_config_test_data import (
    mcp_config_field_persistence_data,
)


@pytest.fixture
def mcp_config(client):
    """Create a global MCP config and yield its ID; clean up on teardown."""
    data = mcp_config_field_persistence_data()
    request = MCPConfigCreateRequest(
        name=data.name,
        config=MCPServerConfigData(
            url="https://mcp.example.com/mcp",
            headers=data.headers,
            type=data.type,
            single_usage=data.single_usage,
            audience=data.audience,
        ),
    )
    created = client.mcp_configs.create(request)
    yield created.id, data
    try:
        client.mcp_configs.delete(created.id)
    except Exception:
        pass


@pytest.mark.sanity
@pytest.mark.mcp
@pytest.mark.api
def test_deploy_mcp_config_preserves_critical_fields(client, mcp_config):
    """TC-001: MCP config deployment preserves headers, type, single_usage, audience."""
    config_id, input_data = mcp_config

    retrieved = client.mcp_configs.get(config_id)
    assert retrieved.config is not None, "config block must be present in response"

    assert_that(
        retrieved.config.headers,
        equal_to(input_data.headers),
        "headers must be preserved post-deployment",
    )
    assert_that(
        retrieved.config.type,
        equal_to(input_data.type),
        "type must be preserved post-deployment",
    )
    assert_that(
        retrieved.config.single_usage,
        equal_to(input_data.single_usage),
        "single_usage must be preserved post-deployment",
    )
    assert_that(
        retrieved.config.audience,
        equal_to(input_data.audience),
        "audience must be preserved post-deployment",
    )
