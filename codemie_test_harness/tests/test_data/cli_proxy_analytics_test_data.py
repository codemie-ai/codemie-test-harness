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

"""Test data for the CodeMie CLI analytics flag tests (`--claude-otlp` and `--copilot-otlp`)."""

from dataclasses import dataclass
from typing import Tuple

import pytest

from codemie_test_harness.tests.utils.cli_proxy_utils import (
    CLAUDE_CODE,
    CLAUDE_DESKTOP,
    COPILOT_CHAT,
    COPILOT_CLI,
    OTHER_PROFILE_NAME,
    VSCODE,
    VSCODE_CLAUDE_CODE,
    VSCODE_INSIDERS,
    desktop_app_can_be_absent,
)

CLAUDE_FLAG = "--claude-otlp"
COPILOT_FLAG = "--copilot-otlp"
CLAUDE_MEMBER_FLAGS = ("--claude-desktop", "--vscode-claude-code", "--claude-code-otlp")
COPILOT_MEMBER_FLAGS = ("--copilot-chat-otlp", "--copilot-cli-otlp")
CLAUDE_CLIENTS = (CLAUDE_CODE, VSCODE_CLAUDE_CODE, CLAUDE_DESKTOP)
COPILOT_CLIENTS = (COPILOT_CHAT, COPILOT_CLI)

CLAUDE_CODE_SUCCESS_LINE = "✓ Claude Code Analytics configured successfully"
COPILOT_CHAT_SUCCESS_LINE = "✓ Copilot Chat analytics configured (hooks-only, no OTel)"
COPILOT_CLI_SUCCESS_LINE = "✓ Copilot CLI analytics configured (hooks-only, no OTel)"
EXTENSION_SUCCESS_LINE = "✓ VS Code Claude Code extension configured"
NO_TERMINAL_LINE = "Claude Code analytics requires confirmation, but no interactive terminal is available."
NO_TERMINAL_REMEDY = "Re-run with --silent to apply it without a prompt: codemie proxy connect --claude-otlp --silent"
NOTHING_TO_DISCONNECT_LINE = "Nothing to disconnect. See: codemie proxy status"
OLDER_CLI_VERSION_LINE = "Version: older CLI — Run: codemie proxy restart"
DESKTOP_OTHER_GATEWAY_VALUE = (
    "points at a local gateway with a key this proxy does not accept "
    "— if it should use CodeMie, run: codemie proxy connect --claude-otlp"
)
UNKNOWN_GATEWAY_KEY = "a-key-this-proxy-does-not-accept"

DESKTOP_NOT_ABSENT = pytest.mark.skipif(
    not desktop_app_can_be_absent(),
    reason="needs macOS without /Applications/Claude.app: Claude Desktop is looked up only on macOS, and it counts as found everywhere else or when the app is installed",
)


def _nothing_found_line(flag: str) -> str:
    return (
        f"Nothing was connected: no client of {flag} was found on this machine. "
        "See: codemie proxy status"
    )


@dataclass(frozen=True)
class SkippedMemberRow:
    """A connect where one member's application is absent: the others are configured, the absent one is not named."""

    command: Tuple[str, ...]
    installed: Tuple[str, ...]
    configured: Tuple[str, ...]
    absent_label: str


SKIPPED_MEMBERS = [
    pytest.param(
        SkippedMemberRow(
            (CLAUDE_FLAG, "--silent"),
            (CLAUDE_CODE, VSCODE),
            (CLAUDE_CODE, VSCODE_CLAUDE_CODE),
            "Claude Desktop",
        ),
        marks=DESKTOP_NOT_ABSENT,
        id="claude-desktop-not-installed",
    ),
    pytest.param(
        SkippedMemberRow(
            (CLAUDE_FLAG, "--silent"),
            (CLAUDE_CODE, CLAUDE_DESKTOP),
            (CLAUDE_CODE, CLAUDE_DESKTOP),
            "VS Code Claude Code extension",
        ),
        id="vscode-not-installed",
    ),
    pytest.param(
        SkippedMemberRow(
            (COPILOT_FLAG,),
            (VSCODE,),
            (COPILOT_CHAT,),
            "Copilot CLI",
        ),
        id="copilot-cli-not-installed",
    ),
    pytest.param(
        SkippedMemberRow(
            (COPILOT_FLAG,),
            (COPILOT_CLI,),
            (COPILOT_CLI,),
            "Copilot Chat",
        ),
        id="copilot-chat-vscode-not-installed",
    ),
]

