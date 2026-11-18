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
Tests of what `codemie proxy status` and `codemie proxy connect` tell about the clients configured
for the daemon: a client on another port or holding the shared key, an older CLI first on PATH, hooks
of another install, and the move of other clients to their named keys.

Each test runs the installed `codemie` CLI in an isolated HOME that holds the client configs.
"""

import json
import re

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_item,
    is_not,
)

from codemie_test_harness.tests.test_data.cli_proxy_daemon_test_data import (
    CLIENT_CODEX_DESKTOP,
    CLIENT_VSCODE_CLAUDE_CODE,
    OLDER_CLI_NOTICES,
)

OLDER_CLI_WARNING = "Warning: an older CodeMie CLI is first on PATH"


def _status_lines(output: str):
    return [line.strip() for line in output.splitlines()]


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_status_shows_the_daemon_cli_version(daemon_env):
    # @case cli-proxy-one-daemon-serves_TC_013
    daemon_env.start_daemon()

    status = daemon_env.status_output()

    assert_that(
        _status_lines(status),
        has_item(f"Version: {daemon_env.version()}"),
        "the version line shows the daemon's CLI version",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_status_names_the_extension_holding_the_shared_key_with_its_connect_command(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_013
    daemon_env.start_daemon()
    daemon_env.write_vscode_claude_code(daemon_env.state()["port"], daemon_env.bearer())

    status = daemon_env.status_output()

    assert_that(
        _status_lines(status),
        has_item(
            "VS Code Claude Code extension: uses the shared key \u2014 Run: codemie proxy connect --vscode-claude-code"
        ),
        "the extension is named with the command that fixes it",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_status_names_codex_desktop_holding_the_shared_key_with_its_connect_command(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_013
    daemon_env.start_daemon()
    daemon_env.write_codex_config(daemon_env.state()["port"], daemon_env.bearer())

    status = daemon_env.status_output()

    assert_that(
        _status_lines(status),
        has_item(
            "Codex desktop: uses the shared key \u2014 Run: codemie proxy connect --codex-desktop"
        ),
        "Codex desktop is named with the command that fixes it",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_status_names_codex_desktop_on_another_port_with_its_connect_command(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_013
    daemon_env.start_daemon()
    daemon_port = daemon_env.state()["port"]
    daemon_env.write_codex_config(
        daemon_port + 1, daemon_env.bearer(CLIENT_CODEX_DESKTOP)
    )

    status = daemon_env.status_output()

    assert_that(
        _status_lines(status),
        has_item(
            f"Codex desktop: points at port {daemon_port + 1}, the proxy listens on {daemon_port} "
            "\u2014 Run: codemie proxy connect --codex-desktop"
        ),
        "the wrong-port client is named with the command that fixes it",
    )
    assert_that(
        status,
        is_not(contains_string("uses the shared key")),
        "a named key is not flagged",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("command", OLDER_CLI_NOTICES)
def test_older_cli_first_on_path_is_named_by_status_and_connect(daemon_env, command):
    # @case cli-proxy-one-daemon-serves_TC_014
    daemon_env.start_daemon()
    older_bin = daemon_env.make_other_install("older-install", "0.0.1")

    if command == "status":
        result = daemon_env.cli("proxy", "status", path_prepend=older_bin)
    else:
        result = daemon_env.cli("proxy", "connect", "--omp", path_prepend=older_bin)

    assert_that(
        result.stdout,
        contains_string(OLDER_CLI_WARNING),
        "the older-CLI-on-PATH warning",
    )
    assert_that(
        result.stdout,
        contains_string(f"{older_bin}/codemie (0.0.1)"),
        "names the older install and its version",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_no_older_cli_warning_when_the_first_codemie_on_path_is_current(daemon_env):
    # @case cli-proxy-one-daemon-serves_TC_014
    daemon_env.start_daemon()

    status = daemon_env.status_output()

    assert_that(
        status,
        is_not(contains_string(OLDER_CLI_WARNING)),
        "no warning without an older install",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_status_names_connector_hooks_that_run_another_install(daemon_env):
    # @case cli-proxy-one-daemon-serves_TC_014
    daemon_env.start_daemon()
    other_install = daemon_env.make_other_install("other-install", "0.16.0")
    daemon_env.write_copilot_cli_hooks(
        other_install.parent
        / "node_modules"
        / "@codemieai"
        / "code"
        / "bin"
        / "codemie.js"
    )

    status = daemon_env.status_output()

    hooks_lines = [
        line for line in _status_lines(status) if line.startswith("Copilot CLI hooks:")
    ]
    assert_that(
        len(hooks_lines), equal_to(1), f"one hooks line in the status:\n{status}"
    )
    assert_that(
        hooks_lines[0],
        contains_string("run another install ("),
        "names the other install",
    )
    assert_that(
        hooks_lines[0],
        contains_string("Run: codemie proxy connect --copilot-cli-otlp"),
        "names the connect flag that fixes them",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_connect_moves_other_clients_from_the_shared_key_to_their_named_keys(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_025
    daemon_env.start_daemon()
    port = daemon_env.state()["port"]
    daemon_env.write_record(clientType=CLIENT_CODEX_DESKTOP, telemetryMode="none")
    extension_settings = daemon_env.write_vscode_claude_code(port, daemon_env.bearer())
    codex_config = daemon_env.write_codex_config(port, daemon_env.bearer())

    result = daemon_env.connect_omp()

    assert_that(
        result.returncode,
        equal_to(0),
        f"connect succeeds: {result.stdout}{result.stderr}",
    )
    assert_that(
        result.stdout,
        contains_string("VS Code Claude Code extension moved to its own key"),
        "one line for the moved extension",
    )
    assert_that(
        result.stdout,
        contains_string("Codex desktop moved to its own key"),
        "one line for Codex desktop",
    )
    extension_env = {
        entry["name"]: entry["value"]
        for entry in json.loads(extension_settings.read_text())[
            "claudeCode.environmentVariables"
        ]
    }
    assert_that(
        extension_env["ANTHROPIC_AUTH_TOKEN"],
        equal_to(daemon_env.bearer(CLIENT_VSCODE_CLAUDE_CODE)),
        "the extension holds its named key",
    )
    assert_that(
        re.search(r'Authorization = "Bearer ([^"]+)"', codex_config.read_text()).group(
            1
        ),
        equal_to(daemon_env.bearer(CLIENT_CODEX_DESKTOP)),
        "Codex desktop holds its named key",
    )
    record = daemon_env.read_record()
    assert_that("clientType" in record, equal_to(False), "legacy clientType removed")
    assert_that(
        "telemetryMode" in record, equal_to(False), "legacy telemetryMode removed"
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_connect_leaves_a_client_config_at_another_gateway_untouched(daemon_env):
    # @case cli-proxy-one-daemon-serves_TC_025
    daemon_env.start_daemon()
    port = daemon_env.state()["port"]
    other_gateway_key = "key-of-another-gateway"
    codex_config = daemon_env.write_codex_config(port + 1, other_gateway_key)
    before = codex_config.read_text()

    result = daemon_env.connect_omp()

    assert_that(
        result.returncode,
        equal_to(0),
        f"connect succeeds: {result.stdout}{result.stderr}",
    )
    assert_that(
        codex_config.read_text(),
        equal_to(before),
        "the config at another gateway is unchanged",
    )
