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
Tests for assistant functionality with sub-assistants.

This module tests the ability to create assistants with sub-assistants,
delegate tasks between parent and child assistants, and manage hierarchical
assistant structures.
"""

import uuid

import pytest
from pydantic import BaseModel
from codemie_sdk.models.assistant import (
    AssistantUpdateRequest,
    ToolDetails,
    ToolKitDetails,
)
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_items,
    is_not,
    matches_regexp,
)

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.output_schema_test_data import output_schema
from codemie_test_harness.tests.enums.environment import Environment
from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.enums.tools import (
    ProjectManagementTool,
    GitTool,
    FileManagementTool,
    Toolkit,
)
from codemie_test_harness.tests.test_data.file_management_tools_test_data import (
    code_tools_test_data,
)
from codemie_test_harness.tests.test_data.git_tools_test_data import (
    list_branches_set_active_branch_test_data,
)
from codemie_test_harness.tests.test_data.pm_tools_test_data import (
    JIRA_TOOL_PROMPT,
    RESPONSE_FOR_JIRA_TOOL,
)
from codemie_test_harness.tests.test_data.mcp_server_test_data import (
    FETCH_MCP_SERVER,
)
from codemie_test_harness.tests.test_data.subagent_tool_call_test_data import (
    BACKEND_400_ERROR_PATTERN,
    JIRA_SUB_ASSISTANT_SYSTEM_PROMPT,
    PARENT_ASSISTANT_SYSTEM_PROMPT,
    JIRA_SUB_ASSISTANT_PROMPT,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_error_details,
    get_random_name,
)
from codemie_test_harness.tests.utils.env_resolver import get_environment


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.api
def test_create_assistant_with_single_sub_assistant(assistant, assistant_utils):
    """
    Test creating an assistant with a single sub-assistant.

    Verifies that:
    - Parent assistant can be created with a sub-assistant reference
    - Sub-assistant is properly linked to parent assistant
    - The assistant_ids field contains the sub-assistant ID
    """
    # Create sub-assistant first
    sub_assistant = assistant(
        system_prompt="You are a specialized sub-assistant for calculations",
    )

    # Create parent assistant with sub-assistant
    parent_assistant = assistant(
        system_prompt="You are a parent assistant that delegates to sub-assistants",
        sub_assistants_ids=[sub_assistant.id],
    )

    # Verify parent has sub-assistant
    assert_that(
        assistant_utils.get_assistant_by_id(parent_assistant.id).assistant_ids,
        has_items(sub_assistant.id),
        "Parent assistant should contain sub-assistant ID",
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.api
def test_create_assistant_with_multiple_sub_assistants(assistant, assistant_utils):
    """
    Test creating an assistant with multiple sub-assistants.

    Verifies that:
    - Parent assistant can reference multiple sub-assistants
    - All sub-assistant IDs are properly stored
    - Multiple sub-assistants can coexist
    """
    # Create multiple sub-assistants
    sub_assistant_1 = assistant(
        system_prompt="You are a specialized sub-assistant for math",
    )

    sub_assistant_2 = assistant(
        system_prompt="You are a specialized sub-assistant for text analysis",
    )

    sub_assistant_3 = assistant(
        system_prompt="You are a specialized sub-assistant for data processing",
    )

    # Create parent assistant with multiple sub-assistants
    parent_assistant = assistant(
        system_prompt="You are a parent assistant coordinating multiple sub-assistants",
        sub_assistants_ids=[sub_assistant_1.id, sub_assistant_2.id, sub_assistant_3.id],
    )

    # Verify parent has all sub-assistants
    parent_assistant = assistant_utils.get_assistant_by_id(parent_assistant.id)
    assert_that(
        len(parent_assistant.assistant_ids),
        equal_to(3),
        "Parent assistant should have 3 sub-assistants",
    )
    assert_that(
        parent_assistant.assistant_ids,
        has_items(sub_assistant_1.id, sub_assistant_2.id, sub_assistant_3.id),
        "Parent assistant should contain all sub-assistant IDs",
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.api
def test_update_assistant_to_add_sub_assistant(assistant, assistant_utils):
    """
    Test updating an existing assistant to add a sub-assistant.

    Verifies that:
    - Existing assistant can be updated to include sub-assistants
    - Sub-assistant list can be modified after creation
    """
    # Create assistants
    sub_assistant = assistant(
        system_prompt="You are a specialized sub-assistant",
    )

    parent_assistant = assistant(
        system_prompt="You are a parent assistant",
    )

    # Verify parent initially has no sub-assistants
    parent_assistant = assistant_utils.get_assistant_by_id(parent_assistant.id)
    assert_that(
        len(parent_assistant.assistant_ids),
        equal_to(0),
        "Parent should initially have no sub-assistants",
    )

    # Update parent to include sub-assistant
    update_request = AssistantUpdateRequest(
        name=parent_assistant.name,
        description=parent_assistant.description,
        shared=False,
        system_prompt=parent_assistant.system_prompt,
        project=PROJECT,
        llm_model_type=parent_assistant.llm_model_type,
        assistant_ids=[sub_assistant.id],
    )

    assistant_utils.update_assistant(parent_assistant.id, update_request)

    # Verify sub-assistant was added
    updated_parent = assistant_utils.get_assistant_by_id(parent_assistant.id)
    assert_that(
        updated_parent["assistant_ids"],
        has_items(sub_assistant.id),
        "Parent assistant should now contain sub-assistant ID",
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.api
def test_update_assistant_to_remove_sub_assistant(assistant, assistant_utils):
    """
    Test updating an assistant to remove a sub-assistant.

    Verifies that:
    - Sub-assistants can be removed from parent assistant
    - Sub-assistant list can be cleared via update
    """
    # Create sub-assistant
    sub_assistant = assistant(
        system_prompt="You are a specialized sub-assistant",
    )

    # Create parent with sub-assistant
    parent_assistant = assistant(
        system_prompt="You are a parent assistant",
        sub_assistants_ids=[sub_assistant.id],
    )

    # Verify sub-assistant was added
    parent_assistant = assistant_utils.get_assistant_by_id(parent_assistant.id)
    assert_that(
        len(parent_assistant.assistant_ids),
        equal_to(1),
        "Parent should have one sub-assistant",
    )

    # Remove sub-assistant
    update_request = AssistantUpdateRequest(
        name=parent_assistant.name,
        slug=parent_assistant.slug,
        description=parent_assistant.description,
        shared=False,
        system_prompt=parent_assistant.system_prompt,
        project=PROJECT,
        llm_model_type=parent_assistant.llm_model_type,
        assistant_ids=[],
    )
    assistant_utils.update_assistant(parent_assistant.id, update_request)

    # Verify sub-assistant was removed
    updated_parent = assistant_utils.get_assistant_by_id(parent_assistant.id)
    assert_that(
        len(updated_parent["assistant_ids"]),
        equal_to(0),
        "Parent should have no sub-assistants after removal",
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.api
def test_nested_sub_assistants_not_allowed(assistant, assistant_utils):
    """
    Test that nested sub-assistant hierarchies are not allowed.

    Verifies that:
    - System prevents or rejects nested sub-assistant structures
    - An assistant that is already a sub-assistant cannot be added as a parent
    - Only flat (single-level) sub-assistant relationships are supported
    """

    assistant_c = assistant(
        system_prompt="You are assistant C",
    )

    # First, make C a sub-assistant of B (B -> C)
    assistant_b = assistant(
        system_prompt="You are assistant B", sub_assistants_ids=[assistant_c.id]
    )

    # Verify B has C as sub-assistant
    assistant_b = assistant_utils.get_assistant_by_id(assistant_b.id)
    assert_that(
        assistant_b["assistant_ids"],
        has_items(assistant_c.id),
        "Assistant B should have C as sub-assistant",
    )

    # Now try to create assistant with sub-assistant B (which has sub-assistant)
    with pytest.raises(Exception) as exec_info:
        assistant_utils.send_create_assistant_request(
            system_prompt="You are assistant A",
            assistant_ids=[assistant_b.id],
        )
    assert_error_details(
        exec_info.value.response,
        400,
        f"Nested assistants aren't supported. Assistant '{assistant_b.name}' can't have its own sub-assistants",
    )

    assistant_a = assistant(
        system_prompt="You are assistant A",
    )

    assistant_a = assistant_utils.get_assistant_by_id(assistant_a.id)

    update_a = AssistantUpdateRequest(
        name=assistant_a.name,
        description=assistant_a.description,
        shared=False,
        system_prompt=assistant_a.system_prompt,
        project=PROJECT,
        llm_model_type=assistant_a.llm_model_type,
        assistant_ids=[assistant_b.id],  # Try to add B (which has C) as sub-assistant
    )

    with pytest.raises(Exception) as exec_info:
        assistant_utils.update_assistant(assistant_a.id, update_a)
    assert_error_details(
        exec_info.value.response,
        400,
        f"Nested assistants aren't supported. Assistant '{assistant_b.name}' can't have its own sub-assistants",
    )


@pytest.mark.github
@pytest.mark.gitlab
@pytest.mark.jira
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.api
def test_chat_with_assistant_having_different_sub_assistants(
    assistant,
    assistant_utils,
    similarity_check,
    jira_integration,
    gitlab_integration,
    code_datasource,
    code_context,
    seeded,
):
    """
    Test chatting with an assistant that has sub-assistants with different tools.

    Verifies that:
    - Parent assistant can delegate to sub-assistants with different capabilities
    - Sub-assistants with Jira, Git, and Code-executor tools work correctly
    - Chat functionality properly routes requests to appropriate sub-assistants
    """

    # 1. Create sub-assistant with Jira tool
    jira_assistant = assistant(
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.JIRA,
        description="Jira expert. Helps with searching and managing Jira issues.",
        settings=jira_integration,
        system_prompt="""
            You are a Jira specialist assistant. When you receive a request, you MUST immediately call the appropriate Jira tool to complete the task.

            CRITICAL RULES:
            1. ALWAYS call a Jira tool for EVERY request - never respond without calling a tool first
            2. When YOU are invoked, YOU are responsible for executing the Jira tool - no one else will do it
            3. Get the actual data using your tool, then respond with the results
            4. NEVER say "please wait" or "I will retrieve" - just call the tool immediately

            STEPS TO FOLLOW:
            1. Identify which Jira tool to use based on the request
            2. Call the tool with appropriate parameters
            3. Return the results from the tool

            If you receive a request about a Jira ticket, you MUST call your Jira tool to retrieve the actual data. Conversational responses without tool calls are not acceptable.
        """,
    )

    # 2. Create sub-assistant with Git tool
    git_assistant = assistant(
        Toolkit.GIT,
        GitTool.LIST_BRANCHES_IN_REPO,
        description="Git expert. Helps with Git repository operations.",
        settings=gitlab_integration,
        context=code_context(code_datasource),
        system_prompt="""
            You are a Git specialist assistant. When you receive a request, you MUST immediately call the appropriate Git tool to complete the task.

            CRITICAL RULES:
            1. ALWAYS call a Git tool for EVERY request - never respond without calling a tool first
            2. When YOU are invoked, YOU are responsible for executing the Git tool - no one else will do it
            3. Get the actual data using your tool, then respond with the results
            4. NEVER say "please wait" or "I will retrieve" - just call the tool immediately

            STEPS TO FOLLOW:
            1. Identify which Git tool to use based on the request (search code, analyze repository, get file content, etc.)
            2. Call the tool with appropriate parameters
            3. Return the results from the tool

            If you receive a request about Git repository operations, code search, or file analysis, you MUST call your Git tool to retrieve the actual data. Conversational responses without tool calls are not acceptable.
        """,
    )

    # 3. Create sub-assistant with Code-executor tool (Python REPL)
    code_executor_assistant = assistant(
        Toolkit.FILE_MANAGEMENT,
        FileManagementTool.CODE_EXECUTOR,
        description="Python code execution expert. Helps with running Python code.",
        system_prompt="""
            You are a Python code execution expert. When you receive a request, you MUST immediately call the code_executor tool to execute the code.

            CRITICAL RULES:
            1. ALWAYS call the code_executor tool for EVERY request - never respond without calling the tool first
            2. When YOU are invoked, YOU are responsible for executing the Python code - no one else will do it
            3. Execute the code using your tool, then respond with the results
            4. NEVER say "please wait" or "I will execute" - just call the tool immediately

            STEPS TO FOLLOW:
            1. Identify the Python code to execute from the request
            2. Call code_executor with the code
            3. Return the execution results (output, errors, or return values)

            If you receive a request to run Python code, test a script, or execute code snippets, you MUST call your code_executor tool to execute it. Conversational responses without tool calls are not acceptable.
        """,
    )

    # 4. Create parent assistant with all sub-assistants
    parent_assistant = assistant(
        system_prompt=(
            "You are a coordinator assistant that delegates tasks to specialized sub-assistants. "
            "You have access to sub-assistants for Jira operations, Git operations, and Python code execution. "
            f"Use {jira_assistant.name} for Jira related requests."
            f"Use {git_assistant.name} for Git related requests."
            f"Use {code_executor_assistant.name} for Code execution requests."
        ),
        sub_assistants_ids=[
            jira_assistant.id,
            git_assistant.id,
            code_executor_assistant.id,
        ],
    )

    # 5. Send a chat request to parent assistant asking Jira-related question
    response = assistant_utils.ask_assistant(
        parent_assistant, seeded(JIRA_TOOL_PROMPT), minimal_response=True, stream=True
    )
    assert_that(
        response,
        is_not(matches_regexp(BACKEND_400_ERROR_PATTERN)),
        "Final response must not contain the appended Azure/LiteLLM 400 error",
    )
    similarity_check.check_similarity(
        response, seeded(RESPONSE_FOR_JIRA_TOOL), similarity_rank=90
    )

    # 6. Send a chat request to parent assistant asking Git-related question
    git_tool_prompt = list_branches_set_active_branch_test_data[0].values[2]
    git_tool_answer = list_branches_set_active_branch_test_data[0].values[3]
    response = assistant_utils.ask_assistant(
        parent_assistant, git_tool_prompt, minimal_response=True, stream=True
    )

    # Default similarity_rank (not 90): the repo's branch population is now seeded per
    # env/run, so the assistant's "matching main" preamble can list a different number of
    # branches than this fixed expected text, which otherwise drags a strict 90 below pass.
    # test_assistant_with_git_tools.py checks this same prompt/expected pair at the default
    # rank for the same reason.
    similarity_check.check_similarity(response, git_tool_answer)

    # 7. Send a chat request to parent assistant asking Code-executor question
    response = assistant_utils.ask_assistant(
        parent_assistant,
        code_tools_test_data[1].values[1],
        minimal_response=True,
        stream=True,
    )

    similarity_check.check_similarity(
        response, code_tools_test_data[1].values[2], similarity_rank=90
    )


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.jira
@pytest.mark.api
@pytest.mark.parametrize("stream_mode", [False, True], ids=["non_stream", "stream"])
def test_chat_with_tool_sub_assistant_handoff_returns_no_backend_error(
    assistant_factory,
    assistant_utils,
    similarity_check,
    jira_integration,
    stream_mode,
    seeded,
):
    """
    Regression test: the supervisor replayed the sub-assistant's
    intermediate tool-call message as the handoff answer, leaving an orphaned
    `tool` message in the history. Azure/LiteLLM rejected it with a 400 and that
    text was appended to an otherwise correct final answer.

    Fixed in Prod 2.57.0 - expected to fail on older builds.

    The sub-assistant MUST call a tool (Jira) for the faulty path to be exercised.
    """
    sub_assistant = assistant_factory.create(
        llm_model_type=ModelTypes.GPT_5_2_2025_12_11,
        system_prompt=JIRA_SUB_ASSISTANT_SYSTEM_PROMPT,
        toolkits=[
            ToolKitDetails(
                toolkit=Toolkit.PROJECT_MANAGEMENT,
                tools=[
                    ToolDetails(
                        name=ProjectManagementTool.JIRA,
                        settings=jira_integration,
                    )
                ],
            )
        ],
    )
    parent_assistant = assistant_factory.create(
        llm_model_type=ModelTypes.GPT_5_2_2025_12_11,
        system_prompt=PARENT_ASSISTANT_SYSTEM_PROMPT,
        assistant_ids=[sub_assistant.id],
    )

    response = assistant_utils.ask_assistant(
        parent_assistant,
        seeded(JIRA_SUB_ASSISTANT_PROMPT),
        minimal_response=True,
        stream=stream_mode,
    )

    assert_that(
        response,
        is_not(matches_regexp(BACKEND_400_ERROR_PATTERN)),
        "Final response must not contain the appended Azure/LiteLLM 400 error",
    )
    similarity_check.check_similarity(
        response, seeded(RESPONSE_FOR_JIRA_TOOL), similarity_rank=90
    )


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.api
@pytest.mark.parametrize(
    "schema_type,stream_mode",
    [
        pytest.param(
            "pydantic",
            False,
            marks=[pytest.mark.smoke, pytest.mark.sanity],
            id="pydantic_non_stream",
        ),
        pytest.param("pydantic", True, id="pydantic_stream"),
        pytest.param("json", False, id="json_non_stream"),
        pytest.param("json", True, id="json_stream"),
    ],
)
def test_chat_with_sub_assistant_and_output_schema(
    assistant, assistant_utils, schema_type, stream_mode
):
    class OutputSchema(BaseModel):
        results: list[int]

    # Create sub-assistant for calculations
    sub_assistant = assistant(
        system_prompt="You are a specialized calculation assistant.",
    )

    # Create parent assistant with sub-assistant
    parent_assistant = assistant(
        system_prompt=(
            f"You are a coordinator assistant that delegates calculation tasks to the sub-assistant. "
            f"When asked about calculations, delegate to {sub_assistant.name}. "
            "Ensure the response follows any structured output schema provided."
        ),
        sub_assistants_ids=[sub_assistant.id],
    )

    # Select schema based on parameter
    schema = OutputSchema if schema_type == "pydantic" else output_schema

    # Send chat request with output schema
    response = assistant_utils.ask_assistant(
        parent_assistant,
        "Trigger sub-assistant to answer 1+1?",
        output_schema=schema,
        stream=stream_mode,
    )

    # Handle response based on schema type
    if schema_type == "pydantic":
        assert_that(response.results[0], equal_to(2))
    else:
        assert_that(response["results"][0], equal_to(2))


@pytest.mark.assistant
@pytest.mark.sub_assistant
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.production_check
@pytest.mark.skipif(
    get_environment() not in Environment.get_aws_environments(),
    reason="claude-sonnet-5 is only served through AWS Bedrock",
)
@pytest.mark.parametrize(
    "name_variant",
    ["boundary_64_chars", "overlong_invalid_chars"],
)
def test_chat_continues_after_handoff_to_sub_assistant_with_long_name(
    assistant_factory, assistant_utils, name_variant
):
    """
    Regression test: Bedrock rejects any replayed
    toolUse.name over 64 chars or outside [a-zA-Z0-9_-]. The handoff tool
    itself is truncated, but the sub-assistant's raw display name used to
    leak into history replay on the turn after a handoff.
    """
    base_name = get_random_name()
    if name_variant == "boundary_64_chars":
        sub_assistant_name = (base_name + "x" * 63)[:63]
    else:
        random_suffix = "a" * 80
        sub_assistant_name = f"{base_name} {random_suffix}"

    sub_assistant = assistant_factory.create(
        assistant_name=sub_assistant_name,
        llm_model_type=ModelTypes.GPT_5_2_2025_12_11,
    )
    parent_assistant = assistant_factory.create(
        llm_model_type=ModelTypes.CLAUDE_5_SONNET,
        system_prompt="ALWAYS delegate any math question to your sub-assistant.",
        assistant_ids=[sub_assistant.id],
        mcp_servers=[FETCH_MCP_SERVER],
    )

    conversation_id = str(uuid.uuid4())

    first_response = assistant_utils.ask_assistant(
        parent_assistant, "What is 2+2?", conversation_id=conversation_id
    )
    assert_that(first_response, contains_string("4"))

    second_response = assistant_utils.ask_assistant(
        parent_assistant, "What is 10+5?", conversation_id=conversation_id
    )
    assert_that(second_response, contains_string("15"))
