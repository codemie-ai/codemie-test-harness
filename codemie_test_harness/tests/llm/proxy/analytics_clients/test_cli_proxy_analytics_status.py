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
Tests of the `Analytics clients:` block of `codemie proxy status`: the five analytics clients in a fixed
order, each `connected`, `not connected` with the command that fixes it, or `not found`; in text and JSON,
with the daemon running or stopped.

Each test runs the installed `codemie` CLI in an isolated HOME whose PATH holds only the clients the test
installs, with a local stub upstream as the profile's API. No stand and no real client is involved.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_item,
    is_not,
    less_than,
)

from codemie_test_harness.tests.test_data.cli_proxy_analytics_test_data import (
    CLAUDE_FLAG,
    DESKTOP_OTHER_GATEWAY_VALUE,
    OLDER_CLI_VERSION_LINE,
    ROW_CLIENTS,
    STATUS_ROWS,
    UNKNOWN_GATEWAY_KEY,
)
from codemie_test_harness.tests.utils.cli_proxy_utils import (
    ANALYTICS_CLIENTS,
    ANALYTICS_LABELS,
    CLAUDE_CODE,
    CLAUDE_DESKTOP,
    COPILOT_CLI,
    VSCODE,
    command_named_by,
    lines_of,
    output_of,
    row_values,
    status_row,
)

ALL_FOUND = (CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP, COPILOT_CLI)
JSON_FIELDS = ["client", "found", "connected", "flag"]


def _expected_rows(row):
    return [
        status_row(ANALYTICS_LABELS[client], value)
        for client, value in zip(ANALYTICS_CLIENTS, row.values)
    ]


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("row", STATUS_ROWS)
def test_status_with_a_running_daemon_lists_the_five_analytics_clients_in_order(
    analytics_env_factory, row
):
    # @case cli-proxy-one-analytics-flag_TC_012
    env = analytics_env_factory(*row.installed)
    env.connect_analytics(*row.connect)

    text = env.status_output()
    payload = env.status_json()

    lines = [line.rstrip() for line in text.splitlines()]
    assert_that(
        lines.index("Status:  running, healthy"),
        less_than(lines.index("Analytics clients:")),
        "the existing status lines come first, then the analytics block",
    )
    assert_that(
        env.analytics_rows(text),
        equal_to(_expected_rows(row)),
        "five rows in the fixed order, labels padded to 32 columns, with their state text",
    )
    assert_that(
        payload["analyticsClients"],
        equal_to(
            [
                {"client": client, "found": found, "connected": connected, "flag": flag}
                for client, found, connected, flag in zip(
                    ANALYTICS_CLIENTS, row.found, row.connected, row.flags
                )
            ]
        ),
        "analyticsClients holds five objects with client, found, connected and flag",
    )
    assert_that(
        list(payload["analyticsClients"][0]),
        equal_to(JSON_FIELDS),
        "each object carries exactly those fields",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_status_under_a_daemon_of_an_older_cli_names_no_command_in_a_not_connected_row(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_013
    env = analytics_env_factory(*ALL_FOUND)
    env.versionless_daemon()

    text = env.status_output()

    assert_that(
        lines_of(text),
        has_item(OLDER_CLI_VERSION_LINE),
        "the Version line names the one remedy: restart first",
    )
    assert_that(
        env.analytics_rows(text),
        equal_to(
            [
                status_row(ANALYTICS_LABELS[client], "not connected")
                for client in ANALYTICS_CLIENTS
            ]
        ),
        "every found, not connected row reads 'not connected' with no command",
    )
    assert_that(
        [row["connected"] for row in env.status_json()["analyticsClients"]],
        equal_to([False] * 5),
        "the JSON rows read not connected too",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_status_flags_claude_desktop_pointing_at_a_local_gateway_with_a_key_this_proxy_does_not_accept(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_014
    env = analytics_env_factory(*ALL_FOUND)
    env.start_daemon()
    env.write_desktop_gateway(env.state()["port"], UNKNOWN_GATEWAY_KEY)

    text = env.status_output()
    payload = env.status_json()

    assert_that(
        row_values(env.analytics_rows(text))[ANALYTICS_LABELS[CLAUDE_DESKTOP]],
        equal_to(DESKTOP_OTHER_GATEWAY_VALUE),
        "the Desktop row carries the gateway sentence",
    )
    desktop = [
        row for row in payload["analyticsClients"] if row["client"] == CLAUDE_DESKTOP
    ]
    assert_that(
        desktop,
        equal_to(
            [
                {
                    "client": CLAUDE_DESKTOP,
                    "found": True,
                    "connected": False,
                    "flag": CLAUDE_FLAG,
                }
            ]
        ),
        "the JSON row reads found and not connected",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_status_with_a_stopped_daemon_shows_the_block_after_status_stopped(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_015
    env = analytics_env_factory(*ALL_FOUND)
    env.write_desktop_gateway(54321, "codemie-proxy")

    text = env.status_output()
    payload = env.status_json()

    lines = [line.rstrip() for line in text.splitlines()]
    at = lines.index("Status: stopped")
    assert_that(
        lines[at + 1],
        equal_to("Analytics clients:"),
        "the block follows 'Status: stopped' directly",
    )
    rows = lines[at + 2 : at + 7]
    assert_that(
        [row.strip().split(":")[0] for row in rows],
        equal_to([ANALYTICS_LABELS[client] for client in ANALYTICS_CLIENTS]),
        "five rows in the fixed order",
    )
    assert_that(
        row_values(rows)[ANALYTICS_LABELS[CLAUDE_DESKTOP]],
        equal_to(f"not connected — Run: codemie proxy connect {CLAUDE_FLAG}"),
        "Claude Desktop reads not connected although its config is present: no daemon to point at",
    )
    assert_that(payload["status"], equal_to("stopped"), "the JSON status is stopped")
    assert_that(
        [row["client"] for row in payload["analyticsClients"]],
        equal_to(list(ANALYTICS_CLIENTS)),
        "the JSON holds the five analyticsClients",
    )
    assert_that(
        [row["connected"] for row in payload["analyticsClients"]],
        equal_to([False] * 5),
        "none of them reads connected",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("row_client", ROW_CLIENTS)
def test_the_command_a_not_connected_row_names_makes_the_row_read_connected(
    analytics_env_factory, row_client
):
    # @case cli-proxy-one-analytics-flag_TC_021
    env = analytics_env_factory(*ALL_FOUND)
    env.start_daemon()
    label = ANALYTICS_LABELS[row_client]
    before = row_values(env.analytics_rows(env.status_output()))[label]
    command = command_named_by(before)

    result = env.cli(*command, "--silent")

    assert_that(
        result.returncode,
        equal_to(0),
        f"the named command succeeds: {output_of(result)}",
    )
    assert_that(output_of(result), is_not(contains_string("✗")), "no failure line")
    assert_that(
        row_values(env.analytics_rows(env.status_output()))[label],
        equal_to("connected"),
        f"the {label} row reads connected at the next status",
    )
