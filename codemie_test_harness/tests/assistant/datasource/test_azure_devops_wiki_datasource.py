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

import os

import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_sdk.models.datasource import DataSourceStatus
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.enums.tools import Default
from codemie_test_harness.tests.test_data.ado_wiki_tools_test_data import (
    ADO_WIKI_DATASOURCE,
    ADO_WIKI_DATASOURCE_COMMENTS,
    ADO_WIKI_DATASOURCE_ATTACHMENTS,
    ADO_WIKI_DATASOURCE_PAGE_CONTENT,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_response,
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.mark.datasource
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.smoke
def test_create_azure_devops_wiki_datasource_with_assistant(
    ado_seed,
    ado_wiki_datasource,
    ado_integration,
    datasource_utils,
    assistant,
    assistant_utils,
    kb_context,
    similarity_check,
    seeded,
):
    """
    Test datasource creation with Azure DevOps Wiki integration and assistant interaction.

    Validates:
    - Datasource is created successfully with valid integration
    - Datasource can be used as knowledge base context for assistant
    - Assistant can search wiki pages using the datasource
    - Search results contain information about the seeded wiki parent page

    ``ado_seed`` is requested ahead of ``ado_wiki_datasource`` so the seeded
    page this test searches for exists before the datasource is created and
    indexes the wiki.
    """
    test_assistant = assistant(
        context=kb_context(ado_wiki_datasource),
        system_prompt="Search the knowledge base for relevant information on each user prompt",
    )

    answer, triggered_tools = assistant_utils.ask_assistant(
        test_assistant,
        seeded(ADO_WIKI_DATASOURCE["prompt_to_assistant"]),
        minimal_response=False,
    )

    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    similarity_check.check_similarity(
        answer, seeded(ADO_WIKI_DATASOURCE["expected_llm_answer"])
    )


@pytest.mark.datasource
@pytest.mark.ado
@pytest.mark.api
def test_reindex_azure_devops_wiki_datasource(
    ado_seed,
    ado_wiki_datasource,
    datasource_utils,
    assistant,
    assistant_utils,
    kb_context,
    similarity_check,
    seeded,
):
    """
    Test full reindex functionality for Azure DevOps Wiki datasource.

    Validates:
    - Full reindex can be triggered via update operation
    - Datasource status returns to COMPLETED after reindex
    - Assistant can still query the datasource after reindex
    - Response contains information about the seeded wiki parent page

    ``ado_seed`` is requested ahead of ``ado_wiki_datasource`` so the seeded
    page this test searches for exists before the datasource is created and
    indexes the wiki.
    """
    test_assistant = assistant(
        context=kb_context(ado_wiki_datasource),
        system_prompt="Search the knowledge base for relevant information on each user prompt",
    )

    # Trigger full reindex
    datasource_utils.update_azure_devops_wiki_datasource(
        ado_wiki_datasource.id, full_reindex=True, skip_reindex=False
    )

    # Verify assistant can still query the datasource after reindex
    answer, triggered_tools = assistant_utils.ask_assistant(
        test_assistant,
        seeded(ADO_WIKI_DATASOURCE["prompt_to_assistant"]),
        minimal_response=False,
    )

    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    similarity_check.check_similarity(
        answer, seeded(ADO_WIKI_DATASOURCE["expected_llm_answer"])
    )


@pytest.mark.datasource
@pytest.mark.ado
@pytest.mark.api
def test_edit_description_for_azure_devops_wiki_datasource(
    client,
    ado_wiki_datasource,
    datasource_utils,
):
    """
    Test updating datasource description without reindexing.

    Validates:
    - Description can be updated successfully
    - Update does not trigger reindexing
    - Other metadata remains unchanged
    """
    updated_description = get_random_name()

    datasource_utils.update_azure_devops_wiki_datasource(
        ado_wiki_datasource.id, description=updated_description, skip_reindex=True
    )

    updated_datasource = client.datasources.get(ado_wiki_datasource.id)
    assert_that(updated_datasource.description, equal_to(updated_description))


@pytest.mark.datasource
@pytest.mark.ado
@pytest.mark.api
def test_create_azure_devops_wiki_datasource_with_existing_name(
    ado_wiki_datasource, datasource_utils
):
    """
    Test error handling for duplicate datasource names.

    Validates:
    - Creating datasource with existing name returns 409 Conflict
    - Error message indicates duplicate name
    """
    datasource = datasource_utils.get_datasource(ado_wiki_datasource.id)

    try:
        datasource_utils.create_azure_devops_wiki_datasource(
            name=datasource.name,
            setting_id=datasource.setting_id,
        )
        raise AssertionError("There are no error message for duplicate datasource name")
    except HTTPError as e:
        assert_response(
            e.response,
            409,
            f"An index with the name '{datasource.name}' already exists in the project '{os.getenv('PROJECT_NAME')}'.",
        )


@pytest.mark.datasource
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.smoke
def test_azure_devops_wiki_datasource_indexes_comments(
    ado_seed,
    ado_wiki_datasource,
    assistant,
    assistant_utils,
    kb_context,
    similarity_check,
    seeded,
):
    """
    Test that Azure DevOps Wiki datasource indexes and makes searchable page comments.

    Validates:
    - Datasource indexes comments from wiki pages
    - Comments are searchable via SEARCH_KB tool
    - Search results include comment text associated with parent page
    - Covers AC#1: Comments are indexed and searchable and associated with the parent wiki page

    ``ado_seed`` is requested ahead of ``ado_wiki_datasource`` so the seeded
    child page's comments this test searches for exist before the
    datasource is created and indexes the wiki.
    """
    test_assistant = assistant(
        context=kb_context(ado_wiki_datasource),
        system_prompt="Search the knowledge base for relevant information on each user prompt",
    )

    answer, triggered_tools = assistant_utils.ask_assistant(
        test_assistant,
        seeded(ADO_WIKI_DATASOURCE_COMMENTS["prompt_to_assistant"]),
        minimal_response=False,
    )

    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    similarity_check.check_similarity(
        answer, seeded(ADO_WIKI_DATASOURCE_COMMENTS["expected_llm_answer"])
    )


@pytest.mark.datasource
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.smoke
def test_azure_devops_wiki_datasource_indexes_attachments(
    ado_seed,
    ado_wiki_datasource,
    assistant,
    assistant_utils,
    kb_context,
    similarity_check,
    seeded,
):
    """
    Test that Azure DevOps Wiki datasource indexes and makes searchable page attachments.

    Validates:
    - Datasource indexes attachments
    - Attachments of supported types
    - Attachment content is searchable via SEARCH_KB tool
    - Search results include attachment content associated with parent page
    - Covers AC#2: Attachments from data source are indexed and searchable and associated with the parent wiki page

    ``ado_seed`` is requested ahead of ``ado_wiki_datasource`` so the seed
    attachment this test searches for is attached to the seed wiki page
    before the datasource is created and indexes the wiki.
    """
    test_assistant = assistant(
        context=kb_context(ado_wiki_datasource),
        system_prompt="Search the knowledge base for relevant information on each user prompt",
    )

    answer, triggered_tools = assistant_utils.ask_assistant(
        test_assistant,
        seeded(ADO_WIKI_DATASOURCE_ATTACHMENTS["prompt_to_assistant"]),
        minimal_response=False,
    )

    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    similarity_check.check_similarity(
        answer, seeded(ADO_WIKI_DATASOURCE_ATTACHMENTS["expected_llm_answer"])
    )


@pytest.mark.datasource
@pytest.mark.ado
@pytest.mark.api
def test_azure_devops_wiki_datasource_page_content_search(
    ado_seed,
    ado_wiki_datasource,
    assistant,
    assistant_utils,
    kb_context,
    similarity_check,
    seeded,
):
    """
    Test that Azure DevOps Wiki datasource search returns content from all sources.

    Validates:
    - Search results include content from page body
    - Covers AC#3: Search results include page content

    ``ado_seed`` is requested ahead of ``ado_wiki_datasource`` so the seeded
    page this test searches for exists before the datasource is created and
    indexes the wiki.
    """
    test_assistant = assistant(
        context=kb_context(ado_wiki_datasource),
        system_prompt="Search the knowledge base for relevant information on each user prompt",
    )

    answer, triggered_tools = assistant_utils.ask_assistant(
        test_assistant,
        seeded(ADO_WIKI_DATASOURCE_PAGE_CONTENT["prompt_to_assistant"]),
        minimal_response=False,
    )

    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    similarity_check.check_similarity(
        answer, seeded(ADO_WIKI_DATASOURCE_PAGE_CONTENT["expected_llm_answer"])
    )


@pytest.fixture
def ado_wiki_context_menu_reindex_setup(project, integration_utils, datasource_utils):
    """
    Isolated setup for context-menu reindex test.

    Creates a new project with 3 Azure DevOps integrations: invalid-1, valid, invalid-2.
    The datasource is created using the valid integration.
    Verifies that reindex uses kb_index.setting_id rather than the first integration.
    """
    isolated_project = project()

    invalid_creds = CredentialsManager.invalid_ado_credentials()
    invalid_integration_1 = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, invalid_creds, project_name=isolated_project.name
    )
    valid_integration = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS,
        CredentialsManager.azure_devops_credentials(),
        project_name=isolated_project.name,
    )
    invalid_integration_2 = integration_utils.create_integration(
        CredentialTypes.AZURE_DEVOPS, invalid_creds, project_name=isolated_project.name
    )

    datasource = datasource_utils.create_azure_devops_wiki_datasource(
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
@pytest.mark.ado
@pytest.mark.api
@pytest.mark.xfail(
    reason="Datasource indexing fails - investigating root cause",
    strict=False,
)
def test_ado_wiki_datasource_context_menu_reindex_without_setting_id(
    datasource_utils, ado_wiki_context_menu_reindex_setup
):
    """
    Regression test: context-menu reindex resolves integration via kb_index.setting_id.

    Verifies that a full reindex uses the stored kb_index.setting_id (the valid
    integration) rather than falling back to the first integration in the project
    (which would be an invalid-token integration, causing reindex to fail).
    """
    updated_datasource = datasource_utils.update_azure_devops_wiki_datasource(
        ado_wiki_context_menu_reindex_setup.id,
        full_reindex=True,
        skip_reindex=False,
    )

    assert_that(updated_datasource.status, equal_to(DataSourceStatus.COMPLETED))
