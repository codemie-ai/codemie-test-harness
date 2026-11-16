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

"""Test data for MCP auth-gate discovery/sign-in failure UI tests.

An inline/manual HTTP MCP server with no ``auth_config`` reaches the
"discovery_failed" auth-gate state only when the backend's MCP auth discovery
probe actually runs and is rejected — i.e. the target host must be reachable
and answer with an auth challenge the stand does not trust, not merely
unresolvable (an unresolvable host surfaces as a plain connection error
instead; confirmed live on the preview stand, recon-report.md "Unexpected
gates"). A catalog MCP config with ``auth_config`` explicitly set bypasses
discovery entirely and routes the same 401 to "authentication_required"
instead (``MCPToolkitService._build_auth_configured_tool_challenge_payload``,
codemie/src/codemie/service/mcp/toolkit_service.py:577-598).
"""

from codemie_sdk.models.assistant import MCPServerConfig, MCPServerDetails
from codemie_sdk.models.mcp_config import MCPConfigCreateRequest, MCPServerConfigData

from codemie_test_harness.tests.utils.base_utils import get_random_name

# A live HTTP MCP server that answers with an OAuth auth challenge the stand does not
# trust for auth discovery — the ticket's own repro endpoint (confirmed live on the
# preview stand, recon-report.md: Observables/TC_001/TC_008, and AC-8).
UNTRUSTED_HTTP_MCP_URL = "https://mcp.figma.com/mcp"

# Verbatim text MCPToolkitService._sanitize_discovery_error_context builds for this
# host's failure_reason ("no_trusted_authorization_server" is a trust-rejection reason —
# codemie/src/codemie/service/mcp/toolkit_service.py:730-741), and what the preview
# stand actually rendered (recon-report.md, step 10).
DISCOVERY_FAILED_ERROR_CONTEXT = (
    "Discovery failed: no_trusted_authorization_server. Add the AS domain to the "
    "trust allowlist or configure auth_config manually for this server."
)

MCP_SERVER_UNAVAILABLE_HEADING = "MCP server unavailable"
MCP_SERVER_UNAVAILABLE_SUBTITLE = (
    "Authentication discovery failed for one or more MCP servers. See the details below."
)
MCP_SERVER_UNAVAILABLE_BADGE = "Server unavailable"

# Minimal schema-valid OAuth2 auth_config (codemie_enterprise.mcp_auth.models.OAuth2AuthConfig:
# auth_type/authorization_url/token_url/client_id/client_type/scopes/token_delivery are all
# required). The authorization/token URLs are never contacted by this fixture — they are only
# read if a user clicks "Authenticate", which these tests never do — so a neutral placeholder
# host is fine here.
OAUTH2_AUTH_CONFIG = {
    "auth_type": "oauth2",
    "authorization_url": "https://mcp-auth.example.com/oauth/authorize",
    "token_url": "https://mcp-auth.example.com/oauth/token",
    "client_id": "codemie-test-harness",
    "client_type": "public",
    "scopes": ["mcp"],
    "token_delivery": {"method": "header"},
}


def build_untrusted_inline_mcp_server(name: str = None) -> MCPServerDetails:
    """An inline/manual HTTP MCP server with no ``auth_config``, pointed at a host the
    stand does not trust for auth discovery — reaches the "discovery_failed" gate.
    """
    server_name = name or f"QA untrusted MCP {get_random_name()}"
    return MCPServerDetails(
        name=server_name,
        description="QA fixture: untrusted-domain HTTP MCP server (discovery-failure gate)",
        enabled=True,
        config=MCPServerConfig(url=UNTRUSTED_HTTP_MCP_URL, type="streamable-http"),
    )


def build_sign_in_required_mcp_config_request(
    name: str = None,
) -> MCPConfigCreateRequest:
    """A catalog MCP config with ``auth_config`` set, so the same unreachable-for-trust
    host raises "authentication_required" instead of "discovery_failed" — the
    pre-existing gate branch this fix leaves unchanged (AC-9).
    """
    config_name = name or f"QA sign-in MCP {get_random_name()}"
    return MCPConfigCreateRequest(
        name=config_name,
        description="QA fixture: catalog MCP server requiring OAuth2 sign-in",
        config=MCPServerConfigData(
            url=UNTRUSTED_HTTP_MCP_URL,
            type="streamable-http",
            auth_config=dict(OAUTH2_AUTH_CONFIG),
        ),
    )


def build_catalog_mcp_server(mcp_config_id: str, name: str) -> MCPServerDetails:
    """Assistant-side reference to a saved catalog MCP config (global/inherited mode).

    A real ``mcp_config_id`` is required for any recoverable (non-discovery_failed)
    auth-gate row to render at all — ``normalizeMCPAuthGateServer`` still rejects a
    row with no id or display name for every status except discovery_failed
    (frontend/src/utils/mcpAuth.ts:104-109).
    """
    return MCPServerDetails(
        name=name,
        description="QA fixture: catalog MCP server requiring OAuth2 sign-in",
        enabled=True,
        mcp_config_id=mcp_config_id,
        use_custom_config=False,
    )
