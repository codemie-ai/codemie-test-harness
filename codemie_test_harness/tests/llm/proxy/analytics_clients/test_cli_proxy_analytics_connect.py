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
Tests of `codemie proxy connect --claude-otlp` and `--copilot-otlp`: each turns analytics on for every
client of a vendor found on the machine, exactly as that vendor's member flags do together.

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
    has_length,
    is_not,
    none,
    not_none,
)

from codemie_test_harness.tests.test_data.cli_proxy_analytics_test_data import (
    AGGREGATE_WITH_MEMBER,
    CLAUDE_FLAG,
    CLAUDE_MEMBER_FLAGS,
    COPILOT_BIN_PATHS,
    COPILOT_CHAT_SUCCESS_LINE,
    COPILOT_CLI_SUCCESS_LINE,
    COPILOT_FLAG,
    COPILOT_MEMBER_FLAGS,
    EXTENSION_DIRECTORY_MISSING_TEXT,
    EXTENSION_SUCCESS_LINE,
    FAILING_MEMBERS,
    MEMBER_FLAGS_ALONE,
    MEMBER_FLAGS_WITHOUT_APPLICATION,
    NO_TERMINAL_LINE,
    NO_TERMINAL_REMEDY,
    NOTHING_FOUND,
    OPTIONS_REACHING_MEMBERS,
    REFUSED_WITHOUT_TERMINAL,
    SKIPPED_MEMBERS,
)
from codemie_test_harness.tests.utils.cli_proxy_utils import (
    CLAUDE_CODE,
    CLAUDE_DESKTOP,
    COPILOT_CHAT,
    COPILOT_CLI,
    VSCODE,
    VSCODE_CLAUDE_CODE,
    VSCODE_INSIDERS,
    lines_of,
    output_of,
    ANALYTICS_LABELS,
    row_values,
)


def contains_all(*texts):
    return all_of(*[contains_string(text) for text in texts])


def contains_none(*texts):
    return is_not(any_of(*[contains_string(text) for text in texts]))


