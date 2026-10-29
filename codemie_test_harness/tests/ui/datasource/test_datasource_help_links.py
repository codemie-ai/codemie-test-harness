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

"""UI Test Suite for Data Source Creation Page Help Links"""

import pytest
from hamcrest import assert_that, contains_string

from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.test_data.links_names_test_data import (
    DatasourceDocUrls,
)


@pytest.mark.ui
@pytest.mark.datasource
def test_datasource_help_links_validation(page):
    """UI Test Suite for Datasource Help Links Validation"""
    create_datasource_page = CreateEditDatasourcePage(page)
    create_datasource_page.navigate_to()

    # Open help panel
    create_datasource_page.click_help_button()
    create_datasource_page.should_have_help_panel_visible()

    # Test "How to work with Data Sources" link
    with page.expect_popup() as popup_info:
        create_datasource_page.help_work_with_datasources_button.click()
    popup = popup_info.value
    assert_that(popup.url, contains_string(DatasourceDocUrls.WORK_WITH_DATASOURCES))
    popup.close()

    # Reopen help panel
    create_datasource_page.click_help_button()

    # Test "How to create Git data source" link
    with page.expect_popup() as popup_info:
        create_datasource_page.help_create_git_datasource_button.click()
    popup = popup_info.value
    assert_that(popup.url, contains_string(DatasourceDocUrls.CREATE_GIT_DATASOURCE))
    popup.close()
