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

import re

import pytest
from playwright.sync_api import expect

from codemie_test_harness.tests import CredentialsManager, PROJECT, TEST_USER
from codemie_test_harness.tests.test_data.google_datasource_test_data import (
    get_google_doc_url,
)
from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceType,
    DataSourceFilterType,
    DataSourceStatus,
    SUBTITLE_CREATE_DATASOURCE,
    TITLE_CREATE_DATASOURCE,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH


@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.ui
def test_open_create_datasource_page_and_elements(
    page, available_embedding_model_labels
):
    """Open Create Datasource page and verify critical elements."""
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    create_page.sidebar.should_see_title_subtitle(
        TITLE_CREATE_DATASOURCE, SUBTITLE_CREATE_DATASOURCE
    )
    create_page.should_see_main_fields()

    create_page.select_datasource_type(DataSourceType.GIT)
    create_page.should_see_git_fields()
    create_page.should_see_embeddings_model_dropdown_values(
        available_embedding_model_labels
    )

    create_page.select_datasource_type(DataSourceFilterType.CONFLUENCE)
    create_page.should_see_confluence_cql_field()
    create_page.should_see_integration_input_or_button()
    create_page.should_see_embeddings_model_field()
    create_page.should_see_reindex_schedule_fields()

    create_page.select_datasource_type(DataSourceFilterType.JIRA)
    create_page.should_see_jql_field()
    create_page.should_see_integration_input_or_button()
    create_page.should_see_embeddings_model_field()
    create_page.should_see_reindex_schedule_fields()

    create_page.select_datasource_type(DataSourceFilterType.X_RAY)
    create_page.should_see_jql_field()
    create_page.should_see_integration_input_or_button()
    create_page.should_see_embeddings_model_field()
    create_page.should_see_reindex_schedule_fields()

    create_page.select_datasource_type(DataSourceFilterType.FILE)
    create_page.should_see_file_fields()
    create_page.should_see_embeddings_model_field()

    create_page.select_datasource_type(DataSourceFilterType.GOOGLE)
    create_page.should_see_google_fields()
    create_page.should_see_embeddings_model_field()
    create_page.should_see_reindex_schedule_fields()

    create_page.select_datasource_type(DataSourceFilterType.ADO_WIKI)
    create_page.should_see_ado_fields()
    create_page.should_see_embeddings_model_field()
    create_page.should_see_reindex_schedule_fields()


@pytest.mark.sanity
@pytest.mark.datasource
@pytest.mark.ui
def test_datasource_creation_validation(page):
    """Test create datasource without data and observing errors."""
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    # Verify name is empty on DS creation start (no auto-generation)
    create_page.should_have_name_empty()
    create_page.select_datasource_type(DataSourceType.GIT)
    # Verify name remains empty after selecting datasource type
    create_page.should_have_name_empty()
    create_page.click_create()
    create_page.should_see_error_for_empty_main_fields()
    create_page.should_see_error_for_empty_git_fields()

    create_page.select_datasource_type(DataSourceFilterType.CONFLUENCE).click_create()
    create_page.should_see_error_for_empty_main_fields()
    create_page.should_see_error_for_empty_confluence_fields()

    create_page.select_datasource_type(DataSourceFilterType.JIRA).click_create()
    create_page.should_see_error_for_empty_main_fields()
    create_page.should_see_error_for_empty_jql_fields()

    create_page.select_datasource_type(DataSourceFilterType.FILE).click_create()
    create_page.should_see_error_for_empty_main_fields()
    create_page.should_see_error_for_empty_file_fields()

    create_page.select_datasource_type(DataSourceFilterType.GOOGLE).click_create()
    create_page.should_see_error_for_empty_main_fields()
    create_page.should_see_error_for_empty_google_fields()

    create_page.select_datasource_type(DataSourceFilterType.X_RAY).click_create()
    create_page.should_see_error_for_empty_main_fields()
    create_page.should_see_error_for_empty_jql_fields()

    create_page.select_datasource_type(DataSourceFilterType.ADO_WIKI).click_create()
    create_page.should_see_error_for_empty_main_fields()


