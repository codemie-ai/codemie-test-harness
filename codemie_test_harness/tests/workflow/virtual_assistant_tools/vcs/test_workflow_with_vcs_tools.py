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

from codemie_test_harness.tests.test_data.vcs_tools_test_data import (
    vcs_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.constants import vcs_integrations


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.vcs
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    "tool_name, prompt, expected_response",
    vcs_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in vcs_tools_test_data],
)
def test_workflow_with_vcs_tool(
    request,
    workflow_with_virtual_assistant,
    workflow_utils,
    similarity_check,
    tool_name,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)

    integration = request.getfixturevalue(vcs_integrations[tool_name])

    assistant_and_state_name = get_random_name()
    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name, tool_name, integration=integration
    )

    response = workflow_utils.execute_workflow(
        test_workflow.id, assistant_and_state_name, user_input=prompt
    )

    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(tool_name, triggered_tools)

    similarity_check.check_similarity(response, expected_response)
