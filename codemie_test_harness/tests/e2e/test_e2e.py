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
from codemie_sdk.models.assistant import (
    Context,
    ContextType,
    ToolDetails,
    ToolKitDetails,
)
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.enums.tools import (
    Toolkit,
    GitTool,
    VcsTool,
    ProjectManagementTool,
)
from codemie_test_harness.tests.test_data.git_tools_test_data import (
    list_branches_set_active_branch_test_data,
)
from codemie_test_harness.tests.test_data.pm_tools_test_data import (
    JIRA_TOOL_PROMPT,
    RESPONSE_FOR_JIRA_TOOL,
    JIRA_CLOUD_TOOL_PROMPT,
    RESPONSE_FOR_JIRA_CLOUD_TOOL,
    CONFLUENCE_TOOL_PROMPT,
    RESPONSE_FOR_CONFLUENCE_TOOL,
    CONFLUENCE_CLOUD_TOOL_PROMPT,
    RESPONSE_FOR_CONFLUENCE_CLOUD_TOOL,
)
from codemie_test_harness.tests.test_data.vcs_tools_test_data import (
    GITLAB_TOOL_TASK,
    GITHUB_TOOL_TASK,
    RESPONSE_FOR_GITLAB,
    RESPONSE_FOR_GITHUB,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_tool_triggered,
    get_random_name,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    ToolModel,
)


@pytest.fixture(scope="session")
def git_integration(integration_utils):
    if os.getenv("GIT_ENV", "gitlab") == "gitlab":
        integration = integration_utils.create_integration(
            credential_type=CredentialTypes.GIT,
            credential_values=CredentialsManager.gitlab_credentials(),
        )
    else:
        integration = integration_utils.create_integration(
            credential_type=CredentialTypes.GIT,
            credential_values=CredentialsManager.github_credentials(),
        )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


@pytest.mark.github
@pytest.mark.gitlab
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.code_kb
@pytest.mark.api
def test_assistant_with_code_kb(
    assistant_utils, code_datasource, default_llm, similarity_check
):
    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        context=[Context(name=code_datasource.name, context_type=ContextType.CODE)],
    )

    response = assistant_utils.ask_assistant(
        assistant,
        "List files in root and confirm that you have an access to the code knowledge base. "
        "Do not return the files to user, just confirm if you have an access or not",
    )

    similarity_check.check_similarity(
        response, "I confirm that I have access to the code knowledge base."
    )


@pytest.mark.assistant
@pytest.mark.vcs
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.skipif(
    os.getenv("GIT_ENV") == "github",
    reason="Test is skipped when GIT_ENV is set to github",
)
def test_assistant_with_vcs_gitlab_tool(
    assistant_utils, git_integration, default_llm, similarity_check
):
    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        toolkits=[
            ToolKitDetails(
                toolkit=Toolkit.VCS,
                tools=[ToolDetails(name=VcsTool.GITLAB, settings=git_integration)],
            )
        ],
    )

    response = assistant_utils.ask_assistant(
        assistant,
        f"Run gitlab tool to list branches in the repository for project with ID {CredentialsManager.get_parameter('GITLAB_PROJECT_ID')}. "
        "Do not ask user confirmation to do this. "
        "Do not return branches to user but just confirm if you have an access to repository or not",
    )

    similarity_check.check_similarity(
        response, "I have confirmed that I have access to the repository."
    )


@pytest.mark.assistant
@pytest.mark.vcs
@pytest.mark.github
@pytest.mark.api
@pytest.mark.skipif(
    os.getenv("GIT_ENV") == "gitlab",
    reason="Test is skipped when GIT_ENV is set to gitlab",
)
def test_assistant_with_vcs_github_tool(
    assistant_utils, github_integration, default_llm, similarity_check
):
    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        toolkits=[
            ToolKitDetails(
                toolkit=Toolkit.VCS,
                tools=[ToolDetails(name=VcsTool.GITHUB, settings=github_integration)],
            )
        ],
    )

    response = assistant_utils.ask_assistant(
        assistant,
        f"Run github tool to list branches in the repository for project {CredentialsManager.get_parameter('GITHUB_PROJECT')}. "
        "Do not ask user confirmation to do this. "
        "Do not return branches to user but just confirm if you have an access to repository or not",
    )

    similarity_check.check_similarity(
        response, "I have confirmed that I have access to the repository."
    )


