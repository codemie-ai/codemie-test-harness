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

"""Helpers for tests that run workspace scripts from workflows and assistants.

Covers a script run from a workflow step with run-start files, and scripts that
call platform tools.
"""

import base64
import json
import re
import tempfile
from pathlib import Path
from typing import Optional

import requests

from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.yaml_utils import StateModel, ToolModel

# A script step provisions a sandbox before the script itself runs, so even a one-tool-call
# script's workflow execution routinely takes longer than the shared ``DEFAULT_TIMEOUT``
# (60s on a shared stand). Observed completion times on that stand climbed across repeated
# runs (130s, 189s, 249s) rather than settling, so no small constant is reliably safe; this
# reuses the project's own existing "generous" timeout (``cli/constants.py``'s
# ``DEFAULT_TIMEOUT = 300``) instead of one more guessed number. If 300s still isn't enough,
# that is itself a signal to investigate stand-side contention (see the "Code executor is at
# capacity" error), not to raise this constant again. Pass this as `timeout=` to
# `workflow_utils.create_workflow_execution` for script-step executions instead of raising
# the timeout for every workflow test.
SCRIPT_WORKFLOW_EXECUTION_TIMEOUT = 300


def unique_script_name(prefix: str = "script") -> str:
    """Return a unique ``.py`` file name so parallel runs never share a path."""
    return f"{prefix}_{get_random_name()[-12:]}.py"


def random_marker() -> str:
    """Return a short unique token to find one run's output among others."""
    return get_random_name()[-10:]


def upload_text_file(client, file_name: str, content: str) -> str:
    """Upload ``content`` as ``file_name`` and return the file reference (``file_url``)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / file_name
        path.write_text(content)
        return client.files.bulk_upload([path]).files[0].file_url


def build_file_token(mime_type: str, owner: str, name: str) -> str:
    """Build a file reference the way the backend encodes it.

    The reference is base64 of three length-prefixed fields: ``<len>~<mime><len>~<owner><len>~<name>``.
    """
    fields = "".join(f"{len(part)}~{part}" for part in (mime_type, owner, name))
    return base64.b64encode(fields.encode()).decode()


def parse_file_token(file_url: str) -> tuple[str, str, str]:
    """Return ``(mime_type, owner, name)`` of a file reference returned by an upload."""
    raw = base64.b64decode(file_url).decode()
    parts = []
    position = 0
    for _ in range(3):
        match = re.compile(r"(\d+)~").match(raw, position)
        length = int(match.group(1))
        start = match.end()
        parts.append(raw[start : start + length])
        position = start + length
    return parts[0], parts[1], parts[2]


def parse_script_result(step_output: str) -> dict:
    """Parse the whole JSON answer of the workspace script tool (message, output, workspace_files)."""
    return json.loads(step_output)


def extract_marked_json(script_stdout: str, marker: str) -> dict:
    """Return the JSON a script printed after ``<marker>=`` on one line."""
    match = re.search(rf"{re.escape(marker)}=(\{{.*\}})", script_stdout)
    if match is None:
        raise AssertionError(
            f"Marker '{marker}=' not found in script output: {script_stdout!r}"
        )
    return json.loads(match.group(1))


def allow_tools(*names: str) -> list[ToolModel]:
    """``tool_access`` that lets a script call the tools ``names`` with the running user's own integrations."""
    return [ToolModel(name=name) for name in names]


def tool_state(
    state_id: str,
    tool: str,
    tool_args: Optional[dict] = None,
    next_state: str = "end",
    output_key: Optional[str] = None,
    tool_access: Optional[list[ToolModel]] = None,
) -> tuple[ToolModel, StateModel]:
    """Build a workflow tool and the bare tool state that runs it (state id equals tool id).

    With ``output_key`` the step output is stored in the context for the following steps. ``tool_access`` lists the
    tools a script of the step may call (see ``allow_tools``); a script step without it can call no tool.
    """
    next_config: dict = {"state_id": next_state}
    if output_key:
        next_config.update({"output_key": output_key, "store_in_context": True})
    return (
        ToolModel(
            id=state_id, tool=tool, tool_args=tool_args or {}, tool_access=tool_access
        ),
        StateModel(id=state_id, tool_id=state_id, next=next_config),
    )


def start_run_expecting_rejection(
    workflow_utils, workflow_id: str, file_names: list[str]
) -> requests.Response:
    """Start a run that the API must refuse and return the HTTP response of the refusal."""
    try:
        workflow_utils.start_run(workflow_id, file_names=file_names)
    except requests.HTTPError as error:
        return error.response
    raise AssertionError("The run was accepted but the request must be rejected")
