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

"""Test data for workflow icon file upload tests.

Icon files are written at test time into the test's own temporary directory, so no
committed image has to match a declared type: the server sniffs the bytes and rejects
a file whose content differs from its extension and declared MIME type.
"""

import base64
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest

from codemie_test_harness.tests.utils.constants import FILES_PATH

# Server limit on an uploaded workflow icon (WORKFLOW_ICON_MAX_BYTES = 512 * 1024)
MAX_ICON_BYTES = 512 * 1024

# An external icon URL is stored unchanged by the server
EXTERNAL_ICON_URL = "https://example.com/workflow-icon.png"
OTHER_EXTERNAL_ICON_URL = "https://example.com/other-workflow-icon.png"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MINIMAL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
    '<rect width="1" height="1" fill="#0a7"/></svg>'
)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def build_png_bytes() -> bytes:
    """A real 1x1 RGB PNG."""
    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixel_row = b"\x00\xff\x00\x00"
    return (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(pixel_row))
        + _png_chunk(b"IEND", b"")
    )


def write_png_icon(directory: Path, name: str = "icon.png") -> Path:
    path = directory / name
    path.write_bytes(build_png_bytes())
    return path


def write_jpeg_icon(directory: Path, name: str = "icon.jpg") -> Path:
    """A real JPEG, copied from the committed JPEG fixture."""
    path = directory / name
    path.write_bytes((FILES_PATH / "test.jpg").read_bytes())
    return path


def write_svg_icon(directory: Path, name: str = "icon.svg") -> Path:
    path = directory / name
    path.write_text(MINIMAL_SVG)
    return path


def write_text_file(directory: Path, name: str = "icon.txt") -> Path:
    path = directory / name
    path.write_text("not an image")
    return path


def write_oversized_png(
    directory: Path, name: str = "oversized.png", size: int = MAX_ICON_BYTES + 1
) -> Path:
    """A PNG-typed file of ``size`` bytes; one byte above the icon size limit by default."""
    path = directory / name
    path.write_bytes(PNG_SIGNATURE + b"\x00" * (size - len(PNG_SIGNATURE)))
    return path


def write_jpeg_bytes_named_png(directory: Path, name: str = "mismatch.png") -> Path:
    """JPEG content under a .png name: the declared type does not match the bytes."""
    path = directory / name
    path.write_bytes((FILES_PATH / "test.jpg").read_bytes())
    return path


def write_empty_png(directory: Path, name: str = "empty.png") -> Path:
    path = directory / name
    path.write_bytes(b"")
    return path


def decode_file_url(file_url: str) -> str:
    """Readable form of an encoded file URL: '<len>~<mime><len>~<owner><len>~<name>'."""
    return base64.b64decode(file_url).decode("utf-8")


def stored_icon_name_regexp(extension: str) -> str:
    """Regexp of the generated stored name of an uploaded icon inside its decoded file URL."""
    return rf"workflow-icons/[0-9a-f]{{32}}\.{extension}$"


@dataclass
class ValidIconCase:
    """TC-001: an icon file the server accepts and the extension it is stored under."""

    write: Callable[[Path], Path]
    stored_extension: str


VALID_ICON_PARAMS = [
    pytest.param(ValidIconCase(write_png_icon, "png"), id="png"),
    pytest.param(ValidIconCase(write_jpeg_icon, "jpg"), id="jpeg"),
    pytest.param(ValidIconCase(write_svg_icon, "svg"), id="svg"),
]


@dataclass
class InvalidIconCase:
    """TC-002: an icon file the server rejects with 400 and the error it reports."""

    write: Callable[[Path], Path]
    expected_message: str
    expected_details: str


INVALID_ICON_PARAMS = [
    pytest.param(
        InvalidIconCase(
            write_text_file,
            "Unsupported icon file type",
            "File extension .txt does not match the declared type text/plain",
        ),
        id="disallowed_type",
    ),
    pytest.param(
        InvalidIconCase(
            write_oversized_png,
            "Unsupported icon file size",
            "Maximum icon size is 0.5 MB",
        ),
        id="above_512_kib",
    ),
    pytest.param(
        InvalidIconCase(
            write_jpeg_bytes_named_png,
            "Unsupported icon file type",
            "File content does not match the declared type image/png",
        ),
        id="content_not_matching_declared_type",
    ),
    pytest.param(
        InvalidIconCase(
            write_empty_png,
            "Invalid icon file",
            "The file is empty",
        ),
        id="empty_file",
    ),
]
