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

from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests import CredentialsManager
from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceFilterType,
)


@pytest.mark.sanity
@pytest.mark.datasource
@pytest.mark.ui
@pytest.mark.not_for_parallel_run
def test_integration_appears_and_disappears_after_refresh(
    page, managed_integration, integration_utils
):
    """Verify the Refresh button on the Create DataSource page updates the integrations dropdown.

    Scenario:
    1. Open the Create DataSource page and select Confluence type.
    2. Assert Refresh button is visible (AC-1).
    3. Create a Confluence integration via API.
    4. Click Refresh — assert the new integration alias appears in the dropdown (AC-2, AC-3).
    5. Delete the integration via API.
    6. Click Refresh again — assert the alias is no longer in the dropdown (AC-2).

    Cleanup is handled by the managed_integration fixture, which tolerates the
    double-delete that results from the explicit mid-test deletion in step 5.
    """
    create_page = CreateEditDatasourcePage(page)
    create_page.navigate_to()
    create_page.select_datasource_type(DataSourceFilterType.CONFLUENCE)
    create_page.should_see_refresh_integrations_button()

    # Must be a global USER-scope integration: the Refresh button calls
    # userSettingsStore.indexSettings() which fetches from v1/settings/user/available,
    # so only USER-scope integrations appear in the dropdown after refresh.
    integration = managed_integration(
        credential_type=CredentialTypes.CONFLUENCE,
        credentials=CredentialsManager.confluence_credentials(),
    )
    alias = integration.alias

    create_page.click_refresh_integrations()
    create_page.should_see_integration_in_dropdown(alias)

    integration_utils.delete_integration(integration)

    create_page.click_refresh_integrations()
    create_page.should_not_see_integration_in_dropdown(alias)
