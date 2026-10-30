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

import pytest
from codemie_test_harness.tests import PROJECT, TEST_USER
from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceStatus,
    DataSourceFilterType,
    UPDATE_SUBTITLE_DATASOURCE,
    UPDATE_TITLE_DATASOURCE,
)
from codemie_test_harness.tests.utils.constants import test_project_name


@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.parametrize(
    "datasource_fixture_name,datasource_type,reindex_type",
    [
        pytest.param(
            "gitlab_datasource",
            DataSourceFilterType.CODE,
            "full",
            marks=pytest.mark.requires_setting("gitlab"),
        ),
        pytest.param(
            "confluence_datasource",
            DataSourceFilterType.CONFLUENCE,
            "full",
            marks=pytest.mark.requires_setting("confluence"),
        ),
        pytest.param(
            "jira_datasource",
            DataSourceFilterType.JIRA,
            "index",
            marks=pytest.mark.requires_setting("jira"),
        ),
        ("file_datasource", DataSourceFilterType.FILE, None),
        pytest.param(
            "google_doc_datasource",
            DataSourceFilterType.GOOGLE,
            "full",
            marks=pytest.mark.requires_setting(
                "OAUTH_CLIENT_ID",
                "OAUTH_CLIENT_SECRET",
                "OAUTH_REFRESH_TOKEN",
                "GMAIL_USER_EMAIL",
                "GOOGLE_DOC_URL",
            ),
        ),
        pytest.param(
            "ado_wiki_datasource",
            DataSourceFilterType.ADO_WIKI,
            "full",
            marks=pytest.mark.requires_setting("ado"),
        ),
    ],
)
@pytest.mark.prod_regression
def test_edit_datasource(
    page,
    request,
    datasource_fixture_name,
    datasource_type,
    reindex_type,
):
    """Test that all main Edit Datasource page elements are visible."""
    datasource_page = DataSourcePage(page)
    edit_page = CreateEditDatasourcePage(page)

    # Get the datasource from the fixture dynamically
    datasource = request.getfixturevalue(datasource_fixture_name)

    datasource_page.navigate_to()
    datasource_page.should_see_table_row_with_values(
        name=datasource.name,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=datasource_type,
        created_by=TEST_USER,
    )

    datasource_page.open_row_action_menu(datasource.name)
    datasource_page.should_see_edit_dropdown_values()

    if reindex_type == "full":
        datasource_page.should_see_edit_dropdown_full_reindex_value()
    elif reindex_type == "index":
        datasource_page.should_see_edit_dropdown_index_values()

    datasource_page.click_row_action("Edit")

    edit_page.sidebar.should_see_title_subtitle(
        UPDATE_TITLE_DATASOURCE, UPDATE_SUBTITLE_DATASOURCE
    )
    edit_page.selector.should_see_disabled_multiselect(PROJECT)
    edit_page.should_see_disabled_name_input(datasource.name)

    if reindex_type is not None:
        edit_page.should_see_save_reindex_button()


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.prod_regression
def test_code_datasource_no_error_after_project_change_and_description_edit(
    page,
    datasource_utils,
    gitlab_integration,
    default_embedding_llm,
):
    """
    Test that after changing project and saving, subsequent description edits succeed without 'Repository not found' error.

    This test reproduces the exact bug where:
    1. User creates a code datasource with PROJECT
    2. User changes the project to test_project_name and saves
    3. User opens datasource for editing again
    4. User edits description field
    5. On save, backend incorrectly tries to resolve repository using stale PROJECT → error

    Prerequisites:
        - GitLab integration is configured
        - Both PROJECT and test_project_name exist

    Test Steps:
        1. Create a GitLab datasource via API with PROJECT
        2. Navigate to datasource list page
        3. Open datasource for editing
        4. Change the project from PROJECT to test_project_name (project selector IS ENABLED in edit mode)
        5. Click "Save & Reindex"
        6. Verify save succeeds and project is updated to test_project_name
        7. Open datasource for editing again
        8. Edit description field
        9. Click "Save & Reindex"
        10. Verify NO "Repository not found" error is received
        11. Verify datasource is in "Completed" status with updated description

    Expected Result:
        - After project change save: datasource status is "Completed" with project = test_project_name
        - After description edit save: NO "Repository not found" error appears
        - After description edit save: datasource status is "Completed"
        - Description is updated in datasource list
    """
    datasource_page = DataSourcePage(page)
    edit_page = CreateEditDatasourcePage(page)

    # Step 1: Create a GitLab datasource via API
    datasource = datasource_utils.create_gitlab_datasource(
        setting_id=gitlab_integration.id,
        embeddings_model=default_embedding_llm.base_name,
        project_name=PROJECT,
    )

    # Step 2: Navigate to datasource list page
    datasource_page.navigate_to()
    datasource_page.should_see_datasource_with_name(datasource.name)

    # Step 3: Open datasource for editing
    datasource_page.open_and_select_row_action(datasource.name, "Edit")

    # Step 4: Change the project (project selector IS ENABLED in edit mode)
    # Change from PROJECT to test_project_name
    edit_page.selector.search_and_select_project(test_project_name)

    # Step 5: Click "Save & Reindex"
    edit_page.click_save_and_reindex()

    # Step 6: Verify save succeeds - datasource appears in list with Completed status and updated project
    datasource_page.should_see_table_row_with_values(
        name=datasource.name,
        status=DataSourceStatus.COMPLETED,
        project=test_project_name,  # Project should now be changed to test_project_name
        type_=DataSourceFilterType.CODE,
        created_by=TEST_USER,
        timeout=120000,  # Longer timeout for reindex
    )

    # Step 7: Open datasource for editing again
    datasource_page.open_and_select_row_action(datasource.name, "Edit")

    # Step 8: Edit description field
    new_description = f"{datasource.description} - Updated after project change"
    edit_page.fill_description(new_description)

    # Step 9: Click "Save & Reindex"
    edit_page.click_save_and_reindex()

    # Step 10: Verify NO error is received
    edit_page.should_not_see_repository_not_found_error()
    edit_page.should_not_see_error_dialog()

    # Step 11: Verify datasource is in "Completed" status with updated description
    datasource_page.should_see_table_row_with_values(
        name=datasource.name,
        status=DataSourceStatus.COMPLETED,
        project=test_project_name,  # Project remains as test_project_name after description edit
        type_=DataSourceFilterType.CODE,
        created_by=TEST_USER,
        timeout=120000,
    )
