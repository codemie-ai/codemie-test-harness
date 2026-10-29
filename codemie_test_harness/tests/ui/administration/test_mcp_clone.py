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

"""UI test for cloning an MCP server from Settings > MCPs.

Pattern: the source MCP is created and removed through the API; the clone flow
is driven and asserted through the browser.
"""

import pytest
from codemie_sdk.models.mcp_config import MCPConfigCreateRequest, MCPServerConfigData

from codemie_test_harness.tests.test_data.mcp_config_clone_test_data import (
    CLONE_DUPLICATE_NAME_MESSAGE,
    mcp_clone_source_data,
)
from codemie_test_harness.tests.ui.pageobject.administration.mcp_management_page import (
    McpManagementPage,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.mcp_config_utils import McpConfigUtils


@pytest.fixture
def mcp_source(client):
    """Source MCP config created via the API."""
    data = mcp_clone_source_data()
    created = client.mcp_configs.create(
        MCPConfigCreateRequest(
            name=data.name,
            description=data.description,
            server_home_url=data.server_home_url,
            source_url=data.source_url,
            categories=data.categories,
            config=MCPServerConfigData(
                url=data.url, type=data.type, headers=data.headers
            ),
        )
    )
    yield data
    try:
        client.mcp_configs.delete(created.id)
    except Exception:
        pass


@pytest.fixture
def clone_name(client):
    """Name the test gives the clone; configs with that name are removed on teardown."""
    name = get_random_name()
    yield name
    try:
        McpConfigUtils(client).delete_by_name(name)
    except Exception:
        pass


@pytest.fixture
def mcp_page(page, mcp_source):
    pom = McpManagementPage(page)
    pom.navigate_to()
    pom.show_100_items_per_page()
    return pom


@pytest.mark.mcp
@pytest.mark.ui
def test_clone_mcp_server_from_list_validates_name_and_creates_clone(
    mcp_page, mcp_source, clone_name
):
    mcp_page.should_see_server_in_list(mcp_source.name)

    mcp_page.open_clone_dialog(mcp_source.name)
    mcp_page.should_see_clone_dialog()
    mcp_page.should_have_empty_clone_name()
    mcp_page.should_have_clone_documentation_link(mcp_source.server_home_url)

    mcp_page.submit_clone()
    mcp_page.should_see_name_required_error()
    mcp_page.should_see_clone_dialog()

    mcp_page.fill_clone_name(mcp_source.name)
    mcp_page.submit_clone()
    mcp_page.should_see_error_toast_with_text(CLONE_DUPLICATE_NAME_MESSAGE)
    mcp_page.should_see_error_toast_with_text(
        f"An MCP configuration with name '{mcp_source.name}' already exists"
    )
    mcp_page.should_see_clone_dialog()
    mcp_page.should_see_server_count_in_list(mcp_source.name, 1)

    mcp_page.fill_clone_name(clone_name)
    mcp_page.submit_clone()
    mcp_page.should_not_see_clone_dialog()
    mcp_page.should_see_server_in_list(clone_name)


@pytest.mark.mcp
@pytest.mark.ui
@pytest.mark.parametrize("acting_credentials", ["plain_user"], indirect=True)
def test_mcp_management_page_is_not_available_for_user_without_permission(
    page, mcp_source
):
    McpManagementPage(page).open_without_waiting_for_content().should_see_not_found()
