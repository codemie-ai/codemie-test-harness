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

"""A script in a workflow tool step calls platform tools.

One sandbox run executes a script that tries every scenario and prints the outcome of each
as JSON; the tests below assert on the scenarios separately, so one slow run backs all of
them. The tool under test is Jira, reached through the running user's own Jira integration
(automatic lookup in the workflow's project, no integration alias in the step).
"""

import json
from types import SimpleNamespace

import pytest
from hamcrest import (
    all_of,
    assert_that,
    contains_string,
    equal_to,
    has_entries,
    has_item,
    has_length,
    is_not,
)

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    CODE_BAD_ARGUMENTS,
    CODE_TOOL_BLOCKED,
    CODE_TOOL_UNAVAILABLE,
    JIRA_TOOL,
    MATRIX_MARKER,
    MATRIX_SOURCE_PROBE,
    TOOL_CALLING_MATRIX_SCRIPT,
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

pytestmark = [
    pytest.mark.workflow,
    pytest.mark.workspace,
    pytest.mark.api,
    pytest.mark.integration,
]


@pytest.fixture(scope="module")
def matrix_run(
    workflow_utils, create_script_workflow, upload_script, jira_user_integration
):
    """Run the tool-calling matrix script once and expose its results and the follow-up greps."""
    sentinel_hex = random_marker()
    script_name, file_url = upload_script(
        render_script(TOOL_CALLING_MATRIX_SCRIPT, hex_value=sentinel_hex),
        prefix="matrix",
    )
    run_tool, run_state = tool_state(
        "run_script",
        AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value,
        {"script_path": script_name},
        "grep_control",
        tool_access=allow_tools(JIRA_TOOL),
    )
    control_tool, control_state = tool_state(
        "grep_control",
        AgentWorkspaceTool.GREP_WORKSPACE_FILES.value,
        {"query": MATRIX_SOURCE_PROBE},
        "grep_sentinel",
    )
    sentinel_tool, sentinel_state = tool_state(
        "grep_sentinel",
        AgentWorkspaceTool.GREP_WORKSPACE_FILES.value,
        {"query": f"SENT-{sentinel_hex}"},
    )
    workflow = create_script_workflow(
        [run_tool, control_tool, sentinel_tool],
        [run_state, control_state, sentinel_state],
    )

    execution = workflow_utils.create_workflow_execution(
        workflow.id, file_names=[file_url], timeout=SCRIPT_WORKFLOW_EXECUTION_TIMEOUT
    )

    outputs = workflow_utils.get_state_outputs(workflow.id, execution.execution_id)
    script_stdout = parse_script_result(outputs["run_script"])["output"]
    return SimpleNamespace(
        results=extract_marked_json(script_stdout, MATRIX_MARKER),
        script_name=script_name,
        grep_control=outputs["grep_control"],
        grep_sentinel=outputs["grep_sentinel"],
    )


@pytest.mark.jira
def test_script_receives_real_result_of_platform_tool(matrix_run):
    """The call returns the tool's real answer, with the HTTP status as data."""
    assert_that(
        matrix_run.results["me"],
        has_entries(status=200, type="dict", keys=has_item("displayName")),
    )


@pytest.mark.jira
def test_sequential_calls_each_get_their_own_result(matrix_run):
    """Two calls one after another in one run are not mixed up."""
    assert_that(matrix_run.results["me"]["keys"], has_item("displayName"))
    assert_that(matrix_run.results["info"]["keys"], has_item("serverTitle"))
    assert_that(
        matrix_run.results["me"]["keys"],
        is_not(equal_to(matrix_run.results["info"]["keys"])),
    )


@pytest.mark.jira
def test_parallel_calls_return_items_in_order_with_failed_call_as_error_item(
    matrix_run,
):
    """call_tools returns one item per call in the order given; a failure does not hide the others."""
    first, failed, third = matrix_run.results["batch"]

    assert_that(matrix_run.results["batch"], has_length(3))
    assert_that(first, has_entries(status=200, keys=has_item("displayName")))
    assert_that(
        failed["error"], has_entries(code=CODE_TOOL_UNAVAILABLE, retryable=False)
    )
    assert_that(third, has_entries(status=200, keys=has_item("serverTitle")))


@pytest.mark.jira
def test_unknown_tool_gives_clear_error(matrix_run):
    """A tool that does not exist is refused with a clear, non-retryable error."""
    assert_that(
        matrix_run.results["unknown_tool"]["error"],
        all_of(
            has_entries(
                code=CODE_TOOL_UNAVAILABLE, retryable=False, may_have_run=False
            ),
            has_entries(message=contains_string("no_such_tool")),
        ),
    )


@pytest.mark.jira
def test_script_tool_cannot_be_called_from_a_script(matrix_run):
    """A tool that is blocked from script use gives a permanent error that names it."""
    assert_that(
        matrix_run.results["script_tool"]["error"],
        has_entries(
            code=CODE_TOOL_BLOCKED,
            retryable=False,
            message=contains_string("execute_workspace_script"),
        ),
    )


@pytest.mark.jira
def test_misspelled_argument_gives_bad_arguments_error(matrix_run):
    """An argument the tool does not have is reported by name."""
    assert_that(
        matrix_run.results["bad_arguments"]["error"],
        has_entries(code=CODE_BAD_ARGUMENTS, message=contains_string("methodd")),
    )


@pytest.mark.jira
def test_tool_call_data_is_not_persisted_in_workspace(matrix_run):
    """The request a script sends never lands in a workspace file.

    The script sent a runtime-built sentinel in a tool call that really ran (404 as data).
    A search of the workspace finds the script source (positive control) but not the sentinel.
    """
    assert_that(matrix_run.results["sentinel"]["status"], equal_to(404))
    assert_that(matrix_run.grep_control, contains_string(matrix_run.script_name))
    assert_that(json.loads(matrix_run.grep_sentinel), has_length(0))
