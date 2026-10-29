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

"""Seed data for Azure DevOps VCS tool tests: a persistent marker pull request.

Pure logic only (no HTTP) so it can be unit tested; AzureDevOpsUtils performs
the requests. The seed PR is created once in the configured Azure DevOps
repository and reused by every later run, so tests never depend on a
pre-existing PR such as the previously hardcoded PR #1.
"""

from dataclasses import asdict, dataclass
from typing import Optional

SEED_TITLE = "CodeMie Test Harness Seed PR"
SEED_SOURCE_BRANCH = "codemie-test-harness-seed"
SEED_TARGET_BRANCH = "main"
SEED_FILE_NAME = "SeedFile.md"
SEED_FILE_CONTENT = (
    "# CodeMie Test Harness Seed File\n\n"
    "Seed file used by codemie-test-harness Azure DevOps tests. "
    "Do not delete or edit.\n"
)
SEED_DESCRIPTION = (
    "Pull request used by codemie-test-harness Azure DevOps tests. "
    "Do not merge or close."
)

AZURE_DEVOPS_SEED_PULL_REQUEST = "azure_devops_seed_pull_request"


@dataclass(frozen=True)
class SeedPullRequest:
    pull_request_id: int
    repository: str
    project: str
    organization: str
    title: str = SEED_TITLE
    description: str = SEED_DESCRIPTION
    status: str = "active"
    source_branch: str = SEED_SOURCE_BRANCH
    target_branch: str = SEED_TARGET_BRANCH
    created_by: str = ""
    created_by_email: str = ""
    creation_date: str = ""
    url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedPullRequest":
        return cls(**data)


def find_seed_pull_request(
    pull_requests: list[dict], title: str = SEED_TITLE
) -> Optional[dict]:
    """The oldest PR whose title equals ``title`` exactly."""
    matches = [pr for pr in pull_requests if pr.get("title") == title]
    if not matches:
        return None
    return min(matches, key=lambda pr: pr["pullRequestId"])
