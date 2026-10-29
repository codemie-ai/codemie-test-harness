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

"""An assistant in a chat runs a script that calls the assistant's tools.

The assistant is driven by an LLM, so the prompts ask it to run one script and repeat the
script's output; the assertions read the outcomes the script itself recorded.
"""

import json

import pytest
from codemie_sdk.models.assistant import (
    AssistantChatRequest,
    ToolCallPolicy,
    ToolDetails,
    ToolKitDetails,
    ToolPermissionsConfig,
)
from hamcrest import assert_that, contains_string, has_entries, is_, is_not

from codemie_test_harness.tests.assistant.tool_permissions.conftest import (
    _iter_stream_chunks,
)
from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool, Toolkit
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    CODE_TOOL_UNAVAILABLE,
    ECHO_SCRIPT,
    JIRA_TOOL,
    SCOPE_MARKER,
    SCOPE_PROBE_SCRIPT,
    render_script,
)
from codemie_test_harness.tests.utils.workspace_script_utils import (
    extract_marked_json,
    random_marker,
    unique_script_name,
    upload_text_file,
)

EXECUTE_SCRIPT = AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value

SYSTEM_PROMPT = (
    "You run workspace scripts. When asked to run a script, call execute_workspace_script "
    "exactly once with that script path, then reply with the complete stdout of the script "
    "and nothing else."
)


def run_script_prompt(script_name: str) -> str:
    return f"Run the workspace script '{script_name}' and reply with its stdout."


@pytest.fixture
def create_script_assistant(default_llm, assistant_utils):
    """Factory ``(tool_permissions=None, integration=None) -> assistant``; deleted at teardown."""
    created = []

    def _create(tool_permissions=None, integration=None):
        toolkits = [
            ToolKitDetails(
                toolkit=Toolkit.AGENT_WORKSPACE,
                tools=[ToolDetails(name=EXECUTE_SCRIPT)],
            )
        ]
        if integration is not None:
            toolkits.append(
                ToolKitDetails(
                    toolkit=Toolkit.PROJECT_MANAGEMENT,
                    tools=[ToolDetails(name=JIRA_TOOL, settings=integration)],
                    settings=integration,
                )
            )
        assistant = assistant_utils.create_assistant(
            llm_model_type=default_llm.base_name,
            toolkits=toolkits,
            system_prompt=SYSTEM_PROMPT,
            tool_permissions=tool_permissions,
        )
        created.append(assistant)
        return assistant

    yield _create
    for assistant in created:
        assistant_utils.delete_assistant(assistant)


@pytest.fixture
def create_conversation(conversation_utils):
    """Factory ``(assistant) -> conversation id``; every conversation is deleted at teardown."""
    created = []

    def _create(assistant) -> str:
        conversation_id = conversation_utils.create_conversation(
            initial_assistant_id=assistant.id, folder=""
        ).get("id")
        created.append(conversation_id)
        return conversation_id

    yield _create
    for conversation_id in created:
        conversation_utils.delete_conversation(conversation_id)


@pytest.mark.jira
@pytest.mark.assistant
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.integration
def test_script_uploaded_in_chat_calls_only_the_assistants_tools(
    client, assistant_utils, create_script_assistant, jira_user_integration
):
    """The assistant has Jira but not Confluence: the script gets Jira's real answer and a Confluence refusal."""
    assistant = create_script_assistant(integration=jira_user_integration)
    script_name = unique_script_name("chat_scope")
    file_url = upload_text_file(client, script_name, SCOPE_PROBE_SCRIPT)

    response = assistant_utils.ask_assistant(
        assistant, run_script_prompt(script_name), file_urls=[file_url]
    )

    scope = extract_marked_json(response, SCOPE_MARKER)
    assert_that(scope["jira"], has_entries(status=200))
    assert_that(scope["confluence"]["error"], has_entries(code=CODE_TOOL_UNAVAILABLE))


@pytest.mark.assistant
@pytest.mark.workspace
@pytest.mark.api
def test_script_run_is_held_for_approval_when_policy_asks(
    client, create_script_assistant, create_conversation
):
    """With "ask for approval" the person is asked first: the stream is interrupted and the script has not run."""
    assistant = create_script_assistant(
        tool_permissions=ToolPermissionsConfig(
            tool_call_policy=ToolCallPolicy.ASK_FOR_APPROVAL, allow_override=True
        )
    )
    marker = random_marker()
    script_name = unique_script_name("chat_approval")
    file_url = upload_text_file(client, script_name, render_script(ECHO_SCRIPT, marker))
    conversation_id = create_conversation(assistant)

    response = client.assistants.chat(
        assistant.id,
        AssistantChatRequest(
            text=run_script_prompt(script_name),
            conversation_id=conversation_id,
            stream=True,
            file_names=[file_url],
        ),
    )
    chunks = list(_iter_stream_chunks(response))

    interrupted = any(
        (chunk.get("thought") or {}).get("interrupted") is True for chunk in chunks
    )
    assert_that(interrupted, is_(True))
    assert_that(json.dumps(chunks), is_not(contains_string(f"ECHO-{marker}")))
