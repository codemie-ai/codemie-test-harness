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

"""Helpers for the global MCP config endpoints (clone, update, lookup by name)."""

import requests
from codemie_sdk.models.mcp_config import (
    MCPConfigCloneRequest,
    MCPConfigResponse,
    MCPConfigUpdateRequest,
)

from codemie_test_harness.tests.utils.base_utils import BaseUtils


class McpConfigUtils(BaseUtils):
    """Clone/update/cleanup operations on global MCP configs."""

    def clone(
        self, config_id: str, request: MCPConfigCloneRequest
    ) -> MCPConfigResponse:
        """POST /v1/mcp-configs/{config_id}/clone through the SDK."""
        return self.client.mcp_configs.clone(config_id, request)

    def clone_rejected(
        self, config_id: str, request: MCPConfigCloneRequest
    ) -> requests.Response:
        """Clone that must be refused; returns the error response so a test can pin its status and body."""
        try:
            self.client.mcp_configs.clone(config_id, request)
        except requests.HTTPError as error:
            return error.response
        raise AssertionError(f"Clone of {config_id} was expected to be rejected")

    def update(
        self, config_id: str, request: MCPConfigUpdateRequest
    ) -> MCPConfigResponse:
        """PUT /v1/mcp-configs/{config_id} through the SDK."""
        return self.client.mcp_configs.update(config_id, request)

    def list_by_name(self, name: str) -> list[MCPConfigResponse]:
        """Configs whose name equals ``name`` (search, then exact match)."""
        configs = self.client.mcp_configs.list(search=name, per_page=100)
        return [config for config in configs if config.name == name]

    def delete_by_name(self, name: str) -> None:
        """Delete every config whose name equals ``name`` (cleanup helper)."""
        for config in self.list_by_name(name):
            self.client.mcp_configs.delete(config.id)
