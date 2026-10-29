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

from codemie_test_harness.tests.test_data.direct_tools.project_management_tools_test_data import (
    project_management_tools_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.constants import project_management_integrations


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.project_management
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, integration_type, prompt, expected_response",
    project_management_tools_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in project_management_tools_data],
)
def test_workflow_with_project_management_tools_direct(
    request,
    workflow_with_tool,
    workflow_utils,
    similarity_check,
    toolkit,
    tool_name,
    integration_type,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    tool_and_state_name = get_random_name()

    integration = request.getfixturevalue(
        project_management_integrations[integration_type]
    )

    test_workflow = workflow_with_tool(
        tool_and_state_name, tool_name, integration=integration
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, tool_and_state_name, json.dumps(prompt)
    )
    similarity_check.check_similarity(response, expected_response, 90)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.project_management
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, integration_type, prompt, expected_response",
    project_management_tools_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in project_management_tools_data],
)
def test_workflow_with_project_management_tools_with_hardcoded_args(
    request,
    workflow_with_tool,
    workflow_utils,
    similarity_check,
    toolkit,
    tool_name,
    integration_type,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    tool_and_state_name = get_random_name()

    integration = request.getfixturevalue(
        project_management_integrations[integration_type]
    )

    test_workflow = workflow_with_tool(
        tool_and_state_name,
        tool_name,
        integration=integration,
        tool_args=prompt,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, tool_and_state_name
    )
    similarity_check.check_similarity(response, expected_response, 90)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.project_management
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, integration_type, prompt, expected_response",
    project_management_tools_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in project_management_tools_data],
)
def test_workflow_with_project_management_tools_with_overriding_args(
    request,
    workflow_with_tool,
    workflow_utils,
    similarity_check,
    toolkit,
    tool_name,
    integration_type,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    tool_and_state_name = get_random_name()

    args_copy = copy.deepcopy(prompt)
    args_copy = {key: random.randint(1, 10) for key in args_copy}

    integration = request.getfixturevalue(
        project_management_integrations[integration_type]
    )

    test_workflow = workflow_with_tool(
        tool_and_state_name, tool_name, integration=integration, tool_args=args_copy
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, tool_and_state_name, json.dumps(prompt)
    )
    similarity_check.check_similarity(response, expected_response, 90)
