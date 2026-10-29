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

"""
E2E tests for AICE Provider CodeExplorationToolkit.

This test suite verifies the end-to-end functionality of creating a datasource provider,
creating a CodeExplorationToolkit datasource against that provider (which indexes the
repository configured on the provider), creating an assistant with the
CodeExplorationToolkit, and validating that the assistant uses the appropriate tools
to answer questions. The questions and expected tools come from
provider_toolkit_test_data.
"""

import pytest
from codemie_sdk.models.assistant import ToolKitDetails, ToolDetails
from hamcrest import assert_that, is_not, empty

from codemie_test_harness.tests.enums.tools import CodeExplorationTools, Toolkit
from codemie_test_harness.tests.test_data.provider_toolkit_test_data import (
    code_exploration_toolkit_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


@pytest.mark.datasource
@pytest.mark.provider
@pytest.mark.aice
@pytest.mark.api
@pytest.mark.parametrize("question, expected_tool", code_exploration_toolkit_test_data)
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="AICE is not configured for sandbox environments",
)
def test_code_exploration_toolkit(
    assistant_utils,
    provider_context,
    code_exploration_datasource,
    question,
    expected_tool,
):
    """
    Test for CodeExplorationToolkit with AICE provider.

    This test:
    1. Uses the CodeExplorationToolkit from a cloned AICE provider (via fixture)
    2. Creates a CodeExplorationToolkit datasource against that provider (via fixture)
    3. Creates an assistant with the CodeExplorationToolkit
    4. Asks a question to verify the assistant uses the appropriate tool

    Args:
        assistant_utils: Utility for assistant operations
        provider_context: Provider context fixture
        code_exploration_datasource: Indexed datasource fixture
        question: Question to ask the assistant
        expected_tool: Expected tool to be triggered
    """

    # Create list of tools from CodeExplorationTools enum
    tools = [ToolDetails(name=tool.value) for tool in CodeExplorationTools]

    # Create toolkit details with configuration
    toolkit_details = ToolKitDetails(
        toolkit=Toolkit.CODE_EXPLORATION,
        tools=tools,
        is_external=True,  # Provider-based toolkit
    )

    # Create assistant with CodeExplorationToolkit
    system_prompt = """You are a code exploration assistant.
            Always use the tools available to you to provide accurate answers."""

    test_assistant = assistant_utils.create_assistant(
        system_prompt=system_prompt,
        toolkits=[toolkit_details],
        context=[provider_context(code_exploration_datasource)],
    )

    # Ask the assistant
    answer, triggered_tools = assistant_utils.ask_assistant(
        test_assistant, question, minimal_response=False
    )

    # Verify the expected tool was triggered
    assert_tool_triggered(expected_tool, triggered_tools)

    # Verify we got a non-empty response
    assert_that(answer, is_not(empty()), "Assistant should provide an answer.")
