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
from hamcrest import not_, assert_that, contains_string

from codemie_test_harness.tests.test_data.direct_tools.vcs_tools_test_data import (
    vcs_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.constants import vcs_integrations


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.vcs
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    vcs_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in vcs_tools_test_data],
)
def test_workflow_with_vcs_tools_direct(
    request,
    workflow_with_tool,
    workflow_utils,
    integration_utils,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    similarity_check,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)

    integration = request.getfixturevalue(vcs_integrations[tool_name])

    assistant_and_state_name = get_random_name()

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        tool_name,
        integration=integration,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name, json.dumps(prompt)
    )

    assert_that(response, not_(contains_string("400 Bad Request")))
    similarity_check.check_similarity(response, expected_response, 90)


@pytest.mark.api
@pytest.mark.direct_tool
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    vcs_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in vcs_tools_test_data],
)
def test_workflow_with_vcs_tools_with_hardcoded_args(
    request,
    workflow_with_tool,
    workflow_utils,
    integration_utils,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    similarity_check,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)

    integration = request.getfixturevalue(vcs_integrations[tool_name])

    assistant_and_state_name = get_random_name()

    test_workflow = workflow_with_tool(
        assistant_and_state_name,
        tool_name,
        integration=integration,
        tool_args=prompt,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, assistant_and_state_name
    )

    similarity_check.check_similarity(response, expected_response, 90)


@pytest.mark.api
@pytest.mark.direct_tool
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    vcs_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in vcs_tools_test_data],
)
def test_workflow_with_vcs_tools_with_overriding_args(
    request,
    workflow_with_tool,
    workflow_utils,
    integration_utils,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    similarity_check,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)

    integration = request.getfixturevalue(vcs_integrations[tool_name])

    assistant_and_state_name = get_random_name()

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

    similarity_check.check_similarity(response, expected_response, 90)
