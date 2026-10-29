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

"""The environment-wide switch for tool calling from scripts.

With the switch off, scripts run exactly as before but cannot call tools. The switch is a
global setting of the environment, so the test flips it for its own duration only and
restores the YAML default afterwards; it must never run in parallel with other script tests.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_entries,
    has_key,
    is_not,
)

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    CODE_UNAVAILABLE,
    ECHO_SCRIPT,
    JIRA_TOOL,
    SWITCH_MARKER,
    SWITCH_PROBE_SCRIPT,
    render_script,
)
from codemie_test_harness.tests.utils.workspace_script_utils import (
    SCRIPT_WORKFLOW_EXECUTION_TIMEOUT,
    allow_tools,
    extract_marked_json,
    parse_script_result,
    random_marker,
    tool_state,
)

EXECUTE_SCRIPT = AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_scripts_run_but_cannot_call_tools_when_bridge_is_switched_off(
    script_bridge_disabled,
    workflow_utils,
    create_script_workflow,
    upload_script,
):
    """A script that tries to call a tool sees an error; an ordinary script is unaffected."""
    echo_marker = random_marker()
    probe_name, probe_url = upload_script(SWITCH_PROBE_SCRIPT, prefix="switch_probe")
    echo_name, echo_url = upload_script(
        render_script(ECHO_SCRIPT, echo_marker), prefix="switch_echo"
    )
    probe_tool, probe_state = tool_state(
        "probe",
        EXECUTE_SCRIPT,
        {"script_path": probe_name},
        "echo",
        tool_access=allow_tools(JIRA_TOOL),
    )
    echo_tool, echo_state = tool_state(
        "echo", EXECUTE_SCRIPT, {"script_path": echo_name}
    )
    workflow = create_script_workflow(
        [probe_tool, echo_tool], [probe_state, echo_state]
    )

    execution = workflow_utils.create_workflow_execution(
        workflow.id,
        file_names=[probe_url, echo_url],
        timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT,
    )

    outputs = workflow_utils.get_state_outputs(workflow.id, execution.execution_id)
    probe_outcome = extract_marked_json(
        parse_script_result(outputs["probe"])["output"], SWITCH_MARKER
    )
    assert_that(probe_outcome, is_not(has_key("status")))
    assert_that(
        probe_outcome["error"],
        has_entries(
            code=CODE_UNAVAILABLE, message=contains_string("not available in this run")
        ),
    )
    assert_that(
        parse_script_result(outputs["echo"])["output"],
        equal_to(f"ECHO-{echo_marker}"),
    )
    assert_that(
        parse_script_result(outputs["echo"])["message"], contains_string("success")
    )
