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

"""Seed data for GitHub VCS tool tests: a persistent marker issue.

Pure logic only (no HTTP) so it can be unit tested; GitHubUtils performs the
requests. The seed issue is created once in the configured GitHub repository
and reused by every later run, so tests never depend on a pre-existing issue
such as the previously hardcoded issue #4.
"""

import re
from dataclasses import asdict, dataclass
from typing import Optional

SEED_TITLE = "CodeMie Test Harness Seed Issue"
SEED_BODY = (
    "Seed issue used by codemie-test-harness GitHub tests. Do not delete or edit."
)

GITHUB_SEED_ISSUE = "github_seed_issue"

# Marker file committed to the repo's default branch; mirrors gitlab_seed.py's SeedFile.java.
SEED_FILE_NAME = "SeedFile.java"
SEED_FILE_CONTENT = (
    "public class SeedFile {\n"
    "    // Seed file used by codemie-test-harness GitHub tests. Do not delete or edit.\n"
    "    public static void main(String[] args) {\n"
    "    }\n"
    "}\n"
)

GITHUB_SEED_FILE = "github_seed_file"

_PROJECT_URL_RE = re.compile(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?/?$")


def parse_owner_repo(project_url: str) -> tuple[str, str]:
    """``GITHUB_PROJECT`` is the repo link, e.g. 'https://github.com/owner/repo'."""
    match = _PROJECT_URL_RE.search(project_url or "")
    if not match:
        raise ValueError(
            f"GITHUB_PROJECT '{project_url}' is not a recognizable "
            f"'https://github.com/<owner>/<repo>' URL"
        )
    return match.group(1), match.group(2)


@dataclass(frozen=True)
class SeedIssue:
    number: int
    owner: str
    repo: str
    title: str = SEED_TITLE
    body: str = SEED_BODY
    author: str = ""
    state: str = "open"
    created_at: str = ""
    updated_at: str = ""
    html_url: str = ""
    api_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedIssue":
        return cls(**data)


def find_seed_issue(issues: list[dict], title: str = SEED_TITLE) -> Optional[dict]:
    """The oldest issue whose title equals ``title`` exactly."""
    matches = [issue for issue in issues if issue.get("title") == title]
    if not matches:
        return None
    return min(matches, key=lambda issue: issue["number"])


@dataclass(frozen=True)
class SeedFile:
    name: str
    path: str
    owner: str
    repo: str
    content: str = SEED_FILE_CONTENT
    sha: str = ""
    html_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedFile":
        return cls(**data)
