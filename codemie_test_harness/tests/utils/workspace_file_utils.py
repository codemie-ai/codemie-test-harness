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

"""Ways to read one workspace file, so a test can run the same check through each endpoint."""

from pathlib import PurePosixPath

from codemie_test_harness.tests.utils.workspace_script_utils import parse_file_token


def read_via_content(client, workspace_id: str, file_path: str) -> str:
    """Read the file through GET /v1/workspaces/{id}/files/content."""
    return client.workspaces.read_file(workspace_id, file_path).content


def read_via_download(client, workspace_id: str, file_path: str) -> str:
    """Read the file through GET /v1/workspaces/{id}/files/download."""
    return client.workspaces.download_file(workspace_id, file_path).decode(
        "utf-8", errors="replace"
    )


def workspace_path_of_upload(file_url: str) -> str:
    """Path under which a chat upload shows in the workspace: the base name of the stored file name."""
    return PurePosixPath(parse_file_token(file_url)[2]).name
