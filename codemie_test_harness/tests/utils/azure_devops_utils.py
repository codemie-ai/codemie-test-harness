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

from codemie_test_harness.tests.utils.azure_devops_seed import (
    SEED_DESCRIPTION,
    SEED_FILE_CONTENT,
    SEED_FILE_NAME,
    SEED_SOURCE_BRANCH,
    SEED_TARGET_BRANCH,
    SEED_TITLE,
    SeedPullRequest,
    find_seed_pull_request,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

logger = logging.getLogger(__name__)

API_VERSION = "7.1"
SEED_SEARCH_TIMEOUT_SECONDS = 60
SEED_SEARCH_POLL_SECONDS = 3


class AzureDevOpsUtils:
    """Utility class for interacting with the Azure DevOps Git REST API."""

    def __init__(self):
        """Initialize Azure DevOps utilities with credentials from CredentialsManager."""
        self.organization = CredentialsManager.get_parameter(
            "AZURE_DEVOPS_ORGANIZATION_NAME"
        )
        self.project = CredentialsManager.get_parameter("AZURE_DEVOPS_PROJECT_NAME")
        # The seed repository is the project's default repo, named after the project
        # itself — the same assumption the existing azuredevops_git tool prompt makes.
        self.repo = self.project
        token = CredentialsManager.get_parameter("AZURE_DEVOPS_TOKEN")
        auth_header = f"Basic {base64.b64encode(f':{token}'.encode()).decode()}"
        self.headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
        }
        self.base_url = (
            f"{CredentialsManager.get_parameter('AZURE_DEVOPS_URL')}/{self.organization}/{self.project}/_apis/git/"
            f"repositories/{self.repo}"
        )

    def _request(self, method: str, path: str, **kwargs):
        params = {**kwargs.pop("params", {}), "api-version": API_VERSION}
        response = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=self.headers,
            params=params,
            timeout=60,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def _get_branch_commit_id(self, branch: str) -> Optional[str]:
        response = self._request("GET", "/refs", params={"filter": f"heads/{branch}"})
        for ref in response.json().get("value", []):
            if ref["name"] == f"refs/heads/{branch}":
                return ref["objectId"]
        return None

    def list_pull_requests(self) -> list[dict]:
        response = self._request(
            "GET",
            "/pullrequests",
            params={"searchCriteria.status": "all", "$top": 100},
        )
        return response.json().get("value", [])

    def find_seed_pull_request(self) -> Optional[dict]:
        return find_seed_pull_request(self.list_pull_requests())

    def _ensure_seed_branch_and_file(self) -> None:
        """Create the seed branch (from the target branch) and its file if missing."""
        if self._get_branch_commit_id(SEED_SOURCE_BRANCH):
            return
        base_commit_id = self._get_branch_commit_id(SEED_TARGET_BRANCH)
        if not base_commit_id:
            raise RuntimeError(
                f"Azure DevOps target branch '{SEED_TARGET_BRANCH}' not found in "
                f"repository '{self.repo}'"
            )
        self._request(
            "POST",
            "/pushes",
            json={
                "refUpdates": [
                    {
                        "name": f"refs/heads/{SEED_SOURCE_BRANCH}",
                        "oldObjectId": base_commit_id,
                    }
                ],
                "commits": [
                    {
                        "comment": "Add codemie-test-harness seed file",
                        "changes": [
                            {
                                "changeType": "add",
                                "item": {"path": f"/{SEED_FILE_NAME}"},
                                "newContent": {
                                    "content": SEED_FILE_CONTENT,
                                    "contentType": "rawtext",
                                },
                            }
                        ],
                    }
                ],
            },
        )

    def _create_seed_pull_request(self) -> dict:
        self._ensure_seed_branch_and_file()
        pr = self._request(
            "POST",
            "/pullrequests",
            json={
                "sourceRefName": f"refs/heads/{SEED_SOURCE_BRANCH}",
                "targetRefName": f"refs/heads/{SEED_TARGET_BRANCH}",
                "title": SEED_TITLE,
                "description": SEED_DESCRIPTION,
            },
        ).json()
        logger.info(
            f"Created Azure DevOps seed PR #{pr['pullRequestId']} in "
            f"{self.organization}/{self.project}/{self.repo}"
        )
        # A just-created PR may not be immediately searchable.
        deadline = time.monotonic() + SEED_SEARCH_TIMEOUT_SECONDS
        while self.find_seed_pull_request() is None:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Azure DevOps seed PR #{pr['pullRequestId']} not searchable "
                    f"after {SEED_SEARCH_TIMEOUT_SECONDS}s"
                )
            time.sleep(SEED_SEARCH_POLL_SECONDS)
        return pr

    def ensure_seed_pull_request(self) -> SeedPullRequest:
        """Find or create the seed pull request."""
        pr = self.find_seed_pull_request() or self._create_seed_pull_request()
        created_by = pr.get("createdBy") or {}
        return SeedPullRequest(
            pull_request_id=pr["pullRequestId"],
            repository=self.repo,
            project=self.project,
            organization=self.organization,
            title=pr["title"],
            description=pr.get("description", ""),
            status=pr["status"],
            source_branch=pr["sourceRefName"].removeprefix("refs/heads/"),
            target_branch=pr["targetRefName"].removeprefix("refs/heads/"),
            created_by=created_by.get("displayName", ""),
            created_by_email=created_by.get("uniqueName", ""),
            creation_date=pr.get("creationDate", ""),
            url=pr.get("url", ""),
        )
