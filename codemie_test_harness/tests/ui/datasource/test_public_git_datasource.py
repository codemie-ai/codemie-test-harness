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

"""
UI E2E tests: Allow creating Git datasource for public
repositories without specifying an integration.

Scenarios:
    TC-002  Create public Git datasource without integration (UI) + optional hint visible
    TC-007  UI shows error notification when private repo used without integration
"""

import pytest

from codemie_test_harness.tests import PROJECT, TEST_USER
from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceFilterType,
    DataSourceStatus,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


# ---------------------------------------------------------------------------
# TC-002 — Create public Git datasource + optional integration hint visible (UI)
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.git
@pytest.mark.ui
@pytest.mark.not_for_parallel_run
def test_create_public_git_datasource_ui_shows_optional_hint(
    page, cleanup_file_datasources
):
    """UI shows optional-integration hint; datasource reaches COMPLETED status.

    Steps:
        1. Navigate to create datasource form.
        2. Verify optional integration hint is visible (AC-2: banner present for Git).
        3. Create datasource with public repo URL, no integration.
        4. Verify datasource row appears with COMPLETED status (AC-1, AC-4, AC-5).
        5. Teardown: delete datasource via API.
    """
    create_page = CreateEditDatasourcePage(page)
    datasource_page = DataSourcePage(page)

    create_page.navigate_to()

    # AC-2: Integration-optional banner is visible before form submission
    create_page.should_see_optional_integration_hint()

    datasource_name = create_page.create_git_datasource(
        project_name=PROJECT,
        repo_link=CredentialsManager.get_parameter("GITHUB_PUBLIC_PROJECT"),
        branch="main",
        # integration omitted — public repo, no credentials needed
    )
    cleanup_file_datasources.append(datasource_name)

    # AC-1, AC-4, AC-5: Datasource created successfully, indexing completes
    datasource_page.should_see_table_row_with_values(
        name=datasource_name,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=DataSourceFilterType.CODE,
        created_by=TEST_USER,
    )


# ---------------------------------------------------------------------------
# TC-007 — UI shows error notification for private repo without integration
# ---------------------------------------------------------------------------


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.git
@pytest.mark.ui
@pytest.mark.not_for_parallel_run
def test_private_git_repo_without_integration_shows_error_notification(page):
    """Submitting a private repo URL without integration shows an error notification.

    The frontend health check (useCreateIndex.ts) probes the repo before creation.
    For a private repo with no integration the health check fails and the UI
    renders an error notification — no datasource entity is created.

    Steps:
        1. Navigate to create datasource form.
        2. Submit with private repo URL, no integration selected.
        3. Verify error notification is visible (AC-6).
    """
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()

    # Attempt creation — the health check will fail for the private repo
    create_page.create_git_datasource(
        project_name=PROJECT,
        repo_link=CredentialsManager.get_parameter("GITLAB_PROJECT"),
        branch="main",
        # integration omitted — private repo, will be rejected by health check
    )

    # AC-6: Error notification visible; no datasource created
    create_page.should_see_public_access_error_notification()
