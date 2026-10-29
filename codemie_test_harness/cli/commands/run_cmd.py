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

from __future__ import annotations
import click
from typing import Optional, Tuple
from ..runner import run_pytest
from ..result_options import add_result_options
from ..utils import get_config_value, ensure_env_from_config
from ..constants import (
    KEY_MARKS,
    KEY_XDIST_N,
    KEY_RERUNS,
    KEY_COUNT,
    KEY_TIMEOUT,
    DEFAULT_MARKS,
    DEFAULT_XDIST_N,
    DEFAULT_RERUNS,
    DEFAULT_TIMEOUT,
    TEST_SUITES,
    CONSOLE,
)


@click.command(name="run")
@click.argument("suite", required=False, default=None)
@click.option("--marks", help="Custom pytest -m expression (overrides suite)")
@click.option(
    "-n", "workers", type=int, help="Override number of xdist workers for this run"
)
@click.option("--reruns", type=int, help="Override number of reruns for this run")
@click.option(
    "--count",
    type=int,
    help="Number of times to repeat each test (requires pytest-repeat)",
)
@click.option(
    "--timeout",
    type=int,
    help="Per-test timeout in seconds (overrides config/default)",
)
@add_result_options
@click.option(
    "--strict",
    is_flag=True,
    help="Fail (instead of skip) tests whose declared setting or capability is missing",
)
@click.option(
    "--list-suites",
    is_flag=True,
    help="Show available test suites and exit",
)
@click.argument("extra", nargs=-1)
@click.pass_context
def run_cmd(
    ctx: click.Context,
    suite: Optional[str],
    marks: Optional[str],
    workers: Optional[int],
    reruns: Optional[int],
    count: Optional[int],
    timeout: Optional[int],
    results_dir: Optional[str],
    no_junit_xml: bool,
    no_json: bool,
    strict: bool,
    list_suites: bool,
    extra: Tuple[str, ...],
):
    """Run pytest with configured options.

    \b
    SUITE: Test suite to run (smoke, sanity, api, ui, opensource, enterprise)
           If not provided, uses default from config or 'smoke'

    \b
    Quick Examples:
        codemie-test-harness run smoke              # Run smoke tests
        codemie-test-harness run api                # Run full API regression
        codemie-test-harness run ui                 # Run UI tests
        codemie-test-harness run opensource         # Run non-enterprise tests
        codemie-test-harness run --marks "jira,mcp"    # Run specific marks

    \b
    Available Test Suites:
        smoke       - Quick smoke tests for local development
        sanity      - Sanity check for DevOps CI/CD pipelines
        api         - Full API regression suite
        ui          - Full UI regression suite
        opensource  - Non-enterprise (open-source) features
        enterprise  - Enterprise-only features

    \b
    Advanced Examples:
        codemie-test-harness run api -n 20 --reruns 3
        codemie-test-harness run --marks "smoke and gitlab" -n 8
        codemie-test-harness run smoke --count 50 -n 10  # Performance test
    """
    # Load configuration into environment variables
    ensure_env_from_config()

    # Fall back to result options given on the root group (before `run`)
    group_opts = (ctx.obj or {}).get("results", {})
    results_dir = results_dir or group_opts.get("results_dir")
    no_junit_xml = no_junit_xml or bool(group_opts.get("no_junit_xml"))
    no_json = no_json or bool(group_opts.get("no_json"))

    # Handle --list-suites flag
    if list_suites:
        _print_suites()
        return

    # Determine marks expression
    if marks:
        # --marks flag takes precedence
        resolved_marks = marks
        # Use defaults for workers/reruns if not explicitly provided
        resolved_workers = (
            workers
            if workers is not None
            else int(get_config_value(KEY_XDIST_N, str(DEFAULT_XDIST_N)))
        )
        resolved_reruns = (
            reruns
            if reruns is not None
            else int(get_config_value(KEY_RERUNS, str(DEFAULT_RERUNS)))
        )
    elif suite:
        # Suite name provided
        if suite not in TEST_SUITES:
            CONSOLE.print(f"[red]Error: Unknown suite '{suite}'[/red]")
            CONSOLE.print(
                f"\n[yellow]Available suites: {', '.join(TEST_SUITES.keys())}[/yellow]"
            )
            CONSOLE.print(
                "\n[dim]Use 'codemie-test-harness run --list-suites' for details[/dim]"
            )
            raise SystemExit(1)

        suite_config = TEST_SUITES[suite]
        resolved_marks = suite_config["marks"]
        # Suite defaults, but CLI flags can override
        resolved_workers = workers if workers is not None else suite_config["workers"]
        resolved_reruns = reruns if reruns is not None else suite_config["reruns"]

        # Get suite-specific pytest arguments (e.g., --ui-headless)
        suite_pytest_args = suite_config.get("pytest_args", [])
        if suite_pytest_args:
            CONSOLE.print(
                f"[dim]Suite pytest args: {' '.join(suite_pytest_args)}[/dim]"
            )

        # Combine extra args with suite pytest args
        combined_extra = list(extra) + suite_pytest_args

        CONSOLE.print(
            f"[cyan]Running test suite:[/cyan] [bold]{suite}[/bold] - {suite_config['description']}"
        )
    else:
        # No suite or marks provided, use config/defaults
        resolved_marks = get_config_value(KEY_MARKS, DEFAULT_MARKS)
        resolved_workers = (
            workers
            if workers is not None
            else int(get_config_value(KEY_XDIST_N, str(DEFAULT_XDIST_N)))
        )
        resolved_reruns = (
            reruns
            if reruns is not None
            else int(get_config_value(KEY_RERUNS, str(DEFAULT_RERUNS)))
        )

    resolved_count = (
        count
        if count is not None
        else (int(get_config_value(KEY_COUNT)) if get_config_value(KEY_COUNT) else None)
    )
    resolved_timeout = (
        timeout
        if timeout is not None
        else int(get_config_value(KEY_TIMEOUT, str(DEFAULT_TIMEOUT)))
    )

    # Use combined_extra if we're in a suite context, otherwise use extra
    final_extra = combined_extra if suite else extra
    if marks:
        # explicit mark selection shows the real result of each test
        final_extra = [*final_extra, "--no-gate"]
    if strict:
        final_extra = [*final_extra, "--strict-requirements"]

    run_pytest(
        int(resolved_workers),
        str(resolved_marks),
        int(resolved_reruns),
        resolved_count,
        resolved_timeout,
        final_extra,
        results_dir=results_dir,
        junit=not no_junit_xml,
        json_=not no_json,
    )


def _print_suites():
    """Print available test suites with descriptions."""
    from rich.table import Table

    table = Table(
        title="Available Test Suites", show_header=True, header_style="bold magenta"
    )
    table.add_column("Suite", style="bold green", width=15)
    table.add_column("Description", style="cyan", width=50)
    table.add_column("Marks", style="yellow", width=40)
    table.add_column("Workers", justify="center", width=8)
    table.add_column("Reruns", justify="center", width=7)

    # Display suites in preferred order
    suite_order = [
        "sanity",
        "sanity-api",
        "sanity-ui",
        "smoke",
        "smoke-api",
        "smoke-ui",
        "api",
        "enterprise",
        "opensource",
        "ui",
    ]
    for suite_name in suite_order:
        if suite_name in TEST_SUITES:
            config = TEST_SUITES[suite_name]
            table.add_row(
                suite_name,
                config["description"],
                config["marks"],
                str(config["workers"]),
                str(config["reruns"]),
            )

    CONSOLE.print()
    CONSOLE.print(table)
    CONSOLE.print("\n[dim]Usage: codemie-test-harness run <suite> [options][/dim]")
    CONSOLE.print("[dim]Example: codemie-test-harness run smoke[/dim]")
