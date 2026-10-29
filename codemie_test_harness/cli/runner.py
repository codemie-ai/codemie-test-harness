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
import os
import stat
import subprocess
import sys
from typing import Iterable, List
from pathlib import Path

try:
    from importlib.resources import files as pkg_files
except Exception:
    pkg_files = None

from .constants import CONSOLE, TEST_SUITES
from .marks_utils import (
    get_all_available_marks,
    is_valid_mark_expression,
    print_marks_list,
)


def resolve_tests_path_and_root() -> tuple[str, str]:
    """Resolve tests path and working directory.

    Returns:
        tuple: (tests_path, root_dir)
            - tests_path: Path to tests for pytest collection
            - root_dir: Directory to use as cwd so pytest.ini/.env are found
    """
    # 1) Use importlib.resources to locate installed package "tests"
    if pkg_files is not None:
        try:
            # Try to locate codemie_test_harness.tests package
            tests_dir = Path(str(pkg_files("codemie_test_harness.tests")))
            # Root dir should be the codemie_test_harness package directory
            # where pytest.ini and .env are located
            root_dir = str(tests_dir.parent)  # codemie_test_harness package root
            return str(tests_dir), root_dir
        except Exception:
            pass

    # 2) Fallback to repo layout when running from source
    # runner.py -> cli -> codemie_test_harness -> <repo_root>
    codemie_test_harness_root = (
        Path(__file__).resolve().parents[1]
    )  # codemie_test_harness directory
    tests_path = str(codemie_test_harness_root / "tests")
    # Use codemie_test_harness as root_dir since pytest.ini and .env are there
    root_dir = str(codemie_test_harness_root)
    return tests_path, root_dir


def build_pytest_cmd(
    workers: int,
    marks: str,
    reruns: int,
    count: int | None = None,
    timeout: int | None = None,
    extra: Iterable[str] | None = None,
    results_dir: Path | None = None,
    junit: bool = True,
    json_: bool = True,
) -> tuple[List[str], str]:
    tests_path, root_dir = resolve_tests_path_and_root()
    cmd = [sys.executable, "-m", "pytest", tests_path]
    if workers:
        cmd += ["-n", str(workers)]
    if marks:
        cmd += ["-m", str(marks)]
    if reruns and int(reruns) > 0:
        cmd += ["--reruns", str(reruns)]
    if count and int(count) > 0:
        cmd += ["--count", str(count)]
    if timeout and int(timeout) > 0:
        cmd += ["--timeout", str(timeout)]
    if extra:
        cmd += list(extra)
    if results_dir is not None:
        # A --junitxml the caller passed in extra wins; pytest keeps the last one
        if junit and not any(a.startswith(JUNITXML_FLAGS) for a in extra or ()):
            cmd += [f"--junitxml={results_dir / 'junit.xml'}"]
        if json_:
            cmd += [
                "-p",
                "codemie_test_harness.results_plugin",
                f"--results-json={results_dir / 'results.json'}",
            ]
    return cmd, root_dir


RESULT_FILES = ("junit.xml", "results.json")
JUNITXML_FLAGS = ("--junitxml", "--junit-xml")


def _remove_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        # Windows cannot delete a read-only file; clear the bit and retry
        os.chmod(path, stat.S_IWRITE)
        path.unlink(missing_ok=True)


def prepare_results_dir(
    results_dir: str | None, junit: bool, json_: bool
) -> Path | None:
    """Resolve, create and check the results folder (against the caller cwd).

    Returns None when both result formats are off. Otherwise removes the
    result files of an earlier run. Exits with code 1 and a red message
    naming the folder when it cannot be used.
    """
    if not (junit or json_):
        return None
    path = Path(results_dir or "codemie-test-reports")
    if not path.is_absolute():
        path = Path.cwd() / path
    path = Path(os.path.normpath(path))
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir() or not os.access(path, os.W_OK | os.X_OK):
            raise OSError("not a writable directory")
        # Drop files of an earlier run (also for a format that is now off), so
        # a run that writes nothing cannot leave old results behind as new
        for name in RESULT_FILES:
            _remove_file(path / name)
    except OSError as e:
        CONSOLE.print(f"[red]Error: cannot use results folder '{path}': {e}[/red]")
        raise SystemExit(1)
    return path


def validate_marks_expression(marks: str) -> None:
    """Validate that the marks expression contains only known marks.

    Args:
        marks: The pytest marks expression to validate

    Raises:
        SystemExit: If unknown marks are found
    """
    if not marks or not marks.strip():
        return

    try:
        available_marks = get_all_available_marks()

        # Add marks from built-in test suites to available marks
        # This allows suite marks (like 'sanity') that may only be in test parameters
        suite_marks = set()
        for suite_config in TEST_SUITES.values():
            # Extract individual marks from the marks expression
            suite_marks_expr = suite_config["marks"]
            # Simple extraction - split by 'and', 'or', 'not' and strip
            import re

            extracted = re.findall(r"\b(\w+)\b", suite_marks_expr)
            # Filter out operators
            for mark in extracted:
                if mark not in {"and", "or", "not"}:
                    suite_marks.add(mark)

        # Combine available marks with suite marks
        all_marks = list(set(available_marks) | suite_marks)

        is_valid, unknown_marks = is_valid_mark_expression(marks, all_marks)

        if not is_valid:
            CONSOLE.print(
                f"[red]Error: Unknown pytest mark(s) found: {', '.join(unknown_marks)}[/red]"
            )
            CONSOLE.print(f"\n[yellow]Expression used:[/yellow] {marks}")
            print_marks_list(show_files=False)
            CONSOLE.print(
                "\n[dim]Use 'codemie-test-harness marks' to see all available marks[/dim]"
            )
            raise SystemExit(1)

    except Exception as e:
        # If mark validation fails for any reason, issue a warning but continue
        CONSOLE.print(f"[yellow]Warning: Could not validate marks: {str(e)}[/yellow]")


def run_pytest(
    workers: int,
    marks: str,
    reruns: int,
    count: int | None = None,
    timeout: int | None = None,
    extra: Iterable[str] | None = None,
    results_dir: str | None = None,
    junit: bool = True,
    json_: bool = True,
) -> None:
    # Validate marks before running pytest
    validate_marks_expression(marks)

    # Resolve against the caller cwd here, in the parent process
    results_path = prepare_results_dir(results_dir, junit, json_)
    cmd, root_dir = build_pytest_cmd(
        workers,
        marks,
        reruns,
        count,
        timeout,
        extra,
        results_dir=results_path,
        junit=junit,
        json_=json_,
    )
    CONSOLE.print(f"[cyan]Running:[/] {' '.join(cmd)} (cwd={root_dir})")

    # Debug: Show API domain and secret store status
    api_domain = os.environ.get("CODEMIE_API_DOMAIN", "NOT SET")
    CONSOLE.print(f"[dim]API Domain: {api_domain}[/dim]")

    secret_store = os.environ.get("HARNESS_SECRET_STORE")
    if secret_store:
        CONSOLE.print(
            f"[dim]Secret store: {secret_store} "
            f"(region={os.environ.get('AWS_PS_REGION', 'NOT SET')}, "
            f"prefix={os.environ.get('AWS_PS_PATH_PREFIX', 'NOT SET')})[/dim]"
        )
    else:
        CONSOLE.print("[dim]Secret store: not enabled[/dim]")

    # Explicitly pass environment variables to subprocess
    # This ensures credentials from config are available to pytest
    raise SystemExit(subprocess.call(cmd, cwd=root_dir, env=os.environ.copy()))
