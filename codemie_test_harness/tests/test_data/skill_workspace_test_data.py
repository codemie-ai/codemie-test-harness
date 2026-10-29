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

"""Test data for skill bundle files in the conversation workspace.

A skill bundle is a set of companion files stored with the skill. When a conversation starts, the
files appear in the conversation's workspace under ``skills/<skill-name>-<first 8 chars of skill id>/``.
Limits quoted here are the documented defaults; tests that depend on them read the values the
environment actually applies from ``GET /v1/skills/config``.
"""

from dataclasses import dataclass

from codemie_sdk.models.skill import SkillCompanionFilePayload

from codemie_test_harness.tests.utils.base_utils import get_random_name

SKILL_FOLDER_PREFIX = "skills/"
SKILL_FOLDER_ID_LENGTH = 8

# Longest bundle path the upload accepts: 1024 (workspace path) - len("skills/") - 64 (skill name)
# - len("-<id8>") - len("/"). A longer path is refused at upload with the message below.
MAX_BUNDLE_PATH_LENGTH = 943
INVALID_COMPANION_PATH_MESSAGE = "Invalid companion file path"
PATH_TOO_LONG_DETAILS = f"path is too long (max {MAX_BUNDLE_PATH_LENGTH} characters)"

RESERVED_PATH_ERROR = "file_path is reserved"

# The reply of the chat is irrelevant: the files are placed before the assistant answers.
SEED_PROMPT = "Reply with the single word OK. Do not call any tool."

SHARED_BUNDLE_PATH = "shared/data.txt"

SCRIPT_BUNDLE_PATH = "scripts/run.py"
SCRIPT_DATA_PATH = "scripts/data.txt"

# Builds its path from __file__ because a bundle script runs from the skill's folder, not the bundle root.
BUNDLE_SCRIPT_TEMPLATE = """\
import os

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "data.txt")) as handle:
    print("RESULT-__MARKER__-" + handle.read().strip())
"""


@dataclass
class BundleFile:
    """One file of a skill bundle: its path inside the bundle and its text content."""

    path: str
    content: str

    def payload(self) -> SkillCompanionFilePayload:
        return SkillCompanionFilePayload(path=self.path, content=self.content)


def bundle_file(path: str, content: str | None = None) -> BundleFile:
    return BundleFile(path, content or f"content of {path} {get_random_name()}")


def two_file_bundle() -> list[BundleFile]:
    return [bundle_file("scripts/hello.py"), bundle_file("docs/guide.md")]


def three_file_bundle() -> list[BundleFile]:
    return [
        bundle_file("docs/first.md"),
        bundle_file("docs/second.md"),
        bundle_file("docs/third.md"),
    ]


def single_file_bundle(path: str = "docs/note.md") -> list[BundleFile]:
    return [bundle_file(path)]


def script_bundle(marker: str) -> list[BundleFile]:
    """A script that prints ``RESULT-<marker>-<data>`` where the data comes from a file next to it."""
    return [
        BundleFile(
            SCRIPT_BUNDLE_PATH, BUNDLE_SCRIPT_TEMPLATE.replace("__MARKER__", marker)
        ),
        BundleFile(SCRIPT_DATA_PATH, f"DATA-{marker}"),
    ]


def numbered_bundle(count: int) -> list[BundleFile]:
    """``count`` tiny files whose names sort in numeric order (``files/f0000.txt`` ...)."""
    return [
        bundle_file(f"files/f{index:04d}.txt", f"f{index:04d}")
        for index in range(count)
    ]


def bundle_with_one_oversized_file(max_file_size_bytes: int) -> list[BundleFile]:
    """Three files in path order; the middle one is one byte over the per-file ceiling."""
    return [
        bundle_file("a_small.txt"),
        BundleFile("b_oversized.txt", "x" * (max_file_size_bytes + 1)),
        bundle_file("c_small.txt"),
    ]


def bundle_over_file_count_ceiling(limits) -> tuple[list[BundleFile], list[BundleFile]]:
    """One file more than the count ceiling; files are taken in path order, so the last one is left out."""
    uploaded = numbered_bundle(limits.bundle_seed_max_file_count + 1)
    return uploaded, uploaded[:-1]


def bundle_over_file_size_ceiling(limits) -> tuple[list[BundleFile], list[BundleFile]]:
    """One file one byte over the per-file ceiling; only that file is left out."""
    uploaded = bundle_with_one_oversized_file(limits.bundle_seed_max_file_size_bytes)
    return uploaded, [uploaded[0], uploaded[2]]


def path_of_length(length: int) -> str:
    """A relative path of exactly ``length`` characters made of folders of 50 characters each."""
    folder = "d" * 49 + "/"
    folders_count = (length - 1) // len(folder)
    prefix = folder * folders_count
    return prefix + "f" * (length - len(prefix))


@dataclass
class ReservedPath:
    """A workspace path owned by the script runtime, in one of the spellings that must be refused."""

    path: str
    spelling: str


RESERVED_PATHS = [
    ReservedPath(".codemie_bridge/x", "bridge-folder"),
    ReservedPath(".CODEMIE_BRIDGE/x", "bridge-folder-uppercase"),
    ReservedPath("codemie_runtime_sdk.py", "runtime-sdk-file"),
    ReservedPath("CODEMIE_RUNTIME_SDK.PY", "runtime-sdk-file-uppercase"),
    ReservedPath("．codemie_bridge/x", "bridge-folder-fullwidth-dot"),
]

# Same names one level down are ordinary files and folders.
NESTED_RESERVED_NAMES = [
    "skills/x/.codemie_bridge/f",
    "sub/codemie_runtime_sdk.py",
]
ROOT_RESERVED_READ_PATH = ".codemie_bridge/f"
