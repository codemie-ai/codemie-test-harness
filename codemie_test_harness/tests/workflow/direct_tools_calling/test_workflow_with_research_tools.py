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

from codemie_test_harness.tests.test_data.direct_tools.research_tools_test_data import (
    research_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.research
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_name, prompt, expected_response",
    research_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in research_tools_test_data],
)
def test_workflow_with_research_tools_direct(
    workflow_with_tool,
    workflow_utils,
    similarity_check,
    tool_name,
    prompt,
    expected_response,
):
    tool_and_state_name = get_random_name()
    test_workflow = workflow_with_tool(tool_and_state_name, tool_name)
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, tool_and_state_name, json.dumps(prompt)
    )
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.research
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_name, prompt, expected_response",
    research_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in research_tools_test_data],
)
def test_workflow_with_research_tools_with_hardcoded_args(
    workflow_with_tool,
    workflow_utils,
    similarity_check,
    tool_name,
    prompt,
    expected_response,
):
    tool_and_state_name = get_random_name()
    test_workflow = workflow_with_tool(tool_and_state_name, tool_name, tool_args=prompt)
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, tool_and_state_name
    )
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.research
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_name, prompt, expected_response",
    research_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in research_tools_test_data],
)
def test_workflow_with_research_tools_with_overriding_args(
    workflow_with_tool,
    workflow_utils,
    similarity_check,
    tool_name,
    prompt,
    expected_response,
):
    tool_and_state_name = get_random_name()

    args_copy = copy.deepcopy(prompt)
    args_copy = {key: random.randint(1, 10) for key in args_copy}

    test_workflow = workflow_with_tool(
        tool_and_state_name, tool_name, tool_args=args_copy
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, tool_and_state_name, user_input=json.dumps(prompt)
    )
    similarity_check.check_similarity(response, expected_response)
