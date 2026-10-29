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

from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

import pytest

from codemie_test_harness.tests.enums.tools import FileManagementTool
from codemie_test_harness.tests.utils.base_utils import get_random_name

COMMAND_LINE_UNIQUE_DIR = get_random_name()
COMMAND_LINE_MARKER_FILE = f"{get_random_name()}.txt"

file_management_tools_test_data = [
    # UNFIXABLE WITHOUT INFRA: one tool call per workflow state, so this entry can't
    # create a directory first. Left pinned to "." until a shared seed fixture exists.
    pytest.param(
        FileManagementTool.LIST_DIRECTORY,
        {"dir_path": "."},
        """
        etc
        tmp
        opt
        srv
        sys
        proc
        sbin
        root
        media
        run
        lib
        boot
        lib64
        var
        mnt
        home
        bin
        dev
        usr
        app
        venv
        secrets
        codemie-ui
        """,
        marks=pytest.mark.skipif(
            EnvironmentResolver.is_localhost(),
            reason="Skipping this test on local environment",
        ),
    ),
    (
        FileManagementTool.WRITE_FILE,
        {"file_path": "/tmp/env.properties", "text": "env=preview"},
        "File written successfully to /tmp/env.properties",
    ),
    pytest.param(
        FileManagementTool.RUN_COMMAND_LINE,
        {
            "command": (
                f"mkdir -p /tmp/{COMMAND_LINE_UNIQUE_DIR} "
                f"&& touch /tmp/{COMMAND_LINE_UNIQUE_DIR}/{COMMAND_LINE_MARKER_FILE} "
                f"&& ls /tmp/{COMMAND_LINE_UNIQUE_DIR}"
            )
        },
        f"""
         ('{COMMAND_LINE_MARKER_FILE}
         ', '', 0) """,
        marks=pytest.mark.skipif(
            EnvironmentResolver.is_localhost(),
            reason="Skipping this test on local environment",
        ),
    ),
]
