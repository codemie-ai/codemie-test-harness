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
from datetime import datetime
import time
from time import sleep

import requests
from hamcrest import assert_that, has_item, is_not

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.jira_seed import build_seed_jql
from codemie_test_harness.tests.utils.confluence_seed import build_seed_cql

from codemie_sdk.exceptions import ApiError
from codemie_sdk.models.datasource import (
    DataSource,
    CodeDataSourceRequest,
    GitFaqDataSourceRequest,
    ConfluenceDataSourceRequest,
    JiraDataSourceRequest,
    GoogleDataSourceRequest,
    FileDataSourceRequest,
    UpdateCodeDataSourceRequest,
    UpdateGoogleDataSourceRequest,
    UpdateFileDataSourceRequest,
    CodeDataSourceType,
    UpdateConfluenceDataSourceRequest,
    UpdateJiraDataSourceRequest,
    CodeExplorationDataSourceRequest,
    AzureDevOpsWikiDataSourceRequest,
    UpdateAzureDevOpsWikiDataSourceRequest,
    AzureDevOpsWorkItemDataSourceRequest,
    UpdateAzureDevOpsWorkItemDataSourceRequest,
    XWikiDataSourceRequest,
    UpdateXWikiDataSourceRequest,
)
from codemie_sdk.models.datasource import DataSourceStatus
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.utils.base_utils import (
    BaseUtils,
    get_random_name,
    wait_for_entity,
)

logger = logging.getLogger(__name__)


