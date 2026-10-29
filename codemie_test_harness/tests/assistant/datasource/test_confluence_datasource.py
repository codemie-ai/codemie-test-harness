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

"""Tests for Confluence datasource operations - Final version."""

import os

import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_sdk.models.datasource import DataSourceStatus
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.test_data.pm_tools_test_data import (
    CONFLUENCE_TOOL_PROMPT,
    RESPONSE_FOR_CONFLUENCE_TOOL,
    CONFLUENCE_CLOUD_TOOL_PROMPT,
    RESPONSE_FOR_CONFLUENCE_CLOUD_TOOL,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_response,
    assert_tool_triggered,
)
from codemie_test_harness.tests.enums.tools import Default


@pytest.fixture(scope="function")
def confluence_cloud_datasource(
    datasource_utils, confluence_cloud_integration, confluence_cloud_seed_page
):
    datasource = datasource_utils.create_confluence_datasource(
        setting_id=confluence_cloud_integration.id,
        cql=confluence_cloud_seed_page.cql,
    )
    yield datasource
    if datasource:
        datasource_utils.delete_datasource(datasource)


@pytest.mark.datasource
@pytest.mark.project_management
@pytest.mark.api
@pytest.mark.parametrize(
    "datasource_fixture, prompt, expected_response",
    [
        pytest.param(
            "confluence_datasource",
            CONFLUENCE_TOOL_PROMPT,
            RESPONSE_FOR_CONFLUENCE_TOOL,
            marks=pytest.mark.confluence,
            id="Confluence",
        ),
        pytest.param(
            "confluence_cloud_datasource",
            CONFLUENCE_CLOUD_TOOL_PROMPT,
            RESPONSE_FOR_CONFLUENCE_CLOUD_TOOL,
            marks=[
                pytest.mark.confluence,
                pytest.mark.confluence_cloud,
                pytest.mark.smoke,
            ],
            id="Confluence Cloud",
        ),
    ],
)
def test_create_datasource_with_confluence_and_confluence_cloud_integration(
    request,
    assistant,
    assistant_utils,
    datasource_utils,
    kb_context,
    similarity_check,
    datasource_fixture,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    datasource = request.getfixturevalue(datasource_fixture)
    assistant = assistant(
        context=kb_context(datasource), system_prompt="Run tools on each user prompt"
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, minimal_response=False
    )
    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    similarity_check.check_similarity(response, expected_response)

    datasource_utils.update_confluence_datasource(
        datasource.id, full_reindex=True, skip_reindex=False
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, minimal_response=False
    )
    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.datasource
@pytest.mark.confluence
@pytest.mark.api
def test_edit_description_for_confluence_data_source(
    client, confluence_datasource, datasource_utils
):
    updated_description = get_random_name()

    datasource_utils.update_confluence_datasource(
        confluence_datasource.id, description=updated_description
    )

    updated_datasource = client.datasources.get(confluence_datasource.id)
    assert_that(updated_datasource.description, equal_to(updated_description))


@pytest.mark.datasource
@pytest.mark.confluence
@pytest.mark.api
def test_create_confluence_datasource_with_existing_name(
    datasource_utils, confluence_datasource
):
    datasource = datasource_utils.get_datasource(confluence_datasource.id)

    try:
        datasource_utils.create_confluence_datasource(
            name=datasource.name, setting_id=datasource.setting_id
        )
        raise AssertionError("There are no error message for duplicate datasource name")
    except HTTPError as e:
        assert_response(
            e.response,
            409,
            f"An index with the name '{datasource.name}' already exists in the project '{os.getenv('PROJECT_NAME')}'.",
        )


@pytest.fixture
def confluence_context_menu_reindex_setup(project, integration_utils, datasource_utils):
    """
    Isolated setup for context-menu reindex test.

    Creates a new project with 3 Confluence integrations: invalid-1, valid, invalid-2.
    The datasource is created using the valid integration.
    Verifies that reindex uses kb_index.setting_id rather than the first integration.
    """
    isolated_project = project()

    invalid_creds = CredentialsManager.invalid_confluence_credentials()
    invalid_integration_1 = integration_utils.create_integration(
        CredentialTypes.CONFLUENCE, invalid_creds, project_name=isolated_project.name
    )
    valid_integration = integration_utils.create_integration(
        CredentialTypes.CONFLUENCE,
        CredentialsManager.confluence_credentials(),
        project_name=isolated_project.name,
    )
    invalid_integration_2 = integration_utils.create_integration(
        CredentialTypes.CONFLUENCE, invalid_creds, project_name=isolated_project.name
    )

    datasource = datasource_utils.create_confluence_datasource(
        setting_id=valid_integration.id,
        project_name=isolated_project.name,
    )

    yield datasource

    datasource_utils.delete_datasource(datasource)
    for intg in [invalid_integration_1, valid_integration, invalid_integration_2]:
        try:
            integration_utils.delete_integration(intg)
        except HTTPError:
            pass


@pytest.mark.datasource
@pytest.mark.confluence
@pytest.mark.api
def test_confluence_datasource_context_menu_reindex_without_setting_id(
    datasource_utils, confluence_context_menu_reindex_setup
):
    """
    Regression test: context-menu reindex resolves integration via kb_index.setting_id.

    Verifies that a full reindex uses the stored kb_index.setting_id (the valid
    integration) rather than falling back to the first integration in the project
    (which would be an invalid-token integration, causing reindex to fail).
    """
    updated_datasource = datasource_utils.update_confluence_datasource(
        confluence_context_menu_reindex_setup.id,
        full_reindex=True,
        skip_reindex=False,
    )

    assert_that(updated_datasource.status, equal_to(DataSourceStatus.COMPLETED))
