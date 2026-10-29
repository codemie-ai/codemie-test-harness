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

import pytest

from hamcrest import assert_that, contains_string

from codemie_sdk.models.integration import CredentialTypes
from codemie_test_harness.tests import autotest_entity_prefix
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)
from codemie_test_harness.tests.enums.tools import CliMcpServer
from codemie_test_harness.tests.test_data.mcp_server_test_data import (
    cli_mcp_server_test_data,
    CLI_MCP_SERVER,
)


@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
@pytest.mark.parametrize(
    "command,expected_answer",
    cli_mcp_server_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in cli_mcp_server_test_data],
)
def test_cli_mcp_server(
    assistant_utils, assistant, similarity_check, command, expected_answer
):
    assistant = assistant(mcp_server=CLI_MCP_SERVER)
    response, triggered_tools = assistant_utils.ask_assistant(
        assistant,
        f"execute command: '{command}'. In case of error just explain the issue and do not suggest "
        "any workarounds and do not try to run command with other parameters.",
        minimal_response=False,
    )
    assert_tool_triggered(CliMcpServer.RUN_COMMAND, triggered_tools)
    similarity_check.check_similarity(response, expected_answer)


@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
def test_env_var_in_mcp_server(
    assistant_utils, assistant, similarity_check, integration_utils
):
    credential_values = CredentialsManager.mcp_credentials()
    settings = integration_utils.create_integration(
        CredentialTypes.MCP, credential_values
    )

    cli_mcp_server_with_integration = deepcopy(CLI_MCP_SERVER)
    cli_mcp_server_with_integration.settings = settings
    cli_mcp_server_with_integration.config.command = "uvx"
    cli_mcp_server_with_integration.config.args = [
        "--with",
        "mcp<2.0.0",
        "cli-mcp-server",
    ]
    cli_mcp_server_with_integration.config.env = {
        "ALLOWED_DIR": "/tmp",
        "ALLOWED_COMMANDS": "ls,echo",
        "ALLOWED_FLAGS": "-l,--help",
        "MAX_COMMAND_LENGTH": "48",
    }

    assistant = assistant(mcp_server=cli_mcp_server_with_integration)

    dir_name = f"{autotest_entity_prefix}{get_random_name()}"
    response, triggered_tools = assistant_utils.ask_assistant(
        assistant,
        f"Execute commands sequentially: 'mkdir {dir_name}' then 'ls'. In the end return output of the second command.",
        minimal_response=False,
    )
    assert_tool_triggered(CliMcpServer.RUN_COMMAND, triggered_tools)
    assert_that(
        response,
        contains_string(dir_name),
        f"Expected directory name '{dir_name}' not found in response",
    )
