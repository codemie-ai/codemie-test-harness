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

"""UI test data for the MCPs catalog management page (Settings > Administration)."""

from dataclasses import dataclass, field

from codemie_test_harness.tests.utils.base_utils import get_random_name

CATALOG_SERVER_DESCRIPTION = (
    "Throwaway catalog server for the environment variable removal check"
)
CATALOG_SERVER_DOCS_URL = "https://mcp.example.com/docs"
CATALOG_SERVER_SOURCE_URL = "https://github.com/example/mcp-server"
CATALOG_SERVER_CONFIG_JSON = (
    '{"url": "https://mcp.example.com/mcp", "type": "streamable-http"}'
)
CATALOG_ENV_VAR_NAME = "AUTOTEST_API_TOKEN"
CATALOG_ENV_VAR_DESCRIPTION = "Token that the removal check deletes again"


@dataclass
class CatalogServerFormData:
    """Add MCP Server form input for a server with a single environment variable."""

    name: str = field(default_factory=get_random_name)
    description: str = CATALOG_SERVER_DESCRIPTION
    documentation_url: str = CATALOG_SERVER_DOCS_URL
    source_url: str = CATALOG_SERVER_SOURCE_URL
    config_json: str = CATALOG_SERVER_CONFIG_JSON
    env_var_name: str = CATALOG_ENV_VAR_NAME
    env_var_description: str = CATALOG_ENV_VAR_DESCRIPTION


def catalog_server_with_one_env_var() -> CatalogServerFormData:
    return CatalogServerFormData()
