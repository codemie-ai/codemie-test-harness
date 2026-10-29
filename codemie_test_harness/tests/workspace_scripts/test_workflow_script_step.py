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

"""A workflow tool step runs a workspace script given when the run starts.

Every test runs a real script in the sandbox. The scripts come only from the run-start
files, which the platform registers in the run's workspace (no conversation involved).
"""

import pytest
from codemie_sdk.models.workflow_state import WorkflowExecutionStatusEnum
from hamcrest import (
    all_of,
    assert_that,
    contains_string,
    has_entries,
    has_item,
    has_key,
    is_not,
    not_,
)

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    ECHO_SCRIPT,
    FAILING_SCRIPT,
    WRITE_FILE_SCRIPT,
    render_script,
)
from codemie_test_harness.tests.utils.workspace_script_utils import (
    SCRIPT_WORKFLOW_EXECUTION_TIMEOUT,
    parse_script_result,
    random_marker,
    tool_state,
)

EXECUTE_SCRIPT = AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value
SUCCESS_MESSAGE = "Workspace script executed successfully"


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
def test_tool_step_runs_script_given_at_run_start(
    workflow_utils, create_script_workflow, upload_script
):
    """AC1/AC2: the step runs the script; its whole JSON answer reaches the following step."""
    marker = random_marker()
    script_name, file_url = upload_script(render_script(ECHO_SCRIPT, marker))
    run_tool, run_state = tool_state(
        "run_script",
        EXECUTE_SCRIPT,
        {"script_path": script_name},
        next_state="next_step",
        output_key="script_result",
    )
    next_tool, next_state = tool_state(
        "next_step", AgentWorkspaceTool.LIST_WORKSPACE_FILES.value
    )
    workflow = create_script_workflow([run_tool, next_tool], [run_state, next_state])

    execution = workflow_utils.create_workflow_execution(
        workflow.id, file_names=[file_url], timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )
    execution_id = execution.execution_id

    step_output = parse_script_result(
        workflow_utils.get_state_outputs(workflow.id, execution_id)["run_script"]
    )
    assert_that(
        step_output,
        all_of(
            has_entries(message=SUCCESS_MESSAGE, output=f"ECHO-{marker}"),
            has_key("workspace_files"),
        ),
    )
    context_at_next_step = workflow_utils.get_context_store_at_state(
        workflow.id, execution_id, "next_step"
    )
    assert_that(
        str(context_at_next_step["script_result"]), contains_string(f"ECHO-{marker}")
    )


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
def test_files_written_by_script_are_visible_to_later_steps(
    workflow_utils, create_script_workflow, upload_script
):
    """AC3: a file the script creates stays in the run workspace for the next step."""
    marker = random_marker()
    script_name, file_url = upload_script(render_script(WRITE_FILE_SCRIPT, marker))
    run_tool, run_state = tool_state(
        "run_script", EXECUTE_SCRIPT, {"script_path": script_name}, "read_result"
    )
    read_tool, read_state = tool_state(
        "read_result",
        AgentWorkspaceTool.READ_WORKSPACE_FILE.value,
        {"file_path": "result.txt"},
    )
    workflow = create_script_workflow([run_tool, read_tool], [run_state, read_state])

    execution = workflow_utils.create_workflow_execution(
        workflow.id, file_names=[file_url], timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )
    execution_id = execution.execution_id

    outputs = workflow_utils.get_state_outputs(workflow.id, execution_id)
    reported_paths = [
        item["path"]
        for item in parse_script_result(outputs["run_script"])["workspace_files"]
    ]
    assert_that(reported_paths, has_item("result.txt"))
    assert_that(outputs["read_result"], contains_string(f"FILE-{marker}"))


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
def test_step_fails_with_clear_message_when_script_path_is_missing(
    workflow_utils, create_script_workflow, upload_script
):
    """AC4: a script path that is not in the run workspace fails the step and names the path."""
    _, other_file_url = upload_script(render_script(ECHO_SCRIPT, random_marker()))
    missing_path = f"missing_{random_marker()}.py"
    run_tool, run_state = tool_state(
        "run_script", EXECUTE_SCRIPT, {"script_path": missing_path}, "never_reached"
    )
    next_tool, next_state = tool_state(
        "never_reached", AgentWorkspaceTool.LIST_WORKSPACE_FILES.value
    )
    workflow = create_script_workflow([run_tool, next_tool], [run_state, next_state])

    execution_id = workflow_utils.start_run(workflow.id, file_names=[other_file_url])
    failure = workflow_utils.wait_for_state_status(
        workflow.id,
        execution_id,
        "run_script",
        WorkflowExecutionStatusEnum.FAILED,
    )

    assert_that(
        failure, all_of(contains_string(missing_path), contains_string("workspace"))
    )
    assert_that(
        workflow_utils.get_state_outputs(workflow.id, execution_id).keys(),
        is_not(has_item("never_reached")),
    )


@pytest.mark.workflow
@pytest.mark.workspace
@pytest.mark.api
def test_step_fails_with_script_output_when_script_raises(
    workflow_utils, create_script_workflow, upload_script
):
    """AC5: a failing script marks the step failed and the failure carries what the script printed."""
    marker = random_marker()
    script_name, file_url = upload_script(render_script(FAILING_SCRIPT, marker))
    run_tool, run_state = tool_state(
        "run_script", EXECUTE_SCRIPT, {"script_path": script_name}
    )
    workflow = create_script_workflow([run_tool], [run_state])

    execution_id = workflow_utils.start_run(workflow.id, file_names=[file_url])
    failure = workflow_utils.wait_for_state_status(
        workflow.id,
        execution_id,
        "run_script",
        WorkflowExecutionStatusEnum.FAILED,
    )

    assert_that(
        failure,
        all_of(
            contains_string(f"BEFORE-FAIL-{marker}"),
            contains_string(f"BOOM-{marker}"),
            not_(contains_string(SUCCESS_MESSAGE)),
        ),
    )
