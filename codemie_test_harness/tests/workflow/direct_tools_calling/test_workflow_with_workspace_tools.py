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

import re

import pytest
from codemie_sdk.models.workflow import WorkflowMode
from hamcrest import assert_that, contains_string, is_not, matches_regexp

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.yaml_utils import (
    StateModel,
    ToolModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

SIMPLE_DECK_PRESENTATION_SCRIPT = """\
from simple_deck import EPAMPresentation


def generate_part1(prs: EPAMPresentation):
    area = prs.add_slide_default_light(
        title="Project risks & mitigations",
        upsubtitle="RISK MANAGEMENT",
        subtitle="Top risks tracked this month",
    )
    prs.add_block_grid(
        parent=area,
        left=0,
        top=0,
        width="100%",
        height=0,
        columns=2,
        gap=0.35,
        block_variant="callout_top",
        title_font_size=16,
        font_size=13,
        blocks=[
            {
                "title": "Schedule slippage",
                "color": "Orange",
                "text": [
                    {"text": "Cause: late dependencies", "is_bullet": True},
                ],
            },
            {
                "title": "Scope creep",
                "color": "Violet",
                "text": [
                    {"text": "Cause: unclear acceptance criteria", "is_bullet": True},
                ],
            },
        ],
    )


def test_part1():
    prs = EPAMPresentation(output_path="presentation_part1.pptx", jpg_export=True)
    generate_part1(prs)
    prs.save()
    print("Part PPTX created: presentation_part1.pptx")


if __name__ == "__main__":
    test_part1()
"""


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.workspace
@pytest.mark.api
def test_workflow_bare_tool_states_share_workspace_across_states(workflow_utils):
    """Regression: sequential bare (non-assistant-mediated)
    tool states in one workflow execution must share the same AgentWorkspace.

    Before the fix, ToolsService.find_tool_from_config built its
    AssistantChatRequest without a conversation_id, so every bare tool state
    minted a fresh random-UUID workspace -- a state that reads/executes a
    file written by an earlier bare state in the same execution could never
    see it. The fix threads execution_id through as conversation_id
    (codemie tools.py: ToolNode -> ToolsService.find_tool_from_config).

    Two tool nodes, no assistant in between: write_state writes a file,
    read_state (a distinct bare tool state in the same execution) reads it
    back. This only passes if both states resolved to the same workspace.
    """
    file_path = f"workspace-{get_random_name()}.txt"
    file_content = f"hello from the first state {get_random_name()}"

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        tools=[
            ToolModel(
                id="write_tool",
                tool=AgentWorkspaceTool.WRITE_WORKSPACE_FILE.value,
                tool_args={"file_path": file_path, "content": file_content},
            ),
            ToolModel(
                id="read_tool",
                tool=AgentWorkspaceTool.READ_WORKSPACE_FILE.value,
                tool_args={"file_path": file_path},
            ),
        ],
        states=[
            StateModel(
                id="write_state",
                tool_id="write_tool",
                next={"state_id": "read_state"},
            ),
            StateModel(
                id="read_state",
                tool_id="read_tool",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=get_random_name(),
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="read_state",
        user_input="Start",
    )

    # read_workspace_file returns the file record as pretty-printed JSON
    # (ReadWorkspaceFileTool.execute -> _dump_json, indent=2). A full-shape
    # match on read_state's own output proves it resolved the exact file
    # write_state wrote -- only possible if both bare tool states shared one
    # AgentWorkspace, i.e. the execution_id/conversation_id fix took effect.
    assert_that(
        output,
        matches_regexp(
            r"^\{\n"
            rf'  "path": "{re.escape(file_path)}",\n'
            r'  "mime_type": "text/plain",\n'
            r'  "checksum": "[0-9a-f]{64}",\n'
            r'  "size": \d+,\n'
            r'  "version": 1,\n'
            r'  "is_binary": false,\n'
            rf'  "content": "{re.escape(file_content)}"\n'
            r"\}$"
        ),
    )


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.workspace
@pytest.mark.api
def test_workflow_execute_workspace_script_generates_simple_deck_presentation(
    workflow_utils,
):
    """Regression: execute_workspace_script must be able to run a
    simple_deck presentation script. simple_deck's import chain pulls in Python's
    turtle/tkinter modules; before the fix, the sandbox execution image was missing
    the system library libtk8.6.so, so the import failed before the script could
    build/export any slide.

    write_state seeds the workspace with a minimal EPAMPresentation-based script
    (modelled on the ticket's reproduction script); execute_state runs it and
    exports the resulting pptx. This only passes if the sandbox image can import
    simple_deck end to end and produce presentation_part1.pptx.
    """
    script_path = f"workspace-{get_random_name()}.py"
    export_file = "presentation_part1.pptx"

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        tools=[
            ToolModel(
                id="write_tool",
                tool=AgentWorkspaceTool.WRITE_WORKSPACE_FILE.value,
                tool_args={
                    "file_path": script_path,
                    "content": SIMPLE_DECK_PRESENTATION_SCRIPT,
                },
            ),
            ToolModel(
                id="execute_tool",
                tool=AgentWorkspaceTool.EXECUTE_WORKSPACE_SCRIPT.value,
                tool_args={"script_path": script_path, "export_files": [export_file]},
            ),
        ],
        states=[
            StateModel(
                id="write_state",
                tool_id="write_tool",
                next={"state_id": "execute_state"},
            ),
            StateModel(
                id="execute_state",
                tool_id="execute_tool",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=get_random_name(),
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="execute_state",
        user_input="Start",
    )

    assert_that(output, is_not(contains_string("ImportError")))
    assert_that(output, is_not(contains_string("Traceback")))
    assert_that(output, contains_string("Part PPTX created: presentation_part1.pptx"))
    assert_that(output, contains_string(export_file))
