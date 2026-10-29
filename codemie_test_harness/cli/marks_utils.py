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

"""Utilities for handling pytest marks in the test harness."""

import re
import ast
from pathlib import Path
from typing import Set, List, Dict
from .constants import CONSOLE
from rich.table import Table

try:
    from importlib.resources import files as pkg_files
except Exception:
    pkg_files = None


def extract_marks_from_file(
    file_path: Path, include_lines: bool = False
) -> Set[str] | Dict[str, List[int]]:
    """Extract pytest marks from a Python test file.

    Args:
        file_path: Path to the Python file to analyze
        include_lines: If True, return dict with mark names and line numbers

    Returns:
        Set of mark names found in the file, or dict mapping marks to line numbers
    """
    if include_lines:
        marks_with_lines = {}
    else:
        marks = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse the file to AST for reliable extraction
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        mark_name = _extract_mark_from_decorator(decorator)
                        if mark_name:
                            if include_lines:
                                if mark_name not in marks_with_lines:
                                    marks_with_lines[mark_name] = []
                                marks_with_lines[mark_name].append(decorator.lineno)
                            else:
                                marks.add(mark_name)
        except SyntaxError:
            # If AST parsing fails, fall back to regex
            pass

        # Additional regex-based extraction for edge cases
        if include_lines:
            regex_marks_with_lines = _extract_marks_with_regex_and_lines(content)
            for mark, lines in regex_marks_with_lines.items():
                if mark not in marks_with_lines:
                    marks_with_lines[mark] = []
                marks_with_lines[mark].extend(lines)
        else:
            regex_marks = _extract_marks_with_regex(content)
            marks.update(regex_marks)

    except (IOError, UnicodeDecodeError):
        # Skip files that can't be read
        pass

    return marks_with_lines if include_lines else marks


def _extract_mark_from_decorator(decorator) -> str | None:
    """Extract mark name from AST decorator node."""
    mark_name = None

    if isinstance(decorator, ast.Attribute):
        # @pytest.mark.some_mark
        if (
            isinstance(decorator.value, ast.Attribute)
            and isinstance(decorator.value.value, ast.Name)
            and decorator.value.value.id == "pytest"
            and decorator.value.attr == "mark"
        ):
            mark_name = decorator.attr
    elif isinstance(decorator, ast.Call):
        # @pytest.mark.some_mark(...) with arguments
        if (
            isinstance(decorator.func, ast.Attribute)
            and isinstance(decorator.func.value, ast.Attribute)
            and isinstance(decorator.func.value.value, ast.Name)
            and decorator.func.value.value.id == "pytest"
            and decorator.func.value.attr == "mark"
        ):
            mark_name = decorator.func.attr

    # Filter out pytest built-in decorators that aren't marks
    if mark_name in {
        "parametrize",
        "fixture",
        "skip",
        "skipif",
        "xfail",
        "usefixtures",
        "testcase",
        "todo",
    }:
        return None

    return mark_name


def _extract_marks_with_regex(content: str) -> Set[str]:
    """Extract marks using regex as fallback."""
    marks = set()

    # Pattern to match pytest.mark.mark_name (with or without leading @)
    pattern = r"pytest\.mark\.(\w+)"
    matches = re.findall(pattern, content)

    for match in matches:
        # Filter out pytest built-in decorators that aren't marks
        if match not in {
            "parametrize",
            "fixture",
            "skip",
            "skipif",
            "xfail",
            "usefixtures",
            "todo",
        }:
            marks.add(match)

    return marks


def _extract_marks_with_regex_and_lines(content: str) -> Dict[str, List[int]]:
    """Extract marks with line numbers using regex as fallback."""
    marks_with_lines = {}
    lines = content.split("\n")

    # Pattern to match pytest.mark.mark_name (with or without leading @)
    pattern = r"pytest\.mark\.(\w+)"

    for line_num, line in enumerate(lines, 1):
        matches = re.findall(pattern, line)
        for match in matches:
            # Filter out pytest built-in decorators that aren't marks
            if match not in {
                "parametrize",
                "fixture",
                "skip",
                "skipif",
                "xfail",
                "usefixtures",
                "todo",
            }:
                if match not in marks_with_lines:
                    marks_with_lines[match] = []
                marks_with_lines[match].append(line_num)

    return marks_with_lines


def _resolve_tests_path() -> str:
    """Resolve tests path for mark discovery.

    Returns:
        Path to tests directory
    """
    # 1) Use importlib.resources to locate installed package "tests"
    if pkg_files is not None:
        try:
            # Try to locate codemie_test_harness.tests package
            tests_dir = Path(str(pkg_files("codemie_test_harness.tests")))
            return str(tests_dir)
        except Exception:
            pass

    # 2) Fallback to repo layout when running from source
    # marks_utils.py -> cli -> codemie_test_harness -> <repo_root>
    codemie_test_harness_root = (
        Path(__file__).resolve().parents[1]
    )  # codemie_test_harness directory
    tests_path = str(codemie_test_harness_root / "tests")
    return tests_path


