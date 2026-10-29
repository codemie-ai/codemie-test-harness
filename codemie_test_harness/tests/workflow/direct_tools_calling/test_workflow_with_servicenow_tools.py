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

import random

import pytest
import json
import copy

from hamcrest import assert_that, contains, has_entries

from codemie_test_harness.tests.enums.tools import ServiceNowTool
from codemie_test_harness.tests.test_data.direct_tools.servicenow_tools_test_data import (
    PROMPT,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.servicenow_seed import seed_tool_expectation


def assert_seed_incident_returned(response: str, seed):
    assert_that(
        json.loads(response),
        has_entries({"result": contains(has_entries(seed_tool_expectation(seed)))}),
    )


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.servicenow
@pytest.mark.api
def test_workflow_with_servicenow_tools_direct(
    service_now_integration,
    workflow_utils,
    workflow_with_tool,
    servicenow_seed_incident,
):
    assistant_and_state_name = get_random_name()

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        ServiceNowTool.SERVICE_NOW,
        integration=service_now_integration,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name, user_input=json.dumps(PROMPT)
    )
    assert_seed_incident_returned(response, servicenow_seed_incident)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.servicenow
@pytest.mark.api
def test_workflow_with_servicenow_tools_with_hardcoded_args(
    service_now_integration,
    workflow_utils,
    workflow_with_tool,
    servicenow_seed_incident,
):
    assistant_and_state_name = get_random_name()

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        ServiceNowTool.SERVICE_NOW,
        integration=service_now_integration,
        tool_args=PROMPT,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name
    )
    assert_seed_incident_returned(response, servicenow_seed_incident)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.servicenow
@pytest.mark.api
def test_workflow_with_servicenow_tools_with_overriding_args(
    service_now_integration,
    workflow_utils,
    workflow_with_tool,
    servicenow_seed_incident,
):
    assistant_and_state_name = get_random_name()

    args_copy = copy.deepcopy(PROMPT)
    args_copy = {key: random.randint(1, 10) for key in args_copy}

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        ServiceNowTool.SERVICE_NOW,
        integration=service_now_integration,
        tool_args=args_copy,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name, user_input=json.dumps(PROMPT)
    )
    assert_seed_incident_returned(response, servicenow_seed_incident)