# (aggregate flag, the vendor's clients installed on no machine): no member found
NOTHING_FOUND = [
    pytest.param(COPILOT_FLAG, _nothing_found_line(COPILOT_FLAG), id="copilot-otlp"),
    pytest.param(
        CLAUDE_FLAG,
        _nothing_found_line(CLAUDE_FLAG),
        marks=DESKTOP_NOT_ABSENT,
        id="claude-otlp",
    ),
]


@dataclass(frozen=True)
class FailingMemberRow:
    """A connect where one found member fails: its failure lines, exit code 1, and the members that stay configured."""

    command: Tuple[str, ...]
    installed: Tuple[str, ...]
    arrange: Tuple[str, ...]
    failure_texts: Tuple[str, ...]
    configured: Tuple[str, ...]


FAILING_MEMBERS = [
    pytest.param(
        FailingMemberRow(
            (CLAUDE_FLAG, "--silent"),
            (CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP),
            ("claude conflict",),
            (
                "✗ Claude Code Analytics — Claude Code settings already contain "
                "conflicting env values for: OTEL_EXPORTER_OTLP_PROTOCOL. Re-run with --force to overwrite.",
            ),
            (VSCODE_CLAUDE_CODE, CLAUDE_DESKTOP),
        ),
        id="claude-code-conflicting-settings",
    ),
    pytest.param(
        FailingMemberRow(
            (CLAUDE_FLAG, "--silent"),
            (CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP),
            ("desktop without url",),
            (
                "✗ Claude Desktop — Selected profile is missing CodeMie URL. "
                "Run: codemie setup or codemie profile login",
            ),
            (CLAUDE_CODE, VSCODE_CLAUDE_CODE),
        ),
        id="claude-desktop-profile-without-url",
    ),
    pytest.param(
        FailingMemberRow(
            (COPILOT_FLAG,),
            (VSCODE, COPILOT_CLI),
            ("copilot chat settings",),
            (
                "Could not configure Copilot Chat analytics: VS Code settings at",
                "✗ Copilot Chat Analytics — VS Code settings at",
                "could not be read",
            ),
            (COPILOT_CLI,),
        ),
        id="copilot-chat-unreadable-settings",
    ),
]


# (member flag, the client it configures, the application it needs when it is installed)
MEMBER_FLAGS_ALONE = [
    pytest.param(
        "--claude-desktop", CLAUDE_DESKTOP, CLAUDE_DESKTOP, id="claude-desktop"
    ),
    pytest.param(
        "--vscode-claude-code", VSCODE_CLAUDE_CODE, VSCODE, id="vscode-claude-code"
    ),
    pytest.param("--claude-code-otlp", CLAUDE_CODE, CLAUDE_CODE, id="claude-code-otlp"),
    pytest.param("--copilot-chat-otlp", COPILOT_CHAT, VSCODE, id="copilot-chat-otlp"),
    pytest.param("--copilot-cli-otlp", COPILOT_CLI, COPILOT_CLI, id="copilot-cli-otlp"),
]

# Member flags that configure their client with its application absent, as before the aggregates.
MEMBER_FLAGS_WITHOUT_APPLICATION = [
    pytest.param(
        "--claude-desktop",
        CLAUDE_DESKTOP,
        marks=DESKTOP_NOT_ABSENT,
        id="claude-desktop",
    ),
    pytest.param("--claude-code-otlp", CLAUDE_CODE, id="claude-code-otlp"),
    pytest.param("--copilot-chat-otlp", COPILOT_CHAT, id="copilot-chat-otlp"),
    pytest.param("--copilot-cli-otlp", COPILOT_CLI, id="copilot-cli-otlp"),
]