@pytest.mark.sanity
@pytest.mark.datasource
@pytest.mark.ui
def test_datasource_name_not_autogenerated_on_creation(page):
    """Verify that datasource alias (name) is NOT auto-generated on creation page.

    The datasource alias/name should remain empty until the user
    provides it explicitly. Auto-generation is only for integrations, not datasources.
    """
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    # Verify name is empty when page loads
    create_page.should_have_name_empty()

    # Verify name stays empty after selecting project
    create_page.select_project(PROJECT)
    create_page.should_have_name_empty()

    # Verify name stays empty after selecting datasource type
    create_page.select_datasource_type(DataSourceType.GIT)
    create_page.should_have_name_empty()

    # Verify name stays empty after selecting integration
    # (integration alias ≠ datasource name)
    create_page.select_datasource_type(DataSourceFilterType.CONFLUENCE)
    create_page.should_have_name_empty()


@pytest.mark.gitlab
@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.ui
def test_create_git_datasource(page, gitlab_integration):
    """Test creating a new datasource with all required fields."""
    datasource_page = DataSourcePage(page)
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    datasource = create_page.create_git_datasource(
        project_name=PROJECT,
        repo_link=CredentialsManager.get_parameter("GITLAB_PROJECT"),
        branch="main",
        integration=gitlab_integration.alias,
    )

    datasource_page.should_see_table_row_with_values(
        name=datasource,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=DataSourceFilterType.CODE,
        created_by=TEST_USER,
    )


@pytest.mark.confluence
@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.ui
def test_create_confluence_datasource(
    page, confluence_integration, confluence_seed_page
):
    """Test creating a new datasource with all required fields."""
    datasource_page = DataSourcePage(page)
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    datasource = create_page.create_confluence_datasource(
        project_name=PROJECT,
        cql_query=confluence_seed_page.cql,
        integration=confluence_integration.alias,
    )

    datasource_page.should_see_table_row_with_values(
        name=datasource,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=DataSourceFilterType.CONFLUENCE,
        created_by=TEST_USER,
    )


@pytest.mark.jira
@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.ui
def test_create_jira_datasource(page, jira_integration, jira_seed_issue):
    """Test creating a new datasource with all required fields."""
    datasource_page = DataSourcePage(page)
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    datasource = create_page.create_jira_datasource(
        project_name=PROJECT,
        jql_query=jira_seed_issue.jql,
        integration=jira_integration.alias,
    )

    datasource_page.should_see_table_row_with_values(
        name=datasource,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=DataSourceFilterType.JIRA,
        created_by=TEST_USER,
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.ui
def test_create_file_datasource(page, cleanup_file_datasources):
    """Test creating a new datasource with all required fields."""
    datasource_page = DataSourcePage(page)
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    datasource = create_page.create_file_datasource(
        project_name=PROJECT,
        file_path=[str(FILES_PATH / "test.txt")],
    )
    cleanup_file_datasources.append(datasource)

    datasource_page.should_see_table_row_with_values(
        name=datasource,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=DataSourceFilterType.FILE,
        created_by=TEST_USER,
    )


@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.ui
def test_create_google_datasource(page, google_integration):
    """Test creating a new datasource with all required fields."""
    datasource_page = DataSourcePage(page)
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    datasource = create_page.create_google_datasource(
        project_name=PROJECT,
        google_doc_link=get_google_doc_url(),
        integration=google_integration.alias,
    )

    datasource_page.should_see_table_row_with_values(
        name=datasource,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=DataSourceFilterType.GOOGLE,
        created_by=TEST_USER,
    )


@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.ui
def test_google_datasource_add_user_integration_dialog(page):
    """Test the 'Add User Integration' flow on the Google Docs datasource create page."""
    create_page = CreateEditDatasourcePage(page)
    dialog = create_page.create_user_integration_dialog

    create_page.navigate_to()
    create_page.select_datasource_type(DataSourceFilterType.GOOGLE)
    create_page.should_see_add_integration_button()

    create_page.click_add_integration_button()
    dialog.should_be_visible()
    dialog.should_have_all_expected_elements()

    popup = dialog.click_sign_in_with_google_and_get_popup()
    expect(popup).to_have_url(re.compile(r"^https://accounts\.google\.com/v3/signin"))
    popup.close()


@pytest.mark.ado
@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.ui
def test_create_ado_wiki_datasource(page, ado_integration):
    """Test creating a new datasource with all required fields."""
    datasource_page = DataSourcePage(page)
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    datasource = create_page.create_ado_wiki_datasource(
        project_name=PROJECT,
        wiki_name=CredentialsManager.azure_devops_wiki_name(),
        integration=ado_integration.alias,
    )

    datasource_page.should_see_table_row_with_values(
        name=datasource,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=DataSourceFilterType.ADO_WIKI,
        created_by=TEST_USER,
    )
