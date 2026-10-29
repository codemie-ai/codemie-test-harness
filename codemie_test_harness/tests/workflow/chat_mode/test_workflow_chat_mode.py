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

import json
import re

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    has_property,
    not_none,
    contains_string,
)

from codemie_test_harness.tests.test_data.direct_tools.vcs_tools_test_data import (
    vcs_tools_test_data,
)
from codemie_test_harness.tests.test_data.git_tools_test_data import (
    list_branches_set_active_branch_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.conversations
@pytest.mark.api
def test_workflow_with_assistant_chat_mode(
    assistant,
    conversation_utils,
    workflow_with_assistant,
    workflow_utils,
):
    """
    Test workflow chat mode functionality.

    Verifies that workflow executions can be created with conversation context,
    and that the conversation properly tracks the interaction.
    """
    # Step 1: Create assistant and workflow
    created_assistant = assistant(
        system_prompt="You are the math expert. Do not format output as markdown"
    )
    created_workflow = workflow_with_assistant(created_assistant, "Run")

    # Step 2: Create workflow conversation
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    # Step 3: Send chat message via workflow execution
    user_message = "Solve it, only answer: 2+2*2"
    execution = workflow_utils.create_workflow_execution(
        workflow_id=created_workflow.id,
        user_input=user_message,
        conversation_id=conversation_id,
    )

    # Verify execution was completed successfully
    assert_that(execution, has_property("prompt", contains_string(user_message)))
    assert_that(execution, has_property("conversation_id", equal_to(conversation_id)))

    # Verify conversation exists and contains user data with LLM response
    conversation_details = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation_details, not_none(), "Conversation should exist")
    assert_that(conversation_details, has_property("id", equal_to(conversation_id)))
    assert_that(
        conversation_details, has_property("is_workflow_conversation", equal_to(True))
    )
    assert_that(
        conversation_details,
        has_property("initial_assistant_id", equal_to(created_workflow.id)),
    )
    assert_that(
        conversation_details,
        has_property("conversation_name", contains_string(user_message)),
    )
    assert_that(
        conversation_details.history[1]
        .thoughts[0]
        .message.strip()
        .replace("text", "")
        .replace("\n", "")
        .replace("`", ""),
        equal_to("6"),
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.conversations
@pytest.mark.api
def test_workflow_with_virtual_assistant_chat_mode(
    conversation_utils,
    workflow_with_virtual_assistant,
    workflow_utils,
):
    """
    Test workflow chat mode functionality.

    Verifies that workflow executions can be created with conversation context,
    and that the conversation properly tracks the interaction.
    """
    # Step 1: Create workflow with virtual assistant

    assistant_and_state_name = get_random_name()

    created_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name, system_prompt="You are the math expert"
    )

    # Step 2: Create workflow conversation
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    # Step 3: Send chat message via workflow execution
    user_message = "Solve it, only answer: 2+2*2"
    execution = workflow_utils.create_workflow_execution(
        workflow_id=created_workflow.id,
        user_input=user_message,
        conversation_id=conversation_id,
    )

    # Verify execution was completed successfully
    assert_that(execution, has_property("prompt", contains_string(user_message)))
    assert_that(execution, has_property("conversation_id", equal_to(conversation_id)))

    # Verify conversation exists and contains user data with LLM response
    conversation_details = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation_details, not_none(), "Conversation should exist")
    assert_that(conversation_details, has_property("id", equal_to(conversation_id)))
    assert_that(
        conversation_details, has_property("is_workflow_conversation", equal_to(True))
    )
    assert_that(
        conversation_details,
        has_property("initial_assistant_id", equal_to(created_workflow.id)),
    )
    assert_that(
        conversation_details,
        has_property("conversation_name", contains_string(user_message)),
    )
    assert_that(
        re.sub(r"\D", "", conversation_details.history[1].thoughts[0].message),
        equal_to("6"),
    )


@pytest.mark.github
@pytest.mark.requires_capability("retrieval")
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.conversations
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    [list_branches_set_active_branch_test_data[1]],
    ids=["git_set_active_branch"],
)
def test_workflow_assistant_with_git_chat_mode(
    assistant,
    conversation_utils,
    workflow_with_assistant,
    workflow_utils,
    code_datasource,
    code_context,
    gitlab_integration,
    similarity_check,
    toolkit,
    tool_name,
    prompt,
    expected_response,
):
    """
    Test workflow chat mode with native assistant using git tool.

    Verifies that workflow executions with conversation context can trigger tools,
    and that the conversation properly tracks the tool usage interaction.
    """
    # Step 1: Create assistant with git tool and workflow
    created_assistant = assistant(
        toolkit,
        tool_name,
        context=code_context(code_datasource),
        settings=gitlab_integration,
    )
    created_workflow = workflow_with_assistant(created_assistant, prompt)

    # Step 2: Create workflow conversation
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    # Step 3: Send chat message via workflow execution and get response
    execution = workflow_utils.create_workflow_execution(
        workflow_id=created_workflow.id,
        user_input=prompt,
        conversation_id=conversation_id,
    )

    # Verify execution was completed successfully with conversation
    assert_that(execution, has_property("prompt", contains_string(prompt)))
    assert_that(execution, has_property("conversation_id", equal_to(conversation_id)))

    # Step 4: Execute workflow and get response
    response = workflow_utils.execute_workflow(
        created_workflow.id, created_assistant.name
    )

    # Verify tool was triggered
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        created_workflow
    )
    assert_tool_triggered(tool_name, triggered_tools)

    # Verify response matches expected
    similarity_check.check_similarity(response, expected_response)

    # Verify conversation exists and contains the interaction
    conversation_details = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation_details, not_none(), "Conversation should exist")
    assert_that(conversation_details, has_property("id", equal_to(conversation_id)))
    assert_that(
        conversation_details, has_property("is_workflow_conversation", equal_to(True))
    )
    assert_that(
        conversation_details,
        has_property("initial_assistant_id", equal_to(created_workflow.id)),
    )


