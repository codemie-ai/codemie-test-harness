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

from codemie_test_harness.tests.enums.tools import Toolkit, CloudTool
from codemie_test_harness.tests.test_data.direct_tools.cloud_tools_test_data import (
    cloud_test_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.cloud
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    "toolkit,tool_name,credential_type,credentials,prompt,expected_response",
    cloud_test_data,
    ids=[
        f"{Toolkit.CLOUD}_{CloudTool.AWS}",
        f"{Toolkit.CLOUD}_{CloudTool.AZURE}",
        f"{Toolkit.CLOUD}_{CloudTool.GCP}",
        f"{Toolkit.CLOUD}_{CloudTool.KUBERNETES}",
    ],
)
def test_workflow_with_cloud_tools_direct(
    integration,
    workflow_utils,
    similarity_check,
    workflow_with_tool,
    toolkit,
    tool_name,
    credential_type,
    credentials,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    tool_and_state_name = get_random_name()

    cloud_integration = integration(credential_type, credentials)

    _workflow = workflow_with_tool(
        tool_and_state_name, tool_name, integration=cloud_integration
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        _workflow.id, tool_and_state_name, user_input=json.dumps(prompt)
    )

    similarity_check.check_similarity(response, expected_response)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.cloud
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,credential_type,credentials,prompt,expected_response",
    cloud_test_data,
    ids=[
        f"{Toolkit.CLOUD}_{CloudTool.AWS}_hardcoded",
        f"{Toolkit.CLOUD}_{CloudTool.AZURE}_hardcoded",
        f"{Toolkit.CLOUD}_{CloudTool.GCP}_hardcoded",
        f"{Toolkit.CLOUD}_{CloudTool.KUBERNETES}_hardcoded",
    ],
)
def test_workflow_with_cloud_tools_with_hardcoded_args(
    integration,
    workflow_utils,
    similarity_check,
    workflow_with_tool,
    toolkit,
    tool_name,
    credential_type,
    credentials,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    tool_and_state_name = get_random_name()

    cloud_integration = integration(credential_type, credentials)

    _workflow = workflow_with_tool(
        tool_and_state_name, tool_name, integration=cloud_integration, tool_args=prompt
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        _workflow.id, tool_and_state_name
    )

    similarity_check.check_similarity(response, expected_response)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.cloud
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,credential_type,credentials,prompt,expected_response",
    cloud_test_data,
    ids=[
        f"{Toolkit.CLOUD}_{CloudTool.AWS}_overriding",
        f"{Toolkit.CLOUD}_{CloudTool.AZURE}_overriding",
        f"{Toolkit.CLOUD}_{CloudTool.GCP}_overriding",
        f"{Toolkit.CLOUD}_{CloudTool.KUBERNETES}_overriding",
    ],
)
def test_workflow_with_cloud_tools_with_overriding_args(
    integration,
    workflow_utils,
    similarity_check,
    workflow_with_tool,
    toolkit,
    tool_name,
    credential_type,
    credentials,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)
    tool_and_state_name = get_random_name()

    cloud_integration = integration(credential_type, credentials)

    args_copy = copy.deepcopy(prompt)
    args_copy = {key: random.randint(1, 10) for key in args_copy}

    _workflow = workflow_with_tool(
        tool_and_state_name,
        tool_name,
        integration=cloud_integration,
        tool_args=args_copy,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        _workflow.id, tool_and_state_name, user_input=json.dumps(prompt)
    )

    similarity_check.check_similarity(response, expected_response)
