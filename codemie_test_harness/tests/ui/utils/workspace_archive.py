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

"""Reader for the archive saved by the workspace popup's "Download all" action."""

import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import Download


@dataclass
class WorkspaceArchive:
    """A downloaded workspace archive: the name the browser saved it under and its file entries."""

    filename: str
    entries: dict[str, bytes] = field(default_factory=dict)

    @property
    def entry_names(self) -> list[str]:
        """Names of the file entries (directory entries are not listed)."""
        return list(self.entries)


def read_workspace_archive(download: Download) -> WorkspaceArchive:
    """Open the zip behind a browser download and read every file entry into memory."""
    with zipfile.ZipFile(Path(download.path())) as archive:
        entries = {
            info.filename: archive.read(info)
            for info in archive.infolist()
            if not info.is_dir()
        }
    return WorkspaceArchive(filename=download.suggested_filename, entries=entries)