@pytest.mark.github
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.gitlab
@pytest.mark.api
def test_assistant_with_list_branches_tool(
    assistant_utils, code_datasource, default_llm, similarity_check, gitlab_integration
):
    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        system_prompt="Do not pass any parameters to tool",
        toolkits=[
            ToolKitDetails(
                toolkit=Toolkit.GIT,
                tools=[
                    ToolDetails(
                        name=GitTool.LIST_BRANCHES_IN_REPO, settings=gitlab_integration
                    )
                ],
                settings=gitlab_integration,
            )
        ],
        context=[Context(name=code_datasource.name, context_type=ContextType.CODE)],
    )

    response = assistant_utils.ask_assistant(
        assistant,
        "List branches in the repository. Run tool without any arguments: {}"
        "No need to pass query at all like {'query': ''}"
        "Do not return branches to user but just confirm if you have an access to repository or not",
    )

    similarity_check.check_similarity(
        response, "I have access to the repository and can list its branches. "
    )


@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.jira
@pytest.mark.project_management
@pytest.mark.api
def test_assistant_with_jira_kb(
    assistant_utils, jira_datasource, default_llm, similarity_check
):
    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        context=[
            Context(name=jira_datasource.name, context_type=ContextType.KNOWLEDGE_BASE)
        ],
    )

    response = assistant_utils.ask_assistant(
        assistant,
        "Find any jira ticket. "
        "Do not return it to user but just confirm if you have an access to jira knowledge base or not",
    )

    similarity_check.check_similarity(
        response, "I have access to Jira knowledge base. and can find tickets."
    )


@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.confluence
@pytest.mark.project_management
@pytest.mark.api
def test_assistant_with_confluence_kb(
    assistant_utils, confluence_datasource, default_llm, similarity_check
):
    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        context=[
            Context(
                name=confluence_datasource.name, context_type=ContextType.KNOWLEDGE_BASE
            )
        ],
    )

    response = assistant_utils.ask_assistant(
        assistant,
        "Search KB to find any confluence page. "
        "Do not return it to user but just confirm if you have an access to confluence knowledge base or not",
    )

    similarity_check.check_similarity(
        response, "I have access to the Confluence knowledge base."
    )


@pytest.mark.assistant
@pytest.mark.vcs
@pytest.mark.gitlab
@pytest.mark.github
@pytest.mark.api
@pytest.mark.skip(
    reason="Bug: Gitlab and Github tools: Integration context leakage between tools causes "
    "authentication and incorrect URL usage"
)
def test_assistant_with_gitlab_and_github_tools(
    assistant_utils,
    gitlab_integration,
    github_integration,
    default_llm,
    similarity_check,
    seeded,
):
    gitlab_tool_task = seeded(GITLAB_TOOL_TASK)
    response_for_gitlab = seeded(RESPONSE_FOR_GITLAB)
    github_tool_task = seeded(GITHUB_TOOL_TASK)
    response_for_github = seeded(RESPONSE_FOR_GITHUB)

    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        system_prompt="You are an assistant that can use GitLab and GitHub tools.",
        toolkits=[
            ToolKitDetails(
                toolkit=Toolkit.VCS,
                tools=[
                    ToolDetails(name=VcsTool.GITLAB, settings=gitlab_integration),
                    ToolDetails(name=VcsTool.GITHUB, settings=github_integration),
                ],
            )
        ],
    )

    # Test GitLab tool
    response_gitlab, triggered_tools_gitlab = assistant_utils.ask_assistant(
        assistant, gitlab_tool_task, minimal_response=False
    )
    assert_tool_triggered(VcsTool.GITLAB, triggered_tools_gitlab)
    similarity_check.check_similarity(response_gitlab, response_for_gitlab)

    # Test GitHub tool
    response_github, triggered_tools_github = assistant_utils.ask_assistant(
        assistant, github_tool_task, minimal_response=False
    )
    assert_tool_triggered(VcsTool.GITHUB, triggered_tools_github)
    similarity_check.check_similarity(response_github, response_for_github)


