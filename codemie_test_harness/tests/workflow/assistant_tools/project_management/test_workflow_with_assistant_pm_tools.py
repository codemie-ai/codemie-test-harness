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

from codemie_test_harness.tests.enums.tools import Toolkit
from codemie_test_harness.tests.test_data.project_management_test_data import (
    pm_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_tool_triggered,
    get_random_name,
)
from codemie_test_harness.tests.utils.constants import (
    project_management_integrations,
    ProjectManagementIntegrationType,
)

_CONFLUENCE_INTEGRATION_TYPES = (
    ProjectManagementIntegrationType.CONFLUENCE,
    ProjectManagementIntegrationType.CONFLUENCE_CLOUD,
)


@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
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
def test_workflow_with_assistant_with_project_management_tools(
    request,
    assistant,
    integration_utils,
    similarity_check,
    jira_integration,
    workflow_utils,
    workflow_with_assistant,
    tool_name,
    integration_type,
    prompt,
    expected_response,
    confluence_page_cleanup,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    integration = request.getfixturevalue(
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
        settings=integration,
    )

    workflow_with_assistant = workflow_with_assistant(assistant, prompt)
    response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, assistant.name
    )

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(tool_name, triggered_tools)

    similarity_check.check_similarity(response, expected_response)
