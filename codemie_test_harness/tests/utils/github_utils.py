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

import base64
import logging
import time
from typing import Optional

import requests

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.github_seed import (
    SEED_BODY,
    SEED_FILE_CONTENT,
    SEED_FILE_NAME,
    SEED_TITLE,
    SeedFile,
    SeedIssue,
    find_seed_issue,
    parse_owner_repo,
)

logger = logging.getLogger(__name__)

API_URL = "https://api.github.com"
SEED_SEARCH_TIMEOUT_SECONDS = 60
SEED_SEARCH_POLL_SECONDS = 3


class GitHubUtils:
    """Utility class for interacting with the GitHub REST API."""

    def __init__(self):
        """Initialize GitHub utilities with credentials from CredentialsManager."""
        self.token = CredentialsManager.get_parameter("GITHUB_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }
        self.owner, self.repo = parse_owner_repo(
            CredentialsManager.get_parameter("GITHUB_PROJECT")
        )

    def _request(self, method: str, path: str, **kwargs):
        response = requests.request(
            method,
            f"{API_URL}{path}",
            headers=self.headers,
            timeout=60,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def list_issues(self) -> list[dict]:
        response = self._request(
            "GET",
            f"/repos/{self.owner}/{self.repo}/issues",
            params={"state": "all", "per_page": 100},
        )
        return response.json()

    def create_issue(self, title: str, body: str) -> dict:
        return self._request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/issues",
            json={"title": title, "body": body},
        ).json()

    def find_seed_issue(self) -> Optional[dict]:
        return find_seed_issue(self.list_issues())

    def _create_seed_issue(self) -> dict:
        issue = self.create_issue(SEED_TITLE, SEED_BODY)
        logger.info(
            f"Created GitHub seed issue #{issue['number']} in {self.owner}/{self.repo}"
        )
        # A just-created issue may not appear in the issues listing immediately.
        deadline = time.monotonic() + SEED_SEARCH_TIMEOUT_SECONDS
        while self.find_seed_issue() is None:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"GitHub seed issue #{issue['number']} not listed after "
                    f"{SEED_SEARCH_TIMEOUT_SECONDS}s"
                )
            time.sleep(SEED_SEARCH_POLL_SECONDS)
        # Concurrent runs may each have created a seed; all settle on the oldest.
        settled = self.find_seed_issue()
        if settled["number"] != issue["number"]:
            logger.warning(
                f"Duplicate GitHub seed issue #{issue['number']} exists next to "
                f"#{settled['number']}; it can be closed"
            )
        return settled

    def ensure_seed_issue(self) -> SeedIssue:
        """Find or create the seed issue."""
        issue = self.find_seed_issue() or self._create_seed_issue()
        return SeedIssue(
            number=issue["number"],
            owner=self.owner,
            repo=self.repo,
            title=issue["title"],
            body=issue.get("body") or SEED_BODY,
            author=issue["user"]["login"],
            state=issue["state"],
            created_at=issue["created_at"],
            updated_at=issue["updated_at"],
            html_url=issue["html_url"],
            api_url=issue["url"],
        )

    def get_file(self, path: str) -> Optional[dict]:
        """Get a repo file's metadata/content from its default branch, or None if missing."""
        try:
            return self._request(
                "GET", f"/repos/{self.owner}/{self.repo}/contents/{path}"
            ).json()
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def create_file(self, path: str, content: str, message: str) -> dict:
        """Create a file on the repo's default branch via the Contents API."""
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
        return self._request(
            "PUT",
            f"/repos/{self.owner}/{self.repo}/contents/{path}",
            json={"message": message, "content": encoded_content},
        ).json()

    def ensure_seed_file(self) -> SeedFile:
        """Find or create the seed marker file at the repo root (default branch)."""
        existing = self.get_file(SEED_FILE_NAME)
        if existing is None:
            created = self.create_file(
                SEED_FILE_NAME,
                SEED_FILE_CONTENT,
                "Add codemie-test-harness seed file",
            )
            logger.info(
                f"Created GitHub seed file {SEED_FILE_NAME} in {self.owner}/{self.repo}"
            )
            file_meta = created["content"]
        else:
            file_meta = existing
        return SeedFile(
            name=file_meta["name"],
            path=file_meta["path"],
            owner=self.owner,
            repo=self.repo,
            sha=file_meta.get("sha", ""),
            html_url=file_meta.get("html_url", ""),
        )
