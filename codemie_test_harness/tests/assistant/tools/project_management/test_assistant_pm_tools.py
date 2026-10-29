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
from codemie_sdk.models.assistant import ToolConfig
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.enums.tools import Toolkit, ProjectManagementTool
from codemie_test_harness.tests.test_data.pm_tools_test_data import (
    CONFLUENCE_TOOL_PROMPT,
    RESPONSE_FOR_CONFLUENCE_TOOL,
    JIRA_TOOL_PROMPT,
    RESPONSE_FOR_JIRA_TOOL,
    RESPONSE_FOR_CONFLUENCE_TOOL_UNAUTHORIZED,
)
from codemie_test_harness.tests.test_data.project_management_test_data import (
    pm_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    credentials_to_dict,
    assert_tool_triggered,
    get_random_name,
)
from codemie_test_harness.tests.utils.constants import (
    project_management_integrations,
    ProjectManagementIntegrationType,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

_CONFLUENCE_INTEGRATION_TYPES = (
    ProjectManagementIntegrationType.CONFLUENCE,
    ProjectManagementIntegrationType.CONFLUENCE_CLOUD,
)


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_name, integration_type, prompt, expected_response",
    pm_tools_test_data,
    ids=[
        f"{getattr(row, 'values', row)[0]}_{getattr(row, 'values', row)[1]}"
        for row in pm_tools_test_data
    ],
)
def test_assistant_with_project_management_tools(
    request,
    assistant,
    assistant_utils,
    similarity_check,
    tool_name,
    integration_type,
    prompt,
    expected_response,
    confluence_page_cleanup,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    _integration = request.getfixturevalue(
        project_management_integrations[integration_type]
    )

    if "%s" in prompt:
        random_name = get_random_name()
        prompt = prompt % random_name
        if integration_type in _CONFLUENCE_INTEGRATION_TYPES:
            confluence_page_cleanup.append(random_name)

    assistant = assistant(
        Toolkit.PROJECT_MANAGEMENT,
        tool_name,
        settings=_integration,
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, minimal_response=False
    )
    assert_tool_triggered(tool_name, triggered_tools)
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.jira
@pytest.mark.api
def test_assistant_with_jira_tool_and_integration_id_in_chat(
    assistant,
    assistant_utils,
    integration_utils,
    similarity_check,
    jira_integration,
    seeded,
):
    invalid_settings = integration_utils.create_integration(
        CredentialTypes.JIRA, CredentialsManager.invalid_jira_credentials()
    )
    tool_config = ToolConfig(
        name=ProjectManagementTool.JIRA, integration_id=jira_integration.id
    )

    assistant = assistant(
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.JIRA,
        settings=invalid_settings,
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant,
        seeded(JIRA_TOOL_PROMPT),
        tools_config=[tool_config],
        minimal_response=False,
    )
    assert_tool_triggered(ProjectManagementTool.JIRA, triggered_tools)
    similarity_check.check_similarity(response, seeded(RESPONSE_FOR_JIRA_TOOL))


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.jira
@pytest.mark.api
def test_assistant_with_jira_tool_and_credentials_in_chat(
    assistant, assistant_utils, integration_utils, similarity_check, seeded
):
    tool_config = ToolConfig(
        name=ProjectManagementTool.JIRA,
        tool_creds=credentials_to_dict(CredentialsManager.jira_credentials()),
    )

    assistant = assistant(
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.JIRA,
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant,
        seeded(JIRA_TOOL_PROMPT),
        tools_config=[tool_config],
        minimal_response=False,
    )
    assert_tool_triggered(ProjectManagementTool.JIRA, triggered_tools)
    similarity_check.check_similarity(response, seeded(RESPONSE_FOR_JIRA_TOOL))


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.api
def test_assistant_with_confluence_tool_and_integration_id_in_chat(
    assistant,
    assistant_utils,
    integration_utils,
    similarity_check,
    confluence_integration,
    seeded,
):
    invalid_settings = integration_utils.create_integration(
        CredentialTypes.JIRA, CredentialsManager.invalid_confluence_credentials()
    )
    tool_config = ToolConfig(
        name=ProjectManagementTool.CONFLUENCE, integration_id=confluence_integration.id
    )

    assistant = assistant(
        Toolkit.PROJECT_MANAGEMENT,
        ProjectManagementTool.CONFLUENCE,
        settings=invalid_settings,
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant,
        seeded(CONFLUENCE_TOOL_PROMPT),
        tools_config=[tool_config],
        minimal_response=False,
    )
    assert_tool_triggered(ProjectManagementTool.CONFLUENCE, triggered_tools)
    similarity_check.check_similarity(response, seeded(RESPONSE_FOR_CONFLUENCE_TOOL))


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.api
def test_assistant_with_confluence_tool_and_credentials_in_chat(
    assistant,
    assistant_utils,
    integration_utils,
    similarity_check,
    confluence_seed_page,
    seeded,
):
    tool_config = ToolConfig(
        name=ProjectManagementTool.CONFLUENCE,
        tool_creds=credentials_to_dict(CredentialsManager.confluence_credentials()),
    )

    assistant = assistant(Toolkit.PROJECT_MANAGEMENT, ProjectManagementTool.CONFLUENCE)

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant,
        seeded(CONFLUENCE_TOOL_PROMPT),
        tools_config=[tool_config],
        minimal_response=False,
    )
    assert_tool_triggered(ProjectManagementTool.CONFLUENCE, triggered_tools)
    similarity_check.check_similarity(response, seeded(RESPONSE_FOR_CONFLUENCE_TOOL))


@pytest.mark.assistant
@pytest.mark.project_management
@pytest.mark.confluence
@pytest.mark.api
@pytest.mark.skip(reason="Test should be fixed")
def test_assistant_with_confluence_tool_and_without_credentials(
    assistant, assistant_utils, similarity_check, seeded
):
    assistant = assistant(Toolkit.PROJECT_MANAGEMENT, ProjectManagementTool.CONFLUENCE)

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, seeded(CONFLUENCE_TOOL_PROMPT), minimal_response=False
    )
    assert_tool_triggered(ProjectManagementTool.CONFLUENCE, triggered_tools)
    similarity_check.check_similarity(
        response, RESPONSE_FOR_CONFLUENCE_TOOL_UNAUTHORIZED
    )