EXTENSION_DIRECTORY_MISSING_TEXT = "VS Code user data directory was not found"


@dataclass(frozen=True)
class OptionRow:
    """An option given to the aggregate and to the member flags: both must leave the same machine."""

    aggregate_command: Tuple[str, ...]
    member_command: Tuple[str, ...]
    installed: Tuple[str, ...]
    arrange: Tuple[str, ...]
    configured: Tuple[str, ...]
    profile: str


_ALL_CLAUDE = (CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP)

OPTIONS_REACHING_MEMBERS = [
    pytest.param(
        OptionRow(
            (CLAUDE_FLAG, "--scope", "project", "--silent"),
            (*CLAUDE_MEMBER_FLAGS, "--scope", "project", "--silent"),
            _ALL_CLAUDE,
            (),
            CLAUDE_CLIENTS,
            "daemon-autotest",
        ),
        id="scope-project-claude",
    ),
    pytest.param(
        OptionRow(
            (COPILOT_FLAG, "--scope", "project"),
            (*COPILOT_MEMBER_FLAGS, "--scope", "project"),
            (VSCODE, COPILOT_CLI),
            (),
            COPILOT_CLIENTS,
            "daemon-autotest",
        ),
        id="scope-project-copilot",
    ),
    pytest.param(
        OptionRow(
            (CLAUDE_FLAG, "--silent"),
            (*CLAUDE_MEMBER_FLAGS, "--silent"),
            _ALL_CLAUDE,
            (),
            CLAUDE_CLIENTS,
            "daemon-autotest",
        ),
        id="silent",
    ),
    pytest.param(
        OptionRow(
            (CLAUDE_FLAG, "--force", "--silent"),
            (*CLAUDE_MEMBER_FLAGS, "--force", "--silent"),
            _ALL_CLAUDE,
            ("claude conflict",),
            CLAUDE_CLIENTS,
            "daemon-autotest",
        ),
        id="force-over-conflicting-settings",
    ),
    pytest.param(
        OptionRow(
            (CLAUDE_FLAG, "--profile", OTHER_PROFILE_NAME, "--silent"),
            (*CLAUDE_MEMBER_FLAGS, "--profile", OTHER_PROFILE_NAME, "--silent"),
            _ALL_CLAUDE,
            ("second profile",),
            CLAUDE_CLIENTS,
            OTHER_PROFILE_NAME,
        ),
        id="profile",
    ),
]

# (aggregate given together with one of its members, the aggregate alone, installed, the member's success line)
AGGREGATE_WITH_MEMBER = [
    pytest.param(
        (CLAUDE_FLAG, "--claude-code-otlp", "--silent"),
        (CLAUDE_FLAG, "--silent"),
        _ALL_CLAUDE,
        CLAUDE_CODE_SUCCESS_LINE,
        id="claude-otlp-with-claude-code-otlp",
    ),
    pytest.param(
        (COPILOT_FLAG, "--copilot-cli-otlp"),
        (COPILOT_FLAG,),
        (VSCODE, COPILOT_CLI),
        COPILOT_CLI_SUCCESS_LINE,
        id="copilot-otlp-with-copilot-cli-otlp",
    ),
]

# (installed with Claude Code found, installed with only VS Code found): the Claude aggregate is refused
REFUSED_WITHOUT_TERMINAL = [
    pytest.param((CLAUDE_CODE,), id="claude-binary-found"),
    pytest.param((VSCODE,), id="only-vscode-found"),
]


@dataclass(frozen=True)
class DisconnectRow:
    """A disconnect aggregate run after the machine changed: what it removes, what it names, what stays."""

    connect: Tuple[str, ...]
    disconnect: Tuple[str, ...]
    installed: Tuple[str, ...]
    changes: Tuple[str, ...]
    named: Tuple[str, ...]
    not_named: Tuple[str, ...]


