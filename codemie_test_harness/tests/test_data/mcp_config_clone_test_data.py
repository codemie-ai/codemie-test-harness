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

from dataclasses import dataclass, field

from codemie_sdk.models.mcp_config import MCPConfigCloneRequest, MCPServerConfigData

from codemie_test_harness.tests.utils.base_utils import get_random_name

SOURCE_DESCRIPTION = "Source MCP config used to verify the clone capability"
SOURCE_CATEGORIES = ["Development"]
EDITED_DESCRIPTION = "Description edited in the clone request"
EDITED_CATEGORIES = ["AI", "API"]
CLONE_EDITED_DESCRIPTION = "Description changed on the clone after cloning"
CLONE_EDITED_URL = "https://mcp.example.com/clone-edited"
SOURCE_EDITED_DESCRIPTION = "Description changed on the source after cloning"
SOURCE_EDITED_URL = "https://mcp.example.com/source-edited"
CLONE_DUPLICATE_NAME_MESSAGE = "Name already exists"
CLONE_UNKNOWN_SOURCE_DETAILS = "No MCP configuration found with id"


@dataclass
class McpCloneSourceData:
    name: str
    description: str
    categories: list[str]
    server_home_url: str
    source_url: str
    url: str
    type: str
    headers: dict[str, str] = field(default_factory=dict)

    def config(self, url: str | None = None) -> MCPServerConfigData:
        """Server config block as sent to the clone/update endpoints."""
        return MCPServerConfigData(
            url=url or self.url, type=self.type, headers=self.headers
        )

    def clone_payload(
        self,
        name: str,
        description: str | None = None,
        categories: list[str] | None = None,
    ) -> MCPConfigCloneRequest:
        """Clone request; it has no is_public field because the API takes it from the source."""
        return MCPConfigCloneRequest(
            name=name,
            description=description or self.description,
            server_home_url=self.server_home_url,
            source_url=self.source_url,
            categories=categories or self.categories,
            config=self.config(),
        )


def mcp_clone_source_data() -> McpCloneSourceData:
    return McpCloneSourceData(
        name=get_random_name(),
        description=SOURCE_DESCRIPTION,
        categories=list(SOURCE_CATEGORIES),
        server_home_url="https://mcp.example.com/docs",
        source_url="https://github.com/example/mcp-server",
        url="https://mcp.example.com/mcp",
        type="streamable-http",
        headers={"X-Custom-Header": "clone-test-value"},
    )
