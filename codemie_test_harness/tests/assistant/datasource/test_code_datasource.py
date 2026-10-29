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
from time import sleep

import pytest
from hamcrest import assert_that, equal_to, not_none
from requests import HTTPError

from codemie_sdk.models.datasource import CodeDataSourceRequest, CodeDataSourceType
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.enums.tools import Default
from codemie_test_harness.tests.test_data.git_datasource_test_data import (
    GITHUB_DATASOURCE_REQUEST,
    GITHUB_DATASOURCE_RESPONSE,
)
from codemie_test_harness.tests.test_data.index_test_data import (
    index_test_data,
    get_first_embedding_model_from_api,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_response,
    assert_tool_triggered,
    wait_for_entity,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


def pytest_generate_tests(metafunc):
    """Dynamically parametrize embedding_model based on test markers."""
    if "embedding_model" in metafunc.fixturenames:
        # Check if smoke marker is present in the test
        marker_option = metafunc.config.getoption("-m", default="")
        is_smoke = "smoke" in marker_option if marker_option else False

        # For smoke tests: use first model from API, for api tests: use hardcoded list
        if is_smoke:
            test_data = get_first_embedding_model_from_api()
        else:
            test_data = index_test_data

        metafunc.parametrize(
            "embedding_model",
            test_data,
            ids=[param.values[0] for param in test_data],
        )


@pytest.fixture
def indexing_code_datasource(client, gitlab_integration, default_embedding_llm):
    """Create a code datasource without waiting for indexing to complete."""
    datasource_name = get_random_name()
    create_request = CodeDataSourceRequest(
        project_name=PROJECT,
        link=CredentialsManager.get_parameter("GITLAB_PROJECT_2"),
        branch="main",
        index_type=CodeDataSourceType.CODE,
        embeddings_model=default_embedding_llm.base_name,
        setting_id=gitlab_integration.id,
        description=get_random_name(),
        name=datasource_name,
    )
    client.datasources.create(create_request)
    datasource = wait_for_entity(
        lambda: client.datasources.list(per_page=200),
        entity_name=datasource_name,
    )
    yield datasource
    try:
        client.datasources.delete(datasource.id)
    except HTTPError:
        pass  # Already deleted by the test


@pytest.mark.datasource
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.smoke
def test_create_index_application_with_embedding_model(
    gitlab_integration,
    datasource_utils,
    assistant,
    assistant_utils,
    similarity_check,
    code_context,
    embedding_model,
):
    question = "Get repo tree and suggest what programming language repository has?"
    expected_answer = """
        The repository primarily uses Java as the programming language,
        as indicated by the file paths and extensions such as .java.
    """

    datasource = datasource_utils.create_gitlab_datasource(
        setting_id=gitlab_integration.id, embeddings_model=embedding_model
    )

    assistant = assistant(
        context=code_context(datasource), system_prompt="Run tools on each user prompt"
    )

    answer, triggered_tools = assistant_utils.ask_assistant(
        assistant, question, minimal_response=False
    )
    assert_tool_triggered(Default.GET_REPOSITORY_FILE_TREE, triggered_tools)
    similarity_check.check_similarity(answer, expected_answer)

    datasource_utils.update_code_datasource(
        datasource.id, full_reindex=True, skip_reindex=False
    )

    answer, triggered_tools = assistant_utils.ask_assistant(
        assistant, question, minimal_response=False
    )
    assert_tool_triggered(Default.GET_REPOSITORY_FILE_TREE, triggered_tools)
    similarity_check.check_similarity(answer, expected_answer)


@pytest.mark.datasource
@pytest.mark.github
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    "integration_fixture",
    [
        "github_integration",
        "github_pat_integration",
        "github_app_integration",
    ],
)
def test_create_index_application_for_different_github_auth(
    request,
    default_embedding_llm,
    integration_fixture,
    assistant,
    assistant_utils,
    code_context,
    datasource_utils,
    similarity_check,
):
    # Get the integration from the fixture
    git_integration = request.getfixturevalue(integration_fixture)

    datasource = datasource_utils.create_github_datasource(
        setting_id=git_integration.id,
        embeddings_model=default_embedding_llm.base_name,
    )

    assistant = assistant(context=code_context(datasource))

    answer, triggered_tools = assistant_utils.ask_assistant(
        assistant, GITHUB_DATASOURCE_REQUEST, minimal_response=False
    )

    assert_tool_triggered(Default.GET_REPOSITORY_FILE_TREE, triggered_tools)
    similarity_check.check_similarity(answer, GITHUB_DATASOURCE_RESPONSE)


