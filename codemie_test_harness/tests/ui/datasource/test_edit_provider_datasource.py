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
E2E tests for editing DSP-based (provider) Data Sources,
migrated to the combined AICE provider.

Covers a full journey through a provider configured with `default_value` on
every defaultable schema field (create -> view -> edit -> save -> verify),
and the parameter-persistence behavior (dropping an obsolete parameter on
update, retaining stored values when the provider declares none).

The default-value journey test creates its own isolated provider via
`provider_with_default_values`; the parameter-persistence cases use
`isolated_provider` / `isolated_provider_datasource`.
"""

import pytest

from codemie_test_harness.tests import PROJECT, TEST_USER
from codemie_test_harness.tests.test_data.provider_toolkit_test_data import (
    DEFAULT_GRAPHDB_PASSWORD_VALUE,
    DEFAULT_GRAPHDB_USERNAME_VALUE,
    default_repositories_json,
)
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
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
)
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


@pytest.mark.ui
def test_provider_datasource_fields_default_values(
    page,
    provider_with_default_values,
    datasource_utils,
):
    """
    Full DSP journey, migrated to the combined AICE provider: a provider
    configured with `default_value` on every one
    of its base parameters — repositories/graphdb_username/graphdb_password/
    graphdb_tenant_url — pre-populates all of them on the Create Data Source
    form without typing (none of AICE's base parameters are required). After
    creation, the
    details page shows the resolved config; the edit form shows the same
    persisted values pre-populated; changing one non-critical field
    (Graph Database Username) and saving (not Save & Reindex) updates the
    value without a full reindex, and the change is reflected back on the
    details page.
    """
    provider_name = provider_with_default_values
    repositories = default_repositories_json()

    datasource_page = DataSourcePage(page)
    create_page = CreateEditDatasourcePage(page)
    view_page = ViewDatasourcePage(page)

    create_page.navigate_to()
    name = get_random_name()
    description = get_random_name()
    create_page.fill_name(name)
    create_page.fill_description(description)
    create_page.selector.search_and_select_project(PROJECT)
    create_page.select_provider_datasource_type(provider_name)

    # Every defaulted field is pre-populated before any manual input
    create_page.should_see_provider_fields_prepopulated_from_defaults(
        repositories=repositories,
        graphdb_username=DEFAULT_GRAPHDB_USERNAME_VALUE,
        graphdb_password=DEFAULT_GRAPHDB_PASSWORD_VALUE,
    )

    create_page.click_create()

    datasource_page.should_see_table_row_with_values(
        name=name,
        status=DataSourceStatus.COMPLETED,
        project=PROJECT,
        type_=DataSourceFilterType.PROVIDER,
        created_by=TEST_USER,
    )

    # Details page reflects the resolved (default-sourced) provider config,
    # `repositories` rendered verbatim as the stored JSON text (verified live).
    datasource_page.click_datasource_row_by_name(name)
    view_page.should_see_provider_repositories_details(
        repositories=repositories,
        graphdb_username=DEFAULT_GRAPHDB_USERNAME_VALUE,
        graphdb_password=DEFAULT_GRAPHDB_PASSWORD_VALUE,
        name=name,
        description=description,
    )

    # Edit form pre-populates from the persisted (not just default) values
    datasource_page.navigate_to()
    datasource_page.open_and_select_row_action(name, "Edit")
    create_page.should_be_ready_to_save()
    create_page.should_see_provider_field_values(
        repositories=repositories,
        graphdb_username=DEFAULT_GRAPHDB_USERNAME_VALUE,
        graphdb_password=DEFAULT_GRAPHDB_PASSWORD_VALUE,
    )

    # Change one non-critical field and save WITHOUT triggering a reindex
    new_graphdb_username = f"graphdb-user-{get_random_name()}"
    create_page.fill_provider_graphdb_username(new_graphdb_username)
    create_page.click_save()

    # Updated value is reflected back on the details page
    datasource_page.should_see_datasource_with_name(name)
    datasource_page.click_datasource_row_by_name(name)
    view_page.should_see_provider_graphdb_username_value(new_graphdb_username)


@pytest.mark.ui
def test_update_provider_datasource_drops_parameter_removed_from_provider(
    page,
    providers_utils,
    isolated_provider,
    isolated_provider_datasource,
):
    """

    A parameter removed from the provider definition is dropped from a
    datasource's stored values the next time the datasource is updated, while
    the datasource_id stays. Repositories is removed from the AICE provider
    after the datasource was created with it; the datasource is then edited
    and saved from the UI.
    """
    datasource = isolated_provider_datasource

    datasource_page = DataSourcePage(page)
    create_page = CreateEditDatasourcePage(page)
    view_page = ViewDatasourcePage(page)

    # Baseline: the Repositories row is shown before the provider changes
    datasource_page.navigate_to()
    datasource_page.search_for(datasource.name)
    datasource_page.should_see_datasource_with_name(datasource.name)
    datasource_page.click_datasource_row_by_name(datasource.name)
    view_page.should_see_provider_repositories_details(
        name=datasource.name,
        description=datasource.description,
    )
    datasource_id = view_page.get_provider_datasource_id()

    # Repositories is no longer declared by the provider (setup asserts the PUT is accepted)
    providers_utils.remove_toolkit_parameters(isolated_provider["id"], ["repositories"])

    # Edit and save (without reindex) from the UI
    datasource_page.navigate_to()
    datasource_page.search_for(datasource.name)
    datasource_page.open_and_select_row_action(datasource.name, "Edit")
    create_page.should_be_ready_to_save()
    new_description = f"{datasource.description} - updated"
    create_page.fill_description(new_description)
    create_page.click_save()

    # Repositories row is gone; datasource_id, name and description are intact
    datasource_page.search_for(datasource.name)
    datasource_page.should_see_datasource_with_name(datasource.name)
    datasource_page.click_datasource_row_by_name(datasource.name)
    view_page.should_see_no_repositories_row(
        datasource_id=datasource_id,
        name=datasource.name,
        description=new_description,
    )


@pytest.mark.ui
def test_update_provider_datasource_keeps_parameters_when_provider_declares_none(
    page,
    providers_utils,
    isolated_provider,
    isolated_provider_datasource,
):
    """

    When the provider's parameter definition is empty, updating a datasource
    leaves every stored parameter unchanged (nothing is pruned). All toolkit
    parameters are removed from the AICE provider after the datasource
    was created; the datasource is then edited and saved from the UI.
    """
    datasource = isolated_provider_datasource

    datasource_page = DataSourcePage(page)
    create_page = CreateEditDatasourcePage(page)
    view_page = ViewDatasourcePage(page)

    # Baseline: the stored Repositories row is shown before the provider changes
    datasource_page.navigate_to()
    datasource_page.search_for(datasource.name)
    datasource_page.should_see_datasource_with_name(datasource.name)
    datasource_page.click_datasource_row_by_name(datasource.name)
    view_page.should_see_provider_repositories_details(
        name=datasource.name,
        description=datasource.description,
    )
    datasource_id = view_page.get_provider_datasource_id()

    # The provider declares no parameters (setup asserts the PUT is accepted)
    providers_utils.remove_toolkit_parameters(isolated_provider["id"])

    # Edit and save (without reindex) from the UI
    datasource_page.navigate_to()
    datasource_page.search_for(datasource.name)
    datasource_page.open_and_select_row_action(datasource.name, "Edit")
    create_page.should_be_ready_to_save()
    new_description = f"{datasource.description} - updated"
    create_page.fill_description(new_description)
    create_page.click_save()

    # All previously stored parameters are still shown with their original values
    datasource_page.search_for(datasource.name)
    datasource_page.should_see_datasource_with_name(datasource.name)
    datasource_page.click_datasource_row_by_name(datasource.name)
    view_page.should_see_provider_repositories_details(
        datasource_id=datasource_id,
        name=datasource.name,
        description=new_description,
    )