_CLAUDE_CONNECT = (CLAUDE_FLAG,)
_INSIDERS_CONNECT = (CLAUDE_FLAG, "--insiders")
_CLAUDE_CODE_LINE = "✓ Claude Code OTLP disconnected"
_DESKTOP_LINE = "✓ Claude Desktop disconnected"
_EXTENSION_LINE = "✓ VS Code Claude Code disconnected"
_CHAT_LINE = "✓ Copilot Chat OTLP disconnected"
_CLI_LINE = "✓ Copilot CLI OTLP disconnected"

DISCONNECT_ROWS = [
    pytest.param(
        DisconnectRow(
            _CLAUDE_CONNECT,
            (CLAUDE_FLAG,),
            _ALL_CLAUDE,
            (),
            (_DESKTOP_LINE, _EXTENSION_LINE, _CLAUDE_CODE_LINE),
            (),
        ),
        id="claude-everything-connected",
    ),
    pytest.param(
        DisconnectRow(
            _INSIDERS_CONNECT,
            (CLAUDE_FLAG, "--insiders"),
            (CLAUDE_CODE, VSCODE_INSIDERS, CLAUDE_DESKTOP),
            (),
            (_DESKTOP_LINE, _EXTENSION_LINE, _CLAUDE_CODE_LINE),
            (),
        ),
        id="claude-insiders-with-insiders-flag",
    ),
    pytest.param(
        DisconnectRow(
            _CLAUDE_CONNECT,
            (CLAUDE_FLAG,),
            _ALL_CLAUDE,
            ("remove vscode",),
            (_DESKTOP_LINE, _CLAUDE_CODE_LINE),
            ("VS Code Claude Code",),
        ),
        id="claude-vscode-gone-extension-skipped",
    ),
    pytest.param(
        DisconnectRow(
            _CLAUDE_CONNECT,
            (CLAUDE_FLAG,),
            _ALL_CLAUDE,
            ("remove vscode", "remove claude binary"),
            (_DESKTOP_LINE, _CLAUDE_CODE_LINE),
            ("VS Code Claude Code",),
        ),
        id="claude-code-not-found-but-hooks-kept",
    ),
    pytest.param(
        DisconnectRow(
            _CLAUDE_CONNECT,
            (CLAUDE_FLAG,),
            _ALL_CLAUDE,
            ("remove vscode", "remove claude binary", "remove claude hooks"),
            (_DESKTOP_LINE,),
            ("VS Code Claude Code", "Claude Code OTLP"),
        ),
        id="claude-code-not-found-and-not-connected-skipped",
    ),
    pytest.param(
        DisconnectRow(
            _CLAUDE_CONNECT,
            (CLAUDE_FLAG,),
            _ALL_CLAUDE,
            ("remove desktop app",),
            (_DESKTOP_LINE, _EXTENSION_LINE, _CLAUDE_CODE_LINE),
            (),
        ),
        marks=DESKTOP_NOT_ABSENT,
        id="desktop-not-found-but-gateway-kept",
    ),
    pytest.param(
        DisconnectRow(
            _CLAUDE_CONNECT,
            (CLAUDE_FLAG,),
            _ALL_CLAUDE,
            ("remove desktop app", "remove desktop gateway"),
            (_EXTENSION_LINE, _CLAUDE_CODE_LINE),
            ("Claude Desktop",),
        ),
        marks=DESKTOP_NOT_ABSENT,
        id="desktop-not-found-and-not-connected-skipped",
    ),
    pytest.param(
        DisconnectRow(
            (COPILOT_FLAG,),
            (COPILOT_FLAG,),
            (VSCODE, COPILOT_CLI),
            (),
            (_CHAT_LINE, _CLI_LINE),
            (),
        ),
        id="copilot-everything-connected",
    ),
    pytest.param(
        DisconnectRow(
            (COPILOT_FLAG,),
            (COPILOT_FLAG,),
            (VSCODE, COPILOT_CLI),
            ("disconnect copilot cli", "remove copilot binary"),
            (_CHAT_LINE,),
            ("Copilot CLI OTLP",),
        ),
        id="copilot-cli-not-found-and-not-connected-skipped",
    ),
    pytest.param(
        DisconnectRow(
            (COPILOT_FLAG,),
            (COPILOT_FLAG,),
            (VSCODE, COPILOT_CLI),
            (
                "disconnect copilot cli",
                "disconnect copilot chat",
                "remove vscode",
                "remove copilot binary",
            ),
            (NOTHING_TO_DISCONNECT_LINE,),
            ("Copilot Chat OTLP", "Copilot CLI OTLP"),
        ),
        id="copilot-nothing-found-nothing-connected",
    ),
]

