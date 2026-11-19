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

"""UI test for the assistant-form MCP tool picker on a discovery failure.

Covers the assistant-form (Step 2: Select Tools) counterpart of the chat auth
gate: a manually-configured MCP server pointed at a host the stand does not
trust for auth discovery must keep its tool controls and a Retry button
reachable, and Retry must clear the stale auth rows before re-fetching.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.test_data.mcp_discovery_failure_test_data import (
    build_untrusted_mcp_json_config,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.mcp
@pytest.mark.ui
def test_assistant_form_mcp_picker_stays_usable_on_discovery_failure(
    page, assistant_factory, sonnet_46_llm
):
    """@case error-message-silently-ignores-mcp_TC_008

    An inline/manual HTTP MCP server configured with no auth_config, pointed
    at a host the environment does not trust for auth discovery, must leave
    the assistant-form tool picker's controls and a Retry button reachable —
    and Retry must clear the stale auth rows before re-fetching, instead of
    leaving the picker stuck or unusable. The re-fetch is held to observe the cleared
    state, then released: the same untrusted server fails discovery again, so the row
    and its badge come back.

    Uses ``sonnet_46_llm`` (Bedrock Claude Sonnet 4.6), not the environment's
    flagged default model: the preview stand rejects assistant creation with
    the default model as deprecated (recon-report.md, "Unexpected gates").
    """
    test_assistant = assistant_factory.create(llm_model_type=sonnet_46_llm.base_name)
    mcp_server_name = f"QA untrusted MCP {get_random_name()}"

    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(test_assistant.name)

    edit_page = assistants_page.click_assistant_edit(test_assistant.name)
    edit_page.mcp_servers.should_have_mcp_servers_accordion_visible()
    edit_page.mcp_servers.expand_mcp_servers_accordion()
    edit_page.mcp_servers.click_mcp_manual_setup()

    edit_page.mcp_servers.fill_mcp_config_name(mcp_server_name)
    edit_page.mcp_servers.fill_mcp_config_description(
        "QA fixture: untrusted-domain HTTP MCP server (discovery-failure gate)"
    )
    edit_page.mcp_servers.fill_mcp_config_json(build_untrusted_mcp_json_config())
    edit_page.mcp_servers.click_mcp_config_next()

    edit_page.mcp_servers.should_have_mcp_tools_discovery_failed_row_visible(
        mcp_server_name
    )

    # Hold the re-fetch so the loading state is stable: the stand answers the same
    # discovery failure again, so without the hold the rows are back almost at once.
    edit_page.mcp_servers.hold_mcp_tools_requests()
    edit_page.mcp_servers.click_mcp_tools_retry()
    edit_page.mcp_servers.should_have_mcp_auth_gate_rows_cleared()

    edit_page.mcp_servers.release_held_mcp_tools_requests()
    edit_page.mcp_servers.should_have_mcp_tools_discovery_failed_row_visible(
        mcp_server_name
    )
