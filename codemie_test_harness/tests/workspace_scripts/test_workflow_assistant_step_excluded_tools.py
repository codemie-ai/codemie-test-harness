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

"""Excluded tools stay refused even when the assistant has them configured.

In a workflow tool step a refusal could also mean "the tool cannot be built there". Here the
assistant of a workflow step has Agent Workspace, code executor, File Analysis, Platform and
MCP tools configured, so the model could call them itself; a script run by the same assistant
must still be refused. A Jira tool in the same assistant is the control that scope works.

The assistant is driven by an LLM, so the prompt asks it to run one script and repeat the
script's output; the assertions read the answers the script itself recorded.
"""

from types import SimpleNamespace

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.mcp_server_test_data import (
    TIME_MCP_SERVER_WITH_CONFIG,
)
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    ASSISTANT_CONFIGURED_EXCLUDED_TOOLS,
    CODE_TOOL_UNAVAILABLE,
    CODES_MARKER,
    JIRA_TOOL,
    render_excluded_tools_probe,
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

pytestmark = [
    pytest.mark.workflow,
    pytest.mark.workspace,
    pytest.mark.api,
    pytest.mark.integration,
]

SYSTEM_PROMPT = (
    "You run workspace scripts. When asked to run a script, call execute_workspace_script "
    "exactly once with that script path, then reply with the complete stdout of the script "
    "and nothing else."
)


@pytest.fixture(scope="module")
def configured_assistant_run(
    workflow_utils,
    create_script_workflow,
    upload_script,
    jira_user_integration,
    default_llm,
):
    """Run the probe once from an assistant step whose assistant has the excluded tools configured."""
    tool_names = [name for _, name in ASSISTANT_CONFIGURED_EXCLUDED_TOOLS]
    script_name, file_url = upload_script(
        render_excluded_tools_probe(tool_names), prefix="assistant_excluded"
    )
    assistant = AssistantModel(
        id="configured_assistant",
        model=default_llm.base_name,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            ToolModel(name=AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value),
            ToolModel(name=JIRA_TOOL, integration_alias=jira_user_integration.alias),
            *[
                ToolModel(name=name)
                for family, name in ASSISTANT_CONFIGURED_EXCLUDED_TOOLS
                if family != "mcp"
            ],
        ],
        mcp_servers=[TIME_MCP_SERVER_WITH_CONFIG],
    )
    state = StateModel(
        id="probe_step",
        assistant_id="configured_assistant",
        task=f"Run the workspace script '{script_name}' and reply with its stdout.",
    )
    workflow = create_script_workflow([], [state], assistants=[assistant])

    execution = workflow_utils.create_workflow_execution(
        workflow.id, file_names=[file_url], timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )
    step_output = workflow_utils.get_state_outputs(workflow.id, execution.execution_id)[
        "probe_step"
    ]

    probe = extract_marked_json(step_output, CODES_MARKER)
    return SimpleNamespace(codes=probe["tools"], control_status=probe["control"])


@pytest.mark.jira
@pytest.mark.parametrize(
    "tool_name",
    [
        pytest.param(name, id=f"{family}-{name}")
        for family, name in ASSISTANT_CONFIGURED_EXCLUDED_TOOLS
    ],
)
def test_configured_excluded_tool_is_refused_for_script(
    configured_assistant_run, tool_name
):
    """A tool the assistant has configured, but that is excluded from scripts, is refused with a clear error."""
    assert_that(
        configured_assistant_run.codes[tool_name], equal_to(CODE_TOOL_UNAVAILABLE)
    )


@pytest.mark.jira
def test_assistants_allowed_tool_is_callable_in_the_same_run(configured_assistant_run):
    """Control: the assistant's Jira tool is reachable by the script in the run that refused the rest."""
    assert_that(configured_assistant_run.control_status, equal_to(200))
