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

from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceType,
    GIT_FILES_FILTER_PLACEHOLDER_EXAMPLES,
)


# @case improve-files-filter-placeholder-examples_TC_001
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.parametrize(
    "example",
    GIT_FILES_FILTER_PLACEHOLDER_EXAMPLES,
    ids=GIT_FILES_FILTER_PLACEHOLDER_EXAMPLES,
)
def test_git_datasource_files_filter_placeholder_lists_example(page, example):
    create_page = CreateEditDatasourcePage(page)
    create_page.navigate_to()
    create_page.select_datasource_type(DataSourceType.GIT)
    create_page.should_see_files_filter_placeholder_line(example)
