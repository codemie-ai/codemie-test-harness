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
UI tests for datasource operations including delete, sync/reindex management, and status indicators.
"""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests import CredentialsManager, PROJECT, TEST_USER
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.constants import FILES_PATH
from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceStatus,
    FULL_REINDEX_STARTED,
)


# ==================== CATEGORY 1: DELETE DATASOURCE ====================


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
def test_datasource_delete_with_confirmation(
    page, datasource_utils, gitlab_integration, default_embedding_llm
):
    """User clicks delete, confirms in dialog, datasource is removed from UI."""
    datasource_page = DataSourcePage(page)

    datasource = datasource_utils.create_gitlab_datasource(
        setting_id=gitlab_integration.id,
        embeddings_model=default_embedding_llm.base_name,
    )
    datasource_name = datasource.name

    datasource_page.navigate_to()
    datasource_page.should_see_datasource_with_name(datasource_name)
    datasource_page.open_row_action_menu(datasource_name)
    datasource_page.click_row_action("Delete")
    datasource_page.should_see_delete_dialog()
    datasource_page.confirm_delete()
    datasource_page.should_not_see_row(datasource_name)


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
def test_datasource_delete_cancel(page, gitlab_datasource):
    """User clicks delete, cancels in dialog, datasource remains visible."""
    datasource_page = DataSourcePage(page)
    datasource_name = gitlab_datasource.name

    datasource_page.navigate_to()
    datasource_page.should_see_datasource_with_name(datasource_name)
    datasource_page.open_delete_dialog(datasource_name)
    datasource_page.should_see_delete_dialog()
    datasource_page.cancel_delete()
    datasource_page.should_not_see_delete_dialog()
    datasource_page.should_see_datasource_with_name(datasource_name)


@pytest.fixture(scope="function")
def file_datasource_used_by_assistants(datasource_utils):
    """Dedicated file datasource so no unrelated assistant appears in the delete dialog."""
    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        files=[str(FILES_PATH / "test.txt")],
    )
    yield datasource
    try:
        datasource_utils.delete_datasource(datasource)
    except Exception:
        pass


@pytest.mark.datasource
@pytest.mark.assistant
@pytest.mark.ui
def test_datasource_delete_dialog_lists_assistants_using_datasource(
    page, file_datasource_used_by_assistants, assistant_factory, kb_context
):
    """Delete dialog lists every assistant the datasource is attached to, with its creator."""
    datasource_page = DataSourcePage(page)
    datasource_name = file_datasource_used_by_assistants.name
    context = kb_context(file_datasource_used_by_assistants)
    first_assistant = assistant_factory.create(context=[context])
    second_assistant = assistant_factory.create(context=[context])

    datasource_page.navigate_to()
    datasource_page.should_see_datasource_with_name(datasource_name)
    datasource_page.open_row_action_menu(datasource_name)
    datasource_page.click_row_action("Delete")
    datasource_page.should_see_delete_dialog()

    datasource_page.should_see_delete_dialog_used_in_assistants_list()
    datasource_page.should_see_delete_dialog_affected_assistant(
        first_assistant.name, TEST_USER
    )
    datasource_page.should_see_delete_dialog_affected_assistant(
        second_assistant.name, TEST_USER
    )

    datasource_page.cancel_delete()
    datasource_page.should_not_see_delete_dialog()
    datasource_page.should_see_datasource_with_name(datasource_name)


# ==================== CATEGORY 2: SYNC/REINDEX MANAGEMENT ====================


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
def test_datasource_trigger_manual_reindex(page, gitlab_datasource):
    """User initiates manual reindex/sync operation via UI action."""
    datasource_page = DataSourcePage(page)
    datasource_name = gitlab_datasource.name

    datasource_page.navigate_to()
    datasource_page.should_see_table_row_with_values(
        name=datasource_name, status=DataSourceStatus.COMPLETED
    )

    datasource_page.open_row_action_menu(datasource_name)
    datasource_page.should_see_full_reindex_menu_item()
    datasource_page.click_full_reindex()

    datasource_page.should_see_pop_up_message(FULL_REINDEX_STARTED)
    datasource_page.should_see_table_row_with_values(
        name=datasource_name, status=DataSourceStatus.COMPLETED
    )


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
def test_datasource_sync_status_progress_to_completed(
    page, gitlab_integration, default_embedding_llm, datasource_utils
):
    """Status indicator transitions to completed after datasource creation."""
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
        status=DataSourceStatus.FETCHING,
    )

    datasource_page.should_see_table_row_with_values(
        name=datasource,
        status=DataSourceStatus.COMPLETED,
    )


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
def test_datasource_force_ongoing_index_operation(page, gitlab_datasource):
    """User can force/restart an index operation and it completes successfully."""
    datasource_page = DataSourcePage(page)
    datasource_name = gitlab_datasource.name

    datasource_page.navigate_to()
    datasource_page.open_row_action_menu(datasource_name)
    datasource_page.click_full_reindex()
    datasource_page.close_modal_if_visible()
    datasource_page.navigate_to()

    datasource_page.open_row_action_menu(datasource_name)
    datasource_page.should_see_full_reindex_menu_item()
    datasource_page.click_full_reindex()
    datasource_page.should_not_see_error_dialog()

    datasource_page.should_see_table_row_with_values(
        name=datasource_name,
        status=DataSourceStatus.COMPLETED,
    )


# ==================== CATEGORY 3: DATASOURCE STATUS INDICATORS ====================


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
def test_datasource_status_badge_completed_state(page, gitlab_datasource):
    """UI displays status badge for completed datasource. Completed status badge displays with green/success styling"""
    datasource_page = DataSourcePage(page)
    datasource_name = gitlab_datasource.name

    datasource_page.navigate_to()
    datasource_page.should_see_table_row_with_values(
        name=datasource_name, status=DataSourceStatus.COMPLETED
    )

    badge_class = datasource_page.get_status_badge_class(datasource_name)

    assert_that("text-success" in badge_class, equal_to(True))


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
def test_datasource_status_badge_failed_state(page, invalid_gitlab_datasource):
    """UI displays status badge for failed datasource. Failed status badge displays with red/error styling"""
    datasource_page = DataSourcePage(page)
    datasource_name = invalid_gitlab_datasource.name

    datasource_page.navigate_to()
    datasource_page.should_see_table_row_with_values(
        name=datasource_name, status=DataSourceStatus.ERROR
    )

    badge_class = datasource_page.get_status_badge_class(datasource_name)

    assert_that("failed" in badge_class, equal_to(True))
