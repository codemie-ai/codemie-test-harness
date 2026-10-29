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

from codemie_sdk.models.integration import (
    CredentialTypes,
    IntegrationType,
)
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.integrations import integrations
from codemie_test_harness.tests.enums.tools import Toolkit, GitTool
from codemie_test_harness.tests.test_data.git_tools_test_data import (
    list_branches_set_active_branch_test_data,
)
from codemie_test_harness.tests.utils.base_utils import assert_tool_triggered
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.constants import test_project_name


git_tool_prompt = list_branches_set_active_branch_test_data[0].values[2]
git_tool_answer = list_branches_set_active_branch_test_data[0].values[3]


@pytest.mark.gitlab
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.integration
@pytest.mark.default_integration
@pytest.mark.datasource
@pytest.mark.not_for_parallel_run
@pytest.mark.api
@pytest.mark.parametrize(
    "user_integration, is_global, project_integration",
    integrations,
    ids=[
        f"{row[0].value}-{'global' if row[1] else 'None'}-{row[2].value if row[2] else 'None'}"
        for row in integrations
    ],
)
def test_assistant_in_workflow_should_use_user_integration_by_default(
    datasource_utils,
    default_embedding_llm,
    gitlab_datasource,
    code_context,
    integration_utils,
    assistant,
    assistant_utils,
    similarity_check,
    user_integration,
    is_global,
    project_integration,
    workflow_with_assistant,
    workflow_utils,
):
    """
    Test to verify that an assistant should use USER integration by default
    if integration of all types [USER, GLOBAL, PROJECT] are available.
    """

    for integration_type in IntegrationType:
        integration_utils.delete_integrations_by_type(
            integration_type, CredentialTypes.GIT, test_project_name
        )

    _git_integration = integration_utils.create_user_integration(
        CredentialTypes.GIT, CredentialsManager.gitlab_credentials(), test_project_name
    )

    # create a new datasource
    git_datasource = datasource_utils.create_gitlab_datasource(
        setting_id=_git_integration.id,
        embeddings_model=default_embedding_llm.base_name,
        project_name=test_project_name,
    )

    if is_global:
        integration_utils.create_global_integration(
            CredentialTypes.GIT,
            CredentialsManager.invalid_git_credentials(),
            test_project_name,
        )

    if project_integration:
        integration_utils.create_project_integration(
            CredentialTypes.GIT,
            CredentialsManager.invalid_git_credentials(),
            test_project_name,
        )

    git_assistant = assistant(
        Toolkit.GIT,
        GitTool.LIST_BRANCHES_IN_REPO,
        context=code_context(git_datasource),
        project_name=test_project_name,
    )

    workflow_with_assistant = workflow_with_assistant(git_assistant, git_tool_prompt)
    response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, git_assistant.name
    )
    similarity_check.check_similarity(response, git_tool_answer)

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(GitTool.LIST_BRANCHES_IN_REPO, triggered_tools)

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(GitTool.LIST_BRANCHES_IN_REPO, triggered_tools)

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(GitTool.LIST_BRANCHES_IN_REPO, triggered_tools)

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(GitTool.LIST_BRANCHES_IN_REPO, triggered_tools)

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(GitTool.LIST_BRANCHES_IN_REPO, triggered_tools)


@pytest.mark.gitlab
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.integration
@pytest.mark.default_integration
@pytest.mark.datasource
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_assistant_in_workflow_with_global_and_project_integration(
    datasource_utils,
    default_embedding_llm,
    code_context,
    integration_utils,
    assistant,
    assistant_utils,
    similarity_check,
    workflow_with_assistant,
    workflow_utils,
):
    """
    Test to verify that an assistant should use GLOBAL integration if USER integration is not available,
    and both GLOBAL and PROJECT integrations exist.
    GLOBAL integration has valid credentials, PROJECT has invalid.
    """
    # Create datasource
    _git_integration = integration_utils.create_global_integration(
        CredentialTypes.GIT, CredentialsManager.gitlab_credentials(), test_project_name
    )
    git_datasource = datasource_utils.create_gitlab_datasource(
        setting_id=_git_integration.id,
        embeddings_model=default_embedding_llm.base_name,
        project_name=test_project_name,
    )

    # Delete all integrations of type GIT
    for integration_type in IntegrationType:
        integration_utils.delete_integrations_by_type(
            integration_type, CredentialTypes.GIT, test_project_name
        )

    # Create only global (valid) and project (invalid) integrations.
    # Global integration is created in project which is different from the project of the assistant.
    _git_integration = integration_utils.create_global_integration(
        CredentialTypes.GIT, CredentialsManager.gitlab_credentials(), PROJECT
    )

    integration_utils.create_project_integration(
        CredentialTypes.GIT,
        CredentialsManager.invalid_git_credentials(),
        test_project_name,
    )

    git_assistant = assistant(
        Toolkit.GIT,
        GitTool.LIST_BRANCHES_IN_REPO,
        context=code_context(git_datasource),
        project_name=test_project_name,
    )

    workflow_with_assistant = workflow_with_assistant(git_assistant, git_tool_prompt)
    response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, git_assistant.name
    )
    similarity_check.check_similarity(response, git_tool_answer)


