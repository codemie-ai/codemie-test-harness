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
Tests of `codemie proxy disconnect --claude-otlp` and `--copilot-otlp`: each does what the vendor's member
disconnects do together, and skips a member that is neither found nor connected.

Each test runs the installed `codemie` CLI in an isolated HOME whose PATH holds only the clients the test
installs, with a local stub upstream as the profile's API. No stand and no real client is involved.
"""

import pytest
from hamcrest import (
    all_of,
    any_of,
    assert_that,
    contains_string,
    empty,
    equal_to,
    has_item,
    is_not,
    none,
    not_none,
)

from codemie_test_harness.tests.test_data.cli_proxy_analytics_test_data import (
    CLAUDE_FLAG,
    COPILOT_FLAG,
    DISCONNECT_AGGREGATE_VS_MEMBERS,
    DISCONNECT_ROWS,
)
from codemie_test_harness.tests.utils.cli_proxy_utils import (
    ANALYTICS_LABELS,
    CLAUDE_CODE,
    CLAUDE_DESKTOP,
    COPILOT_CHAT,
    COPILOT_CLI,
    VSCODE,
    VSCODE_CLAUDE_CODE,
    VSCODE_INSIDERS,
    lines_of,
    output_of,
    row_values,
)

OTHER_PROJECT = "/other/project"


def contains_none(*texts):
    return is_not(any_of(*[contains_string(text) for text in texts]))


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("row", DISCONNECT_ROWS)
def test_disconnect_aggregate_removes_what_is_connected_and_skips_members_neither_found_nor_connected(
    analytics_env_factory, row
):
    # @case cli-proxy-one-analytics-flag_TC_010
    env = analytics_env_factory(*row.installed)
    env.connect_analytics(*row.connect)
    env.change_machine(*row.changes)

    result = env.cli("proxy", "disconnect", *row.disconnect)

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        lines_of(result.stdout),
        all_of(*[has_item(contains_string(line)) for line in row.named]),
        "every member that is found or connected is disconnected",
    )
    assert_that(
        result.stdout,
        contains_none(*row.not_named)
        if row.not_named
        else is_not(contains_string("✗")),
        "a member that is neither found nor connected is skipped without a line",
    )
    assert_that(
        env.configured_clients(), empty(), "no client of the vendor is left configured"
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize(
    ("connect", "aggregate", "member_flags", "installed"),
    DISCONNECT_AGGREGATE_VS_MEMBERS,
)
def test_disconnect_aggregate_leaves_the_machine_as_the_members_disconnects_do_together(
    analytics_env_factory, connect, aggregate, member_flags, installed
):
    # @case cli-proxy-one-analytics-flag_TC_010
    by_aggregate = analytics_env_factory(*installed)
    by_members = analytics_env_factory(*installed)
    by_aggregate.connect_analytics(*connect)
    by_members.connect_analytics(*connect)

    first = by_aggregate.cli("proxy", "disconnect", *aggregate)
    second = by_members.cli("proxy", "disconnect", *member_flags)

    assert_that(first.returncode, equal_to(0), f"aggregate: {output_of(first)}")
    assert_that(second.returncode, equal_to(0), f"members: {output_of(second)}")
    assert_that(
        [
            by_aggregate.mask(line)
            for line in lines_of(first.stdout)
            if line.startswith("✓")
        ],
        equal_to(
            [
                by_members.mask(line)
                for line in lines_of(second.stdout)
                if line.startswith("✓")
            ]
        ),
        "the same disconnect lines are printed",
    )
    assert_that(
        by_aggregate.config_snapshot(),
        equal_to(by_members.config_snapshot()),
        "the machine is left as the member disconnects leave it",
    )
    assert_that(
        by_aggregate.configured_clients(), empty(), "nothing is left configured"
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_disconnect_claude_otlp_with_scope_project_removes_only_the_current_project_and_keeps_desktop_and_extension(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_011
    env = analytics_env_factory(CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP)
    env.connect_analytics(CLAUDE_FLAG, "--scope", "project")
    env.set_tracked_projects([str(env.home), OTHER_PROJECT])

    result = env.cli("proxy", "disconnect", CLAUDE_FLAG, "--scope", "project")

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        lines_of(result.stdout),
        has_item(contains_string("✓ Project removed from Claude Code OTLP tracking")),
        "Claude Code analytics drops the current project",
    )
    assert_that(
        env.tracked_projects(CLAUDE_CODE),
        equal_to([OTHER_PROJECT]),
        "the other project is still tracked",
    )
    assert_that(
        result.stdout,
        contains_none("Claude Desktop", "VS Code Claude Code"),
        "Claude Desktop and the extension are not touched or named",
    )
    assert_that(
        env.configured_clients(),
        equal_to([CLAUDE_CODE, VSCODE_CLAUDE_CODE, CLAUDE_DESKTOP]),
        "Claude Code, the extension route and Desktop all stay connected",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_disconnect_claude_otlp_with_scope_project_removing_the_last_project_keeps_desktop_and_extension(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_011
    env = analytics_env_factory(CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP)
    env.connect_analytics(CLAUDE_FLAG, "--scope", "project")

    result = env.cli("proxy", "disconnect", CLAUDE_FLAG, "--scope", "project")

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        lines_of(result.stdout),
        has_item(contains_string("✓ Claude Code OTLP disconnected")),
        "Claude Code analytics is disconnected with its last project",
    )
    assert_that(
        env.configured_clients(),
        equal_to([VSCODE_CLAUDE_CODE, CLAUDE_DESKTOP]),
        "the extension route and Desktop stay connected",
    )
    assert_that(
        row_values(env.analytics_rows(env.status_output()))[
            ANALYTICS_LABELS[CLAUDE_DESKTOP]
        ],
        equal_to("connected"),
        "status still reads Claude Desktop connected",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_disconnect_copilot_otlp_with_scope_project_removes_the_current_project_from_both_members(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_011
    env = analytics_env_factory(VSCODE, COPILOT_CLI)
    env.connect_analytics(COPILOT_FLAG, "--scope", "project")

    result = env.cli("proxy", "disconnect", COPILOT_FLAG, "--scope", "project")

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        env.configured_clients(),
        empty(),
        "both Copilot members were scoped to the project only and are disconnected",
    )
    assert_that(
        env.copilot_scope(COPILOT_CHAT),
        equal_to({"enabled": False}),
        "Copilot Chat's scope record is disabled",
    )
    assert_that(
        env.copilot_scope(COPILOT_CLI),
        equal_to({"enabled": False}),
        "Copilot CLI's scope record is disabled",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_extension_connected_with_insiders_reads_connected_on_an_insiders_only_machine(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_025
    env = analytics_env_factory(CLAUDE_CODE, VSCODE_INSIDERS, CLAUDE_DESKTOP)

    env.connect_analytics(CLAUDE_FLAG, "--insiders")

    assert_that(
        row_values(env.analytics_rows(env.status_output()))[
            ANALYTICS_LABELS[VSCODE_CLAUDE_CODE]
        ],
        equal_to("connected"),
        "the extension row reads connected, the state AC-8 disconnects from",
    )
    assert_that(
        env.vscode_route(insiders=True),
        not_none(),
        "the CodeMie route is in the Insiders settings.json",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.xfail(
    reason=(
        "Confirmed product bug (AC-8): with only VS Code Insiders installed, disconnect --claude-otlp "
        "without --insiders skips the extension, whose 'configured' check looks at the stable directory only, "
        "and leaves its route in the Insiders settings.json although proxy status reads it connected"
    ),
    raises=AssertionError,
    strict=True,
)
def test_disconnect_claude_otlp_without_insiders_removes_the_extension_route_on_an_insiders_only_machine(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_025
    env = analytics_env_factory(CLAUDE_CODE, VSCODE_INSIDERS, CLAUDE_DESKTOP)
    env.connect_analytics(CLAUDE_FLAG, "--insiders")

    result = env.cli("proxy", "disconnect", CLAUDE_FLAG)

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        env.vscode_route(insiders=True),
        none(),
        "AC-8: a member that is not found but reads connected is disconnected, "
        "so no CodeMie gateway route may be left in the Insiders settings.json",
    )
