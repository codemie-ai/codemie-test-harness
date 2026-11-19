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
render without a React duplicate-key collision, that the pre-existing
sign-in-required gate for a recoverable auth status is unchanged by the fix,
and the ticket's own literal repro (an assistant built through the UI with an
inline figma MCP server).
"""

import pytest

from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)
from codemie_test_harness.tests.ui.test_data.mcp_discovery_failure_test_data import (
    DISCOVERY_FAILED_ERROR_CONTEXT,
    build_untrusted_mcp_json_config,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name, wait_for_entity


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
    chat_page.should_have_mcp_auth_gate_row(
        mcp_server_name, DISCOVERY_FAILED_ERROR_CONTEXT
    )
    chat_page.should_have_mcp_auth_gate_status_badge_count(1)


@pytest.mark.mcp
@pytest.mark.ui
def test_chat_shows_two_untrusted_mcp_servers_each_in_own_row(
    page, chat_with_two_untrusted_mcp_servers
):
    """@case error-message-silently-ignores-mcp_TC_002

    Two inline/manual HTTP MCP servers on the same assistant, each with no
    auth_config and no saved mcp_config_id, both render their own discovery_failed
    row (each gets its own syntheticKey-based identity): two badges, and each name
    sits in a row of its own with the error text.

    The row and badge-count checks are the guard against the duplicate-key bug. A
    console check for React's duplicate-key warning is deliberately not used: the
    stand serves a production bundle, which strips that warning, so such a check
    would pass whether or not the bug exists.
    """
    chat_page, server_a_name, server_b_name = chat_with_two_untrusted_mcp_servers(page)

    chat_page.send_message_and_wait_for_mcp_auth_prompt(
        f"Please use the '{server_a_name}' and '{server_b_name}' MCP servers' "
        "tools to help me with this task."
    )

    chat_page.should_have_mcp_auth_gate_status_badge_count(2)
    chat_page.should_have_mcp_auth_gate_row(
        server_a_name, DISCOVERY_FAILED_ERROR_CONTEXT
    )
    chat_page.should_have_mcp_auth_gate_row(
        server_b_name, DISCOVERY_FAILED_ERROR_CONTEXT
    )


@pytest.mark.mcp
@pytest.mark.ui
def test_chat_sign_in_required_gate_unaffected_by_discovery_fix(
    page, chat_with_sign_in_required_mcp_server
):
    """@case error-message-silently-ignores-mcp_TC_003

    An MCP server that requires sign-in (authentication_required) — reached
    through a saved catalog config with auth_config configured, so the same
    kind of 401 is *not* routed to the new discovery_failed path — still shows
    the pre-existing "Authentication required" auth gate heading, unchanged by
    this fix (normalizeMCPAuthGateServer still rejects an id-less row for every
    status except discovery_failed).
    """
    chat_page = chat_with_sign_in_required_mcp_server(page)

    chat_page.send_message_and_wait_for_mcp_auth_prompt(
        "Please use your configured MCP server's tools to help me with this task."
    )

    chat_page.should_have_mcp_sign_in_prompt_visible("Authentication required")
    chat_page.should_not_have_mcp_discovery_failure_prompt()


@pytest.mark.mcp
@pytest.mark.ui
def test_chat_shows_figma_repro_discovery_failure_warning(
    page, client, created_assistant_cleanup, open_chat_for_assistant
):
    """@case error-message-silently-ignores-mcp_TC_004

    Literal reproduction of the ticket: an assistant built end to end through the
    UI (Create Assistant -> Manual Setup) with one inline HTTP MCP server named
    "figma" at https://mcp.figma.com/mcp and no auth_config, saved with a
    non-deprecated LLM model (the preview stand rejects the environment's flagged
    default model as deprecated, recon-report.md), surfaces the "MCP server
    unavailable" warning and a discovery-failed row named "figma" when chat is used.

    The precondition also depends on api.figma.com being excluded from the
    stand's MCP_AUTH_TRUSTED_AS_DOMAINS — an environment-side setting outside
    this diff's evidence, not something this test sets up or asserts directly.
    If this test fails because figma.com has since become a trusted domain (the
    warning never appears), that is an environment/precondition drift, not a
    defect in this test.
    """
    assistant_name = f"QA figma repro {get_random_name()}"
    mcp_server_name = "figma"
    created_assistant_cleanup.track_name(assistant_name)

    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()
    create_page.fill_name(assistant_name)
    create_page.fill_description(
        "QA fixture: literal figma MCP discovery-failure repro"
    )
    create_page.fill_system_prompt("Act as a helpful assistant.")

    create_page.mcp_servers.should_have_mcp_servers_accordion_visible()
    create_page.mcp_servers.expand_mcp_servers_accordion()
    create_page.mcp_servers.click_mcp_manual_setup()
    create_page.mcp_servers.fill_mcp_config_name(mcp_server_name)
    create_page.mcp_servers.fill_mcp_config_description(
        "QA fixture: literal figma MCP discovery-failure repro"
    )
    create_page.mcp_servers.fill_mcp_config_json(build_untrusted_mcp_json_config())
    create_page.mcp_servers.click_mcp_config_next()
    create_page.mcp_servers.select_use_all_tools_checkbox()
    create_page.mcp_servers.click_mcp_tools_add()

    # Swap the default LLM model for a non-deprecated one before saving — the
    # preview stand rejects the environment's flagged default model as deprecated
    # (recon-report.md, "Unexpected gates"), the same as every other case here.
    create_page.select_llm_model(ModelTypes.CLAUDE_4_6_SONNET.value)
    create_page.click_save()

    # Confirm creation by searching the assistants list rather than the transient
    # success toast: the toast can already have auto-dismissed by the time this
    # check runs, which is a UI-timing race, not evidence creation failed.
    assistants_page = AssistantsPage(page)
    assistants_page.should_be_on_assistants_page()
    assistants_page.search_assistants(assistant_name)
    assistants_page.should_see_assistant_with_name(assistant_name)

    created_assistant = wait_for_entity(
        lambda: client.assistants.list(per_page=200), entity_name=assistant_name
    )
    created_assistant_cleanup.track(created_assistant)
    chat_page = open_chat_for_assistant(page, created_assistant.id)

    chat_page.send_message_and_wait_for_mcp_auth_prompt(
        "Please use the figma MCP server's tools to help me with this task."
    )

    chat_page.should_have_mcp_discovery_failure_prompt_visible()
    chat_page.should_have_mcp_auth_gate_row(
        mcp_server_name, DISCOVERY_FAILED_ERROR_CONTEXT
    )
