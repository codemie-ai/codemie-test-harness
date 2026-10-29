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
from hamcrest import assert_that, greater_than

from codemie_test_harness.tests.enums.tools import ResearchToolName
from codemie_test_harness.tests.test_data.research_tools_test_data import (
    search_tools_test_data,
    interactions_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    percent_of_relevant_titles,
    assert_tool_triggered,
)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.research
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_name, prompt, expected_percentage",
    search_tools_test_data,
    ids=[ResearchToolName.GOOGLE_SEARCH, ResearchToolName.TAVILY_SEARCH],
)
def test_workflow_with_search_tools(
    workflow_with_virtual_assistant,
    workflow_utils,
    tool_name,
    prompt,
    expected_percentage,
):
    assistant_and_state_name = get_random_name()
    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        tool_name,
        task=prompt,
    )
    response = workflow_utils.execute_workflow(
        test_workflow.id, assistant_and_state_name
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(tool_name, triggered_tools)
    percent = percent_of_relevant_titles(response)

    assert_that(
        percent,
        greater_than(expected_percentage),
        f"The percentage of relevant titles ({percent}%) is less than {expected_percentage}%",
    )


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.research
@pytest.mark.api
@pytest.mark.parametrize(
    "tool_name, prompt, expected_response",
    interactions_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in interactions_tools_test_data],
)
def test_workflow_with_interaction_tools(
    workflow_with_virtual_assistant,
    similarity_check,
    workflow_utils,
    tool_name,
    prompt,
    expected_response,
):
    assistant_and_state_name = get_random_name()
    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        tool_name,
        task=prompt,
    )
    response = workflow_utils.execute_workflow(
        test_workflow.id, assistant_and_state_name
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(tool_name, triggered_tools)

    similarity_check.check_similarity(response, expected_response)
