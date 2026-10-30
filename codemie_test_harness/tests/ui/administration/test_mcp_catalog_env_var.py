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

"""UI test for removing an environment variable from an MCP catalog server.

Pattern: the catalog server is created and edited through the Administration UI (the SDK
has no admin catalog update call); the `catalog_server` fixture (tests/ui/conftest.py) removes it through the API on teardown.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.mcp_management_page import (
    McpManagementPage,
)


@pytest.fixture
def mcp_page(page):
    pom = McpManagementPage(page)
    pom.navigate_to()
    pom.show_100_items_per_page()
    return pom


@pytest.mark.mcp
@pytest.mark.ui
def test_remove_only_environment_variable_from_catalog_server_persists_after_update(
    mcp_page, catalog_server
):
    # @case mcp-catalog-env-var_TC_001
    mcp_page.open_add_server_dialog()
    mcp_page.fill_server_form(catalog_server)
    mcp_page.add_environment_variable(
        catalog_server.env_var_name, catalog_server.env_var_description
    )
    mcp_page.submit_create()
    mcp_page.should_see_server_dialog_closed()
    mcp_page.should_see_server_in_list(catalog_server.name)

    mcp_page.reload_catalog()
    mcp_page.open_details(catalog_server.name)
    mcp_page.should_see_details_variable_count(1)
    mcp_page.should_see_details_variable(catalog_server.env_var_name)
    mcp_page.close_details(catalog_server.name)

    mcp_page.open_edit_dialog(catalog_server.name)
    mcp_page.should_see_edit_dialog()
    mcp_page.should_see_dialog_environment_variable_count(1)
    mcp_page.should_see_dialog_environment_variable(catalog_server.env_var_name)

    mcp_page.remove_environment_variable()
    mcp_page.should_see_dialog_environment_variable_count(0)
    mcp_page.should_see_no_environment_variables_in_dialog()
    mcp_page.submit_update()
    mcp_page.should_have_sent_empty_env_vars()
    mcp_page.should_see_server_dialog_closed()

    mcp_page.reload_catalog()
    mcp_page.open_details(catalog_server.name)
    mcp_page.should_see_details_variable_count(0)
    mcp_page.should_see_no_variables_in_details()
    mcp_page.should_not_see_details_variable(catalog_server.env_var_name)
    mcp_page.should_see_details_updated_timestamp()
    mcp_page.close_details(catalog_server.name)

    mcp_page.open_edit_dialog(catalog_server.name)
    mcp_page.should_see_edit_dialog()
    mcp_page.should_see_dialog_environment_variable_count(0)
    mcp_page.should_see_no_environment_variables_in_dialog()
