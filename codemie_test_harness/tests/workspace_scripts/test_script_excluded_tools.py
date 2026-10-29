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

"""Tools a script must never call.

Only tools whose class opts in may be called from a script. Agent Workspace, FileSystem,
File Analysis, Platform tools, the code executor and the other tools below are not opted in,
so a script that names one of them is refused and the tool never runs.

One sandbox run in a workflow tool step tries every tool by name and records the answer of
each; the tests below assert on one tool each. A Jira call in the same run shows the script
could call tools at all, so a refusal is not just a broken channel.

Every excluded tool is refused as `tool_unavailable`; only the script tool itself is
`tool_blocked` (covered by the matrix tests).
"""

import pytest
from hamcrest import assert_that, equal_to
from types import SimpleNamespace

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    CODE_TOOL_UNAVAILABLE,
    CODES_MARKER,
    EXCLUDED_TOOLS,
    JIRA_TOOL,
    render_excluded_tools_probe,
)
from codemie_test_harness.tests.utils.workspace_script_utils import (
    SCRIPT_WORKFLOW_EXECUTION_TIMEOUT,
    extract_marked_json,
    allow_tools,
    parse_script_result,
    tool_state,
)

pytestmark = [
    pytest.mark.workflow,
    pytest.mark.workspace,
    pytest.mark.api,
    pytest.mark.integration,
]


@pytest.fixture(scope="module")
def excluded_tools_run(
    workflow_utils, create_script_workflow, upload_script, jira_user_integration
):
    """Run the probe once for all tools; expose each tool's answer and the Jira control status."""
    script_name, file_url = upload_script(
        render_excluded_tools_probe([name for _, name in EXCLUDED_TOOLS]),
        prefix="excluded",
    )
    tool, state = tool_state(
        "probe",
        AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value,
        {"script_path": script_name},
        tool_access=allow_tools(JIRA_TOOL),
    )
    workflow = create_script_workflow([tool], [state])

    execution = workflow_utils.create_workflow_execution(
        workflow.id, file_names=[file_url], timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )

    step_output = workflow_utils.get_state_outputs(workflow.id, execution.execution_id)[
        "probe"
    ]
    probe = extract_marked_json(
        parse_script_result(step_output)["output"], CODES_MARKER
    )
    return SimpleNamespace(codes=probe["tools"], control_status=probe["control"])


@pytest.mark.jira
@pytest.mark.parametrize(
    "tool_name",
    [pytest.param(name, id=f"{family}-{name}") for family, name in EXCLUDED_TOOLS],
)
def test_excluded_tool_is_refused_for_script(excluded_tools_run, tool_name):
    """The call is refused with `tool_unavailable`: never answered, and not an internal error."""
    assert_that(excluded_tools_run.codes[tool_name], equal_to(CODE_TOOL_UNAVAILABLE))


@pytest.mark.jira
def test_allowed_tool_is_still_callable_in_the_same_run(excluded_tools_run):
    """Control: in the run that was refused everywhere above, a Jira call goes through."""
    assert_that(excluded_tools_run.control_status, equal_to(200))