@pytest.mark.gitlab
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.integration
@pytest.mark.default_integration
@pytest.mark.datasource
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_assistant_in_workflow_with_project_integration_only(
    datasource_utils,
    default_embedding_llm,
    code_context,
    integration_utils,
    assistant,
    assistant_utils,
    similarity_check,
    workflow_with_assistant,
    workflow_utils,
):
    """
    Test to verify that an assistant should use PROJECT integration if it is the only one available.
    """
    for integration_type in IntegrationType:
        integration_utils.delete_integrations_by_type(
            integration_type, CredentialTypes.GIT, test_project_name
        )

    # Create project integration only
    _git_integration = integration_utils.create_project_integration(
        CredentialTypes.GIT, CredentialsManager.gitlab_credentials(), test_project_name
    )

    # create a new datasource
    git_datasource = datasource_utils.create_gitlab_datasource(
        setting_id=_git_integration.id,
        embeddings_model=default_embedding_llm.base_name,
        project_name=test_project_name,
    )

    git_assistant = assistant(
        Toolkit.GIT,
        GitTool.LIST_BRANCHES_IN_REPO,
        context=code_context(git_datasource),
        project_name=test_project_name,
    )

    workflow_with_assistant = workflow_with_assistant(git_assistant, git_tool_prompt)
    response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, git_assistant.name
    )
    similarity_check.check_similarity(response, git_tool_answer)


@pytest.mark.gitlab
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.integration
@pytest.mark.default_integration
@pytest.mark.datasource
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_assistant_in_workflow_with_global_valid_and_user_invalid_integration(
    assistant,
    assistant_utils,
    integration_utils,
    similarity_check,
    datasource_utils,
    default_embedding_llm,
    code_context,
    workflow_with_assistant,
    workflow_utils,
):
    """
    Test to verify that an assistant should use GLOBAL integration if USER integration is not valid,
    and both GLOBAL and USER integrations exist.
    GLOBAL integration has valid credentials, USER has invalid.
    """
    # Create datasource
    _git_integration = integration_utils.create_global_integration(
        CredentialTypes.GIT, CredentialsManager.gitlab_credentials(), test_project_name
    )
    git_datasource = datasource_utils.create_gitlab_datasource(
        setting_id=_git_integration.id,
        embeddings_model=default_embedding_llm.base_name,
        project_name=test_project_name,
    )

    # Delete all integrations of type GIT
    for integration_type in IntegrationType:
        integration_utils.delete_integrations_by_type(
            integration_type, CredentialTypes.GIT, test_project_name
        )

    # Create global valid integration
    _git_integration = integration_utils.create_global_integration(
        CredentialTypes.GIT, CredentialsManager.gitlab_credentials(), PROJECT
    )

    # Create user invalid integration
    integration_utils.create_user_integration(
        CredentialTypes.GIT,
        CredentialsManager.invalid_git_credentials(),
        PROJECT,
    )

    git_assistant = assistant(
        Toolkit.GIT,
        GitTool.LIST_BRANCHES_IN_REPO,
        context=code_context(git_datasource),
        project_name=test_project_name,
    )

    workflow_with_assistant = workflow_with_assistant(git_assistant, git_tool_prompt)
    response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, git_assistant.name
    )
    similarity_check.check_similarity(response, git_tool_answer)


@pytest.mark.gitlab
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.integration
@pytest.mark.default_integration
@pytest.mark.datasource
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_assistant_in_workflow_with_project_valid_and_user_invalid_integration(
    assistant,
    assistant_utils,
    integration_utils,
    similarity_check,
    datasource_utils,
    default_embedding_llm,
    code_context,
    workflow_with_assistant,
    workflow_utils,
):
    """
    Test to verify that an assistant should use PROJECT integration if USER integration is not valid,
    and both PROJECT and USER integrations exist.
    PROJECT integration has valid credentials, USER has invalid.
    """
    # Create datasource
    _git_integration = integration_utils.create_global_integration(
        CredentialTypes.GIT, CredentialsManager.gitlab_credentials(), test_project_name
    )
    git_datasource = datasource_utils.create_gitlab_datasource(
        setting_id=_git_integration.id,
        embeddings_model=default_embedding_llm.base_name,
        project_name=test_project_name,
    )

    # Delete all integrations of type GIT
    for integration_type in IntegrationType:
        integration_utils.delete_integrations_by_type(
            integration_type, CredentialTypes.GIT, test_project_name
        )

    # Create global valid integration
    _git_integration = integration_utils.create_project_integration(
        CredentialTypes.GIT, CredentialsManager.gitlab_credentials(), test_project_name
    )

    # Create user invalid integration
    integration_utils.create_user_integration(
        CredentialTypes.GIT,
        CredentialsManager.invalid_git_credentials(),
        PROJECT,
    )

    git_assistant = assistant(
        Toolkit.GIT,
        GitTool.LIST_BRANCHES_IN_REPO,
        context=code_context(git_datasource),
        project_name=test_project_name,
    )

    workflow_with_assistant = workflow_with_assistant(git_assistant, git_tool_prompt)
    response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, git_assistant.name
    )
    similarity_check.check_similarity(response, git_tool_answer)
