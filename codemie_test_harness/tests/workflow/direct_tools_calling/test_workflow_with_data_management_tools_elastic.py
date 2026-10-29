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
from hamcrest import assert_that, has_length, greater_than

from codemie_test_harness.tests import CredentialsManager
from codemie_test_harness.tests.enums.tools import DataManagementTool
from codemie_test_harness.tests.test_data.direct_tools.data_management_tools_test_data import (
    ELASTIC_TOOL_TASK,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

pytestmark = pytest.mark.skipif(
    EnvironmentResolver.is_localhost(),
    reason="Skipping this tests on local environment",
)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.elastic
@pytest.mark.api
def test_workflow_with_elastic_tools_direct(
    workflow_with_tool, workflow_utils, integration_utils
):
    assistant_and_state_name = get_random_name()
    credential_values = CredentialsManager.elasticsearch_credentials()
    integration = integration_utils.create_integration(
        CredentialTypes.ELASTIC, credential_values
    )

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        DataManagementTool.ELASTIC,
        integration=integration,
    )

    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name, json.dumps(ELASTIC_TOOL_TASK)
    )

    assert_that(json.loads(response)["hits"]["hits"], has_length(greater_than(0)))


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.elastic
@pytest.mark.api
def test_workflow_with_elastic_tools_with_hardcoded_args(
    workflow_with_tool, workflow_utils, integration_utils
):
    assistant_and_state_name = get_random_name()
    credential_values = CredentialsManager.elasticsearch_credentials()
    integration = integration_utils.create_integration(
        CredentialTypes.ELASTIC, credential_values
    )

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        DataManagementTool.ELASTIC,
        integration=integration,
        tool_args=ELASTIC_TOOL_TASK,
    )

    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name
    )

    assert_that(json.loads(response)["hits"]["hits"], has_length(greater_than(0)))


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.elastic
@pytest.mark.api
def test_workflow_with_elastic_tools_with_overriding_args(
    workflow_with_tool, workflow_utils, integration_utils
):
    assistant_and_state_name = get_random_name()
    credential_values = CredentialsManager.elasticsearch_credentials()
    integration = integration_utils.create_integration(
        CredentialTypes.ELASTIC, credential_values
    )

    args_copy = copy.deepcopy(ELASTIC_TOOL_TASK)
    args_copy = {key: random.randint(1, 10) for key in args_copy}

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        DataManagementTool.ELASTIC,
        integration=integration,
        tool_args=args_copy,
    )

    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name, json.dumps(ELASTIC_TOOL_TASK)
    )

    assert_that(json.loads(response)["hits"]["hits"], has_length(greater_than(0)))
