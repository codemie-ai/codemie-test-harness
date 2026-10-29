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

import click


def add_result_options(func):
    """Add --results-dir, --no-junit-xml and --no-json (shared by root and `run`)."""
    for option in reversed(
        (
            click.option(
                "--results-dir",
                help="Folder for junit.xml and results.json "
                "(default: ./codemie-test-reports)",
            ),
            click.option("--no-junit-xml", is_flag=True, help="Do not write junit.xml"),
            click.option("--no-json", is_flag=True, help="Do not write results.json"),
        )
    ):
        func = option(func)
    return func
