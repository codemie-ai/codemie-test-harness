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

from codemie_sdk.models.integration import CredentialTypes
from codemie_test_harness.tests.enums.tools import CodeBaseTool
from codemie_test_harness.tests.test_data.codebase_tools_test_data import (
    code_tools_test_data,
    sonar_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import assert_tool_triggered


@pytest.mark.github
@pytest.mark.gitlab
@pytest.mark.requires_capability("retrieval")
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.codebase
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    code_tools_test_data,
    ids=[
        f"{getattr(row, 'values', row)[0]}_{getattr(row, 'values', row)[1]}"
        for row in code_tools_test_data
    ],
)
def test_workflow_with_codebase_tools(
    assistant,
    code_datasource,
    code_context,
    similarity_check,
    workflow_with_assistant,
    workflow_utils,
    toolkit,
    tool_name,
    prompt,
    expected_response,
):
    assistant = assistant(toolkit, tool_name, context=code_context(code_datasource))
    workflow_with_assistant = workflow_with_assistant(assistant, prompt)
    response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, assistant.name
    )

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(tool_name, triggered_tools)

    similarity_check.check_similarity(response, expected_response)


@pytest.mark.github
@pytest.mark.gitlab
@pytest.mark.requires_capability("retrieval")
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, credentials, prompt,expected",
    sonar_tools_test_data,
)
def test_workflow_with_sonar_tools(
    assistant,
    code_datasource,
    code_context,
    integration_utils,
    similarity_check,
    workflow_with_assistant,
    workflow_utils,
    toolkit,
    tool_name,
    credentials,
    prompt,
    expected,
):
    settings = integration_utils.create_integration(CredentialTypes.SONAR, credentials)

    assistant = assistant(
        toolkit,
        CodeBaseTool.SONAR,
        context=code_context(code_datasource),
        settings=settings,
    )
    workflow_with_assistant = workflow_with_assistant(assistant, prompt)
    response = workflow_utils.execute_workflow(
        workflow_with_assistant.id, assistant.name
    )

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        workflow_with_assistant
    )
    assert_tool_triggered(CodeBaseTool.SONAR, triggered_tools)

    similarity_check.check_similarity(response, expected)
