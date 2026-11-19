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

"""Test data for the MCP catalog link-predicate save-validation tests.

A "link" is an mcp_servers entry that is enabled, points at a catalog entry
(``mcp_config_id``) and does not carry its own configuration (``use_custom_config``
is False). Only links are checked against the catalog and for duplicates; a
disabled or custom-config entry always saves, even with a dead ``mcp_config_id``.
"""

from codemie_sdk.models.assistant import MCPServerDetails
from codemie_sdk.models.mcp_config import MCPConfigCreateRequest, MCPServerConfigData

from codemie_test_harness.tests.utils.base_utils import get_random_name

# The exact messages MCPAccessControlService.validate_on_save raises (ValidationException,
# mapped to HTTP 400 with body {"error": {"message": ...}}).
DUPLICATE_CATALOG_MESSAGE = (
    "The same MCP server from the catalogue was added more than once. Keep only one."
)


def catalog_unavailable_message(server_name: str) -> str:
    """Exact message for a single unavailable link named ``server_name``."""
    return (
        f"MCP server not available in the catalogue: '{server_name}'. "
        f"Choose another MCP server or ask your administrator."
    )


def catalog_entry_create_request(
    name: str | None = None, is_public: bool = True
) -> MCPConfigCreateRequest:
    """A minimal, valid request to create a catalog MCP config used as a link target."""
    return MCPConfigCreateRequest(
        name=name or get_random_name(),
        description="Catalog entry created for MCP link-predicate save validation tests",
        config=MCPServerConfigData(
            url="https://mcp.example.com/mcp", type="streamable-http"
        ),
        is_public=is_public,
    )


def link_server(
    name: str | None = None,
    mcp_config_id: str | None = None,
    *,
    enabled: bool = True,
    use_custom_config: bool = False,
    description: str | None = None,
) -> MCPServerDetails:
    """An mcp_servers entry referencing a catalog config by id.

    ``is_link`` (the production predicate) is exactly: enabled, carries
    ``mcp_config_id``, and ``use_custom_config`` is False.
    """
    return MCPServerDetails(
        name=name or get_random_name(),
        description=description,
        enabled=enabled,
        mcp_config_id=mcp_config_id,
        use_custom_config=use_custom_config,
    )
