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

"""UI tests for the chat MCP auth-gate discovery-failure warning.

Covers the ticket's core symptom: an MCP server that fails auth *discovery*
(not sign-in) used to leave the chat turn with no visible feedback at all.
These tests assert the chat turn now surfaces a dedicated "MCP server
unavailable" warning, that two such inline servers on the same assistant
render without a React duplicate-key collision, and that the pre-existing
sign-in-required gate for a recoverable auth status is unchanged by the fix.
"""

import pytest

from codemie_test_harness.tests.ui.test_data.mcp_discovery_failure_test_data import (
    DISCOVERY_FAILED_ERROR_CONTEXT,
)


@pytest.mark.mcp
@pytest.mark.ui
def test_chat_shows_mcp_discovery_failure_warning(page, chat_with_untrusted_mcp_server):
    """@case error-message-silently-ignores-mcp_TC_001

    An assistant with one inline/manual HTTP MCP server configured with no
    auth_config, pointed at a host the environment does not trust for auth
    discovery, surfaces a visible "MCP server unavailable" warning in chat
    instead of no feedback at all.
    """
    chat_page, mcp_server_name = chat_with_untrusted_mcp_server(page)

    chat_page.send_message_and_wait_for_mcp_auth_prompt(
        f"Please use the '{mcp_server_name}' MCP server's tools to help me with this task."
    )

    chat_page.should_have_mcp_discovery_failure_prompt_visible()
    chat_page.should_have_mcp_auth_gate_row(mcp_server_name, DISCOVERY_FAILED_ERROR_CONTEXT)
    chat_page.should_have_mcp_auth_gate_status_badge_count(1)


@pytest.mark.mcp
@pytest.mark.ui
def test_chat_shows_two_untrusted_mcp_servers_without_key_collision(
    page, chat_with_two_untrusted_mcp_servers
):
    """@case error-message-silently-ignores-mcp_TC_002

    Two inline/manual HTTP MCP servers on the same assistant, each with no
    auth_config and no saved mcp_config_id, both render a discovery_failed row
    (each gets its own syntheticKey-based identity) with no React duplicate-key
    console error.
    """
    chat_page, server_a_name, server_b_name = chat_with_two_untrusted_mcp_servers(page)

    console_messages = chat_page.capture_console_messages_during(
        lambda: chat_page.send_message_and_wait_for_mcp_auth_prompt(
            f"Please use the '{server_a_name}' and '{server_b_name}' MCP servers' "
            "tools to help me with this task."
        )
    )

    chat_page.should_have_mcp_auth_gate_status_badge_count(2)
    chat_page.should_have_mcp_auth_gate_row(server_a_name, DISCOVERY_FAILED_ERROR_CONTEXT)
    chat_page.should_have_mcp_auth_gate_row(server_b_name, DISCOVERY_FAILED_ERROR_CONTEXT)
    chat_page.should_have_no_duplicate_key_console_warning(console_messages)


@pytest.mark.mcp
@pytest.mark.ui
def test_chat_sign_in_required_gate_unaffected_by_discovery_fix(
    page, chat_with_sign_in_required_mcp_server
):
    """@case error-message-silently-ignores-mcp_TC_003

    An MCP server that requires sign-in (authentication_required) — reached
    through a saved catalog config with auth_config configured, so the same
    kind of 401 is *not* routed to the new discovery_failed path — still shows
    the pre-existing "Authentication required" auth gate with a sign-in
    control, unchanged by this fix (normalizeMCPAuthGateServer still rejects
    an id-less row for every status except discovery_failed).
    """
    chat_page = chat_with_sign_in_required_mcp_server(page)

    chat_page.send_message_and_wait_for_mcp_auth_prompt(
        "Please use your configured MCP server's tools to help me with this task."
    )

    chat_page.should_have_mcp_sign_in_prompt_visible("Authentication required")
