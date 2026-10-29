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
UI tests for manual Full Reindex of Git FAQ datasources.
"""

import pytest
from codemie_sdk.models.datasource import DataSourceStatus as ApiDataSourceStatus
from hamcrest import assert_that, equal_to, greater_than

from codemie_test_harness.tests import CredentialsManager
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceStatus,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name

REINDEX_TIMEOUT_SECONDS = 180


@pytest.fixture(scope="function")
def git_faq_datasource(datasource_utils, gitlab_integration):
    """Indexed Git FAQ datasource, deleted in teardown (reindex mutates it)."""
    datasource = datasource_utils.create_git_faq_datasource(
        name=get_random_name(),
        link=CredentialsManager.get_parameter("GITLAB_PROJECT"),
        branch="main",
        setting_id=gitlab_integration.id,
    )
    yield datasource
    try:
        datasource_utils.delete_datasource(datasource)
    except Exception:
        pass


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.ui
def test_git_faq_datasource_full_reindex_from_list_refreshes_updated_date(
    page, datasource_utils, git_faq_datasource
):
    """Full Reindex is offered for a completed Git FAQ datasource; running it refreshes Updated and ends Completed."""
    datasource_page = DataSourcePage(page)
    datasource_name = git_faq_datasource.name
    update_date_before = git_faq_datasource.update_date

    datasource_page.navigate_to()
    datasource_page.should_see_table_row_with_values(
        name=datasource_name, status=DataSourceStatus.COMPLETED
    )
    datasource_page.open_row_action_menu(datasource_name)
    datasource_page.should_see_full_reindex_menu_item()
    datasource_page.click_full_reindex()

    datasource_utils.wait_for_update_date_change(
        git_faq_datasource.id,
        timeout=REINDEX_TIMEOUT_SECONDS,
        initial_update_date=update_date_before,
    )

    completed = datasource_utils.wait_for_indexing(
        git_faq_datasource.id, timeout=REINDEX_TIMEOUT_SECONDS
    )
    assert_that(
        completed.status,
        equal_to(ApiDataSourceStatus.COMPLETED),
        "Git FAQ datasource must return to COMPLETED after Full Reindex",
    )
    assert_that(
        completed.update_date,
        greater_than(update_date_before),
        "Updated date must remain later than before the Full Reindex",
    )

    datasource_page.navigate_to()
    datasource_page.should_see_table_row_with_values(
        name=datasource_name, status=DataSourceStatus.COMPLETED
    )
