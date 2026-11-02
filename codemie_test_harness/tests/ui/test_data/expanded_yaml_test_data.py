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

"""Test data for the expanded YAML configuration dialog UI tests."""

from dataclasses import dataclass

# Title shown in the frame header of the expanded dialog in both contexts.
EXPANDED_YAML_FRAME_TITLE = "yaml"

# Line typed into the expanded editor; it is not valid YAML ("bad indentation of a mapping entry").
INVALID_YAML_LINE = "invalid: yaml: line"

# Key of the line the save/cancel tests extend with a typed suffix.
EDITED_LINE_MARKER = "system_prompt:"

LONG_YAML_NODE_COUNT = 3
LONG_YAML_PROMPT_LINES = 20
LONG_YAML_FIRST_NODE = "node_1"

# A single prompt line far wider than the dialog (max-w-6xl), made of short words so it can wrap.
LONG_PROMPT_LINE = " ".join(
    ["wrap this long prompt line inside the expanded editor"] * 12
)


@dataclass(frozen=True)
class ExpandedYamlContext:
    """Place the expanded YAML dialog is opened from.

    Attributes:
        name: Readable id for ``parametrize``.
        is_editor: True for the workflow editor, False for execution details.
        has_copy_and_download: Whether the frame header carries Copy and Download.
    """

    name: str
    is_editor: bool
    has_copy_and_download: bool


EDITOR_CONTEXT = ExpandedYamlContext(
    name="editor", is_editor=True, has_copy_and_download=False
)
EXECUTION_DETAILS_CONTEXT = ExpandedYamlContext(
    name="execution_details", is_editor=False, has_copy_and_download=True
)
EXPANDED_YAML_CONTEXTS = [EDITOR_CONTEXT, EXECUTION_DETAILS_CONTEXT]


def build_long_workflow_yaml(model: str) -> str:
    """Valid multi-node workflow YAML that does not fit in the expanded dialog.

    A chain of ``LONG_YAML_NODE_COUNT`` nodes. Every assistant has a multi-line
    block prompt (``LONG_YAML_PROMPT_LINES`` lines) and the second one also holds a
    line wider than the dialog. Block scalars are highlighted as Ace string tokens.
    """
    assistants = []
    states = []
    for index in range(1, LONG_YAML_NODE_COUNT + 1):
        node_id = f"node_{index}"
        prompt_lines = [
            f"      Guideline {line} for helper {index}: keep every answer short."
            for line in range(1, LONG_YAML_PROMPT_LINES + 1)
        ]
        if index == 2:
            prompt_lines.append(f"      {LONG_PROMPT_LINE}")
        assistants.append(
            f"  - id: {node_id}\n"
            f"    model: {model}\n"
            f"    system_prompt: |\n" + "\n".join(prompt_lines) + "\n"
        )
        next_state = f"node_{index + 1}" if index < LONG_YAML_NODE_COUNT else "end"
        states.append(
            f"  - id: {node_id}\n"
            f"    next:\n"
            f"      state_id: {next_state}\n"
            f"    assistant_id: {node_id}\n"
        )
    return "assistants:\n" + "".join(assistants) + "\nstates:\n" + "".join(states)
