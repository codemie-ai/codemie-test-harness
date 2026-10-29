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

"""Test data for the assistant-level "Hide tool outputs from end users" tests."""

from dataclasses import dataclass
from typing import Tuple

import pytest

from codemie_test_harness.tests.enums.tools import ResearchToolName
from codemie_test_harness.tests.ui.test_data.chat_test_data import (
    get_tool_invoking_message,
)

# Copy rendered by ToolOutputVisibilitySection.tsx (codemie-ui, MR 2039).
HIDE_TOOL_OUTPUTS_SWITCH_LABEL = "Hide tool outputs from end users"

HIDE_TOOL_OUTPUTS_HINT = (
    "When enabled, end users see only the final assistant response. "
    "Tool calls, intermediate outputs, raw payloads, and execution traces stay hidden, "
    "and conversation settings can't turn them back on."
)

HIDE_TOOL_OUTPUTS_ENABLED_NOTE = (
    "This applies to everyone chatting with this assistant, including you. "
    "Turn it off to inspect tool execution while testing."
)

MULTI_TOOL_PROMPT = (
    "You must call several tools right now. "
    "First use the Wikipedia tool to search for 'Python programming language'. "
    "Then use the Google Search tool to search for 'Python programming language'. "
    "Do not answer without calling both tools first."
)


@dataclass(frozen=True)
class ToolScenario:
    """A tool configuration of the assistant plus the prompt that invokes it."""

    tools: Tuple[ResearchToolName, ...]
    prompt: str


# TC_003: one tool call and several tool calls in one answer.
tool_scenarios = [
    pytest.param(
        ToolScenario(
            tools=(ResearchToolName.WIKIPEDIA,),
            prompt=get_tool_invoking_message().content,
        ),
        id="single_tool",
    ),
    pytest.param(
        ToolScenario(
            tools=(ResearchToolName.WIKIPEDIA, ResearchToolName.GOOGLE_SEARCH),
            prompt=MULTI_TOOL_PROMPT,
        ),
        id="multi_tool",
    ),
]
