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
E2E tests for cloning a Data Source.

Clone is offered from the Data Sources list actions menu and from the details
page. It opens /data-sources/<id>/clone, which is the normal create form
prefilled with the source configuration and an empty name. Saving creates a new,
independent Data Source.
"""

import logging
import uuid
from http import HTTPStatus

import pytest
from hamcrest import assert_that, equal_to, is_not

from codemie_test_harness.tests import PROJECT, TEST_USER
from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.view_datasource_page import (
    ViewDatasourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    CLONE_ACTION,
    CLONE_DATA_SOURCE_NOT_FOUND,
    DataSourceFilterType,
    DataSourceStatus,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.constants import FILES_PATH

CLONE_FILE_NAME = "test.txt"

logger = logging.getLogger(__name__)


@pytest.fixture
def git_datasource_to_clone(
    datasource_utils, gitlab_integration, default_embedding_llm
):
    """Git datasource created for one test via the API, deleted in teardown.

    Indexing is not awaited: cloning does not depend on the source's status.
    """
    datasource = datasource_utils.create_gitlab_datasource(
        setting_id=gitlab_integration.id,
        embeddings_model=default_embedding_llm.base_name,
        wait_for_completion=False,
    )
    yield datasource
    try:
        datasource_utils.delete_datasource(datasource)
    except Exception:
        pass


@pytest.fixture
def indexed_git_datasource_to_clone(
    datasource_utils, gitlab_integration, default_embedding_llm
):
    """Fully indexed Git datasource, for tests that update it through the API."""
    datasource = datasource_utils.create_gitlab_datasource(
        setting_id=gitlab_integration.id,
        embeddings_model=default_embedding_llm.base_name,
    )
    yield datasource
    try:
        datasource_utils.delete_datasource(datasource)
    except Exception:
        pass


@pytest.fixture
def clone_cleanup(client, datasource_utils):
    """Names of data sources a test may create; every datasource of the project
    with one of these names is deleted in teardown (best effort, never raises).
    """
    names = []
    yield names
    try:
        datasources = client.datasources.list(per_page=200, projects=[PROJECT])
    except Exception:
        return
    for datasource in datasources:
        if datasource.name in names:
            try:
                datasource_utils.delete_datasource(datasource)
            except Exception:
                pass


@pytest.fixture
def file_datasource_to_clone(datasource_utils, default_embedding_llm):
    """File datasource with one uploaded file, deleted via the API in teardown.

    Indexing is not awaited: the uploaded file is attached to the record when
    the create request returns, and cloning does not depend on the status.
    """
    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        files=[str(FILES_PATH / CLONE_FILE_NAME)],
        embeddings_model=default_embedding_llm.base_name,
        wait_for_completion=False,
    )
    yield datasource
    try:
        datasource_utils.delete_datasource(datasource)
    except Exception as e:
        logger.warning(f"Failed to delete file datasource {datasource.id}: {e}")


# ==================== AC-1: Clone action is offered ====================


# @case clone-datasource_TC_001
@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.prod_regression
def test_clone_action_in_list_actions_menu(page, git_datasource_to_clone):
    """The Data Sources list actions menu of a source offers 'Clone'."""
    datasource_page = DataSourcePage(page)

    datasource_page.navigate_to()
    datasource_page.open_row_action_menu(git_datasource_to_clone.name)
    datasource_page.should_see_clone_menu_item()


# @case clone-datasource_TC_001
@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.prod_regression
def test_clone_button_on_details_page(page, git_datasource_to_clone):
    """The source details page offers a 'Clone' button."""
    datasource_page = DataSourcePage(page)
    view_page = ViewDatasourcePage(page)

    datasource_page.navigate_to()
    datasource_page.open_datasource_details(git_datasource_to_clone.name)
    view_page.should_see_ds_name_and_owner(datasource_name=git_datasource_to_clone.name)
    view_page.should_see_clone_button()


# ==================== AC-2: Clone opens a prefilled create form ====================


# @case clone-datasource_TC_002
@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.prod_regression
def test_clone_opens_prefilled_form_for_source(page, git_datasource_to_clone):
    """Clone opens /data-sources/<id>/clone with the source configuration prefilled and the name empty."""
    datasource_page = DataSourcePage(page)
    clone_page = CreateEditDatasourcePage(page)

    datasource_page.navigate_to()
    datasource_page.open_and_select_row_action(
        git_datasource_to_clone.name, CLONE_ACTION
    )

    clone_page.should_be_on_clone_page(git_datasource_to_clone.id)
    clone_page.should_see_clone_form_prefilled(
        description=git_datasource_to_clone.description,
        repo_link=git_datasource_to_clone.code.link,
        branch=git_datasource_to_clone.code.branch,
    )


# ==================== AC-3, AC-5, AC-6: Saving creates an independent copy ====================


# @case clone-datasource_TC_003
@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.prod_regression
def test_clone_saves_independent_datasource(
    page,
    datasource_utils,
    gitlab_integration,
    indexed_git_datasource_to_clone,
    clone_cleanup,
):
    """Editing the prefilled values and saving creates a separate data source; source and clone do not affect each other."""
    source = indexed_git_datasource_to_clone
    clone_name = get_random_name()
    clone_description = get_random_name()
    updated_source_description = get_random_name()
    updated_clone_description = get_random_name()
    clone_cleanup.append(clone_name)

    datasource_page = DataSourcePage(page)
    clone_page = CreateEditDatasourcePage(page)

    datasource_page.navigate_to()
    datasource_page.open_and_select_row_action(source.name, CLONE_ACTION)
    clone_page.should_see_clone_form_prefilled(
        description=source.description,
        repo_link=source.code.link,
        branch=source.code.branch,
    )
    clone_page.fill_name(clone_name)
    clone_page.fill_description(clone_description)
    clone_page.click_create()

    datasource_page.should_see_table_row_with_values(
        name=clone_name,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=DataSourceFilterType.CODE,
        created_by=TEST_USER,
    )

    clone = datasource_utils.get_datasource_by_name(clone_name)
    source_after_clone = datasource_utils.get_datasource(source.id)

    assert_that(clone.id, is_not(equal_to(source.id)), "Clone must have its own id")
    assert_that(clone.name, equal_to(clone_name), "Clone holds the entered name")
    assert_that(
        clone.description, equal_to(clone_description), "Clone holds edited description"
    )
    assert_that(
        clone.code.link, equal_to(source.code.link), "Clone keeps the source repo link"
    )
    assert_that(
        clone.code.branch, equal_to(source.code.branch), "Clone keeps the source branch"
    )
    assert_that(source_after_clone.name, equal_to(source.name), "Source name unchanged")
    assert_that(
        source_after_clone.description,
        equal_to(source.description),
        "Source description is unchanged by saving the clone",
    )

    datasource_utils.update_gitlab_datasource(
        source.id,
        setting_id=gitlab_integration.id,
        description=updated_source_description,
    )
    assert_that(
        datasource_utils.get_datasource(clone.id).description,
        equal_to(clone_description),
        "Clone is not affected by an update of the source",
    )

    datasource_utils.update_gitlab_datasource(
        clone.id,
        setting_id=gitlab_integration.id,
        description=updated_clone_description,
    )
    assert_that(
        datasource_utils.get_datasource(source.id).description,
        equal_to(updated_source_description),
        "Source is not affected by an update of the clone",
    )


# ==================== AC-4: Name is required and unique ====================


# @case clone-datasource_TC_004
@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.prod_regression
def test_clone_with_empty_name_is_blocked(page, git_datasource_to_clone):
    """Saving a clone with the name left empty shows the required-name validation and stays on the clone page."""
    datasource_page = DataSourcePage(page)
    clone_page = CreateEditDatasourcePage(page)

    datasource_page.navigate_to()
    datasource_page.open_and_select_row_action(
        git_datasource_to_clone.name, CLONE_ACTION
    )
    clone_page.should_see_clone_form_prefilled(
        description=git_datasource_to_clone.description,
        repo_link=git_datasource_to_clone.code.link,
        branch=git_datasource_to_clone.code.branch,
    )
    clone_page.click_create()

    clone_page.should_see_name_required_error()
    clone_page.should_be_on_clone_page(git_datasource_to_clone.id)


# @case clone-datasource_TC_004
@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.prod_regression
def test_clone_with_duplicate_name_is_rejected(
    page, datasource_utils, git_datasource_to_clone, clone_cleanup
):
    """Saving a clone under the source's own name is rejected with 409 and creates no second data source."""
    clone_cleanup.append(git_datasource_to_clone.name)
    datasource_page = DataSourcePage(page)
    clone_page = CreateEditDatasourcePage(page)

    datasource_page.navigate_to()
    datasource_page.open_and_select_row_action(
        git_datasource_to_clone.name, CLONE_ACTION
    )
    clone_page.should_see_clone_form_prefilled(
        description=git_datasource_to_clone.description,
        repo_link=git_datasource_to_clone.code.link,
        branch=git_datasource_to_clone.code.branch,
    )
    clone_page.fill_name(git_datasource_to_clone.name)
    create_status = clone_page.click_create_and_get_create_status()

    assert_that(
        create_status,
        equal_to(HTTPStatus.CONFLICT),
        "Create request with an existing name must be rejected with 409",
    )
    clone_page.should_be_on_clone_page(git_datasource_to_clone.id)
    assert_that(
        datasource_utils.count_datasources_by_name(git_datasource_to_clone.name),
        equal_to(1),
        "Rejected clone must not create a second data source with the same name",
    )


