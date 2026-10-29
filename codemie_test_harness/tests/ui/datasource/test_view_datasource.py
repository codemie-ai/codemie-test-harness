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
from playwright.sync_api import expect

from codemie_test_harness.tests import PROJECT, TEST_USER
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.view_datasource_page import (
    ViewDatasourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    TITLE_VIEW_DATASOURCE,
    SUBTITLE_VIEW_DATASOURCE,
    DataSourceStatus,
    DataSourceType,
    DataSourceFilterType,
)


@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.parametrize(
    "datasource_fixture_name,datasource_filter_type,datasource_type,is_git",
    [
        pytest.param(
            "gitlab_datasource",
            DataSourceFilterType.CODE,
            DataSourceType.GIT,
            True,
            marks=pytest.mark.requires_setting("gitlab"),
        ),
        pytest.param(
            "confluence_datasource",
            DataSourceFilterType.CONFLUENCE,
            DataSourceFilterType.CONFLUENCE,
            False,
            marks=pytest.mark.requires_setting("confluence"),
        ),
        pytest.param(
            "jira_datasource",
            DataSourceFilterType.JIRA,
            DataSourceFilterType.JIRA,
            False,
            marks=pytest.mark.requires_setting("jira"),
        ),
        (
            "file_datasource",
            DataSourceFilterType.FILE,
            DataSourceFilterType.FILE,
            False,
        ),
        pytest.param(
            "google_doc_datasource",
            DataSourceFilterType.GOOGLE,
            DataSourceFilterType.GOOGLE,
            False,
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
            DataSourceFilterType.ADO_WIKI,
            False,
            marks=pytest.mark.requires_setting("ado"),
        ),
    ],
)
def test_view_datasource_page(
    page,
    request,
    client,
    default_embedding_llm,
    datasource_fixture_name,
    datasource_filter_type,
    datasource_type,
    is_git,
):
    """Test that all main View Datasource page elements are visible."""
    datasource_page = DataSourcePage(page)
    view_page = ViewDatasourcePage(page)

    # Get the datasource from the fixture dynamically
    datasource = request.getfixturevalue(datasource_fixture_name)

    datasource_page.navigate_to()
    datasource_page.should_see_table_row_with_values(
        name=datasource.name,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=datasource_filter_type,
        created_by=TEST_USER,
    )

    datasource_page.click_datasource_row_by_name(datasource.name)
    view_page.sidebar.should_see_title_subtitle(
        TITLE_VIEW_DATASOURCE, SUBTITLE_VIEW_DATASOURCE
    )
    view_page.should_see_ds_name_and_owner(
        datasource_name=datasource.name, owner=TEST_USER
    )
    view_page.should_see_description(description=datasource.description)

    if is_git:
        view_page.should_see_processing_summary(is_git=True)
        view_page.should_see_overview(
            project=PROJECT, ds_type=datasource_type, ds_id=datasource.id
        )
        view_page.should_see_configuration(embeddings_model=default_embedding_llm.label)
        view_page.should_open_and_see_processed_data()
    else:
        view_page.should_see_processing_summary()
        view_page.should_see_overview(
            project=PROJECT, ds_type=datasource_type, ds_id=datasource.id
        )
        view_page.should_see_configuration(embeddings_model=default_embedding_llm.label)
        view_page.should_see_processed_data()


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
def test_view_datasource_shows_edit_button_for_authorized_user(
    page,
    gitlab_datasource,
):
    """Edit button is visible on the Datasource View page for the datasource owner."""
    datasource_page = DataSourcePage(page)
    view_page = ViewDatasourcePage(page)

    datasource_page.navigate_to()
    datasource_page.click_datasource_row_by_name(gitlab_datasource.name)

    expect(view_page.edit_button).to_be_visible()


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
def test_view_datasource_delete_button_opens_confirmation_dialog(
    page,
    gitlab_datasource,
):
    """Clicking the Delete button on the Datasource View page opens the confirmation dialog."""
    datasource_page = DataSourcePage(page)
    view_page = ViewDatasourcePage(page)

    datasource_page.navigate_to()
    datasource_page.click_datasource_row_by_name(gitlab_datasource.name)

    expect(view_page.delete_button).to_be_visible()
    view_page.delete_button.click()

    datasource_page.should_see_delete_dialog()
