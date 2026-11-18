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
Tests of the CodeMie CLI proxy daemon lifecycle: when a command reuses, replaces or refuses a
running daemon, which settings a replacement keeps, and that two starts leave one daemon.

Each test runs the installed `codemie` CLI in an isolated HOME with a local stub upstream as
the profile's API. No stand is involved.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_entries,
    is_not,
)

from codemie_test_harness.tests.test_data.cli_proxy_daemon_test_data import (
    ADOPTING_HOOK_EVENTS,
    CLIENT_CODEX_DESKTOP,
    CLIENT_CLAUDE_DESKTOP,
    CONFLICT_TEXT,
    DIFFERING_SETTINGS,
    MISMATCH_RESTART_TEXT,
    NEWER_DAEMON_VERSION,
    OLDER_DAEMON_RESTART_TEXT,
    OLDER_DAEMON_VERSION,
    PROJECT_KEEPING_EVENTS,
    REPLACING_COMMANDS,
    REUSE_COMMANDS,
    SIMULTANEOUS_STARTS,
    START_PATHS,
)
from codemie_test_harness.tests.utils.cli_proxy_utils import (
    PROFILE_MODEL,
    PROJECT_NAME,
    STREAM_ANSWER,
    is_alive,
    reported_pid,
    wait_until,
)

