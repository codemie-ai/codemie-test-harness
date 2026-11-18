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
Tests of how the installed CodeMie CLI describes its analytics flags: `proxy connect --help`, the bare
`proxy connect` target list, and the README and changelog shipped in the package.

Each test runs the installed `codemie` CLI, or reads files from its package root. No stand is involved.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_item,
)

from codemie_test_harness.tests.test_data.cli_proxy_analytics_test_data import (
    BARE_CONNECT_EXAMPLES,
    BARE_CONNECT_LINES,
    CHANGELOG_BULLET_PARTS,
    CHANGELOG_BULLET_START,
    CHANGELOG_STATUS_BULLET,
    HELP_DESCRIPTIONS,
    README_SENTENCES,
)
from codemie_test_harness.tests.utils.cli_proxy_utils import (
    line_starting_with,
    lines_of,
    nearest_heading,
    one_line,
    output_of,
)


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize(("flag", "description"), HELP_DESCRIPTIONS)
def test_connect_help_names_the_aggregate_flag_with_what_it_covers_and_the_routing(
    analytics_env_factory, flag, description
):
    # @case cli-proxy-one-analytics-flag_TC_017
    env = analytics_env_factory()

    result = env.cli("proxy", "connect", "--help")

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        one_line(result.stdout),
        contains_string(f"{flag} {description}"),
        "the flag, its members, and for --claude-otlp the routing sentence with the disconnect remark",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("expected", BARE_CONNECT_LINES)
def test_bare_connect_target_list_names_both_aggregate_flags_and_what_they_cover(
    analytics_env_factory, expected
):
    # @case cli-proxy-one-analytics-flag_TC_017
    env = analytics_env_factory()

    result = env.cli("proxy", "connect")

    assert_that(result.returncode, equal_to(0), f"exit code 0: {output_of(result)}")
    assert_that(
        one_line(result.stdout),
        contains_string(expected),
        "the target list of a bare connect",
    )
    assert_that(env.state(), equal_to(None), "a bare connect starts no daemon")


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("example", BARE_CONNECT_EXAMPLES)
def test_bare_connect_examples_include_both_aggregate_flags(
    analytics_env_factory, example
):
    # @case cli-proxy-one-analytics-flag_TC_017
    env = analytics_env_factory()

    result = env.cli("proxy", "connect")

    assert_that(
        lines_of(result.stdout),
        has_item(example),
        "the example line is listed",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("sentence", README_SENTENCES)
def test_readme_shipped_with_the_cli_describes_both_aggregate_flags_and_the_claude_routing(
    analytics_env_factory, sentence
):
    # @case cli-proxy-one-analytics-flag_TC_018
    env = analytics_env_factory()

    readme = (env.package_dir / "README.md").read_text(encoding="utf-8")

    assert_that(
        one_line(readme),
        contains_string(sentence),
        "the README names the flags, their members, the routing and that disconnect removes the route",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("part", CHANGELOG_BULLET_PARTS)
def test_changelog_shipped_with_the_cli_lists_both_aggregate_flags_as_added(
    analytics_env_factory, part
):
    # @case cli-proxy-one-analytics-flag_TC_018
    env = analytics_env_factory()
    changelog = (env.package_dir / "CHANGELOG.md").read_text(encoding="utf-8")

    bullet = line_starting_with(changelog, CHANGELOG_BULLET_START)

    assert_that(
        bullet, contains_string(part), "the changelog bullet of the flags says so"
    )
    assert_that(
        nearest_heading(changelog, CHANGELOG_BULLET_START),
        equal_to("### Added"),
        "the bullet is listed under Added",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_changelog_shipped_with_the_cli_lists_the_analytics_clients_block_as_added(
    analytics_env_factory,
):
    # @case cli-proxy-one-analytics-flag_TC_018
    env = analytics_env_factory()
    changelog = (env.package_dir / "CHANGELOG.md").read_text(encoding="utf-8")

    assert_that(
        nearest_heading(changelog, CHANGELOG_STATUS_BULLET),
        equal_to("### Added"),
        "the status block bullet is listed under Added",
    )
