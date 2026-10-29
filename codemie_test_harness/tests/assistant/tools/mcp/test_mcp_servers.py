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

from copy import deepcopy

from codemie_test_harness.tests.utils.base_utils import assert_tool_triggered
from codemie_test_harness.tests.enums.tools import (
    McpServerTime,
    McpServerFetch,
)

import pytest

from codemie_test_harness.tests.test_data.mcp_server_test_data import (
    time_mcp_server_test_data,
    time_expected_response,
    FETCH_MCP_SERVER,
    fetch_expected_response,
    time_server_prompt,
    fetch_server_prompt,
    mcp_server_assistant_test_data,
)


@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
@pytest.mark.parametrize(
    "mcp_server",
    time_mcp_server_test_data,
    ids=[
        f"With config: {data.config is not None}" for data in time_mcp_server_test_data
    ],
)
def test_creation_mcp_server_with_form_configuration(
    assistant_utils, assistant, similarity_check, mcp_server
):
    assistant = assistant(mcp_server=mcp_server)

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant,
        time_server_prompt,
        minimal_response=False,
    )

    assert_tool_triggered(McpServerTime.CONVERT_TIME, triggered_tools)
    similarity_check.check_similarity(response, time_expected_response)


@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
def test_fetch_mcp_server(assistant_utils, assistant, similarity_check):
    assistant = assistant(mcp_server=FETCH_MCP_SERVER)

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, fetch_server_prompt, minimal_response=False
    )

    assert_tool_triggered(McpServerFetch.FETCH, triggered_tools)
    similarity_check.check_similarity(response, fetch_expected_response)


@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
@pytest.mark.parametrize(
    "test_case",
    mcp_server_assistant_test_data,
    ids=[test_case.mcp_server.name for test_case in mcp_server_assistant_test_data],
)
def test_assistant_with_mcp_server(
    assistant_utils, assistant, similarity_check, test_case, request, seeded
):
    """
    Test assistant with various MCP servers.

    Flow:
    - Create an Assistant with specific MCP server (add credentials if required)
    - Send a message to the assistant
    - Verify the response from the assistant
    - Verify appropriate MCP server tool was used (if applicable)
    """
    user_message = seeded(test_case.user_message)
    expected_response = seeded(test_case.expected_response)

    # Get integration fixture if specified
    if test_case.integration_fixture:
        integration = request.getfixturevalue(test_case.integration_fixture)
        mcp_server_with_integration = deepcopy(test_case.mcp_server)
        mcp_server_with_integration.settings = integration
        assistant_obj = assistant(mcp_server=mcp_server_with_integration)
    else:
        assistant_obj = assistant(mcp_server=test_case.mcp_server)

    # Send message to assistant
    response, triggered_tools = assistant_utils.ask_assistant(
        assistant_obj,
        user_message,
        minimal_response=False,
    )

    # Verify expected tools were used
    for expected_tool in test_case.expected_tools:
        assert_tool_triggered(expected_tool, triggered_tools)

    # Verify response matches expected
    similarity_check.check_similarity(response, expected_response)