# (connect flags, aggregate disconnect, the member flags it stands for, installed)
DISCONNECT_AGGREGATE_VS_MEMBERS = [
    pytest.param(
        _CLAUDE_CONNECT,
        (CLAUDE_FLAG,),
        CLAUDE_MEMBER_FLAGS,
        _ALL_CLAUDE,
        id="claude-otlp",
    ),
    pytest.param(
        (COPILOT_FLAG,),
        (COPILOT_FLAG,),
        COPILOT_MEMBER_FLAGS,
        (VSCODE, COPILOT_CLI),
        id="copilot-otlp",
    ),
]


@dataclass(frozen=True)
class StatusRow:
    """A machine and what the five analytics rows of `proxy status` read on it: text values and JSON."""

    installed: Tuple[str, ...]
    connect: Tuple[str, ...]
    values: Tuple[str, ...]
    found: Tuple[bool, ...]
    connected: Tuple[bool, ...]
    flags: Tuple[str, ...]


_CONNECTED = "connected"
_RUN_CLAUDE = f"not connected — Run: codemie proxy connect {CLAUDE_FLAG}"
_RUN_COPILOT = f"not connected — Run: codemie proxy connect {COPILOT_FLAG}"
_ALL_INSTALLED = (CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP, COPILOT_CLI)


def _not_found(flag: str) -> str:
    return f"not found — if it is installed, run: codemie proxy connect {flag}"


STATUS_ROWS = [
    pytest.param(
        StatusRow(
            _ALL_INSTALLED,
            (CLAUDE_FLAG, COPILOT_FLAG),
            (_CONNECTED,) * 5,
            (True,) * 5,
            (True,) * 5,
            (CLAUDE_FLAG,) * 3 + (COPILOT_FLAG,) * 2,
        ),
        id="all-connected",
    ),
    pytest.param(
        StatusRow(
            _ALL_INSTALLED,
            (),
            (_RUN_CLAUDE,) * 3 + (_RUN_COPILOT,) * 2,
            (True,) * 5,
            (False,) * 5,
            (CLAUDE_FLAG,) * 3 + (COPILOT_FLAG,) * 2,
        ),
        id="all-found-none-connected",
    ),
    pytest.param(
        StatusRow(
            (CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP),
            ("--claude-code-otlp",),
            (
                _CONNECTED,
                _RUN_CLAUDE,
                _RUN_CLAUDE,
                _RUN_COPILOT,
                _not_found("--copilot-cli-otlp"),
            ),
            (True, True, True, True, False),
            (True, False, False, False, False),
            (CLAUDE_FLAG,) * 3 + (COPILOT_FLAG, "--copilot-cli-otlp"),
        ),
        id="claude-code-connected-by-its-own-flag",
    ),
    pytest.param(
        StatusRow(
            (),
            (),
            (
                _not_found("--claude-code-otlp"),
                _not_found("--vscode-claude-code"),
                _not_found("--claude-desktop"),
                _not_found("--copilot-chat-otlp"),
                _not_found("--copilot-cli-otlp"),
            ),
            (False,) * 5,
            (False,) * 5,
            (
                "--claude-code-otlp",
                "--vscode-claude-code",
                "--claude-desktop",
                "--copilot-chat-otlp",
                "--copilot-cli-otlp",
            ),
        ),
        marks=DESKTOP_NOT_ABSENT,
        id="nothing-installed",
    ),
]

