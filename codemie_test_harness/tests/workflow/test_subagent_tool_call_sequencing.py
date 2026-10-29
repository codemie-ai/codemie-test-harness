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
from codemie_sdk.models.assistant import ToolDetails, ToolKitDetails
from hamcrest import assert_that, is_not, none

from codemie_test_harness.tests.enums.tools import ProjectManagementTool, Toolkit
from codemie_test_harness.tests.test_data.pm_tools_test_data import (
    RESPONSE_FOR_JIRA_TOOL,
)
from codemie_test_harness.tests.test_data.subagent_tool_call_test_data import (
    JIRA_SUB_ASSISTANT_SYSTEM_PROMPT,
    PARENT_ASSISTANT_SYSTEM_PROMPT,
    PARENT_ASSISTANT_WITH_MULTIPLE_SUBS_SYSTEM_PROMPT,
    JIRA_SUB_ASSISTANT_PROMPT,
)


@pytest.mark.workflow
@pytest.mark.jira
@pytest.mark.api
def test_workflow_with_subagent_tool_call_completes_without_error(
    assistant_factory,
    default_llm,
    workflow_with_assistant,
    workflow_utils,
    similarity_check,
    jira_integration,
    seeded,
):
    """
    Verify that a workflow containing an assistant with a tool-using sub-assistant
    completes without a 400 error from Azure litellm.

    The bug caused a malformed tool_call/result sequence when a sub-assistant
    issued a tool call — the tool_call message was not immediately followed by
    the corresponding tool result, triggering a 400 from Azure litellm.
    """
    sub_assistant = assistant_factory.create(
        llm_model_type=default_llm.base_name,
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
        llm_model_type=default_llm.base_name,
        system_prompt=PARENT_ASSISTANT_SYSTEM_PROMPT,
        assistant_ids=[sub_assistant.id],
    )

    test_workflow = workflow_with_assistant(
        parent_assistant, seeded(JIRA_SUB_ASSISTANT_PROMPT)
    )

    response = workflow_utils.execute_workflow(
        test_workflow.id,
        execution_name=parent_assistant.name,
        user_input="Start",
    )

    # assert_tool_triggered(ProjectManagementTool.JIRA, triggered_tools)
    assert_that(response, is_not(none()))
    similarity_check.check_similarity(
        response, seeded(RESPONSE_FOR_JIRA_TOOL), similarity_rank=90
    )


@pytest.mark.workflow
@pytest.mark.jira
@pytest.mark.api
def test_workflow_with_multiple_subagents_tool_calls_completes_without_error(
    assistant_factory,
    default_llm,
    workflow_with_assistant,
    workflow_utils,
    similarity_check,
    jira_integration,
    seeded,
):
    """
    Verify that a workflow with a parent assistant delegating to multiple
    tool-using sub-assistants completes without 400 errors.

    Covers the case where two sub-assistants independently issue Jira tool calls,
    verifying that neither produces a malformed tool_call/result sequence.
    """
    sub_assistant_one = assistant_factory.create(
        llm_model_type=default_llm.base_name,
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

    sub_assistant_two = assistant_factory.create(
        llm_model_type=default_llm.base_name,
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
        llm_model_type=default_llm.base_name,
        system_prompt=PARENT_ASSISTANT_WITH_MULTIPLE_SUBS_SYSTEM_PROMPT,
        assistant_ids=[sub_assistant_one.id, sub_assistant_two.id],
    )

    test_workflow = workflow_with_assistant(
        parent_assistant, seeded(JIRA_SUB_ASSISTANT_PROMPT)
    )

    response = workflow_utils.execute_workflow(
        test_workflow.id,
        execution_name=parent_assistant.name,
        user_input="Start",
    )

    # assert_tool_triggered(ProjectManagementTool.JIRA, triggered_tools)
    assert_that(response, is_not(none()))
    similarity_check.check_similarity(
        response, seeded(RESPONSE_FOR_JIRA_TOOL), similarity_rank=90
    )
