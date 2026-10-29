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

"""A script run by a workflow assistant step may call only that assistant's tools.

Unlike a bare tool step (any catalog tool), an
assistant step gets the scope of its own assistant, as in a chat.

The assistant is driven by an LLM, so the prompt asks it to run one script and repeat the
script's output; the assertions read the outcomes the script itself recorded.
"""

import pytest
from hamcrest import assert_that, has_entries

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    CODE_TOOL_UNAVAILABLE,
    JIRA_TOOL,
    SCOPE_MARKER,
    SCOPE_PROBE_SCRIPT,
)
from codemie_test_harness.tests.utils.workspace_script_utils import (
    SCRIPT_WORKFLOW_EXECUTION_TIMEOUT,
    extract_marked_json,
)
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    ToolModel,
)

SYSTEM_PROMPT = (
    "You run workspace scripts. When asked to run a script, call execute_workspace_script "
    "exactly once with that script path, then reply with the complete stdout of the script "
    "and nothing else."
)


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.integration
def test_assistant_step_script_can_call_only_its_assistants_tools(
    workflow_utils,
    create_script_workflow,
    upload_script,
    jira_user_integration,
    default_llm,
):
    """The assistant has Jira but not Confluence: the script reaches Jira and is refused Confluence."""
    script_name, file_url = upload_script(SCOPE_PROBE_SCRIPT, prefix="scope")
    assistant = AssistantModel(
        id="scoped_assistant",
        model=default_llm.base_name,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            ToolModel(name=AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value),
            ToolModel(name=JIRA_TOOL, integration_alias=jira_user_integration.alias),
        ],
    )
    state = StateModel(
        id="scoped_step",
        assistant_id="scoped_assistant",
        task=f"Run the workspace script '{script_name}' and reply with its stdout.",
    )
    workflow = create_script_workflow([], [state], assistants=[assistant])

    execution = workflow_utils.create_workflow_execution(
        workflow.id, file_names=[file_url], timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )
    step_output = workflow_utils.get_state_outputs(workflow.id, execution.execution_id)[
        "scoped_step"
    ]

    scope = extract_marked_json(step_output, SCOPE_MARKER)
    assert_that(scope["jira"], has_entries(status=200))
    assert_that(scope["confluence"]["error"], has_entries(code=CODE_TOOL_UNAVAILABLE))
