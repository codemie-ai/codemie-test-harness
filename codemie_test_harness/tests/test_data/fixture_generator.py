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

"""Runtime generation of oversized fixture files for large-file tests.

Generates files block-by-block so no test ever needs to commit or ship a
multi-hundred-megabyte binary fixture, and so the whole content is never held
in memory at once (no `f.write(b'x' * 105_000_000)`).
"""

from pathlib import Path

_CHUNK_LINE = (b"x" * 79 + b"\n") * 1024  # ~80KB of repeated, newline-delimited text


def generate_large_text_file(path: Path, size_mb: int = 105, chunk_mb: int = 1) -> Path:
    """Write more than ``size_mb`` MB of text to ``path`` in ``chunk_mb`` blocks.

    Writes happen in a loop of fixed-size chunks rather than building the
    full buffer in memory. ``path`` may be any writable location (e.g. a
    pytest ``tmp_path``); nothing here assumes a location relative to the
    repository's source tree.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    target_bytes = size_mb * 1024 * 1024
    chunk_bytes = chunk_mb * 1024 * 1024

    chunk = _CHUNK_LINE * (chunk_bytes // len(_CHUNK_LINE) + 1)
    chunk = chunk[:chunk_bytes]

    written = 0
    with path.open("wb") as fh:
        while written < target_bytes:
            fh.write(chunk)
            written += len(chunk)

    return path
