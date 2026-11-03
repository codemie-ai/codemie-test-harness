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

"""Test data for the workflow node-panel State Settings visibility tests.

Covers which State Settings fields (Task, Output Schema, the other switches) the
visual editor shows for each node type, and that values stored in fields the panel
hides survive editing another setting and saving.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from codemie_test_harness.tests.enums.tools import AgentWorkspaceTool
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    CustomNodeModel,
    StateModel,
    ToolModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

# State under test in every generated workflow.
NODE_STATE_ID = "node_under_test"
# State ID typed into the panel by the hidden-value preservation tests.
RENAMED_NODE_STATE_ID = "node_under_test_renamed"

_ACTOR_ID = "node_under_test_actor"
# The visual editor recognises a Transform node by this literal custom-node id.
_TRANSFORM_ACTOR_ID = "transform_node"
_ASSISTANT_ID = "node_assistant"
_TOOL_ID = "node_tool"

# Values stored in YAML on nodes whose panel hides them.
SEEDED_TASK = "Seeded task kept for hidden-value check"
SEEDED_OUTPUT_SCHEMA = '{"type": "object"}'

# Required config of the state-processor custom node (its Output Template field).
STATE_PROCESSOR_OUTPUT_TEMPLATE = "Seeded output template"
# Label of that required field as rendered in the Custom node configuration form.
STATE_PROCESSOR_REQUIRED_FIELD_LABEL = "Output Template"


class NodeKind(str, Enum):
    TOOL = "tool"
    SUB_WORKFLOW = "sub-workflow"
    CUSTOM = "custom"
    ASSISTANT = "assistant"
    TRANSFORM = "transform"


class CustomNodeType(str, Enum):
    """Values of ``custom_node_id`` for the custom node types selectable in the editor."""

    GENERATE_DOCUMENTS_TREE = "generate_documents_tree"
    STATE_PROCESSOR = "state_processor_node"
    RESULT_FINALIZER = "result_finalizer_node"
    SUPERVISOR = "supervisor_node"
    SUMMARIZE_CONVERSATION = "summarize_conversation_node"


# Option labels of the "Custom node type" selector.
CUSTOM_NODE_TYPE_LABELS = {
    CustomNodeType.GENERATE_DOCUMENTS_TREE: "Generate Document Tree",
    CustomNodeType.STATE_PROCESSOR: "State Processor",
    CustomNodeType.RESULT_FINALIZER: "Result Finalizer",
    CustomNodeType.SUPERVISOR: "Supervisor",
    CustomNodeType.SUMMARIZE_CONVERSATION: "Summarize Conversation",
}


@dataclass(frozen=True)
class NonCustomNodeVisibilityCase:
    """Expected State Settings of a Tool, Sub-workflow, Assistant or Transform panel."""

    case_id: str
    node_kind: NodeKind
    # Title of the node-specific accordion; proves the panel of the right node type opened.
    section_title: str
    task_visible: bool
    output_schema_visible: bool
    # Interrupt Before, Finish Iteration, Resolve Dynamic Values in Prompt, Result as Human Message.
    other_settings_visible: bool


@dataclass(frozen=True)
class CustomNodeVisibilityCase:
    """Expected State Settings of the Custom panel for one custom node type."""

    case_id: str
    custom_node_type: CustomNodeType
    task_visible: bool

    @property
    def type_label(self) -> str:
        return CUSTOM_NODE_TYPE_LABELS[self.custom_node_type]


@dataclass(frozen=True)
class HiddenValueCase:
    """Node whose stored Task/Output Schema must survive an unrelated edit and save."""

    case_id: str
    node_kind: NodeKind
    custom_node_type: Optional[CustomNodeType]
    # The Custom state-processor panel shows Task; every other value stays hidden.
    task_visible: bool


NON_CUSTOM_NODE_VISIBILITY_CASES = [
    NonCustomNodeVisibilityCase(
        "tool", NodeKind.TOOL, "Tool Configuration", False, False, True
    ),
    NonCustomNodeVisibilityCase(
        "sub-workflow",
        NodeKind.SUB_WORKFLOW,
        "Sub-Workflow Configuration",
        False,
        False,
        True,
    ),
    NonCustomNodeVisibilityCase(
        "assistant", NodeKind.ASSISTANT, "Assistant Configuration", True, True, True
    ),
    NonCustomNodeVisibilityCase(
        "transform", NodeKind.TRANSFORM, "Transform Configuration", False, False, False
    ),
]

CUSTOM_NODE_VISIBILITY_CASES = [
    CustomNodeVisibilityCase("state_processor", CustomNodeType.STATE_PROCESSOR, True),
    CustomNodeVisibilityCase(
        "generate_documents_tree", CustomNodeType.GENERATE_DOCUMENTS_TREE, False
    ),
    CustomNodeVisibilityCase(
        "result_finalizer", CustomNodeType.RESULT_FINALIZER, False
    ),
    CustomNodeVisibilityCase("supervisor", CustomNodeType.SUPERVISOR, False),
    CustomNodeVisibilityCase(
        "summarize_conversation", CustomNodeType.SUMMARIZE_CONVERSATION, False
    ),
]

HIDDEN_VALUE_CASES = [
    HiddenValueCase("tool", NodeKind.TOOL, None, False),
    HiddenValueCase("sub-workflow", NodeKind.SUB_WORKFLOW, None, False),
    HiddenValueCase(
        "custom-state-processor", NodeKind.CUSTOM, CustomNodeType.STATE_PROCESSOR, True
    ),
]


def build_node_workflow_yaml(
    model: str,
    node_kind: NodeKind,
    custom_node_type: Optional[CustomNodeType] = None,
    sub_workflow_id: Optional[str] = None,
    with_hidden_values: bool = False,
    with_required_config: bool = True,
) -> str:
    """Build workflow YAML holding one node of ``node_kind`` in the state ``NODE_STATE_ID``.

    Args:
        model: LLM model name for the Assistant node.
        node_kind: Which kind of node the state is.
        custom_node_type: Required for ``NodeKind.CUSTOM``.
        sub_workflow_id: Required for ``NodeKind.SUB_WORKFLOW``; the workflow to call.
        with_hidden_values: Seed ``SEEDED_TASK`` / ``SEEDED_OUTPUT_SCHEMA`` on the state.
        with_required_config: For the state-processor custom node, seed its required
            Output Template config; ``False`` leaves the node unconfigured.
    """
    state = StateModel(id=NODE_STATE_ID)
    if with_hidden_values:
        state.task = SEEDED_TASK
        state.output_schema = SEEDED_OUTPUT_SCHEMA

    workflow = WorkflowYamlModel(enable_summarization_node=False, states=[state])

    if node_kind == NodeKind.TOOL:
        state.tool_id = _TOOL_ID
        workflow.tools = [
            ToolModel(
                id=_TOOL_ID,
                tool=AgentWorkspaceTool.READ_WORKSPACE_FILE.value,
                tool_args={"file_path": "node-settings.txt"},
            )
        ]
    elif node_kind == NodeKind.SUB_WORKFLOW:
        state.workflow_id = sub_workflow_id
    elif node_kind == NodeKind.ASSISTANT:
        state.assistant_id = _ASSISTANT_ID
        workflow.assistants = [
            AssistantModel(
                id=_ASSISTANT_ID,
                model=model,
                system_prompt="You are helpful assistant",
            )
        ]
    elif node_kind == NodeKind.TRANSFORM:
        state.custom_node_id = _TRANSFORM_ACTOR_ID
        workflow.custom_nodes = [
            CustomNodeModel(
                id=_TRANSFORM_ACTOR_ID,
                custom_node_id=_TRANSFORM_ACTOR_ID,
                config={
                    "input_source": "context_store",
                    "input_key": "input",
                    "mappings": [
                        {
                            "output_field": "static_value",
                            "type": "constant",
                            "value": "static",
                        }
                    ],
                },
            )
        ]
    else:
        state.custom_node_id = _ACTOR_ID
        config = None
        if custom_node_type == CustomNodeType.STATE_PROCESSOR and with_required_config:
            config = {"output_template": STATE_PROCESSOR_OUTPUT_TEMPLATE}
        workflow.custom_nodes = [
            CustomNodeModel(
                id=_ACTOR_ID, custom_node_id=custom_node_type.value, config=config
            )
        ]

    return prepare_yaml_content(workflow.model_dump(exclude_none=True))


def build_simple_assistant_workflow_yaml(model: str) -> str:
    """Minimal one-assistant workflow, used as the target of a Sub-workflow node."""
    workflow = WorkflowYamlModel(
        assistants=[
            AssistantModel(
                id=_ASSISTANT_ID, model=model, system_prompt="You are helpful assistant"
            )
        ],
        states=[StateModel(id=_ASSISTANT_ID, assistant_id=_ASSISTANT_ID)],
    )
    return prepare_yaml_content(workflow.model_dump(exclude_none=True))