@pytest.mark.gitlab
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.vcs
@pytest.mark.git
@pytest.mark.github
@pytest.mark.api
@pytest.mark.skip(
    reason="Bug: Gitlab and Github tools: Integration context leakage between tools causes "
    "authentication and incorrect URL usage"
)
def test_assistant_with_git_datasource_and_github_tool(
    assistant_utils,
    code_datasource,
    gitlab_integration,
    github_integration,
    default_llm,
    similarity_check,
    seeded,
):
    """Test assistant with git datasource, git tool, and github tool."""
    github_tool_task = seeded(GITHUB_TOOL_TASK)
    response_for_github = seeded(RESPONSE_FOR_GITHUB)

    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        system_prompt="You are an assistant with access to code repository knowledge base and GitHub tools.",
        toolkits=[
            ToolKitDetails(
                toolkit=Toolkit.GIT,
                tools=[ToolDetails(name=GitTool.LIST_BRANCHES_IN_REPO)],
                settings=gitlab_integration,
            ),
            ToolKitDetails(
                toolkit=Toolkit.VCS,
                tools=[ToolDetails(name=VcsTool.GITHUB, settings=github_integration)],
            ),
        ],
        context=[Context(name=code_datasource.name, context_type=ContextType.CODE)],
    )

    git_tool_prompt = list_branches_set_active_branch_test_data[0].values[2]
    git_tool_answer = list_branches_set_active_branch_test_data[0].values[3]

    # Test git tool and datasource access
    response_datasource, triggered_tools = assistant_utils.ask_assistant(
        assistant, git_tool_prompt, minimal_response=False
    )
    assert_tool_triggered(GitTool.LIST_BRANCHES_IN_REPO, triggered_tools)
    similarity_check.check_similarity(response_datasource, git_tool_answer)

    # Test GitHub VCS tool
    response_github, triggered_tools_github = assistant_utils.ask_assistant(
        assistant, github_tool_task, minimal_response=False
    )
    assert_tool_triggered(VcsTool.GITHUB, triggered_tools_github)
    similarity_check.check_similarity(response_github, response_for_github)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.vcs