def discover_all_marks(
    include_details: bool = False,
) -> Dict[str, List[str]] | Dict[str, List[Dict]]:
    """Discover all pytest marks used in the test suite.

    Args:
        include_details: If True, return detailed info with line numbers

    Returns:
        Dictionary with mark names as keys and list of files (or detailed info) as values
    """
    tests_path = _resolve_tests_path()
    tests_dir = Path(tests_path)

    if not tests_dir.exists():
        return {}

    marks_info = {}

    # Find all Python files in the tests directory (including test_data, conftest, etc.)
    for py_file in tests_dir.rglob("*.py"):
        rel_path = str(py_file.relative_to(tests_dir))

        if include_details:
            marks_with_lines = extract_marks_from_file(py_file, include_lines=True)

            for mark, lines in marks_with_lines.items():
                if mark not in marks_info:
                    marks_info[mark] = []

                for line in lines:
                    marks_info[mark].append({"file": rel_path, "line": line})
        else:
            marks = extract_marks_from_file(py_file)

            for mark in marks:
                if mark not in marks_info:
                    marks_info[mark] = []
                # Store relative path for readability
                if rel_path not in marks_info[mark]:
                    marks_info[mark].append(rel_path)

    return marks_info


def get_all_available_marks() -> List[str]:
    """Get sorted list of all available pytest marks."""
    marks_to_files = discover_all_marks()
    return sorted(marks_to_files.keys())


def is_valid_mark_expression(
    expression: str, available_marks: List[str]
) -> tuple[bool, List[str]]:
    """Validate if a mark expression contains only known marks.

    Args:
        expression: The pytest mark expression (e.g., "smoke and ui", "not integration")
        available_marks: List of all available marks

    Returns:
        Tuple of (is_valid, list_of_unknown_marks)
    """
    if not expression or not expression.strip():
        return True, []

    # Extract mark names from the expression
    # This regex finds word tokens that could be mark names
    potential_marks = re.findall(r"\b(\w+)\b", expression)

    # Filter out logical operators and known keywords
    logical_keywords = {"and", "or", "not", "true", "false"}
    unknown_marks = []

    available_marks_set = set(available_marks)

    for mark in potential_marks:
        if mark not in logical_keywords and mark not in available_marks_set:
            unknown_marks.append(mark)

    return len(unknown_marks) == 0, unknown_marks


def print_marks_list(marks_info=None, show_files: bool = False):
    """Print formatted list of available marks.

    Args:
        marks_info: Optional pre-computed marks dictionary
        show_files: Whether to show detailed information in table format
    """
    if marks_info is None:
        marks_info = discover_all_marks(include_details=show_files)

    if not marks_info:
        CONSOLE.print("[yellow]No pytest marks found in test files.[/yellow]")
        return

    if show_files:
        # Verbose mode - show table with detailed information
        CONSOLE.print(
            f"\n[bold cyan]Available pytest marks ({len(marks_info)} total):[/bold cyan]\n"
        )

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Mark", style="bold green", width=25)
        table.add_column("File", style="cyan", width=110)
        table.add_column("Usage Count", style="blue", justify="right", width=12)

        for mark in sorted(marks_info.keys()):
            details = marks_info[mark]

            # Group by file and count occurrences
            file_counts = {}
            for detail in details:
                file_path = detail["file"]
                if file_path not in file_counts:
                    file_counts[file_path] = []
                file_counts[file_path].append(detail["line"])

            # Add rows for each file
            first_row = True
            for file_path, lines in sorted(file_counts.items()):
                mark_display = (
                    mark if first_row else ""
                )  # Just the mark name, no @pytest.mark. prefix
                usage_count = str(len(lines))

                table.add_row(mark_display, file_path, usage_count)
                first_row = False

            # Add separator row if not the last mark
            if mark != sorted(marks_info.keys())[-1]:
                table.add_row("", "", "", style="dim")

        CONSOLE.print(table)
        CONSOLE.print(f"\n[dim]Total: {len(marks_info)} unique marks found[/dim]")
    else:
        # Simple mode - just list marks
        CONSOLE.print(
            f"\n[bold cyan]Available pytest marks ({len(marks_info)} total):[/bold cyan]\n"
        )

        for mark in sorted(marks_info.keys()):
            files = marks_info[mark]
            CONSOLE.print(f"[green]• {mark}[/green] [dim]({len(files)} files)[/dim]")

        CONSOLE.print(
            "\n[dim]Use --verbose to see detailed information in table format.[/dim]"
        )
