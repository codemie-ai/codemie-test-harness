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

"""Seed data for GitLab VCS tool tests: a persistent marker merge request.

Pure logic only (no HTTP) so it can be unit tested; GitBudUtils performs the
requests. The seed MR is created once in the configured GitLab project and
reused by every later run, so tests never depend on a pre-existing MR such
as the previously hardcoded MR !7014.
"""

from dataclasses import asdict, dataclass
from typing import Optional

SEED_TITLE = "CodeMie Test Harness Seed MR"
SEED_SOURCE_BRANCH = "codemie-test-harness-seed"
SEED_TARGET_BRANCH = "main"
SEED_FILE_NAME = "SeedFile.java"
SEED_FILE_CONTENT = (
    "public class SeedFile {\n"
    "    // Seed file used by codemie-test-harness GitLab tests. Do not delete or edit.\n"
    "    public static void main(String[] args) {\n"
    "    }\n"
    "}\n"
)
SEED_DESCRIPTION = (
    "Merge request used by codemie-test-harness GitLab tests. Do not merge or close."
)

GITLAB_SEED_MERGE_REQUEST = "gitlab_seed_merge_request"

# Persistent marker branches for the LIST_BRANCHES_IN_REPO / SET_ACTIVE_BRANCH tests.
SEED_BRANCH_NAMES = (
    "main-seed-branch-1",
    "main-seed-branch-2",
    "main-seed-branch-3",
    "main-seed-branch-4",
)

GITLAB_SEED_BRANCHES = "gitlab_seed_branches"


@dataclass(frozen=True)
class SeedBranches:
    """The persistent marker branches, including the real target branch."""

    names: list

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedBranches":
        return cls(**data)


@dataclass(frozen=True)
class SeedMergeRequest:
    iid: int
    project_id: int
    title: str = SEED_TITLE
    description: str = SEED_DESCRIPTION
    source_branch: str = SEED_SOURCE_BRANCH
    target_branch: str = SEED_TARGET_BRANCH
    state: str = "opened"
    author: str = ""
    author_web_url: str = ""
    web_url: str = ""
    created_at: str = ""
    updated_at: str = ""
    sha: str = ""
    base_sha: str = ""
    start_sha: str = ""
    head_sha: str = ""
    file_path: str = SEED_FILE_NAME

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedMergeRequest":
        return cls(**data)


def find_seed_merge_request(
    merge_requests: list[dict], title: str = SEED_TITLE
) -> Optional[dict]:
    """The oldest MR whose title equals ``title`` exactly."""
    matches = [mr for mr in merge_requests if mr.get("title") == title]
    if not matches:
        return None
    return min(matches, key=lambda mr: mr["iid"])
