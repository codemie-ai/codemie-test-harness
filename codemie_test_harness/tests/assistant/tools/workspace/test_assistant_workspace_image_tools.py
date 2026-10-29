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
from hamcrest import (
    all_of,
    assert_that,
    contains_string,
    greater_than,
    has_item,
    has_length,
    has_property,
    is_not,
)

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool, Toolkit
from codemie_test_harness.tests.test_data.workspace_image_test_data import (
    IMAGE_FILE,
    INVALID_IMAGE_FILE,
    MULTI_STEP_SYSTEM_PROMPT,
    OLD_IMAGE_ARTIFACT_MARKER,
    SYSTEM_PROMPT,
    describe_image_prompt,
    inspect_image_prompt,
    invalid_image_inspect_prompt,
    multi_step_prompt,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_tool_not_triggered,
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH


@pytest.mark.assistant
@pytest.mark.api
def test_assistant_with_workspace_inspect_image_tool(
    assistant_utils, assistant, similarity_check, conversation_utils
):
    created = assistant(
        Toolkit.AGENT_WORKSPACE,
        AgentWorkspaceTool.INSPECT_WORKSPACE_IMAGE,
        system_prompt=SYSTEM_PROMPT,
    )

    uploaded_file = assistant_utils.upload_file_to_chat(FILES_PATH / IMAGE_FILE)
    file_url = uploaded_file.get("file_url")

    response, triggered_tools = assistant_utils.ask_assistant(
        created,
        inspect_image_prompt(),
        file_urls=[file_url],
        minimal_response=False,
    )

    assert_tool_triggered(AgentWorkspaceTool.INSPECT_WORKSPACE_IMAGE, triggered_tools)
    similarity_check.check_similarity(response, "Dog")

    # AC-1: the independent LLM call must return the analysis as a plain tool
    # response — it must no longer insert an extra history message carrying the
    # base64 image (the removed `content_and_artifact` side-channel). A single
    # chat turn is exactly one user item + one assistant item.
    conversations = conversation_utils.get_conversation_by_assistant_id(created.id)
    conversation = conversation_utils.get_conversation_by_id(conversations[0].id)

    assert_that(conversation.history, has_length(2))
    assert_that(
        conversation.history,
        is_not(
            has_item(
                has_property("message", contains_string(OLD_IMAGE_ARTIFACT_MARKER))
            )
        ),
    )


@pytest.mark.assistant
@pytest.mark.api
def test_assistant_regular_chat_with_image_attachment_does_not_trigger_inspect_tool(
    assistant_utils, assistant, similarity_check
):
    # No AgentWorkspace/inspect_workspace_image toolkit is attached here: this is
    # a plain assistant, so there is no way for inspect_workspace_image to fire.
    # This isolates the AC-8 regression guard — a regular chat message with an
    # image attachment must keep working through the plain multimodal chat path
    # (independent of the now-lazy AgentWorkspaceToolkit LLM-client construction)
    # — from the model's own (valid) choice to use the tool when it is offered.
    created = assistant()

    uploaded_file = assistant_utils.upload_file_to_chat(FILES_PATH / IMAGE_FILE)
    file_url = uploaded_file.get("file_url")

    response, triggered_tools = assistant_utils.ask_assistant(
        created,
        describe_image_prompt(),
        file_urls=[file_url],
        minimal_response=False,
    )

    assert_tool_not_triggered(
        AgentWorkspaceTool.INSPECT_WORKSPACE_IMAGE, triggered_tools
    )
    similarity_check.check_similarity(response, "The image shows a dog.")


@pytest.mark.assistant
@pytest.mark.api
def test_assistant_continues_multi_step_workflow_after_inspect_image_tool_on_non_anthropic_model(
    assistant_utils, assistant_factory, non_anthropic_multimodal_model
):
    tool = ToolKitDetails(
        toolkit=Toolkit.AGENT_WORKSPACE,
        tools=[ToolDetails(name=AgentWorkspaceTool.INSPECT_WORKSPACE_IMAGE)],
    )
    created = assistant_factory.create(
        non_anthropic_multimodal_model,
        toolkits=[tool],
        system_prompt=MULTI_STEP_SYSTEM_PROMPT,
    )

    uploaded_file = assistant_utils.upload_file_to_chat(FILES_PATH / IMAGE_FILE)
    file_url = uploaded_file.get("file_url")

    response, triggered_tools = assistant_utils.ask_assistant(
        created,
        multi_step_prompt(),
        file_urls=[file_url],
        minimal_response=False,
    )

    # AC-9: the agentic loop must not stop after inspect_workspace_image executes
    # mid-workflow on a non-Anthropic model — all three requested steps must be
    # completed.
    assert_tool_triggered(AgentWorkspaceTool.INSPECT_WORKSPACE_IMAGE, triggered_tools)
    assert_that(
        response.lower(),
        all_of(
            contains_string("4"),
            contains_string("dog"),
            contains_string("paris"),
        ),
    )


@pytest.mark.assistant
@pytest.mark.api
def test_assistant_surfaces_inspect_image_tool_failure_for_non_image_file(
    assistant_utils, assistant
):
    created = assistant(
        Toolkit.AGENT_WORKSPACE,
        AgentWorkspaceTool.INSPECT_WORKSPACE_IMAGE,
        system_prompt=SYSTEM_PROMPT,
    )

    uploaded_file = assistant_utils.upload_file_to_chat(FILES_PATH / INVALID_IMAGE_FILE)
    file_url = uploaded_file.get("file_url")

    response, triggered_tools = assistant_utils.ask_assistant(
        created,
        invalid_image_inspect_prompt(),
        file_urls=[file_url],
        minimal_response=False,
        extract_failed_tools=True,
    )

    # AC-7: the ToolException wrapping (non-multimodal/lookup/invoke/no-response
    # paths) must surface through the standard tool-failure channel — the chat
    # call itself succeeds, the failed tool thought is still reported, and the
    # final answer is natural language rather than a raw stack trace.
    assert_tool_triggered(AgentWorkspaceTool.INSPECT_WORKSPACE_IMAGE, triggered_tools)
    assert_that(response, has_length(greater_than(0)))
    assert_that(response, is_not(contains_string("Traceback")))