@pytest.mark.datasource
@pytest.mark.gitlab
@pytest.mark.api
def test_edit_description_for_code_data_source(
    client,
    gitlab_datasource,
    datasource_utils,
):
    updated_description = get_random_name()

    datasource_utils.update_code_datasource(
        gitlab_datasource.id, description=updated_description
    )

    updated_datasource = client.datasources.get(gitlab_datasource.id)
    assert_that(updated_datasource.description, equal_to(updated_description))


@pytest.mark.datasource
@pytest.mark.gitlab
@pytest.mark.api
def test_create_code_datasource_with_existing_name(gitlab_datasource, datasource_utils):
    datasource = datasource_utils.get_datasource(gitlab_datasource.id)

    try:
        datasource_utils.create_gitlab_datasource(
            name=datasource.name,
            setting_id=datasource.setting_id,
            embeddings_model=datasource.embeddings_model,
        )
        raise AssertionError("There are no error message for duplicate datasource name")
    except HTTPError as e:
        assert_response(
            e.response,
            409,
            f"An index with the name '{datasource.name}' already exists in the project '{os.getenv('PROJECT_NAME')}'.",
        )


@pytest.mark.datasource
@pytest.mark.gitlab
@pytest.mark.api
def test_delete_code_datasource_during_active_indexing(
    indexing_code_datasource,
    datasource_utils,
):
    datasource_utils.wait_for_fetching(indexing_code_datasource.id)
    datasource_utils.delete_datasource(indexing_code_datasource)
    sleep(10)
    datasource_utils.assert_datasource_absent_during_window(indexing_code_datasource.id)


@pytest.mark.datasource
@pytest.mark.gitlab
@pytest.mark.api
def test_partial_update_preserves_required_fields(
    client,
    gitlab_datasource,
    datasource_utils,
):
    """Partial update preserves required fields."""
    original_datasource = client.datasources.get(gitlab_datasource.id)
    original_link = original_datasource.code.link
    original_branch = original_datasource.code.branch
    original_embeddings_model = original_datasource.embeddings_model
    original_setting_id = original_datasource.setting_id

    assert_that(original_link, not_none())
    assert_that(original_branch, not_none())
    assert_that(original_embeddings_model, not_none())
    assert_that(original_setting_id, not_none())

    new_description = get_random_name()
    response = datasource_utils.partial_update_code_datasource(
        original_datasource.name,
        description=new_description,
        skip_reindex=True,
    )

    assert_that(response.status_code, equal_to(201))

    updated_datasource = client.datasources.get(gitlab_datasource.id)
    assert_that(updated_datasource.description, equal_to(new_description))
    assert_that(updated_datasource.code.link, equal_to(original_link))
    assert_that(updated_datasource.code.branch, equal_to(original_branch))
    assert_that(
        updated_datasource.embeddings_model, equal_to(original_embeddings_model)
    )
    assert_that(updated_datasource.setting_id, equal_to(original_setting_id))


@pytest.mark.datasource
@pytest.mark.gitlab
@pytest.mark.api
def test_partial_update_with_name_only(
    client,
    gitlab_datasource,
    datasource_utils,
):
    """Minimal partial update preserves all fields."""
    original_datasource = client.datasources.get(gitlab_datasource.id)
    original_link = original_datasource.code.link
    original_branch = original_datasource.code.branch
    original_embeddings_model = original_datasource.embeddings_model
    original_setting_id = original_datasource.setting_id
    original_description = original_datasource.description

    response = datasource_utils.partial_update_code_datasource(
        original_datasource.name,
        skip_reindex=True,
    )

    assert_that(response.status_code, equal_to(201))

    updated_datasource = client.datasources.get(gitlab_datasource.id)
    assert_that(updated_datasource.description, equal_to(original_description))
    assert_that(updated_datasource.code.link, equal_to(original_link))
    assert_that(updated_datasource.code.branch, equal_to(original_branch))
    assert_that(
        updated_datasource.embeddings_model, equal_to(original_embeddings_model)
    )
    assert_that(updated_datasource.setting_id, equal_to(original_setting_id))
