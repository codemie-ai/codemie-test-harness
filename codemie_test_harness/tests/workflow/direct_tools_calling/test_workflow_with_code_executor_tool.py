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

import json

import pytest
from hamcrest import contains_string, assert_that

from codemie_test_harness.tests.enums.tools import FileManagementTool
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.code_executor
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Skipping this tests on sandbox environments",
)
def test_workflow_with_code_executor_tool_node(workflow_with_tool, workflow_utils):
    """A bare Code Executor tool node (no assistant) runs hardcoded code and returns its stdout."""
    tool_and_state_name = get_random_name()
    test_workflow = workflow_with_tool(
        tool_and_state_name,
        FileManagementTool.CODE_EXECUTOR,
        tool_args={"code": "print(21 * 2)"},
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, tool_and_state_name, user_input=json.dumps({})
    )
    assert_that(response, contains_string("42"))