# Each client's row label, the connect command of a daemon with every client found and none connected.
ROW_CLIENTS = [
    pytest.param(CLAUDE_CODE, id="claude-code"),
    pytest.param(VSCODE_CLAUDE_CODE, id="vscode-claude-code-extension"),
    pytest.param(CLAUDE_DESKTOP, id="claude-desktop"),
    pytest.param(COPILOT_CHAT, id="copilot-chat"),
    pytest.param(COPILOT_CLI, id="copilot-cli"),
]

# (CODEMIE_COPILOT_BIN kind, clients configured): VS Code is installed, no `copilot` is on PATH.
COPILOT_BIN_PATHS = [
    pytest.param(
        "existing absolute",
        (COPILOT_CHAT, COPILOT_CLI),
        id="existing-absolute-path",
    ),
    pytest.param(
        "existing relative",
        (COPILOT_CHAT, COPILOT_CLI),
        id="existing-relative-path",
    ),
    pytest.param("missing absolute", (COPILOT_CHAT,), id="missing-absolute-path"),
    pytest.param("missing relative", (COPILOT_CHAT,), id="missing-relative-path"),
]

HELP_DESCRIPTIONS = [
    pytest.param(
        "--claude-otlp",
        "Analytics for every Claude client found on this machine — Claude Code, the VS Code Claude Code "
        "extension, Claude Desktop (same as --claude-desktop --vscode-claude-code --claude-code-otlp); routes "
        "Claude Desktop and the extension through the CodeMie proxy, and codemie proxy disconnect --claude-otlp "
        "removes that route",
        id="claude-otlp",
    ),
    pytest.param(
        "--copilot-otlp",
        "Analytics for every Copilot client found on this machine — Copilot Chat, Copilot CLI "
        "(same as --copilot-chat-otlp --copilot-cli-otlp)",
        id="copilot-otlp",
    ),
]

BARE_CONNECT_EXAMPLES = [
    pytest.param("codemie proxy connect --claude-otlp", id="claude-otlp"),
    pytest.param("codemie proxy connect --copilot-otlp", id="copilot-otlp"),
]

BARE_CONNECT_LINES = [
    pytest.param(
        "--claude-otlp Analytics for every Claude client found (Claude Code, VS Code extension, Claude Desktop) "
        "Routes Claude Desktop and the extension through the CodeMie proxy; its disconnect removes that route",
        id="claude-otlp",
    ),
    pytest.param(
        "--copilot-otlp Analytics for every Copilot client found (Copilot Chat, Copilot CLI)",
        id="copilot-otlp",
    ),
    pytest.param("Select at least one target to configure:", id="target-list-header"),
]

README_SENTENCES = [
    pytest.param(
        "`--claude-otlp` and `--copilot-otlp` turn CodeMie analytics on for every client of a vendor found on the machine.",
        id="both-flags",
    ),
    pytest.param(
        "`--claude-otlp` covers Claude Code, the VS Code Claude Code extension and Claude Desktop",
        id="claude-members",
    ),
    pytest.param(
        "so it also routes Claude Desktop and the extension through the CodeMie proxy, and "
        "`codemie proxy disconnect --claude-otlp` removes that route together with the analytics",
        id="claude-routing-and-disconnect",
    ),
    pytest.param(
        "`--copilot-otlp` covers Copilot Chat and Copilot CLI",
        id="copilot-members",
    ),
]

CHANGELOG_STATUS_BULLET = "block of the five analytics clients"
CHANGELOG_BULLET_START = (
    "- `codemie proxy connect --claude-otlp` turns analytics on for every Claude client"
)
CHANGELOG_BULLET_PARTS = [
    pytest.param(
        "(Claude Code, the VS Code Claude Code extension, Claude Desktop)",
        id="claude-members",
    ),
    pytest.param(
        "routes Claude Desktop and the extension through the CodeMie proxy",
        id="claude-routing",
    ),
    pytest.param(
        "`--copilot-otlp` does the same for Copilot Chat and Copilot CLI",
        id="copilot-flag",
    ),
    pytest.param("`--claude-otlp` removes that route", id="disconnect-removes-route"),
]
