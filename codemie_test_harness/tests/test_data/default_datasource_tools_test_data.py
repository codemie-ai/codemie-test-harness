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

"""Names and run-time rows for the datasource default tools (deselection) tests."""

from dataclasses import dataclass
from typing import Callable

from codemie_test_harness.tests.enums.tools import Default
from codemie_test_harness.tests.utils.base_utils import (
    assert_tool_not_triggered,
    assert_tool_triggered,
)

# Tool names a caller may list in disabled_context_tools.
GET_REPOSITORY_FILE_TREE = "get_repository_file_tree"
SEARCH_CODE_REPO = "search_code_repo"
SEARCH_KB = "search_kb"

# Tools the Codebase Tools toolkit lists: the standard pair, the "with filtering" pair
# and the knowledge base search.
CODEBASE_TOOLKIT_TOOL_NAMES = [
    GET_REPOSITORY_FILE_TREE,
    SEARCH_CODE_REPO,
    "get_repository_file_tree_v2",
    "search_code_repo_v2",
    SEARCH_KB,
]

UNKNOWN_TOOL_NAME = "not_a_default_tool"
UNKNOWN_TOOLS_MESSAGE = "Unknown deselected default tools detected"

SYSTEM_PROMPT_RUN_TOOLS = "Run tools on each user prompt"
CODE_PROMPT = "Get repo tree and suggest what programming language repository has?"
KB_PROMPT = (
    "Show KB context. Return all information available in the context. "
    "Query may be 'Show content of the KB'"
)


@dataclass(frozen=True)
class DefaultToolRunRow:
    """One run-time row: a datasource, the deselected list and the tool's expected state."""

    datasource_fixture: str
    context_fixture: str
    disabled_context_tools: list[str]
    tool: Default
    prompt: str
    assert_tool_state: Callable


CODE_TOOL_ROWS = [
    DefaultToolRunRow(
        datasource_fixture="code_datasource",
        context_fixture="code_context",
        disabled_context_tools=[],
        tool=Default.GET_REPOSITORY_FILE_TREE,
        prompt=CODE_PROMPT,
        assert_tool_state=assert_tool_triggered,
    ),
    DefaultToolRunRow(
        datasource_fixture="code_datasource",
        context_fixture="code_context",
        disabled_context_tools=[GET_REPOSITORY_FILE_TREE],
        tool=Default.GET_REPOSITORY_FILE_TREE,
        prompt=CODE_PROMPT,
        assert_tool_state=assert_tool_not_triggered,
    ),
]

KB_TOOL_ROWS = [
    DefaultToolRunRow(
        datasource_fixture="file_datasource",
        context_fixture="kb_context",
        disabled_context_tools=[],
        tool=Default.SEARCH_KB,
        prompt=KB_PROMPT,
        assert_tool_state=assert_tool_triggered,
    ),
    DefaultToolRunRow(
        datasource_fixture="file_datasource",
        context_fixture="kb_context",
        disabled_context_tools=[SEARCH_KB],
        tool=Default.SEARCH_KB,
        prompt=KB_PROMPT,
        assert_tool_state=assert_tool_not_triggered,
    ),
]