MODEL_BODY = {"model": PROFILE_MODEL, "input": []}


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_connecting_a_second_client_does_not_restart_the_daemon_or_cut_a_stream(
    cli_proxy_env_factory,
):
    # @case cli-proxy-one-daemon-serves_TC_004
    env = cli_proxy_env_factory(stream=True)
    env.start_daemon()
    pid_before = env.state()["pid"]
    env.stub.hold_streams()
    in_flight = env.post_in_background(
        "/v1/responses", env.bearer(CLIENT_CODEX_DESKTOP), MODEL_BODY
    )
    env.stub.wait_for_model_requests(1)
    env.make_vscode_user_dir()

    connected = env.cli("proxy", "connect", "--vscode-claude-code")
    env.stub.release_streams()

    assert_that(
        connected.returncode,
        equal_to(0),
        f"connect succeeds: {connected.stdout}{connected.stderr}",
    )
    assert_that(
        connected.stdout,
        is_not(contains_string(MISMATCH_RESTART_TEXT)),
        "no restart message",
    )
    assert_that(
        connected.stdout,
        is_not(contains_string(OLDER_DAEMON_RESTART_TEXT)),
        "no restart message",
    )
    assert_that(env.state()["pid"], equal_to(pid_before), "the daemon was not replaced")
    assert_that(
        in_flight.result().text,
        equal_to(STREAM_ANSWER),
        "the in-flight stream completed",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("command", REUSE_COMMANDS)
def test_daemon_of_same_version_and_profile_is_reused(daemon_env, command):
    # @case cli-proxy-one-daemon-serves_TC_008
    daemon_env.start_daemon()
    before = daemon_env.state()

    result = daemon_env.run_start_command(command)

    assert_that(
        result.returncode,
        equal_to(0),
        f"command succeeds: {result.stdout}{result.stderr}",
    )
    assert_that(daemon_env.state()["pid"], equal_to(before["pid"]), "pid unchanged")
    assert_that(
        daemon_env.state()["startedAt"],
        equal_to(before["startedAt"]),
        "same process start",
    )
    assert_that(
        result.stdout,
        is_not(contains_string(OLDER_DAEMON_RESTART_TEXT)),
        "no replacement line",
    )
    assert_that(
        result.stdout,
        is_not(contains_string(MISMATCH_RESTART_TEXT)),
        "no replacement line",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("command", REPLACING_COMMANDS)
def test_daemon_of_an_older_cli_is_replaced_keeping_project_key_model_and_port(
    daemon_env, command
):
    # @case cli-proxy-one-daemon-serves_TC_009
    older = daemon_env.older_daemon()

    result = daemon_env.run_start_command(command)

    assert_that(
        result.returncode,
        equal_to(0),
        f"command succeeds: {result.stdout}{result.stderr}",
    )
    replaced = daemon_env.state()
    assert_that(
        replaced["pid"], is_not(equal_to(older["pid"])), "the daemon was replaced"
    )
    assert_that(is_alive(older["pid"]), equal_to(False), "the older daemon is gone")
    assert_that(
        replaced["version"],
        equal_to(daemon_env.version()),
        "replacement is of this CLI",
    )
    assert_that(
        replaced,
        has_entries(
            port=older["port"],
            gatewayKey=older["gatewayKey"],
            project=older["project"],
            model=older["model"],
        ),
        "port, key, project and model carried over",
    )
    response = daemon_env.post(
        "/v1/responses", daemon_env.bearer(CLIENT_CODEX_DESKTOP), MODEL_BODY
    )
    assert_that(response.status_code, equal_to(200), "the replacement serves requests")
    forwarded = daemon_env.stub.model_requests()[-1].headers
    assert_that(
        forwarded["x-codemie-project"], equal_to(older["project"]), "project forwarded"
    )
    assert_that(
        forwarded["x-codemie-cli-model"], equal_to(older["model"]), "model forwarded"
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_connect_over_an_older_daemon_replaces_it_with_the_connecting_profile_settings(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_009
    older = daemon_env.older_daemon()
    daemon_env.write_config(project="connecting-project", model="gpt-5.4-2026-03-05")

    result = daemon_env.connect_omp()

    assert_that(
        result.returncode,
        equal_to(0),
        f"connect succeeds: {result.stdout}{result.stderr}",
    )
    assert_that(
        result.stdout,
        contains_string(OLDER_DAEMON_RESTART_TEXT),
        "replacement is announced",
    )
    assert_that(
        daemon_env.state(),
        has_entries(project="connecting-project", model="gpt-5.4-2026-03-05"),
        "settings of the connecting profile",
    )
    assert_that(
        daemon_env.state()["pid"],
        is_not(equal_to(older["pid"])),
        "the daemon was replaced",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("differs", DIFFERING_SETTINGS)
def test_start_refuses_a_daemon_running_with_different_settings(daemon_env, differs):
    # @case cli-proxy-one-daemon-serves_TC_010
    daemon_env.start_daemon()
    before = daemon_env.state()

    result = daemon_env.start_with_differing(differs)

    assert_that(result.returncode, is_not(equal_to(0)), "start fails")
    assert_that(
        result.stdout + result.stderr, contains_string(CONFLICT_TEXT), "conflict text"
    )
    assert_that(
        daemon_env.state()["pid"], equal_to(before["pid"]), "the daemon is untouched"
    )
    assert_that(is_alive(before["pid"]), equal_to(True), "the daemon still runs")


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("event", ADOPTING_HOOK_EVENTS)
def test_prompt_hook_adopts_an_older_daemon_as_it_is(daemon_env, event):
    # @case cli-proxy-one-daemon-serves_TC_010
    older = daemon_env.older_daemon()

    result = daemon_env.cold_start(event=event)

    assert_that(
        result.returncode, equal_to(0), f"hook succeeds: {result.stdout}{result.stderr}"
    )
    assert_that(daemon_env.state()["pid"], equal_to(older["pid"]), "pid unchanged")
    assert_that(
        daemon_env.state()["version"],
        equal_to(OLDER_DAEMON_VERSION),
        "still the older daemon",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("command", REUSE_COMMANDS)
def test_daemon_of_a_newer_cli_is_reused_by_every_command(daemon_env, command):
    # @case cli-proxy-one-daemon-serves_TC_010
    daemon_env.start_daemon()
    newer = daemon_env.write_state(version=NEWER_DAEMON_VERSION)

    result = daemon_env.run_start_command(command)

    assert_that(
        result.returncode,
        equal_to(0),
        f"command succeeds: {result.stdout}{result.stderr}",
    )
    assert_that(daemon_env.state()["pid"], equal_to(newer["pid"]), "pid unchanged")
    assert_that(
        daemon_env.state()["version"],
        equal_to(NEWER_DAEMON_VERSION),
        "still the newer daemon",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("starts", SIMULTANEOUS_STARTS)
def test_two_simultaneous_starts_leave_exactly_one_daemon(daemon_env, starts):
    # @case cli-proxy-one-daemon-serves_TC_011
    first, second = daemon_env.run_concurrently(*starts)

    assert_that(
        first.returncode,
        equal_to(0),
        f"first start succeeds: {first.stdout}{first.stderr}",
    )
    assert_that(
        second.returncode,
        equal_to(0),
        f"second start succeeds: {second.stdout}{second.stderr}",
    )
    state = daemon_env.state()
    assert_that(
        daemon_env.daemon_pids(),
        equal_to([str(state["pid"])]),
        "exactly one daemon process",
    )
    for command, result in zip(starts, (first, second)):
        if command == "hook":
            assert_that(
                reported_pid(result),
                equal_to(state["pid"]),
                "the hook uses that daemon",
            )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("command", REPLACING_COMMANDS)
def test_replaced_daemon_comes_up_on_the_port_the_clients_are_configured_with(
    daemon_env, command
):
    # @case cli-proxy-one-daemon-serves_TC_012
    older = daemon_env.older_daemon()
    clients_port = daemon_env.read_record()["port"]
    assert_that(
        clients_port,
        is_not(equal_to(4001)),
        "the clients are connected on a port other than 4001",
    )

    result = daemon_env.run_start_command(command)

    assert_that(
        result.returncode,
        equal_to(0),
        f"replacement succeeds: {result.stdout}{result.stderr}",
    )
    assert_that(
        daemon_env.state()["pid"],
        is_not(equal_to(older["pid"])),
        "the daemon was replaced",
    )
    assert_that(
        daemon_env.state()["port"],
        equal_to(clients_port),
        "new daemon port equals the clients' port",
    )
    assert_that(
        daemon_env.read_record()["port"],
        equal_to(clients_port),
        "the record still names that port",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_one_connect_with_omp_and_vscode_configures_both_under_one_daemon(daemon_env):
    # @case cli-proxy-one-daemon-serves_TC_016
    daemon_env.make_vscode_user_dir()

    result = daemon_env.cli("proxy", "connect", "--omp", "--vscode")

    assert_that(
        result.returncode,
        equal_to(0),
        f"connect succeeds: {result.stdout}{result.stderr}",
    )
    assert_that(
        result.stdout, contains_string("oh-my-pi extension"), "oh-my-pi reported"
    )
    assert_that(
        result.stdout, contains_string("VS Code configured"), "VS Code reported"
    )
    assert_that(
        result.stdout,
        contains_string(f"{daemon_env.gateway_key}.vscode-byok"),
        "the BYOK named key is printed",
    )
    assert_that(
        daemon_env.daemon_pids(),
        equal_to([str(daemon_env.state()["pid"])]),
        "exactly one daemon",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("start_path", START_PATHS)
def test_every_start_path_forwards_the_same_project_cli_marker_and_model_once(
    daemon_env, start_path
):
    # @case cli-proxy-one-daemon-serves_TC_019
    if start_path == "replacement":
        daemon_env.older_daemon()
        command = "hook"
    else:
        if start_path == "proxy restart":
            daemon_env.start_daemon()
        command = start_path
    result = daemon_env.run_start_command(command)
    assert_that(
        result.returncode,
        equal_to(0),
        f"start succeeds: {result.stdout}{result.stderr}",
    )

    daemon_env.post(
        "/v1/messages",
        daemon_env.bearer(CLIENT_CLAUDE_DESKTOP),
        {"model": "claude-opus-4-5", "messages": []},
    )
    daemon_env.post(
        "/v1/responses", daemon_env.bearer(CLIENT_CODEX_DESKTOP), MODEL_BODY
    )

    forwarded = daemon_env.stub.model_requests()
    assert_that(len(forwarded), equal_to(2), "each request is forwarded exactly once")
    for seen in forwarded:
        assert_that(
            seen.headers["x-codemie-project"], equal_to(PROJECT_NAME), "project"
        )
        assert_that(
            seen.headers["x-codemie-cli"],
            equal_to(f"codemie-cli/{daemon_env.version()}"),
            "CLI marker",
        )
        assert_that(
            seen.headers.get("x-codemie-cli-model"), equal_to(PROFILE_MODEL), "model"
        )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("event", PROJECT_KEEPING_EVENTS)
def test_daemon_replaced_by_a_hook_or_restarted_after_a_crash_keeps_its_project(
    daemon_env, event
):
    # @case cli-proxy-one-daemon-serves_TC_020
    if event == "hook replacement":
        before = daemon_env.older_daemon()
    else:
        before = daemon_env.start_daemon()
        daemon_env.kill_daemon()
    # What the profile resolves to now differs, so a replacement that re-read it would show.
    daemon_env.write_config(project="project-the-profile-names-now")

    result = daemon_env.cold_start()
    assert_that(
        result.returncode, equal_to(0), f"hook succeeds: {result.stdout}{result.stderr}"
    )
    wait_until(
        lambda: daemon_env.state()["pid"] != before["pid"],
        30,
        "a new daemon in the state",
    )
    response = daemon_env.post(
        "/v1/responses", daemon_env.bearer(CLIENT_CODEX_DESKTOP), MODEL_BODY
    )

    assert_that(response.status_code, equal_to(200), "a daemon is serving")
    assert_that(
        daemon_env.state()["project"], equal_to(PROJECT_NAME), "state keeps the project"
    )
    assert_that(
        daemon_env.stub.model_requests()[-1].headers["x-codemie-project"],
        equal_to(PROJECT_NAME),
        "forwarded project is the original one",
    )
