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
from hamcrest import assert_that, contains_inanyorder

from codemie_test_harness.tests.test_data.direct_tools.data_management_tools_test_data import (
    sql_tools_test_data,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.base_utils import get_random_name

pytestmark = pytest.mark.skipif(
    EnvironmentResolver.is_localhost(),
    reason="Skipping this tests on local environment",
)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.sql
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,db_dialect,prompt,expected_response",
    sql_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[2]}" for row in sql_tools_test_data],
)
def test_workflow_with_sql_tools_direct(
    workflow_with_tool,
    workflow_utils,
    integration_utils,
    toolkit,
    tool_name,
    db_dialect,
    prompt,
    expected_response,
):
    assistant_and_state_name = get_random_name()
    credential_values = CredentialsManager.sql_credentials(db_dialect)
    integration = integration_utils.create_integration(
        CredentialTypes.SQL, credential_values
    )

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        tool_name,
        integration=integration,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name, json.dumps(prompt)
    )

    filtered_response = [
        item for item in json.loads(response) if item in expected_response
    ]

    assert_that(filtered_response, contains_inanyorder(*expected_response))


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.sql
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,db_dialect,prompt,expected_response",
    sql_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[2]}" for row in sql_tools_test_data],
)
def test_workflow_with_sql_tools_with_hardcoded_args(
    workflow_with_tool,
    workflow_utils,
    integration_utils,
    toolkit,
    tool_name,
    db_dialect,
    prompt,
    expected_response,
):
    assistant_and_state_name = get_random_name()
    credential_values = CredentialsManager.sql_credentials(db_dialect)
    integration = integration_utils.create_integration(
        CredentialTypes.SQL, credential_values
    )

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        tool_name,
        integration=integration,
        tool_args=prompt,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name
    )

    filtered_response = [
        item for item in json.loads(response) if item in expected_response
    ]

    assert_that(filtered_response, contains_inanyorder(*expected_response))


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.sql
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,db_dialect,prompt,expected_response",
    sql_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[2]}" for row in sql_tools_test_data],
)
def test_workflow_with_sql_tools_with_overriding_args(
    workflow_with_tool,
    workflow_utils,
    integration_utils,
    toolkit,
    tool_name,
    db_dialect,
    prompt,
    expected_response,
):
    assistant_and_state_name = get_random_name()
    credential_values = CredentialsManager.sql_credentials(db_dialect)
    integration = integration_utils.create_integration(
        CredentialTypes.SQL, credential_values
    )

    args_copy = copy.deepcopy(prompt)
    args_copy = {key: random.randint(1, 10) for key in args_copy}

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        tool_name,
        integration=integration,
        tool_args=args_copy,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name, json.dumps(prompt)
    )

    filtered_response = [
        item for item in json.loads(response) if item in expected_response
    ]

    assert_that(filtered_response, contains_inanyorder(*expected_response))
