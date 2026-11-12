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

"""Test data for the long plain-text tool output preview (hidden-lines toggle)."""

from dataclasses import dataclass

# The chat collapses a tool result to its first and last PREVIEW_EDGE_LINES lines once
# it has MINIMUM_PREVIEW_LINES non-empty lines (TextBlock.tsx: PREVIEW_EDGE_LINES = 20,
# MINIMUM_PREVIEW_LINES = 60).
PREVIEW_EDGE_LINES = 20
MINIMUM_PREVIEW_LINES = 60

# VERIFY: the tool card title for code_executor was not observed in the chat; the
# pattern is matched as a substring against the tool block text.
CODE_EXECUTOR_TOOL_LABEL = "Code Execute"

CODE_EXECUTOR_SYSTEM_PROMPT = (
    "You are a test assistant with the code_executor tool. For every user request "
    "call code_executor exactly once, passing exactly the Python code the user gives, "
    "unchanged. Do not answer before the tool has run. After the tool returns, reply "
    "with the single word Done and do not repeat the tool output."
)


@dataclass(frozen=True)
class NumberedLinesPrompt:
    """A prompt that makes code_executor print ``line_count`` numbered lines."""

    line_count: int
    content: str


def numbered_lines_prompt(line_count: int) -> NumberedLinesPrompt:
    """Prompt asking the assistant to run exactly the one-line numbered-output script."""
    code = f'print("\\n".join(f"line {{i}}" for i in range(1, {line_count}+1)))'
    return NumberedLinesPrompt(
        line_count=line_count,
        content=(
            "You must call the code_executor tool right now, exactly once, with "
            f"exactly this Python code and nothing else: {code}"
        ),
    )


# 100 lines: above the threshold, 60 lines are hidden between the two edges.
LONG_OUTPUT_PROMPT = numbered_lines_prompt(100)

# 59 lines: one below the threshold, the output is shown in full.
BELOW_THRESHOLD_OUTPUT_PROMPT = numbered_lines_prompt(MINIMUM_PREVIEW_LINES - 1)
