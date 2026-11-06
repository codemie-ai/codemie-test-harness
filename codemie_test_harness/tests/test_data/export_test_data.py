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

"""Test data for the public export API (GET /v1/export/{kind}/{id}).

Literal values below are deliberately shaped like real credentials/secrets so the export
service's redaction/refusal logic (name- and shape-based) actually engages; they are never
real credentials.
"""

# A literal value fed into a credential-bearing field; exported, it must never appear in the
# document, only an `env:` reference derived from it.
LITERAL_INTEGRATION_TOKEN = "literal-integration-token-value"
LITERAL_DATASOURCE_URL_PASSWORD = "literal-datasource-url-password"
LITERAL_MCP_COMMAND = "run-literal-mcp-command"
LITERAL_MCP_ENV_SECRET = "literal-env-map-secret-value"
LITERAL_MCP_CONNECT_AUTH_TOKEN = "literal-connect-auth-token-value"

# Prefix for a `env:` credential reference; every redacted field must start with this.
ENV_REF_PREFIX = "env:"

# The server-side mask placeholder an update sends back to mean "keep the stored secret"
# (SettingsService.MASKED_VALUE on the backend: "*" * 10).
CREDENTIAL_MASK = "*" * 10

# Config of a `transform_node` custom node with the simplest mapping (no upstream data needed).
TRANSFORM_NODE_CONFIG = {
    "input_source": "context_store",
    "mappings": [
        {"output_field": "greeting", "type": "constant", "value": "hello"},
    ],
}