@pytest.mark.gitlab
@pytest.mark.github
@pytest.mark.api
@pytest.mark.skip(
    reason="Bug: Gitlab and Github tools: Integration context leakage between tools causes "
    "authentication and incorrect URL usage. 400 error when creating workflow with multiple integrations."
)
def test_workflow_with_gitlab_and_github_tools(
    gitlab_integration,
    github_integration,
    similarity_check,
    workflow_utils,
    workflow,
    default_llm,
    seeded,
):
    gitlab_tool_task = seeded(GITLAB_TOOL_TASK)
    response_for_gitlab = seeded(RESPONSE_FOR_GITLAB)
    github_tool_task = seeded(GITHUB_TOOL_TASK)
    response_for_github = seeded(RESPONSE_FOR_GITHUB)

    # Create workflow with virtual assistant that has both GitLab and GitHub tools
    workflow_name = get_random_name()

    assistant = AssistantModel(
        id=workflow_name,
        model=default_llm.base_name,
        system_prompt="You are an assistant that can use GitLab and GitHub tools.",
        tools=[
            ToolModel(
                name=VcsTool.GITLAB.value,
                integration_alias=gitlab_integration.alias,
            ),
            ToolModel(
                name=VcsTool.GITHUB.value,
                integration_alias=github_integration.alias,
            ),
        ],
    )

    state = StateModel(
        id=workflow_name,
        assistant_id=workflow_name,
    )

    test_workflow = workflow(assistant_model=assistant, state_model=state)

    # Test GitLab tool in workflow
    response_gitlab = workflow_utils.execute_workflow(
        test_workflow.id, workflow_name, user_input=gitlab_tool_task
    )

    triggered_tools_gitlab = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(VcsTool.GITLAB, triggered_tools_gitlab)
    similarity_check.check_similarity(response_gitlab, response_for_gitlab)

    # Test GitHub tool in workflow
    response_github = workflow_utils.execute_workflow(
        test_workflow.id, workflow_name, user_input=github_tool_task
    )

    triggered_tools_github = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(VcsTool.GITHUB, triggered_tools_github)
    similarity_check.check_similarity(response_github, response_for_github)


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.jira
@pytest.mark.jira_cloud
@pytest.mark.requires_setting("jira")
@pytest.mark.api
def test_assistant_with_jira_tool_and_several_integrations(
    assistant_utils,
    jira_integration,
    jira_cloud_integration,
    integration_utils,
    default_llm,
    similarity_check,
    seeded,
):
    # Different JIRA integrations
    jira_server_integration = jira_integration
    jira_cloud_integration = jira_cloud_integration
    # invalid_settings
    integration_utils.create_integration(
        CredentialTypes.JIRA, CredentialsManager.invalid_jira_credentials()
    )

    # Test JIRA Server tool
    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        system_prompt="You are an assistant that can use Jira tool.",
        toolkits=[
            ToolKitDetails(
                toolkit=Toolkit.PROJECT_MANAGEMENT,
                tools=[
                    ToolDetails(
                        name=ProjectManagementTool.JIRA,
                        settings=jira_server_integration,
                    ),
                ],
            )
        ],
    )

    response_jira, triggered_tools_jira = assistant_utils.ask_assistant(
        assistant, seeded(JIRA_TOOL_PROMPT), minimal_response=False
    )
    assert_tool_triggered(ProjectManagementTool.JIRA, triggered_tools_jira)
    similarity_check.check_similarity(response_jira, seeded(RESPONSE_FOR_JIRA_TOOL))

    # Test JIRA Cloud tool
    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        system_prompt="You are an assistant that can use Jira tool.",
        toolkits=[
            ToolKitDetails(
                toolkit=Toolkit.PROJECT_MANAGEMENT,
                tools=[
                    ToolDetails(
                        name=ProjectManagementTool.JIRA, settings=jira_cloud_integration
                    ),
                ],
            )
        ],
    )

    response_jira, triggered_tools_jira = assistant_utils.ask_assistant(
        assistant, seeded(JIRA_CLOUD_TOOL_PROMPT), minimal_response=False
    )
    assert_tool_triggered(ProjectManagementTool.JIRA, triggered_tools_jira)
    similarity_check.check_similarity(
        response_jira, seeded(RESPONSE_FOR_JIRA_CLOUD_TOOL)
    )


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.confluence_cloud
@pytest.mark.requires_setting("confluence")
@pytest.mark.api
def test_assistant_with_confluence_tool_and_several_integrations(
    assistant_utils,
    confluence_integration,
    confluence_cloud_integration,
    integration_utils,
    default_llm,
    similarity_check,
    seeded,
):
    # Different Confluence integrations
    confluence_server_integration = confluence_integration
    confluence_cloud_integration = confluence_cloud_integration
    # invalid_settings
    integration_utils.create_integration(
        CredentialTypes.CONFLUENCE, CredentialsManager.invalid_confluence_credentials()
    )

    # Test Confluence Server tool
    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        system_prompt="You are an assistant that can use Confluence tool.",
        toolkits=[
            ToolKitDetails(
                toolkit=Toolkit.PROJECT_MANAGEMENT,
                tools=[
                    ToolDetails(
                        name=ProjectManagementTool.CONFLUENCE,
                        settings=confluence_server_integration,
                    ),
                ],
            )
        ],
    )

    response_confluence, triggered_tools_confluence = assistant_utils.ask_assistant(
        assistant, seeded(CONFLUENCE_TOOL_PROMPT), minimal_response=False
    )
    assert_tool_triggered(ProjectManagementTool.CONFLUENCE, triggered_tools_confluence)
    similarity_check.check_similarity(
        response_confluence, seeded(RESPONSE_FOR_CONFLUENCE_TOOL)
    )

    # Test Confluence Cloud tool
    assistant = assistant_utils.create_assistant(
        llm_model_type=default_llm.base_name,
        system_prompt="You are an assistant that can use Confluence tool.",
        toolkits=[
            ToolKitDetails(
                toolkit=Toolkit.PROJECT_MANAGEMENT,
                tools=[
                    ToolDetails(
                        name=ProjectManagementTool.CONFLUENCE,
                        settings=confluence_cloud_integration,
                    ),
                ],
            )
        ],
    )

    response_confluence, triggered_tools_confluence = assistant_utils.ask_assistant(
        assistant, seeded(CONFLUENCE_CLOUD_TOOL_PROMPT), minimal_response=False
    )
    assert_tool_triggered(ProjectManagementTool.CONFLUENCE, triggered_tools_confluence)
    similarity_check.check_similarity(
        response_confluence, seeded(RESPONSE_FOR_CONFLUENCE_CLOUD_TOOL)
    )