class DataSourceUtils(BaseUtils):
    def create_code_datasource(self, **kwargs):
        create_request_params = {
            "project_name": kwargs.get("project_name", PROJECT),
            "link": kwargs.get("link"),
            "branch": kwargs.get("branch"),
            "index_type": CodeDataSourceType.CODE,
            "embeddings_model": kwargs.get("embeddings_model"),
            "setting_id": kwargs.get("setting_id"),
            "description": kwargs.get("description", get_random_name()),
            "project_space_visible": kwargs.get("project_space_visible", False),
            "name": kwargs.get("name", get_random_name()),
        }

        create_datasource_request = CodeDataSourceRequest(**create_request_params)

        self.client.datasources.create(create_datasource_request)

        datasource = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200),
            entity_name=create_datasource_request.name,
        )

        if not kwargs.get("wait_for_completion", True):
            return self.get_datasource(datasource.id)

        return self.wait_for_indexing(datasource.id)

    def create_git_faq_datasource(self, **kwargs):
        create_request_params = {
            "project_name": kwargs.get("project_name", PROJECT),
            "link": kwargs.get("link"),
            "branch": kwargs.get("branch"),
            "files_filter": kwargs.get("files_filter"),
            "setting_id": kwargs.get("setting_id"),
            "description": kwargs.get("description", get_random_name()),
            "project_space_visible": kwargs.get("project_space_visible", False),
            "name": kwargs.get("name", get_random_name()),
        }

        create_datasource_request = GitFaqDataSourceRequest(**create_request_params)

        self.client.datasources.create(create_datasource_request)

        datasource = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200),
            entity_name=create_datasource_request.name,
        )

        return self.wait_for_indexing(datasource.id)

    def update_code_datasource(self, datasource_id, **kwargs):
        datasource = self.get_datasource(datasource_id)

        update_request_params = {
            "project_name": datasource.project_name,
            "link": kwargs.get("link", datasource.code.link),
            "branch": kwargs.get("branch", datasource.code.branch),
            "index_type": CodeDataSourceType.CODE,
            "embeddings_model": kwargs.get(
                "embeddings_model", datasource.embeddings_model
            ),
            "setting_id": kwargs.get("setting_id"),
            "description": kwargs.get("description", datasource.description),
            "name": datasource.name,
            "project_space_visible": kwargs.get(
                "project_space_visible", datasource.shared_with_project
            ),
            "full_reindex": kwargs.get("full_reindex", False),
            "skip_reindex": kwargs.get("skip_reindex", True),
            "incremental_reindex": kwargs.get("incremental_reindex", False),
        }

        update_datasource_request = UpdateCodeDataSourceRequest(**update_request_params)

        self.client.datasources.update(datasource.id, update_datasource_request)

        return self.wait_for_indexing(datasource.id)

    def create_gitlab_datasource(self, **kwargs):
        return self.create_code_datasource(
            name=kwargs.get("name", get_random_name()),
            link=kwargs.get("link", CredentialsManager.get_parameter("GITLAB_PROJECT")),
            branch=kwargs.get("branch", "main"),
            setting_id=kwargs.get("setting_id"),
            embeddings_model=kwargs.get("embeddings_model"),
            project_name=kwargs.get("project_name", PROJECT),
            wait_for_completion=kwargs.get("wait_for_completion", True),
        )

    def create_github_datasource(self, **kwargs):
        return self.create_code_datasource(
            name=kwargs.get("name", get_random_name()),
            link=kwargs.get("link", CredentialsManager.get_parameter("GITHUB_PROJECT")),
            branch=kwargs.get("branch", "main"),
            setting_id=kwargs.get("setting_id"),
            embeddings_model=kwargs.get("embeddings_model"),
        )

    def update_gitlab_datasource(self, datasource_id, **kwargs):
        return self.update_code_datasource(datasource_id, **kwargs)

    def partial_update_code_datasource(self, datasource_name, **kwargs):
        """Send partial update via raw HTTP, bypassing SDK validation."""
        payload = {"name": datasource_name}
        payload.update(kwargs)

        token = self.client._token
        api_domain = CredentialsManager.get_parameter("CODEMIE_API_DOMAIN")
        url = f"{api_domain}/v1/application/{PROJECT}/index/{datasource_name}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.put(url, json=payload, headers=headers, timeout=30)
        return response

    def create_google_doc_datasource(self, **kwargs):
        datasource_name = kwargs.get("name", get_random_name())
        project = kwargs.get("project_name", PROJECT)

        create_request_params = {
            "name": datasource_name,
            "project_name": project,
            "description": kwargs.get("description", get_random_name()),
            "google_doc": kwargs.get("google_doc"),
            "shared_with_project": kwargs.get("shared_with_project", False),
            "setting_id": kwargs.get("setting_id"),
        }

        create_datasource_request = GoogleDataSourceRequest(**create_request_params)
        self.client.datasources.create(create_datasource_request)

        datasource = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200, projects=[project]),
            entity_name=datasource_name,
        )

        return self.wait_for_indexing(datasource.id)

    def update_google_doc_datasource(self, datasource_id, **kwargs):
        datasource = self.get_datasource(datasource_id)

        update_request_params = {
            "name": kwargs.get("name", datasource.name),
            "project_name": datasource.project_name,
            "description": kwargs.get("description", datasource.description),
            "google_doc": kwargs.get("google_doc", datasource.google_doc_link),
            "full_reindex": kwargs.get("full_reindex", False),
            "skip_reindex": kwargs.get("skip_reindex", True),
            "incremental_reindex": kwargs.get("incremental_reindex", False),
        }

        update_datasource_request = UpdateGoogleDataSourceRequest(
            **update_request_params
        )
        self.client.datasources.update(datasource_id, update_datasource_request)

        return self.wait_for_indexing(datasource_id)

    def send_create_file_datasource_request(self, **kwargs):
        """
        Send request to create file datasource.

        Args:
            **kwargs: Datasource parameters

        Returns:
            str: The datasource name used in the request
        """
        datasource_name = kwargs.get("name", get_random_name())

        create_request_params = {
            "name": datasource_name,
            "project_name": kwargs.get("project_name", PROJECT),
            "description": kwargs.get("description", get_random_name()),
            "shared_with_project": kwargs.get("shared_with_project", False),
            "embeddings_model": kwargs.get("embeddings_model"),
            "csv_separator": kwargs.get("csv_separator", ";"),
            "csv_start_row": kwargs.get("csv_start_row", 1),
            "csv_rows_per_document": kwargs.get("csv_rows_per_document", 1000),
        }
        files = kwargs.get("files")

        create_datasource_request = FileDataSourceRequest(**create_request_params)

        self.client.datasources.create_file_datasource(create_datasource_request, files)

        return datasource_name

    def create_file_datasource(self, **kwargs):
        project = kwargs.get("project_name", PROJECT)
        datasource_name = self.send_create_file_datasource_request(**kwargs)

        datasource = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200, projects=[project]),
            entity_name=datasource_name,
        )

        if not kwargs.get("wait_for_completion", True):
            return self.get_datasource(datasource.id)

        return self.wait_for_indexing(datasource.id)

    def create_file_datasource_expecting_failure(self, **kwargs):
        """
        Create file datasource and wait for it to fail during indexing, then return the error.

        This method is useful for testing scenarios where datasource creation is expected
        to fail (e.g., due to guardrails blocking harmful content).

        Args:
            **kwargs: Same parameters as create_file_datasource()

        Returns:
            ApiError: The error raised when datasource indexing fails

        Raises:
            TimeoutError: If datasource doesn't fail within timeout
            AssertionError: If datasource indexing succeeds when failure was expected
        """
        project = kwargs.get("project_name", PROJECT)
        datasource_name = self.send_create_file_datasource_request(**kwargs)

        datasource = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200, projects=[project]),
            entity_name=datasource_name,
        )

        return self.wait_for_indexing_failure(datasource.id)

    def update_file_datasource(self, datasource_id, **kwargs) -> DataSource:
        datasource = self.get_datasource(datasource_id)

        update_request_params = {
            "name": datasource.name,
            "project_name": datasource.project_name,
            "description": kwargs.get("description", datasource.description),
            "project_space_visible": kwargs.get(
                "project_space_visible", datasource.shared_with_project
            ),
            "full_reindex": kwargs.get("full_reindex", False),
            "skip_reindex": kwargs.get("skip_reindex", True),
            "incremental_reindex": kwargs.get("incremental_reindex", False),
            "embeddings_model": kwargs.get(
                "embeddings_model", datasource.embeddings_model
            ),
        }

        update_datasource_request = UpdateFileDataSourceRequest(**update_request_params)
        self.client.datasources.update(
            datasource_id, update_datasource_request, files=kwargs.get("files")
        )

        return self.wait_for_indexing(datasource_id)

    def move_file_datasource(
        self, datasource_id: str, new_project_name: str
    ) -> DataSource:
        """Move a file datasource to a different project.

        Uses the `new_project_name` field supported by the backend update endpoint.
        The datasource ID and indexed content are preserved; only the project
        association changes. No re-indexing is triggered (`skip_reindex=True`),
        so `wait_for_indexing` is intentionally not called — the status is expected
        to remain COMPLETED throughout.

        Note: the backend update API identifies the datasource by (name, project_name),
        not by UUID. The returned object's ID is checked against the input to detect
        any name-collision mis-targeting in parallel test environments.

        Args:
            datasource_id: ID of the datasource to move.
            new_project_name: Target project name.

        Returns:
            DataSource: The updated datasource object with the new project_name.

        Raises:
            TimeoutError: If the project_name change is not reflected within timeout.
            AssertionError: If the returned datasource ID does not match the input.
        """
        datasource = self.get_datasource(datasource_id)

        update_request_params = {
            "name": datasource.name,
            "project_name": datasource.project_name,
            "description": datasource.description,
            "project_space_visible": datasource.shared_with_project,
            "embeddings_model": datasource.embeddings_model,
            "skip_reindex": True,
            "new_project_name": new_project_name,
        }

        update_datasource_request = UpdateFileDataSourceRequest(**update_request_params)
        self.client.datasources.update(datasource_id, update_datasource_request)

        timeout = int(CredentialsManager.get_parameter("DEFAULT_TIMEOUT", "120"))
        start_time = time.time()
        while time.time() - start_time < timeout:
            sleep(3)
            moved = self.get_datasource(datasource_id)
            if moved.project_name == new_project_name:
                if moved.id != datasource_id:
                    raise AssertionError(
                        f"move_file_datasource: returned datasource ID {moved.id!r} does not "
                        f"match expected {datasource_id!r}. A name collision may have caused "
                        "the wrong datasource to be targeted."
                    )
                return moved

        raise TimeoutError(
            f"Datasource {datasource_id!r} project_name did not change to "
            f"{new_project_name!r} within the timeout period."
        )

    def wait_for_indexing(
        self,
        datasource_id: str,
        timeout: int = int(CredentialsManager.get_parameter("DEFAULT_TIMEOUT", "120")),
        pool_interval: int = 3,
    ) -> DataSource:
        start_time = time.time()
        while time.time() - start_time < timeout:
            sleep(pool_interval)
            datasource = self.client.datasources.get(datasource_id)
            if datasource.status == DataSourceStatus.COMPLETED:
                return datasource
            elif datasource.status == DataSourceStatus.FAILED:
                raise ApiError(f"Datasource {datasource_id} indexing failed")
        raise TimeoutError("Datasource was not indexed within the timeout period.")

    def wait_for_indexing_failure(
        self,
        datasource_id: str,
        timeout: int = int(CredentialsManager.get_parameter("DEFAULT_TIMEOUT", "120")),
        pool_interval: int = 3,
    ) -> DataSource:
        """
        Wait for datasource indexing to fail and return the error.

        This method polls the datasource until indexing fails, then returns the error
        instead of raising it. Useful for testing expected failures.

        Args:
            datasource_id: The ID of the datasource to monitor
            timeout: Maximum time to wait in seconds
            pool_interval: Polling interval in seconds

        Returns:
            DataSource: failed datasource object with error details

        Raises:
            AssertionError: If indexing succeeds when failure was expected
            TimeoutError: If indexing doesn't fail within timeout period
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            sleep(pool_interval)
            datasource = self.client.datasources.get(datasource_id)
            if datasource.status == DataSourceStatus.COMPLETED:
                raise AssertionError(
                    f"Expected datasource {datasource_id} to fail, but it succeeded"
                )
            elif datasource.status == DataSourceStatus.FAILED:
                return datasource

        raise TimeoutError("Datasource did not fail within the timeout period.")

    def wait_for_update_date_change(
        self,
        datasource_id: str,
        timeout: int = 80,
        pool_interval: int = 3,
        initial_update_date: datetime = None,
    ) -> DataSource:
        """Wait for datasource update_date to become greater than created_date at more than 30 seconds.

        This method polls the datasource and waits until the update_date is greater
        than the created_date, indicating that the datasource has been updated/re-indexed.

        Args:
            datasource_id: The ID of the datasource to monitor
            timeout: Maximum time to wait in seconds (default from DEFAULT_TIMEOUT)
            pool_interval: Time between polling attempts in seconds (default 3)

        Returns:
            DataSource: The updated datasource object with update_date > created_date

        Raises:
            TimeoutError: If update_date doesn't change within the timeout period
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            sleep(pool_interval)
            datasource = self.client.datasources.get(datasource_id)

            if datasource.update_date > initial_update_date:
                return datasource

        raise TimeoutError(
            f"Datasource {datasource_id} update_date did not change within the timeout period. "
            f"Initial update date: {initial_update_date}, Last checked update: {datasource.update_date}"
        )

    def get_datasource(self, datasource_id):
        return self.client.datasources.get(datasource_id)

    def get_datasource_by_name(self, name: str) -> DataSource:
        """Wait until a datasource with this name is listed and return it in full."""
        listed = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200), entity_name=name
        )
        return self.get_datasource(listed.id)

    def count_datasources_by_name(self, name: str, project_name: str = PROJECT) -> int:
        """Number of datasources in a project whose name equals `name`."""
        datasources = self.client.datasources.list(
            per_page=200, projects=[project_name]
        )
        return len([ds for ds in datasources if ds.name == name])

    def create_confluence_datasource(self, **kwargs):
        name = kwargs.get("name", get_random_name())
        project = kwargs.get("project_name", PROJECT)
        create_request_params = {
            "name": name,
            "project_name": project,
            "description": kwargs.get("description", get_random_name()),
            "cql": kwargs.get(
                "cql", build_seed_cql(CredentialsManager.confluence_space_key())
            ),
            "project_space_visible": kwargs.get("project_space_visible", False),
            "setting_id": kwargs.get("setting_id"),
        }

        create_datasource_request = ConfluenceDataSourceRequest(**create_request_params)
        self.client.datasources.create(create_datasource_request)
        datasource = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200, projects=[project]),
            entity_name=name,
        )

        return self.wait_for_indexing(datasource.id)

    def update_confluence_datasource(self, datasource_id, **kwargs):
        datasource = self.get_datasource(datasource_id)

        update_request_params = {
            "name": kwargs.get("name", datasource.name),
            "project_name": datasource.project_name,
            "description": kwargs.get("description", datasource.description),
            "cql": kwargs.get("cql", datasource.confluence.cql),
            "full_reindex": kwargs.get("full_reindex", False),
            "skip_reindex": kwargs.get("skip_reindex", True),
            "incremental_reindex": kwargs.get("incremental_reindex", False),
            "setting_id": kwargs.get("setting_id"),
            "project_space_visible": kwargs.get(
                "project_space_visible", datasource.shared_with_project
            ),
        }

        update_datasource_request = UpdateConfluenceDataSourceRequest(
            **update_request_params
        )
        self.client.datasources.update(datasource_id, update_datasource_request)

        return self.wait_for_indexing(datasource_id)

    def create_jira_datasource(self, **kwargs):
        name = kwargs.get("name", get_random_name())
        project = kwargs.get("project_name", PROJECT)
        create_request_params = {
            "name": name,
            "project_name": project,
            "description": kwargs.get("description", get_random_name()),
            "jql": kwargs.get(
                "jql", build_seed_jql(CredentialsManager.jira_project_key())
            ),
            "project_space_visible": kwargs.get("project_space_visible", False),
            "setting_id": kwargs.get("setting_id"),
            "cron_expression": kwargs.get("cron_expression"),
            "timezone": kwargs.get("timezone"),
            "custom_fields": kwargs.get("custom_fields"),
        }

        create_datasource_request = JiraDataSourceRequest(**create_request_params)
        self.client.datasources.create(create_datasource_request)
        datasource = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200, projects=[project]),
            entity_name=name,
        )

        return self.wait_for_indexing(datasource.id)

    def update_jira_datasource(self, datasource_id, **kwargs):
        datasource = self.get_datasource(datasource_id)

        update_request_params = {
            "name": kwargs.get("name", datasource.name),
            "project_name": datasource.project_name,
            "description": kwargs.get("description", datasource.description),
            "jql": kwargs.get("jql", datasource.jira.jql),
            "full_reindex": kwargs.get("full_reindex", False),
            "skip_reindex": kwargs.get("skip_reindex", True),
            "incremental_reindex": kwargs.get("incremental_reindex", False),
            "setting_id": kwargs.get("setting_id"),
            "project_space_visible": kwargs.get(
                "project_space_visible", datasource.shared_with_project
            ),
            "custom_fields": kwargs.get("custom_fields"),
        }

        update_datasource_request = UpdateJiraDataSourceRequest(**update_request_params)
        self.client.datasources.update(datasource_id, update_datasource_request)

        return self.wait_for_indexing(datasource_id)

    def wait_for_fetching(
        self,
        datasource_id: str,
        timeout: int = 60,
        poll_interval: int = 2,
    ) -> DataSource:
        """Poll until datasource status transitions to IN_PROGRESS."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            sleep(poll_interval)
            datasource = self.client.datasources.get(datasource_id)
            if datasource.status in (
                DataSourceStatus.IN_PROGRESS,
                DataSourceStatus.FETCHING,
            ):
                return datasource
            if datasource.status in (
                DataSourceStatus.COMPLETED,
                DataSourceStatus.FAILED,
            ):
                raise TimeoutError(
                    f"Datasource {datasource_id!r} reached terminal state "
                    f"{datasource.status!r} before FETCHING was observed."
                )
        raise TimeoutError(
            f"Datasource {datasource_id!r} did not enter FETCHING state within {timeout}s."
        )

    def assert_datasource_absent_during_window(
        self,
        datasource_id: str,
        duration: int = 60,
        poll_interval: int = 3,
    ) -> None:
        """Poll datasource list for `duration` seconds, asserting the ID never reappears."""
        start_time = time.time()
        while time.time() - start_time < duration:
            sleep(poll_interval)
            current_ids = [ds.id for ds in self.client.datasources.list(per_page=200)]
            assert_that(
                current_ids,
                is_not(has_item(datasource_id)),
                f"Deleted datasource {datasource_id!r} reappeared in the datasource list.",
            )

    def delete_datasource(self, datasource):
        return self.client.datasources.delete(datasource.id)

    def safe_delete_datasource(self, datasource) -> None:
        """Best-effort datasource delete for fixture teardown: logs and
        swallows any failure instead of raising, so a cleanup problem never
        masks a real assertion failure from the test itself.
        """
        try:
            self.delete_datasource(datasource)
        except Exception as e:
            logger.warning(f"Failed to delete datasource {datasource.id}: {e}")

    def create_azure_devops_wiki_datasource(self, **kwargs):
        name = kwargs.get("name", get_random_name())
        create_request_params = {
            "name": name,
            "project_name": kwargs.get("project_name", PROJECT),
            "description": kwargs.get("description", get_random_name()),
            "wiki_name": kwargs.get(
                "wiki_name", CredentialsManager.azure_devops_wiki_name()
            ),
            "wiki_query": kwargs.get("wiki_query", ""),
            "project_space_visible": kwargs.get("project_space_visible", False),
            "setting_id": kwargs.get("setting_id"),
        }

        create_datasource_request = AzureDevOpsWikiDataSourceRequest(
            **create_request_params
        )
        self.client.datasources.create(create_datasource_request)
        datasource = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200),
            entity_name=name,
        )

        return self.wait_for_indexing(datasource.id, timeout=240)

    def update_azure_devops_wiki_datasource(self, datasource_id, **kwargs):
        datasource = self.get_datasource(datasource_id)

        update_request_params = {
            "name": kwargs.get("name", datasource.name),
            "project_name": datasource.project_name,
            "description": kwargs.get("description", datasource.description),
            "wiki_name": kwargs.get(
                "wiki_name", datasource.azure_devops_wiki.wiki_name
            ),
            "wiki_query": kwargs.get(
                "wiki_query", datasource.azure_devops_wiki.wiki_query or ""
            ),
            "full_reindex": kwargs.get("full_reindex", False),
            "skip_reindex": kwargs.get("skip_reindex", True),
            "incremental_reindex": kwargs.get("incremental_reindex", False),
            "setting_id": kwargs.get("setting_id"),
            "project_space_visible": kwargs.get(
                "project_space_visible", datasource.shared_with_project
            ),
        }

        update_datasource_request = UpdateAzureDevOpsWikiDataSourceRequest(
            **update_request_params
        )
        self.client.datasources.update(datasource_id, update_datasource_request)

        return self.wait_for_indexing(datasource_id)

    def create_azure_devops_work_items_datasource(self, **kwargs):
        name = kwargs.get("name", get_random_name())
        create_request_params = {
            "name": name,
            "project_name": kwargs.get("project_name", PROJECT),
            "description": kwargs.get("description", get_random_name()),
            "wiql_query": kwargs.get("wiql_query", ""),
            "project_space_visible": kwargs.get("project_space_visible", False),
            "setting_id": kwargs.get("setting_id"),
        }

        create_datasource_request = AzureDevOpsWorkItemDataSourceRequest(
            **create_request_params
        )
        self.client.datasources.create(create_datasource_request)
        datasource = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200),
            entity_name=name,
        )

        return self.wait_for_indexing(datasource.id, timeout=180)

    def update_azure_devops_work_items_datasource(self, datasource_id, **kwargs):
        datasource = self.get_datasource(datasource_id)

        update_request_params = {
            "name": kwargs.get("name", datasource.name),
            "project_name": datasource.project_name,
            "description": kwargs.get("description", datasource.description),
            "wiql_query": kwargs.get(
                "wiql_query",
                datasource.azure_devops_work_item.wiql_query
                if datasource.azure_devops_work_item
                else CredentialsManager.azure_devops_work_items_wiql(),
            ),
            "full_reindex": kwargs.get("full_reindex", False),
            "skip_reindex": kwargs.get("skip_reindex", True),
            "incremental_reindex": kwargs.get("incremental_reindex", False),
            "setting_id": kwargs.get("setting_id"),
            "project_space_visible": kwargs.get(
                "project_space_visible", datasource.shared_with_project
            ),
        }

        update_datasource_request = UpdateAzureDevOpsWorkItemDataSourceRequest(
            **update_request_params
        )
        self.client.datasources.update(datasource_id, update_datasource_request)

        return self.wait_for_indexing(datasource_id, timeout=180)

    def create_xwiki_datasource(self, **kwargs):
        name = kwargs.get("name", get_random_name())
        project = kwargs.get("project_name", PROJECT)
        create_request_params = {
            "name": name,
            "project_name": project,
            "description": kwargs.get("description", get_random_name()),
            "space": kwargs.get("space"),
            "wiki": kwargs.get("wiki"),
            "project_space_visible": kwargs.get("project_space_visible", False),
            "setting_id": kwargs.get("setting_id"),
        }

        create_datasource_request = XWikiDataSourceRequest(**create_request_params)
        self.client.datasources.create(create_datasource_request)
        datasource = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200, projects=[project]),
            entity_name=name,
        )

        return self.wait_for_indexing(datasource.id, timeout=240)

    def update_xwiki_datasource(self, datasource_id, **kwargs):
        datasource = self.get_datasource(datasource_id)

        update_request_params = {
            "name": kwargs.get("name", datasource.name),
            "project_name": datasource.project_name,
            "description": kwargs.get("description", datasource.description),
            "space": kwargs.get("space", datasource.xwiki.space),
            "wiki": kwargs.get("wiki", datasource.xwiki.wiki),
            "full_reindex": kwargs.get("full_reindex", False),
            "skip_reindex": kwargs.get("skip_reindex", True),
            "setting_id": kwargs.get("setting_id"),
            "project_space_visible": kwargs.get(
                "project_space_visible", datasource.shared_with_project
            ),
        }

        update_datasource_request = UpdateXWikiDataSourceRequest(
            **update_request_params
        )
        self.client.datasources.update(datasource_id, update_datasource_request)

        return self.wait_for_indexing(datasource_id, timeout=240)

    def create_code_exploration_datasource(
        self,
        toolkit_id: str,
        provider_name: str,
        project_name: str = None,
        name: str = None,
        description: str = None,
        project_space_visible: bool = True,
    ) -> DataSource:
        """
        Create a CodeExplorationToolkit datasource. The AICE provider needs no
        other datasources.

        Args:
            toolkit_id: ID of the CodeExplorationToolkit
            provider_name: Name of the provider
            project_name: Project name (defaults to PROJECT)
            name: Datasource name (auto-generated if not provided)
            description: Datasource description (auto-generated if not provided)
            project_space_visible: Whether datasource is visible to project (default: True)

        Returns:
            DataSource: The indexed datasource object

        Raises:
            TimeoutError: If datasource indexing doesn't complete within timeout
            ApiError: If datasource creation or indexing fails
        """
        datasource_name = name if name else get_random_name()

        create_request_params = {
            "name": datasource_name,
            "description": description if description else get_random_name(),
            "project_name": project_name if project_name else PROJECT,
            "project_space_visible": project_space_visible,
        }

        create_datasource_request = CodeExplorationDataSourceRequest(
            **create_request_params
        )

        # Create the datasource using the SDK
        self.client.datasources.create_provider_datasource(
            toolkit_id=toolkit_id,
            provider_name=provider_name,
            request=create_datasource_request,
        )

        # Wait for the datasource to appear in the list
        datasource = wait_for_entity(
            lambda: self.client.datasources.list(per_page=200),
            entity_name=datasource_name,
        )

        # Wait for indexing to complete
        return self.wait_for_indexing(
            datasource.id, timeout=1200
        )  # Longer timeout for exploration datasource
