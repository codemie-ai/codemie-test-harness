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
Tests of how the CodeMie CLI proxy daemon collects Claude Desktop sessions: only while Desktop's
applied config points at this daemon, and Cowork sessions only when the daemon served them.

Each test runs the installed `codemie` CLI in an isolated HOME that holds a faked Desktop applied
config and a synthetic session store, with a local stub upstream. No stand and no real Desktop.
The daemon polls Desktop on its own 10 s clock, so every wait is a bounded poll, not a sleep.
"""

import time
from datetime import datetime

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_item,
    has_length,
    is_,
    is_not,
    none,
    not_,
)

from codemie_test_harness.tests.test_data.cli_proxy_daemon_test_data import (
    CLIENT_CLAUDE_DESKTOP,
    DESKTOP_CLIENT_ROW_LABEL,
    DESKTOP_CONNECT_HINT,
    DESKTOP_NOT_COLLECTING_LINE,
    DESKTOP_NOT_CONNECTED_TEXT,
    DESKTOP_REFUSED_KEY_LINE,
    DESKTOP_CONNECTIONS,
)
from codemie_test_harness.tests.utils.cli_proxy_utils import stays_true, wait_until

# The daemon polls Desktop every 10 s; a change is read at the next poll and a disconnect
# takes the second poll in a row.
POLL_SECONDS = 10
CONNECT_WAIT = 4 * POLL_SECONDS
DISCONNECT_WAIT = 4 * POLL_SECONDS

IDLE_SESSION = ("aaaa0001", "11111111-1111-4111-8111-111111111111")
ACTIVE_SESSION = ("bbbb0002", "22222222-2222-4222-8222-222222222222")
NEW_SESSION = ("cccc0003", "33333333-3333-4333-8333-333333333333")
SERVED_COWORK = "aaaaaaaa-1111-4111-8111-111111111111"
CURSOR_COWORK = "bbbbbbbb-2222-4222-8222-222222222222"
NEVER_SERVED_COWORK = "cccccccc-3333-4333-8333-333333333333"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _desktop_key(env, kind: str) -> str:
    return env.bearer() if kind == "shared" else env.bearer(CLIENT_CLAUDE_DESKTOP)


def _start_daemon_with_desktop_configured(env, command: str):
    """Start the daemon by `command` while Desktop's applied config already points at it."""
    result = env.run_start_command(command)
    assert_that(
        result.returncode,
        equal_to(0),
        f"{command} succeeds: {result.stdout}{result.stderr}",
    )
    return result


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("key_kind, command", DESKTOP_CONNECTIONS)
def test_desktop_is_collected_while_its_applied_config_points_at_the_daemon(
    daemon_env, key_kind, command
):
    # @case cli-proxy-one-daemon-serves_TC_006
    env = daemon_env
    now = _now_ms()
    env.write_desktop_session(
        *IDLE_SESSION, last_activity_ms=now - 3_600_000, created_ms=now - 7_200_000
    )
    env.write_desktop_gateway(env.port, _desktop_key(env, key_kind))

    _start_daemon_with_desktop_configured(env, command)

    state = env.wait_for_state(
        lambda s: s.get("desktopConnectedSince"),
        CONNECT_WAIT,
        "desktopConnectedSince in the daemon state",
    )
    assert_that(
        state["desktopConnectedSince"],
        is_not(none()),
        "the daemon noticed Desktop connected",
    )
    status = env.status_output()
    assert_that(
        status, contains_string("Desktop: collecting"), "proxy status says collecting"
    )
    assert_that(status, is_not(contains_string("NOT collecting")))
    # A session idle since before the connect is not collected; a session active after it is.
    env.write_desktop_session(
        *ACTIVE_SESSION, last_activity_ms=_now_ms(), created_ms=now - 7_200_000
    )
    wait_until(
        lambda: env.is_session_collected(ACTIVE_SESSION[0]),
        CONNECT_WAIT,
        "the active session to be collected",
    )
    assert_that(
        env.is_session_collected(IDLE_SESSION[0]),
        equal_to(False),
        "the idle session is not collected",
    )
    # A session that began before the connect is collected only from the connect moment on: its
    # record starts at desktopConnectedSince, not at its own earlier start.
    connected_since_ms = int(
        datetime.fromisoformat(
            state["desktopConnectedSince"].replace("Z", "+00:00")
        ).timestamp()
        * 1000
    )
    assert_that(
        env.session_record(ACTIVE_SESSION[0])["startTime"],
        equal_to(connected_since_ms),
        "the earlier session starts at the connect moment",
    )


