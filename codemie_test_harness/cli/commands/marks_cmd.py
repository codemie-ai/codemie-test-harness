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

"""CLI command for listing pytest marks."""

from __future__ import annotations
import click
from ..marks_utils import discover_all_marks, print_marks_list
from ..constants import CONSOLE


@click.command(name="marks")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information in table format with line numbers",
)
@click.option(
    "--count", "-c", is_flag=True, help="Show only the count of available marks"
)
def marks_cmd(verbose: bool, count: bool):
    """List all available pytest marks in the test suite.

    Examples:
        codemie-test-harness marks                    # List all marks
        codemie-test-harness marks --verbose          # List marks with file details in table format
        codemie-test-harness marks --count            # Show only count
    """
    try:
        if count:
            # For count mode, we don't need detailed information
            marks_info = discover_all_marks(include_details=False)
            CONSOLE.print(f"[green]{len(marks_info)}[/green] pytest marks available")
            return

        # Let print_marks_list handle the discovery with appropriate details
        print_marks_list(marks_info=None, show_files=verbose)

    except Exception as e:
        CONSOLE.print(f"[red]Error discovering marks: {str(e)}[/red]")
        raise click.ClickException("Failed to discover pytest marks")
