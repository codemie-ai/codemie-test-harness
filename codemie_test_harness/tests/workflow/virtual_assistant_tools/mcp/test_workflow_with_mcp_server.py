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

import pytest

from codemie_test_harness.tests.enums.tools import (
    CliMcpServer,
    McpServerFetch,
    McpServerTime,
)
from codemie_test_harness.tests.test_data.mcp_server_test_data import (
    FETCH_MCP_SERVER,
    fetch_expected_response,
    time_expected_response,
    TIME_MCP_SERVER_WITH_CONFIG,
    time_server_prompt,
    fetch_server_prompt,
)
from codemie_test_harness.tests.test_data.mcp_server_test_data import (
    cli_mcp_server_test_data,
    CLI_MCP_SERVER,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.mcp
@pytest.mark.api
def test_workflow_with_time_mcp_server(
    workflow_with_virtual_assistant,
    workflow_utils,
    similarity_check,
):
    """Test workflow execution with Time MCP server."""
    assistant_and_state_name = get_random_name()

    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        mcp_servers=[TIME_MCP_SERVER_WITH_CONFIG],
    )

    response = workflow_utils.execute_workflow(
        test_workflow.id,
        assistant_and_state_name,
        time_server_prompt,
    )

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(McpServerTime.CONVERT_TIME, triggered_tools)

    similarity_check.check_similarity(response, time_expected_response)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.mcp
@pytest.mark.api
@pytest.mark.parametrize(
    "command, expected_answer",
    cli_mcp_server_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in cli_mcp_server_test_data],
)
def test_workflow_with_cli_mcp_server(
    workflow_with_virtual_assistant,
    workflow_utils,
    similarity_check,
    command,
    expected_answer,
):
    """Test workflow execution with CLI MCP server."""
    assistant_and_state_name = get_random_name()

    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        mcp_servers=[CLI_MCP_SERVER],
        task="Run command. In case of error just explain the issue and do not suggest any workarounds and do not try to run command with other parameters.",
    )

    response = workflow_utils.execute_workflow(
        test_workflow.id, assistant_and_state_name, f"execute the command: '{command}'"
    )

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(CliMcpServer.RUN_COMMAND, triggered_tools)

    similarity_check.check_similarity(response, expected_answer)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.mcp
@pytest.mark.api
def test_workflow_with_fetch_mcp_server(
    workflow_with_virtual_assistant,
    workflow_utils,
    similarity_check,
):
    """Test workflow execution with Fetch MCP server."""
    assistant_and_state_name = get_random_name()

    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name, mcp_servers=[FETCH_MCP_SERVER], task="Run tool"
    )
    response = workflow_utils.execute_workflow(
        test_workflow.id, assistant_and_state_name, fetch_server_prompt
    )

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(McpServerFetch.FETCH, triggered_tools)

    similarity_check.check_similarity(response, fetch_expected_response)
