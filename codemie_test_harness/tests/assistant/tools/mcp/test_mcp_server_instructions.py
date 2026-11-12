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

"""Tests for MCP server-side instructions reaching the assistant's prompt."""

import uuid

import pytest
from hamcrest import assert_that, contains_string

from codemie_test_harness.tests.utils.base_utils import assert_tool_triggered
from codemie_test_harness.tests.enums.tools import McpServerInstructionsFixture
from codemie_test_harness.tests.test_data.mcp_server_instructions_test_data import (
    INSTRUCTIONS_MCP_SERVER,
    INSTRUCTIONS_MCP_SERVER_PROMPT,
    PREDEFINED_REPLY_SENTENCE,
)


def _instructed_assistant_via_direct_attach(
    assistant_factory, skill_factory, skill_utils
):
    """Attach the instructed MCP server directly to the assistant (execution_path=assistant)."""
    return assistant_factory(mcp_server=INSTRUCTIONS_MCP_SERVER)


def _instructed_assistant_via_skill_attach(
    assistant_factory, skill_factory, skill_utils
):
    """Attach the instructed MCP server through a skill (execution_path=skill)."""
    instructed_skill = skill_factory(mcp_servers=[INSTRUCTIONS_MCP_SERVER])
    created_assistant = assistant_factory()
    skill_utils.attach_skill_to_assistant(created_assistant.id, instructed_skill.id)
    return created_assistant


EXECUTION_PATH_ASSISTANT_BUILDERS = {
    "assistant": _instructed_assistant_via_direct_attach,
    "skill": _instructed_assistant_via_skill_attach,
}


@pytest.mark.assistant
@pytest.mark.mcp
@pytest.mark.api
@pytest.mark.parametrize(
    "execution_path",
    ["assistant", "skill"],
    ids=["assistant", "skill"],
)
def test_mcp_server_instructions_reach_the_prompt_from_the_first_call(
    assistant_utils, assistant, skill, skill_utils, execution_path
):
    """
    MCP server-declared instructions reach the prompt before the first tool call,
    for both the Assistant and Skill execution paths, and persist across a session.

    # @case mcp-server-instructions-not-applied_TC_001

    Flow:
    - Attach an MCP server declaring server-side instructions (requesting a predefined
      reply whenever its tool is used) to the execution path under test
    - Ask the assistant something that requires the attached MCP server's tool
    - Verify the first response already complies with the server's instructions
    - Ask again in the same conversation and verify the second response still complies,
      consistent with the instructions being reused for the session rather than re-fetched
    """
    created_assistant = EXECUTION_PATH_ASSISTANT_BUILDERS[execution_path](
        assistant, skill, skill_utils
    )

    conversation_id = str(uuid.uuid4())

    first_response, first_triggered_tools = assistant_utils.ask_assistant(
        created_assistant,
        INSTRUCTIONS_MCP_SERVER_PROMPT,
        conversation_id=conversation_id,
        minimal_response=False,
    )
    assert_tool_triggered(
        McpServerInstructionsFixture.CONFIRM_REPLY, first_triggered_tools
    )
    assert_that(
        first_response,
        contains_string(PREDEFINED_REPLY_SENTENCE),
        "First response did not comply with the MCP server's declared instructions "
        "(the instructions were not already in context before the first tool call)",
    )

    second_response, second_triggered_tools = assistant_utils.ask_assistant(
        created_assistant,
        INSTRUCTIONS_MCP_SERVER_PROMPT,
        conversation_id=conversation_id,
        minimal_response=False,
    )
    assert_tool_triggered(
        McpServerInstructionsFixture.CONFIRM_REPLY, second_triggered_tools
    )
    assert_that(
        second_response,
        contains_string(PREDEFINED_REPLY_SENTENCE),
        "Second response in the same conversation did not comply with the MCP "
        "server's declared instructions (instructions were not reused for the session)",
    )
