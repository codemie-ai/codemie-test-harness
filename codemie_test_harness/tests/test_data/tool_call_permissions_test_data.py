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

"""Test data for tool-call confirmation tests."""

import pytest

from codemie_test_harness.tests.enums.tools import ResearchToolName

# Research tools exercised under the ASK_FOR_APPROVAL ("Manual") policy.
# Google and Web Scrapper cover the case where the approval popup was skipped for them.
approval_research_tools = [
    pytest.param(ResearchToolName.WIKIPEDIA, id="wikipedia"),
    pytest.param(ResearchToolName.GOOGLE_SEARCH, id="google_search"),
    pytest.param(ResearchToolName.WEB_SCRAPPER, id="web_scrapper"),
]

# All research tools configured together on one assistant.
multi_tool_research_tools = [
    ResearchToolName.WIKIPEDIA,
    ResearchToolName.GOOGLE_SEARCH,
    ResearchToolName.WEB_SCRAPPER,
]

_TOOL_PROMPTS = {
    ResearchToolName.WIKIPEDIA: (
        "Use the Wikipedia tool to search for 'Python programming language'"
    ),
    ResearchToolName.GOOGLE_SEARCH: (
        "Use the Google Search tool to search for 'Python programming language'"
    ),
    ResearchToolName.WEB_SCRAPPER: (
        "Use the Web Scrapper tool to scrape "
        "https://en.wikipedia.org/wiki/Python_(programming_language)"
    ),
}

APPROVAL_SYSTEM_PROMPT = (
    "You are a helpful research assistant. "
    "When the user's message names a specific tool, ALWAYS call that tool "
    "immediately before answering — even for simple requests. Do not answer "
    "from memory. For a message that names no tool (e.g. a greeting), answer "
    "normally without calling any tool."
)


def get_approval_tool_prompt(tool: ResearchToolName) -> str:
    """User message that reliably triggers a call to ``tool``."""
    return (
        f"You must call the tool right now. {_TOOL_PROMPTS[tool]} "
        "and tell me about it. Do not answer without calling the tool first."
    )