def _success_lines(result):
    return [line for line in lines_of(result.stdout) if line.startswith("✓")]


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_claude_otlp_configures_the_three_claude_clients_as_the_three_member_flags_do(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_001
    aggregate = analytics_env_factory(CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP)
    members = analytics_env_factory(CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP)

    by_aggregate = aggregate.cli("proxy", "connect", CLAUDE_FLAG, "--silent")
    by_members = members.cli("proxy", "connect", *CLAUDE_MEMBER_FLAGS, "--silent")

    assert_that(
        by_aggregate.returncode,
        equal_to(0),
        f"the aggregate connect succeeds: {output_of(by_aggregate)}",
    )
    assert_that(
        by_members.returncode,
        equal_to(0),
        f"the member flags connect succeeds: {output_of(by_members)}",
    )
    assert_that(aggregate.daemon_pids(), has_length(1), "the aggregate runs one daemon")
    assert_that(
        aggregate.configured_clients(),
        equal_to(["claude-code", "vscode-claude-code", "claude-desktop"]),
        "the aggregate configures all three Claude clients",
    )
    assert_that(
        aggregate.config_snapshot(),
        equal_to(members.config_snapshot()),
        "client configs, connection record and daemon state fields equal those of the member flags",
    )
    assert_that(
        sorted(aggregate.state()),
        equal_to(sorted(members.state())),
        "the aggregate adds no client or telemetry-mode field to the daemon state",
    )
    assert_that(
        aggregate.desktop_applied_config()["inferenceGatewayApiKey"],
        equal_to(aggregate.bearer("claude-desktop")),
        "Desktop is given the daemon's gateway key named for it",
    )
    assert_that(
        [aggregate.mask(line) for line in _success_lines(by_aggregate)],
        equal_to([members.mask(line) for line in _success_lines(by_members)]),
        "the same success lines are printed",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_copilot_otlp_configures_copilot_chat_and_cli_as_the_two_member_flags_do(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_002
    aggregate = analytics_env_factory(VSCODE, COPILOT_CLI)
    members = analytics_env_factory(VSCODE, COPILOT_CLI)

    by_aggregate = aggregate.cli("proxy", "connect", COPILOT_FLAG)
    by_members = members.cli("proxy", "connect", *COPILOT_MEMBER_FLAGS)

    assert_that(
        by_aggregate.returncode,
        equal_to(0),
        f"the aggregate connect succeeds: {output_of(by_aggregate)}",
    )
    assert_that(
        by_members.returncode,
        equal_to(0),
        f"the member flags connect succeeds: {output_of(by_members)}",
    )
    assert_that(
        lines_of(by_aggregate.stdout),
        has_item(COPILOT_CHAT_SUCCESS_LINE),
        "Copilot Chat success line",
    )
    assert_that(
        lines_of(by_aggregate.stdout),
        has_item(COPILOT_CLI_SUCCESS_LINE),
        "Copilot CLI success line",
    )
    assert_that(
        [aggregate.mask(line) for line in _success_lines(by_aggregate)],
        equal_to([members.mask(line) for line in _success_lines(by_members)]),
        "the member flags print the same lines",
    )
    assert_that(
        aggregate.config_snapshot(),
        equal_to(members.config_snapshot()),
        "the connector scope records and hook files equal those of the member flags",
    )
    assert_that(
        aggregate.configured_clients(),
        equal_to([COPILOT_CHAT, COPILOT_CLI]),
        "both Copilot clients are configured",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("row", SKIPPED_MEMBERS)
def test_member_whose_application_is_not_found_is_skipped_silently(
    analytics_env_factory, row
):
    # @case cli-proxy-one-analytics-flag_TC_003
    env = analytics_env_factory(*row.installed)

    result = env.cli("proxy", "connect", *row.command)

    assert_that(
        result.returncode,
        equal_to(0),
        f"the connect succeeds: {output_of(result)}",
    )
    assert_that(
        output_of(result),
        is_not(contains_string(row.absent_label)),
        "no line names the skipped member",
    )
    assert_that(
        env.configured_clients(),
        equal_to(list(row.configured)),
        "the others are configured and the skipped member has no file written",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize(("flag", "nothing_connected_line"), NOTHING_FOUND)
def test_aggregate_with_no_member_found_starts_no_daemon_and_exits_0(
    analytics_env_factory, flag, nothing_connected_line
):
    # @case cli-proxy-one-analytics-flag_TC_004
    env = analytics_env_factory()

    result = env.cli("proxy", "connect", flag)

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        lines_of(result.stdout),
        has_item(nothing_connected_line),
        "one line says nothing was connected and points at proxy status",
    )
    assert_that(
        result.stdout,
        contains_none("Using profile", "Starting proxy"),
        "no profile is resolved and no proxy start is printed",
    )
    assert_that(env.state(), none(), "no daemon state is written")
    assert_that(env.daemon_pids(), empty(), "no daemon process runs")


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("row", FAILING_MEMBERS)
def test_found_member_that_fails_prints_its_failure_and_exits_1_with_the_others_configured(
    analytics_env_factory, row
):
    # @case cli-proxy-one-analytics-flag_TC_005
    env = analytics_env_factory(*row.installed)
    env.arrange(*row.arrange)

    result = env.cli("proxy", "connect", *row.command)

    assert_that(result.returncode, equal_to(1), f"exit code 1: {output_of(result)}")
    assert_that(
        output_of(result),
        contains_all(*row.failure_texts),
        "the failing member's failure line is printed",
    )
    assert_that(
        env.configured_clients(),
        equal_to(list(row.configured)),
        "the members that succeed stay configured",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize(("flag", "client", "application"), MEMBER_FLAGS_ALONE)
def test_member_flag_alone_configures_its_client_when_the_application_is_present(
    analytics_env_factory, flag, client, application
):
    # @case cli-proxy-one-analytics-flag_TC_006
    env = analytics_env_factory(application)

    result = env.cli("proxy", "connect", flag, "--silent")

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        env.configured_clients(),
        equal_to([client]),
        "only its own client is configured",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize(("flag", "client"), MEMBER_FLAGS_WITHOUT_APPLICATION)
def test_member_flag_alone_still_configures_its_client_when_the_application_is_absent(
    analytics_env_factory, flag, client
):
    # @case cli-proxy-one-analytics-flag_TC_006
    env = analytics_env_factory()

    result = env.cli("proxy", "connect", flag, "--silent")

    assert_that(
        result.returncode,
        equal_to(0),
        f"exit code 0, no silent skip: {output_of(result)}",
    )
    assert_that(
        env.configured_clients(),
        equal_to([client]),
        "the client is configured although its application is absent",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_vscode_claude_code_flag_alone_still_fails_without_the_vscode_directory(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_006
    env = analytics_env_factory()

    result = env.cli("proxy", "connect", "--vscode-claude-code")

    assert_that(
        result.returncode,
        equal_to(1),
        f"the member flag fails, it is not skipped: {output_of(result)}",
    )
    assert_that(
        output_of(result),
        contains_string(EXTENSION_DIRECTORY_MISSING_TEXT),
        "the failure names the missing VS Code user data directory",
    )
    assert_that(env.configured_clients(), empty(), "nothing is configured")


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("row", OPTIONS_REACHING_MEMBERS)
def test_options_given_to_the_aggregate_reach_each_member_as_under_its_own_flag(
    analytics_env_factory, row
):
    # @case cli-proxy-one-analytics-flag_TC_008
    aggregate = analytics_env_factory(*row.installed)
    members = analytics_env_factory(*row.installed)
    aggregate.arrange(*row.arrange)
    members.arrange(*row.arrange)

    by_aggregate = aggregate.cli("proxy", "connect", *row.aggregate_command)
    by_members = members.cli("proxy", "connect", *row.member_command)

    assert_that(
        by_aggregate.returncode,
        equal_to(0),
        f"the aggregate connect succeeds: {output_of(by_aggregate)}",
    )
    assert_that(
        by_members.returncode,
        equal_to(0),
        f"the member flags connect succeeds: {output_of(by_members)}",
    )
    assert_that(
        aggregate.configured_clients(),
        equal_to(list(row.configured)),
        "every member is configured",
    )
    assert_that(
        aggregate.config_snapshot(),
        equal_to(members.config_snapshot()),
        "each member's config equals the one the member flags leave with the same option",
    )
    assert_that(
        aggregate.state()["profile"],
        equal_to(row.profile),
        "the daemon runs under the profile asked for",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_insiders_given_to_the_aggregate_reaches_the_extension_as_under_its_own_flag(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_008
    aggregate = analytics_env_factory(CLAUDE_CODE, VSCODE, VSCODE_INSIDERS)
    members = analytics_env_factory(CLAUDE_CODE, VSCODE, VSCODE_INSIDERS)

    by_aggregate = aggregate.cli(
        "proxy", "connect", CLAUDE_FLAG, "--insiders", "--silent"
    )
    by_members = members.cli(
        "proxy", "connect", *CLAUDE_MEMBER_FLAGS, "--insiders", "--silent"
    )

    assert_that(
        by_aggregate.returncode,
        equal_to(0),
        f"the aggregate connect succeeds: {output_of(by_aggregate)}",
    )
    assert_that(
        by_members.returncode,
        equal_to(0),
        f"the member flags connect succeeds: {output_of(by_members)}",
    )
    assert_that(
        aggregate.vscode_route(insiders=True),
        not_none(),
        "the extension route is written to the Insiders settings",
    )
    assert_that(
        aggregate.vscode_route(insiders=False),
        none(),
        "the stable VS Code settings get no route",
    )
    assert_that(
        aggregate.config_snapshot(),
        equal_to(members.config_snapshot()),
        "the machine equals the one the member flags leave with --insiders",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_scope_project_given_to_the_aggregate_tracks_only_the_current_project(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_008
    env = analytics_env_factory(CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP, COPILOT_CLI)

    claude = env.cli("proxy", "connect", CLAUDE_FLAG, "--scope", "project", "--silent")
    copilot = env.cli("proxy", "connect", COPILOT_FLAG, "--scope", "project")

    assert_that(claude.returncode, equal_to(0), f"Claude connect: {output_of(claude)}")
    assert_that(
        copilot.returncode, equal_to(0), f"Copilot connect: {output_of(copilot)}"
    )
    assert_that(
        env.tracked_projects(CLAUDE_CODE),
        equal_to([str(env.home)]),
        "Claude Code tracks the current project only",
    )
    assert_that(
        env.tracked_projects(COPILOT_CHAT),
        equal_to([str(env.home)]),
        "Copilot Chat tracks the current project only",
    )
    assert_that(
        env.tracked_projects(COPILOT_CLI),
        equal_to([str(env.home)]),
        "Copilot CLI tracks the current project only",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize(
    ("with_member", "alone", "installed", "member_success_line"), AGGREGATE_WITH_MEMBER
)
def test_aggregate_given_with_one_of_its_members_behaves_as_the_aggregate_alone(
    analytics_env_factory, with_member, alone, installed, member_success_line
):
    # @case cli-proxy-one-analytics-flag_TC_008
    given_with_member = analytics_env_factory(*installed)
    given_alone = analytics_env_factory(*installed)

    first = given_with_member.cli("proxy", "connect", *with_member)
    second = given_alone.cli("proxy", "connect", *alone)

    assert_that(first.returncode, equal_to(0), f"with member: {output_of(first)}")
    assert_that(second.returncode, equal_to(0), f"alone: {output_of(second)}")
    assert_that(
        lines_of(first.stdout).count(member_success_line),
        equal_to(1),
        "the member is configured once, not twice",
    )
    assert_that(
        given_with_member.config_snapshot(),
        equal_to(given_alone.config_snapshot()),
        "the machine is left as the aggregate alone leaves it",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("installed", REFUSED_WITHOUT_TERMINAL)
def test_claude_otlp_without_a_terminal_and_without_silent_is_refused_before_anything_changes(
    analytics_env_factory, installed
):
    # @case cli-proxy-one-analytics-flag_TC_009
    env = analytics_env_factory(*installed)

    result = env.cli("proxy", "connect", CLAUDE_FLAG)

    assert_that(result.returncode, equal_to(1), f"exit code 1: {output_of(result)}")
    assert_that(
        output_of(result),
        contains_all(NO_TERMINAL_LINE, NO_TERMINAL_REMEDY),
        "the refusal names --silent",
    )
    assert_that(env.state(), none(), "no daemon is started")
    assert_that(env.configured_clients(), empty(), "no client file is written")
    assert_that(
        env.claude_settings_path.exists(),
        equal_to(False),
        "the Claude Code settings are untouched",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_claude_otlp_without_claude_code_or_vscode_is_not_refused_for_the_missing_terminal(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_009
    env = analytics_env_factory(CLAUDE_DESKTOP)

    result = env.cli("proxy", "connect", CLAUDE_FLAG)

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        output_of(result),
        is_not(contains_string(NO_TERMINAL_LINE)),
        "no refusal, as the Claude Code settings are not to be written",
    )
    assert_that(
        env.configured_clients(),
        equal_to([CLAUDE_DESKTOP]),
        "the members that need no confirmation are configured",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_rerunning_copilot_otlp_after_installing_copilot_cli_configures_it_and_keeps_the_project_list(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_016
    env = analytics_env_factory(VSCODE)
    first = env.cli("proxy", "connect", COPILOT_FLAG, "--scope", "project")
    chat_hooks_before = env.copilot_hook_file(COPILOT_CHAT).read_text()
    env.install_clients(COPILOT_CLI)

    again = env.cli("proxy", "connect", COPILOT_FLAG)

    assert_that(first.returncode, equal_to(0), f"first run: {output_of(first)}")
    assert_that(again.returncode, equal_to(0), f"second run: {output_of(again)}")
    assert_that(
        env.configured_clients(),
        equal_to([COPILOT_CHAT, COPILOT_CLI]),
        "the newly installed Copilot CLI is configured",
    )
    assert_that(
        env.copilot_hook_file(COPILOT_CHAT).read_text(),
        equal_to(chat_hooks_before),
        "Copilot Chat stays as it was",
    )
    assert_that(
        env.tracked_projects(COPILOT_CHAT),
        equal_to([str(env.home)]),
        "the named project list is kept without --scope",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_scope_user_on_a_rerun_replaces_the_project_list_as_under_the_members_own_flag(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_016
    env = analytics_env_factory(CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP)
    env.connect_analytics(CLAUDE_FLAG, "--scope", "project")
    kept = env.cli("proxy", "connect", CLAUDE_FLAG, "--silent")
    tracked_after_kept_run = env.tracked_projects(CLAUDE_CODE)

    replaced = env.cli("proxy", "connect", CLAUDE_FLAG, "--scope", "user", "--silent")

    assert_that(kept.returncode, equal_to(0), f"rerun: {output_of(kept)}")
    assert_that(
        tracked_after_kept_run,
        equal_to([str(env.home)]),
        "a rerun without --scope keeps the named project list",
    )
    assert_that(
        replaced.returncode,
        equal_to(0),
        f"rerun with scope user: {output_of(replaced)}",
    )
    assert_that(
        env.tracked_projects(CLAUDE_CODE),
        empty(),
        "--scope user replaces the list: all projects are tracked",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_claude_otlp_with_only_vscode_insiders_skips_the_extension_until_insiders_is_given(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_019
    env = analytics_env_factory(CLAUDE_CODE, VSCODE_INSIDERS)

    without = env.cli("proxy", "connect", CLAUDE_FLAG, "--silent")
    skipped_route = env.vscode_route(insiders=True)
    status_before = env.status_output()
    with_insiders = env.cli("proxy", "connect", CLAUDE_FLAG, "--insiders", "--silent")

    assert_that(without.returncode, equal_to(0), f"exit code 0: {output_of(without)}")
    assert_that(
        output_of(without),
        contains_none(EXTENSION_SUCCESS_LINE, "✗"),
        "the extension is skipped without a failure line",
    )
    assert_that(skipped_route, none(), "the Insiders settings hold no route yet")
    assert_that(
        row_values(env.analytics_rows(status_before))[
            ANALYTICS_LABELS[VSCODE_CLAUDE_CODE]
        ],
        equal_to("not connected — Run: codemie proxy connect --claude-otlp --insiders"),
        "the status row names the command with --insiders",
    )
    assert_that(
        with_insiders.returncode,
        equal_to(0),
        f"exit code 0 with --insiders: {output_of(with_insiders)}",
    )
    assert_that(
        env.vscode_route(insiders=True),
        not_none(),
        "the extension is configured in the Insiders settings",
    )
    assert_that(
        row_values(env.analytics_rows(env.status_output()))[
            ANALYTICS_LABELS[VSCODE_CLAUDE_CODE]
        ],
        equal_to("connected"),
        "the extension reads connected afterwards",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_claude_otlp_with_vscode_but_no_claude_binary_writes_the_shared_settings(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_020
    env = analytics_env_factory(VSCODE)

    result = env.cli("proxy", "connect", CLAUDE_FLAG, "--silent")
    rows = row_values(env.analytics_rows(env.status_output()))

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        env.claude_hooks_present(),
        equal_to(True),
        "the CodeMie hooks are in ~/.claude/settings.json",
    )
    assert_that(
        rows[ANALYTICS_LABELS[VSCODE_CLAUDE_CODE]],
        equal_to("connected"),
        "the extension row reads connected",
    )
    assert_that(
        rows[ANALYTICS_LABELS[CLAUDE_CODE]],
        equal_to("connected"),
        "the Claude Code row reads connected from the same shared settings",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize(("bin_kind", "configured"), COPILOT_BIN_PATHS)
def test_codemie_copilot_bin_naming_a_path_is_checked_as_a_file_against_the_cwd(
    analytics_env_factory, bin_kind, configured
):
    # @case cli-proxy-one-analytics-flag_TC_022
    env = analytics_env_factory(VSCODE)
    env.point_copilot_bin_at(bin_kind)

    result = env.cli("proxy", "connect", COPILOT_FLAG)

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        env.configured_clients(),
        equal_to(list(configured)),
        "Copilot CLI is configured only when the path names a file",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_invalid_stored_project_filter_fails_only_claude_code_analytics_under_the_aggregate(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_023
    env = analytics_env_factory(CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP)
    env.arrange("invalid project filter")

    result = env.cli("proxy", "connect", CLAUDE_FLAG, "--silent")

    assert_that(result.returncode, equal_to(1), f"exit code 1: {output_of(result)}")
    assert_that(
        lines_of(result.stdout),
        has_item(
            "✗ Claude Code Analytics — Claude Code settings contain an invalid "
            "CODEMIE_ANALYTICS_PROJECT_FILTER value. Fix it manually or re-run with --force to discard it."
        ),
        "Claude Code analytics reports the invalid list",
    )
    assert_that(
        env.configured_clients(),
        equal_to([VSCODE_CLAUDE_CODE, CLAUDE_DESKTOP]),
        "the extension route and Desktop are configured",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_invalid_stored_project_filter_still_fails_the_whole_connect_under_the_member_flags(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_023
    env = analytics_env_factory(CLAUDE_CODE, VSCODE, CLAUDE_DESKTOP)
    env.arrange("invalid project filter")

    result = env.cli("proxy", "connect", *CLAUDE_MEMBER_FLAGS, "--silent")

    assert_that(result.returncode, equal_to(1), f"exit code 1: {output_of(result)}")
    assert_that(
        output_of(result),
        contains_string("invalid CODEMIE_ANALYTICS_PROJECT_FILTER value"),
        "the invalid list is reported",
    )
    assert_that(
        env.configured_clients(),
        empty(),
        "nothing is configured: only the aggregate fails Claude Code analytics alone",
    )