# ==================== AC-7: Unavailable source ====================


# @case clone-datasource_TC_005
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.prod_regression
def test_clone_route_for_unknown_datasource_is_blocked(page):
    """/clone for a non-existent data source shows 'Data source not found' and Save is disabled."""
    clone_page = CreateEditDatasourcePage(page)

    clone_page.navigate_to_clone(str(uuid.uuid4()))
    clone_page.should_see_clone_blocked(CLONE_DATA_SOURCE_NOT_FOUND)


# ==================== File data source ====================


# @case clone-datasource_TC_012
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.prod_regression
def test_clone_file_datasource_clears_uploaded_files(page, file_datasource_to_clone):
    """Cloning a file data source keeps its settings but the uploaded file list is empty."""
    source = file_datasource_to_clone
    datasource_page = DataSourcePage(page)
    form_page = CreateEditDatasourcePage(page)

    # Control: the source itself lists its uploaded file on the edit form
    datasource_page.navigate_to()
    datasource_page.open_and_select_row_action(source.name, "Edit")
    form_page.should_see_uploaded_file_by_name(CLONE_FILE_NAME)

    datasource_page.navigate_to()
    datasource_page.open_and_select_row_action(source.name, CLONE_ACTION)
    form_page.should_be_on_clone_page(source.id)
    form_page.should_see_file_clone_form_without_files(
        description=source.description, file_name=CLONE_FILE_NAME
    )
