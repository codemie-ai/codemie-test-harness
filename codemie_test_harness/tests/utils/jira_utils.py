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

import logging
import time
from typing import Optional

import requests

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.jira_seed import (
    CUSTOM_FIELD_VALUES,
    SEED_DESCRIPTION,
    SEED_SUMMARY,
    CustomField,
    SeedIssue,
    build_seed_jql,
    find_seed_issue_key,
    is_writable,
    select_custom_fields,
)

logger = logging.getLogger(__name__)


# v2 accepts plain-text descriptions and custom field values on Server and Cloud,
# while Cloud v3 requires Atlassian Document Format.
WRITE_API = "/rest/api/2"
SEED_SEARCH_TIMEOUT_SECONDS = 60
SEED_SEARCH_POLL_SECONDS = 3


class JiraUtils:
    """Utility class for interacting with Jira API."""

    def __init__(self, is_cloud: bool = False):
        """
        Initialize Jira utilities with credentials from CredentialsManager.

        Args:
            is_cloud: Whether to use Jira Cloud or Jira Server credentials
        """
        self.is_cloud = is_cloud

        if is_cloud:
            self.jira_url = CredentialsManager.get_parameter("JIRA_CLOUD_URL")
            self.token = CredentialsManager.get_parameter("JIRA_CLOUD_TOKEN")
            self.email = CredentialsManager.get_parameter("JIRA_CLOUD_EMAIL")
            self.auth = (self.email, self.token)
            self.headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            self.jira_api = "/rest/api/3"
            self.search_endpoint = "/search/jql"
            self.project_key = CredentialsManager.jira_cloud_project_key()
            self.custom_field_override_keys = (
                "JIRA_CLOUD_CUSTOM_FIELD_1",
                "JIRA_CLOUD_CUSTOM_FIELD_2",
            )
        else:
            self.jira_url = CredentialsManager.get_parameter("JIRA_URL")
            self.token = CredentialsManager.get_parameter("JIRA_TOKEN")
            self.email = None
            self.auth = None
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            self.jira_api = "/rest/api/2"
            self.search_endpoint = "/search"
            self.project_key = CredentialsManager.jira_project_key()
            self.custom_field_override_keys = (
                "JIRA_CUSTOM_FIELD_1",
                "JIRA_CUSTOM_FIELD_2",
            )

    def _request(self, method: str, path: str, api: Optional[str] = None, **kwargs):
        response = requests.request(
            method,
            f"{self.jira_url}{api or self.jira_api}{path}",
            headers=self.headers,
            auth=self.auth,
            verify=True,
            timeout=60,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def search_issues(
        self, jql: str, fields: str = "summary", max_results: int = 100
    ) -> list[dict]:
        response = self._request(
            "GET",
            self.search_endpoint,
            params={"jql": jql, "maxResults": max_results, "fields": fields},
        )
        return response.json().get("issues", [])

    def create_issue(
        self, summary: str, description: str, issue_type: str = "Task"
    ) -> str:
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
            }
        }
        return self._request("POST", "/issue", api=WRITE_API, json=payload).json()[
            "key"
        ]

    def get_editmeta(self, key: str) -> dict:
        response = self._request("GET", f"/issue/{key}/editmeta", api=WRITE_API)
        return response.json().get("fields", {})

    def get_issue_fields(self, key: str, field_ids: list[str]) -> dict:
        if not field_ids:
            return {}
        response = self._request(
            "GET",
            f"/issue/{key}",
            api=WRITE_API,
            params={"fields": ",".join(field_ids)},
        )
        return response.json().get("fields", {})

    def update_issue_fields(self, key: str, fields: dict) -> None:
        self._request("PUT", f"/issue/{key}", api=WRITE_API, json={"fields": fields})

    def find_seed_issue_key(self) -> Optional[str]:
        return find_seed_issue_key(self.search_issues(build_seed_jql(self.project_key)))

    def _create_seed_issue(self) -> str:
        key = self.create_issue(SEED_SUMMARY, SEED_DESCRIPTION)
        logger.info(f"Created Jira seed issue {key} in project {self.project_key}")
        # The search index lags behind writes; datasources index via JQL.
        deadline = time.monotonic() + SEED_SEARCH_TIMEOUT_SECONDS
        while self.find_seed_issue_key() is None:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Jira seed issue {key} not searchable after "
                    f"{SEED_SEARCH_TIMEOUT_SECONDS}s"
                )
            time.sleep(SEED_SEARCH_POLL_SECONDS)
        # Concurrent runs may each have created a seed; all settle on the oldest.
        settled = self.find_seed_issue_key()
        if settled != key:
            logger.warning(
                f"Duplicate Jira seed issue {key} exists next to {settled}; "
                f"it can be deleted"
            )
        return settled

    def ensure_seed_issue(self) -> SeedIssue:
        """Find or create the seed issue and populate its custom fields."""
        key = self.find_seed_issue_key() or self._create_seed_issue()

        editmeta = self.get_editmeta(key)
        overrides = [
            value
            for value in (
                CredentialsManager.get_parameter(name)
                for name in self.custom_field_override_keys
            )
            if value
        ]
        selected = select_custom_fields(editmeta, overrides)
        expected = {
            field_id: CUSTOM_FIELD_VALUES[index]
            for index, (field_id, _) in enumerate(selected)
            if is_writable(editmeta, field_id)
        }

        current = self.get_issue_fields(key, list(expected))
        # Field writes fail soft: an unusable field only skips its own tests.
        values = {}
        for field_id, value in expected.items():
            if current.get(field_id) != value:
                try:
                    self.update_issue_fields(key, {field_id: value})
                except requests.exceptions.HTTPError as e:
                    status = e.response.status_code if e.response is not None else None
                    logger.warning(
                        f"Could not set Jira custom field {field_id} on {key} "
                        f"(HTTP {status}); treating it as unpopulated"
                    )
                    continue
            values[field_id] = value

        return SeedIssue(
            key=key,
            project_key=self.project_key,
            custom_fields=tuple(
                CustomField(field_id, name, values.get(field_id))
                for field_id, name in selected
            ),
        )

    def delete_jira_item(self, issue_key: str):
        """
        Delete a Jira issue via Jira API.

        Args:
            issue_key: The Jira issue key (e.g., 'PROJ-123')
        """
        # Construct API endpoint
        endpoint = f"{self.jira_url}{self.jira_api}/issue/{issue_key}"

        try:
            logger.info(f"Deleting Jira issue: {issue_key}")
            requests.delete(
                url=endpoint,
                headers=self.headers,
                auth=self.auth,
                verify=True,
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting Jira issue {issue_key}: {str(e)}")

    def cleanup_jira_project(
        self,
        summary_prefix: str = None,
        summary_contains: str = None,
        project_key: str = None,
    ) -> int:
        """
        Clean up Jira issues in a project matching the given summary filter.

        Args:
            project_key: The Jira project key (e.g., 'EPMCDMETST')
            summary_prefix: Delete issues whose summary starts with this string (session-scoped cleanup).
            summary_contains: Delete issues whose summary contains this string (session-agnostic cleanup).

        Returns:
            Number of issues deleted.
        """
        # Construct JQL query to find all issues in the project
        # We'll filter by summary in Python since JQL text search has limitations
        project_key = self.project_key if not project_key else project_key

        jql = f'project = "{project_key}"'

        try:
            # Search for issues matching the JQL
            search_endpoint = f"{self.jira_url}{self.jira_api}{self.search_endpoint}"
            params = {
                "jql": jql,
                "maxResults": 100,
                "fields": "key,summary",
            }

            filter_desc = summary_prefix or summary_contains or "(none)"
            logger.info(
                f"Searching for Jira issues in project {project_key} matching '{filter_desc}'"
            )
            response = requests.get(
                url=search_endpoint,
                headers=self.headers,
                auth=self.auth,
                params=params,
                verify=True,
            )

            if response.status_code != 200:
                # Suppress errors during cleanup - project may not exist or token may be expired
                logger.debug(
                    f"Could not search Jira issues (expected during cleanup). Status: {response.status_code}"
                )
                return 0

            all_issues = response.json().get("issues", [])

            if summary_prefix:
                issues_to_delete = [
                    issue
                    for issue in all_issues
                    if issue.get("fields", {})
                    .get("summary", "")
                    .startswith(summary_prefix)
                ]
            elif summary_contains:
                issues_to_delete = [
                    issue
                    for issue in all_issues
                    if summary_contains in issue.get("fields", {}).get("summary", "")
                ]
            else:
                issues_to_delete = list(all_issues)

            # The seed issue is shared by every run and must survive cleanup.
            issues_to_delete = [
                issue
                for issue in issues_to_delete
                if issue.get("fields", {}).get("summary") != SEED_SUMMARY
            ]

            for issue in issues_to_delete:
                self.delete_jira_item(issue["key"])

            return len(issues_to_delete)

        except requests.exceptions.RequestException as e:
            # Suppress errors during cleanup - credentials may be expired
            logger.debug(f"Jira cleanup skipped for project {project_key}: {str(e)}")
            return 0