def _connect_desktop_and_collect_a_session(env) -> None:
    env.write_desktop_gateway(env.port, env.bearer())
    env.start_daemon()
    env.wait_for_state(
        lambda s: s.get("desktopConnectedSince"), CONNECT_WAIT, "Desktop collected"
    )
    env.write_desktop_session(
        *ACTIVE_SESSION, last_activity_ms=_now_ms(), created_ms=_now_ms()
    )
    wait_until(
        lambda: env.is_session_collected(ACTIVE_SESSION[0]),
        CONNECT_WAIT,
        "the first session to be collected",
    )


def _assert_collection_stopped(env) -> str:
    """The daemon cleared desktopConnectedSince and ignores a new session; returns `proxy status`."""
    state = env.wait_for_state(
        lambda s: not s.get("desktopConnectedSince"),
        DISCONNECT_WAIT,
        "desktopConnectedSince to clear",
    )
    assert_that(
        state.get("desktopConnectedSince"),
        is_(none()),
        "desktopConnectedSince is cleared",
    )
    status = env.status_output()
    assert_that(
        status, not_(contains_string("Desktop: collecting")), "no longer collecting"
    )
    env.write_desktop_session(
        *NEW_SESSION, last_activity_ms=_now_ms(), created_ms=_now_ms()
    )
    stays_true(
        lambda: not env.is_session_collected(NEW_SESSION[0]),
        POLL_SECONDS + 5,
        "the new session stays undiscovered across a full poll cycle",
    )
    return status


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_collection_stops_and_status_names_the_port_when_desktop_points_at_another_port(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_007
    env = daemon_env
    _connect_desktop_and_collect_a_session(env)

    env.write_desktop_gateway(env.port + 1, env.bearer())

    status = _assert_collection_stopped(env)

    assert_that(
        status,
        contains_string(DESKTOP_NOT_COLLECTING_LINE),
        "proxy status prints the NOT collecting line",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_collection_stops_and_status_names_the_refused_key_when_desktop_holds_another_key(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_007
    env = daemon_env
    _connect_desktop_and_collect_a_session(env)

    env.write_desktop_gateway(env.port, "some-other-gateway-key")

    status = _assert_collection_stopped(env)

    assert_that(
        status,
        contains_string(DESKTOP_REFUSED_KEY_LINE),
        "proxy status prints the refused-key notice",
    )
    assert_that(
        status,
        not_(contains_string(DESKTOP_NOT_COLLECTING_LINE)),
        "no NOT collecting line: the refused key replaces it",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_collection_stops_and_status_says_desktop_is_not_connected_when_the_config_is_removed(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_007
    env = daemon_env
    _connect_desktop_and_collect_a_session(env)

    env.remove_desktop_gateway()

    status = _assert_collection_stopped(env)

    desktop_rows = [
        line for line in status.splitlines() if DESKTOP_CLIENT_ROW_LABEL in line
    ]
    assert_that(desktop_rows, has_length(1), "proxy status has one Claude Desktop row")
    assert_that(
        desktop_rows[0],
        contains_string(DESKTOP_NOT_CONNECTED_TEXT),
        "the row says Desktop is not connected",
    )
    assert_that(
        desktop_rows[0],
        contains_string(DESKTOP_CONNECT_HINT),
        "the row names the command that connects it",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_cowork_sessions_are_collected_only_when_served_or_already_collected(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_021
    env = daemon_env
    now = _now_ms()
    for short, cli_session in (
        ("aaaa0001", SERVED_COWORK),
        ("bbbb0002", CURSOR_COWORK),
        ("cccc0003", NEVER_SERVED_COWORK),
    ):
        env.write_desktop_session(
            short, cli_session, last_activity_ms=now - 30_000, created_ms=now - 60_000
        )
    # A session with a cursor file only counts, even when the cursor is unreadable.
    state_dir = env.codemie_home / "analytics" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / f"{CURSOR_COWORK}.cowork.json").write_text("{not json")
    env.start_daemon()

    # The served mark is left by a claude-desktop request that carries the session id; the daemon
    # lists its Cowork sessions on start, so the request goes before Desktop connects.
    served = env.post(
        "/v1/messages",
        env.bearer(CLIENT_CLAUDE_DESKTOP),
        {"model": "claude-opus-4-5", "messages": []},
        {"x-claude-code-session-id": SERVED_COWORK},
    )
    assert_that(served.status_code, equal_to(200), "the served request is forwarded")
    assert_that(
        env.cowork_served_mark(SERVED_COWORK).exists(),
        equal_to(True),
        "a served mark exists for the served session",
    )
    assert_that(
        env.cowork_served_mark(NEVER_SERVED_COWORK).exists(),
        equal_to(False),
        "the never-served session leaves no mark",
    )
    assert_that(
        env.cowork_served_mark(CURSOR_COWORK).exists(),
        equal_to(False),
        "the cursor-only session has no mark",
    )
    env.write_desktop_gateway(env.port, env.bearer())

    env.wait_for_state(
        lambda s: s.get("desktopConnectedSince"), CONNECT_WAIT, "Desktop collected"
    )
    wait_until(
        lambda: {SERVED_COWORK, CURSOR_COWORK} <= set(env.cowork_spool_sessions()),
        CONNECT_WAIT,
        "events of the served and of the cursor session in the spool",
    )
    assert_that(
        env.cowork_spool_sessions(),
        not_(has_item(NEVER_SERVED_COWORK)),
        "none for the unserved session",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_tail_of_a_collected_cowork_session_survives_the_hook_replacement_of_the_daemon(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_021
    env = daemon_env
    now = _now_ms()
    env.write_desktop_session(
        "aaaa0001",
        SERVED_COWORK,
        last_activity_ms=now - 30_000,
        created_ms=now - 60_000,
    )
    env.start_daemon()
    env.post(
        "/v1/messages",
        env.bearer(CLIENT_CLAUDE_DESKTOP),
        {"model": "claude-opus-4-5", "messages": []},
        {"x-claude-code-session-id": SERVED_COWORK},
    )
    env.write_desktop_gateway(env.port, env.bearer())
    wait_until(
        lambda: SERVED_COWORK in env.cowork_spool_sessions(),
        CONNECT_WAIT,
        "the events of the served session in the spool",
    )
    tail_id = "msg_after_replacement"
    assert_that(
        env.cowork_spool_text(SERVED_COWORK),
        not_(contains_string(tail_id)),
        "the tail is not collected before it is written",
    )
    older = env.write_state(version="0.0.1")
    env.append_desktop_session_message(SERVED_COWORK, tail_id)

    result = env.cold_start()

    assert_that(
        result.returncode, equal_to(0), f"hook succeeds: {result.stdout}{result.stderr}"
    )
    assert_that(
        env.state()["pid"],
        is_not(equal_to(older["pid"])),
        "the hook replaced the daemon",
    )
    wait_until(
        lambda: tail_id in env.cowork_spool_text(SERVED_COWORK),
        CONNECT_WAIT,
        "the tail written across the replacement in the spool",
    )
