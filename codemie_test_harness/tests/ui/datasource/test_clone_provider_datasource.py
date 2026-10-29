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
E2E test for cloning a provider-based (DSP) Data Source.

Each test creates its own provider (access_token without a default value) and
a data source on it, and deletes both in teardown. AICE is not available on
sandbox environments.
"""

import pytest

from codemie_test_harness.tests.test_data.provider_toolkit_test_data import (
    DEFAULT_GRAPHDB_USERNAME_VALUE,
    default_repositories_json,
)
from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import CLONE_ACTION
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

pytestmark = [
    pytest.mark.datasource,
    pytest.mark.provider,
    pytest.mark.aice,
    pytest.mark.skipif(
        EnvironmentResolver.is_sandbox(),
        reason="AICE is not configured for sandbox environments",
    ),
]


# @case clone-datasource_TC_008
@pytest.mark.gitlab
@pytest.mark.ui
def test_clone_provider_datasource_blanks_secret_fields(
    page, provider_datasource_without_default_password
):
    """Cloning a provider data source keeps its plain settings but leaves the credential field (graph database password) blank."""
    source = provider_datasource_without_default_password
    datasource_page = DataSourcePage(page)
    clone_page = CreateEditDatasourcePage(page)

    datasource_page.navigate_to()
    datasource_page.open_and_select_row_action(source.name, CLONE_ACTION)

    clone_page.should_be_on_clone_page(source.id)
    clone_page.should_see_provider_clone_with_blank_secret(
        repositories=default_repositories_json(),
        graphdb_username=DEFAULT_GRAPHDB_USERNAME_VALUE,
    )
