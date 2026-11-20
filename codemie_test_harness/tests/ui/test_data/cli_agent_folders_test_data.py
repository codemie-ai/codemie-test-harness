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

"""
Test data for the chat sidebar "Folders" section tests of CLI agents.

A CLI agent (Gemini, Codex, ...) syncs its chats with the ``X-CodeMie-Client`` header of
that agent and ``folder`` set to the agent's folder name. The backend maps the header to
a write-once import source, so the sidebar shows the chats in one ``import:<kind>`` entry
instead of a second, empty entry named after the registered folder.
"""

from dataclasses import dataclass
from datetime import datetime

import pytest
from codemie_sdk.models.conversation import HistoryItem


@dataclass(frozen=True)
class CliAgent:
    """A CLI agent as the Folders section shows it."""

    folder: str  # folder name the agent syncs its chats into
    client_header: str  # X-CodeMie-Client value the agent sends
    label: str  # display label of the sidebar entry
    group_key: str  # data-folder key of the sidebar entry


GEMINI = CliAgent("gemini", "codemie-gemini", "Gemini", "import:gemini")
CODEX = CliAgent("codex", "codemie-codex", "Codex", "import:codex")
COPILOT_CLI = CliAgent(
    "copilot-cli", "codemie-copilot", "Copilot CLI", "import:copilot_cli"
)
OPENCODE = CliAgent("opencode", "codemie-opencode", "Opencode", "import:opencode")
PI = CliAgent("pi", "codemie-pi", "Pi", "import:pi")
# The header maps to the claude_cli import source, which takes priority over the legacy
# "Claude Imports" mapping of the folder name "claude".
CLAUDE = CliAgent("claude", "codemie-claude", "Claude CLI", "import:claude_cli")

# Registered empty folders that must not get an entry: every spelling the frontend
# normalizes (trim, lower case, "-" read as "_") to an agent import source.
EMPTY_AGENT_FOLDER_NAMES = [
    pytest.param("gemini", id="gemini"),
    pytest.param("GEMINI", id="gemini-upper-case"),
    pytest.param("codex", id="codex"),
    pytest.param("opencode", id="opencode"),
    pytest.param("pi", id="pi"),
    pytest.param("copilot-cli", id="copilot-hyphen"),
    pytest.param("copilot_cli", id="copilot-underscore"),
    pytest.param("Copilot_CLI", id="copilot-mixed-case"),
]

# Agents whose synced chats are checked together; Gemini has its own test.
SYNCED_AGENTS = [
    pytest.param(CODEX, id="codex"),
    pytest.param(COPILOT_CLI, id="copilot-cli"),
    pytest.param(OPENCODE, id="opencode"),
    pytest.param(PI, id="pi"),
]

# Folder spellings a synced Copilot CLI chat can arrive with.
COPILOT_FOLDER_NAMES = [
    pytest.param("copilot-cli", id="hyphen"),
    pytest.param("Copilot_CLI", id="mixed-case-underscore"),
]

# Agent-named folders that hold a regular (non-imported) chat.
AGENT_NAMED_CUSTOM_FOLDERS = [
    pytest.param(GEMINI.folder, GEMINI.group_key, id="gemini"),
    pytest.param("Copilot_CLI", COPILOT_CLI.group_key, id="copilot-mixed-case"),
]

# Agents used for the move / Move chat popup checks (one plain name, one that needs
# the hyphen-to-underscore normalization).
MOVE_AGENTS = [
    pytest.param(GEMINI, id="gemini"),
    pytest.param(COPILOT_CLI, id="copilot-cli"),
]


def agent_history(topic: str) -> list[HistoryItem]:
    """A one-exchange history, the minimum a CLI agent syncs."""
    now = datetime.now()
    return [
        HistoryItem(
            role="User",
            message=f"Explain {topic}",
            messageRaw=f"Explain {topic}",
            historyIndex=0,
            date=now,
            fileNames=[],
        ),
        HistoryItem(
            role="Assistant",
            message=f"{topic} explained",
            historyIndex=0,
            date=now,
            fileNames=[],
        ),
    ]
