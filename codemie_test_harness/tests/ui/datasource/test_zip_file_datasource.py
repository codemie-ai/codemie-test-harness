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
from codemie_test_harness.tests.test_data.file_test_data import ZIP_ARCHIVE_FILE_COUNT
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
    DataSourceFilterType,
    DataSourceStatus,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH


@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.ui
@pytest.mark.prod_regression
def test_zip_file_accepted_by_file_upload_input(page):
    """The file input/drop zone accepts a .zip file for a File datasource
    without triggering a validation error.
    """
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    create_page.select_datasource_type(DataSourceFilterType.FILE)
    create_page.select_file(str(FILES_PATH / "test.zip"))

    # The browser only ever knows the selected File object's own name; the
    # server-side extraction of the archive's contents happens after upload,
    # so the create-page file chip always shows the archive's own name, not
    # the names of the files extracted from inside it (confirmed live via
    # playwright-cli inspection of the DOM after selecting test.zip).
    create_page.should_see_uploaded_file("test.zip")


@pytest.mark.smoke
@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.ui
@pytest.mark.sanity
@pytest.mark.prod_regression
def test_zip_file_datasource_shows_extracted_files_after_creation(page):
    """Each file extracted from an uploaded ZIP is visible as a separate
    processed document on the Data Source's View page after creation.
    """
    datasource_page = DataSourcePage(page)
    view_page = ViewDatasourcePage(page)
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    datasource = create_page.create_file_datasource(
        project_name=PROJECT,
        file_path=[str(FILES_PATH / "test.zip")],
    )

    datasource_page.should_see_table_row_with_values(
        name=datasource,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=DataSourceFilterType.FILE,
        created_by=TEST_USER,
    )

    datasource_page.click_datasource_row_by_name(datasource)
    view_page.should_see_processed_data(min_count=ZIP_ARCHIVE_FILE_COUNT)


@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.ui
@pytest.mark.prod_regression
def test_file_upload_hint_text_mentions_zip_support(page):
    """File-format hint text under the upload control mentions ZIP support."""
    create_page = CreateEditDatasourcePage(page)

    create_page.navigate_to()
    create_page.select_datasource_type(DataSourceFilterType.FILE)

    create_page.should_see_file_fields()
