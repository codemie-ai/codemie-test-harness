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

import copy
import json
import random

import pytest

from codemie_sdk.models.integration import CredentialTypes
from codemie_test_harness.tests.enums.tools import CodeBaseTool
from codemie_test_harness.tests.test_data.direct_tools.codebase_tools_test_data import (
    sonar_tools_test_data,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.sonar_seed import assert_issue_search_response


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, prompt, expected_issue_type",
    sonar_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in sonar_tools_test_data],
)
def test_workflow_with_sonar_tools_direct(
    workflow_with_tool,
    workflow_utils,
    integration_utils,
    toolkit,
    tool_name,
    prompt,
    expected_issue_type,
):
    assistant_and_state_name = get_random_name()
    credential_values = (
        CredentialsManager.sonar_credentials()
        if tool_name == CodeBaseTool.SONAR
        else CredentialsManager.sonar_cloud_credentials()
    )

    integration = integration_utils.create_integration(
        CredentialTypes.SONAR, credential_values
    )

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        CodeBaseTool.SONAR,
        integration=integration,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name, user_input=json.dumps(prompt)
    )
    assert_issue_search_response(response, expected_type=expected_issue_type)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, prompt, expected_issue_type",
    sonar_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in sonar_tools_test_data],
)
def test_workflow_with_sonar_tools_with_hardcoded_args(
    workflow_with_tool,
    workflow_utils,
    integration_utils,
    toolkit,
    tool_name,
    prompt,
    expected_issue_type,
):
    assistant_and_state_name = get_random_name()
    credential_values = (
        CredentialsManager.sonar_credentials()
        if tool_name == CodeBaseTool.SONAR
        else CredentialsManager.sonar_cloud_credentials()
    )

    integration = integration_utils.create_integration(
        CredentialTypes.SONAR, credential_values
    )

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        CodeBaseTool.SONAR,
        integration=integration,
        tool_args=prompt,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name
    )
    assert_issue_search_response(response, expected_type=expected_issue_type)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, prompt, expected_issue_type",
    sonar_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in sonar_tools_test_data],
)
def test_workflow_with_sonar_tools_with_overriding_args(
    workflow_with_tool,
    workflow_utils,
    integration_utils,
    toolkit,
    tool_name,
    prompt,
    expected_issue_type,
):
    assistant_and_state_name = get_random_name()
    credential_values = (
        CredentialsManager.sonar_credentials()
        if tool_name == CodeBaseTool.SONAR
        else CredentialsManager.sonar_cloud_credentials()
    )

    integration = integration_utils.create_integration(
        CredentialTypes.SONAR, credential_values
    )

    args_copy = copy.deepcopy(prompt)
    args_copy = {key: random.randint(1, 10) for key in args_copy}

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        CodeBaseTool.SONAR,
        integration=integration,
        tool_args=args_copy,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name, user_input=json.dumps(prompt)
    )
    assert_issue_search_response(response, expected_type=expected_issue_type)