@pytest.mark.github
@pytest.mark.requires_capability("retrieval")
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.conversations
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    [list_branches_set_active_branch_test_data[1]],
    ids=["git_set_active_branch"],
)
def test_workflow_virtual_assistant_git_chat_mode(
    conversation_utils,
    workflow_with_virtual_assistant,
    workflow_utils,
    code_datasource,
    gitlab_integration,
    similarity_check,
    toolkit,
    tool_name,
    prompt,
    expected_response,
):
    """
    Test workflow chat mode with virtual assistant using git tool.

    Verifies that workflow executions with conversation context can trigger tools,
    and that the conversation properly tracks the tool usage interaction.
    """
    # Step 1: Create workflow with virtual assistant and git tool
    assistant_and_state_name = get_random_name()

    created_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        tool_name,
        integration=gitlab_integration,
        task=prompt,
        datasource_ids=[code_datasource.id],
    )

    # Step 2: Create workflow conversation
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    # Step 3: Send chat message via workflow execution and get response
    execution = workflow_utils.create_workflow_execution(
        workflow_id=created_workflow.id,
        user_input=prompt,
        conversation_id=conversation_id,
    )

    # Verify execution was completed successfully with conversation
    assert_that(execution, has_property("prompt", contains_string(prompt)))
    assert_that(execution, has_property("conversation_id", equal_to(conversation_id)))

    # Step 4: Execute workflow and get response
    response = workflow_utils.execute_workflow(
        created_workflow.id, assistant_and_state_name
    )

    # Verify tool was triggered
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        created_workflow
    )
    assert_tool_triggered(tool_name, triggered_tools)

    # Verify response matches expected
    similarity_check.check_similarity(response, expected_response)

    # Verify conversation exists and contains the interaction
    conversation_details = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation_details, not_none(), "Conversation should exist")
    assert_that(conversation_details, has_property("id", equal_to(conversation_id)))
    assert_that(
        conversation_details, has_property("is_workflow_conversation", equal_to(True))
    )
    assert_that(
        conversation_details,
        has_property("initial_assistant_id", equal_to(created_workflow.id)),
    )


@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.conversations
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    [vcs_tools_test_data[1]],
    ids=["vcs_gitlab"],
)
def test_workflow_direct_tool_git_chat_mode(
    conversation_utils,
    workflow_with_tool,
    workflow_utils,
    gitlab_integration,
    similarity_check,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    seeded,
):
    """
    Test workflow chat mode with direct tool calling using git tool.

    Verifies that workflow executions with conversation context can trigger tools directly,
    and that the conversation properly tracks the tool usage interaction.
    """
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)

    # Step 1: Create workflow with direct tool call
    assistant_and_state_name = get_random_name()

    created_workflow = workflow_with_tool(
        assistant_and_state_name,
        tool_name,
        integration=gitlab_integration,
    )

    # Step 2: Create workflow conversation
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]

    # Step 3: Send chat message via workflow execution with tool arguments
    execution = workflow_utils.create_workflow_execution_without_prompt_modification(
        workflow_id=created_workflow.id,
        user_input=json.dumps(prompt),
        conversation_id=conversation_id,
    )

    # Verify execution was completed successfully with conversation
    assert_that(execution, has_property("conversation_id", equal_to(conversation_id)))

    # Step 4: Execute workflow and get response
    response = workflow_utils.execute_workflow_without_prompt_modification(
        created_workflow.id, assistant_and_state_name, json.dumps(prompt)
    )

    # Verify response matches expected using similarity check
    similarity_check.check_similarity(response, expected_response, 95)

    # Verify conversation exists and contains the interaction
    conversation_details = conversation_utils.get_conversation_by_id(conversation_id)
    assert_that(conversation_details, not_none(), "Conversation should exist")
    assert_that(conversation_details, has_property("id", equal_to(conversation_id)))
    assert_that(
        conversation_details, has_property("is_workflow_conversation", equal_to(True))
    )
    assert_that(
        conversation_details,
        has_property("initial_assistant_id", equal_to(created_workflow.id)),
    )
