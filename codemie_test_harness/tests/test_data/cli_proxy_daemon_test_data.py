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

"""Test data for the CodeMie CLI proxy daemon tests."""

import pytest

CLIENT_CLAUDE_DESKTOP = "claude-desktop"
CLIENT_CODEX_DESKTOP = "codex-desktop"
CLIENT_VSCODE_BYOK = "vscode-byok"
CLIENT_VSCODE_CLAUDE_CODE = "vscode-claude-code"
CLIENT_DAEMON = "codemie-daemon"

INVALID_KEY_BODY = {
    "type": "error",
    "error": {"type": "authentication_error", "message": "Invalid API key"},
}
SIGN_IN_PROMPT_START = "CodeMie SSO session expired."
CONFLICT_TEXT = "A proxy is already running with different settings:"
OLDER_DAEMON_RESTART_TEXT = "Restarting proxy: it was started by an older CodeMie CLI"
MISMATCH_RESTART_TEXT = "Restarting proxy to match"
NEWER_DAEMON_VERSION = "999.0.0"
OLDER_DAEMON_VERSION = "0.0.1"

NON_DESKTOP_CLIENTS = [
    pytest.param(CLIENT_CODEX_DESKTOP, id="codex-desktop"),
    pytest.param(CLIENT_VSCODE_BYOK, id="vscode-byok"),
    pytest.param(CLIENT_DAEMON, id="codemie-daemon"),
]

# Bearer values that name no client: `{key}` is the daemon's gateway key.
REFUSED_KEYS = [
    pytest.param("{key}.unknown-client", id="unknown-name"),
    pytest.param("not-the-gateway-key", id="wrong-key"),
    pytest.param("{key}.Claude-Desktop", id="differently-cased-name"),
]

# Connection record fields an older CLI left, and the label the shared key is then served as.
LEGACY_RECORDS = [
    pytest.param(
        {"clientType": "codex-desktop"},
        CLIENT_CODEX_DESKTOP,
        id="client-type-codex-desktop",
    ),
    pytest.param(
        {"clientType": "vscode-byok"}, CLIENT_VSCODE_BYOK, id="client-type-vscode-byok"
    ),
    pytest.param(
        {"telemetryMode": "claude-desktop"},
        CLIENT_CLAUDE_DESKTOP,
        id="desktop-telemetry-mode",
    ),
    pytest.param({"telemetryMode": "none"}, CLIENT_DAEMON, id="telemetry-mode-none"),
    pytest.param(
        {"clientType": "codemie-claude"},
        CLIENT_DAEMON,
        id="client-type-not-a-model-client",
    ),
]

# (key shape in Desktop's applied config, command that starts the daemon)
DESKTOP_CONNECTIONS = [
    pytest.param("shared", "proxy connect", id="shared-key-connect"),
    pytest.param("named", "proxy start", id="named-key-start"),
    pytest.param("shared", "proxy restart", id="shared-key-restart"),
    pytest.param("named", "hook cold start", id="named-key-hook"),
]

# What `proxy status` prints once Desktop's applied config no longer connects it. Another port: the
# Desktop line. Another key: the daemon refuses the key, so this client notice replaces the Desktop line.
# Config removed: the `Claude Desktop:` row of the client table reads "not connected" with the aggregate
# connect command (its label is padded to a column, so only the label and the text after it are named).
DESKTOP_NOT_COLLECTING_LINE = "Desktop: NOT collecting"
DESKTOP_CLIENT_ROW_LABEL = "Claude Desktop:"
DESKTOP_NOT_CONNECTED_TEXT = "not connected"
DESKTOP_CONNECT_HINT = "codemie proxy connect --claude-otlp"
DESKTOP_REFUSED_KEY_LINE = (
    "Claude Desktop: points at a local gateway with a key this proxy does not accept "
    "\u2014 if it should use CodeMie, run: codemie proxy connect --claude-desktop"
)

REUSE_COMMANDS = [
    pytest.param("proxy connect", id="connect"),
    pytest.param("proxy start", id="start"),
    pytest.param("hook cold start", id="hook"),
]

REPLACING_COMMANDS = [
    pytest.param("hook", id="hook"),
    pytest.param("proxy start", id="start"),
    pytest.param("proxy restart", id="restart"),
    pytest.param("proxy connect", id="connect"),
]

DIFFERING_SETTINGS = [
    pytest.param("profile", id="profile"),
    pytest.param("project", id="project"),
    pytest.param("provider", id="provider"),
    pytest.param("target URL", id="target-url"),
    pytest.param("port", id="port"),
]

# Claude Code hook events a prompt hook adopts an older daemon on.
ADOPTING_HOOK_EVENTS = [
    pytest.param("UserPromptSubmit", id="user-prompt-submit"),
    pytest.param("PostCompact", id="post-compact"),
]

SIMULTANEOUS_STARTS = [
    pytest.param(("hook", "hook"), id="hook-and-hook"),
    pytest.param(("hook", "proxy connect"), id="hook-and-connect"),
]

OLDER_CLI_NOTICES = [
    pytest.param("status", id="older-cli-status"),
    pytest.param("connect", id="older-cli-connect"),
]

START_PATHS = [
    pytest.param("proxy connect", id="connect"),
    pytest.param("proxy start", id="start"),
    pytest.param("proxy restart", id="restart"),
    pytest.param("hook cold start", id="hook"),
    pytest.param("replacement", id="replacement"),
]

PROJECT_KEEPING_EVENTS = [
    pytest.param("hook replacement", id="hook-replacement"),
    pytest.param("crash then hook", id="crash-then-hook"),
]

SIGN_IN_KEYS = [
    pytest.param("shared", id="shared-key"),
    pytest.param("named", id="named-key"),
]
