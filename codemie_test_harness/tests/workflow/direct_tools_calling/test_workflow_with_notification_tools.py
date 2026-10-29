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

import pytest

from codemie_test_harness.tests.enums.tools import NotificationTool
from codemie_test_harness.tests.test_data.direct_tools.notification_tools_test_data import (
    notification_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.constants import notification_integrations


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.notification
@pytest.mark.api
@pytest.mark.parametrize(
    "tool, prompt, expected_response",
    notification_tools_test_data,
    ids=[NotificationTool.EMAIL, NotificationTool.TELEGRAM],
)
def test_workflow_with_notification_tools_direct(
    request,
    workflow_utils,
    similarity_check,
    workflow_with_tool,
    tool,
    prompt,
    expected_response,
):
    tool_and_state_name = get_random_name()

    _integration = request.getfixturevalue(notification_integrations[tool])

    _workflow = workflow_with_tool(tool_and_state_name, tool, integration=_integration)

    response = workflow_utils.execute_workflow_without_prompt_modification(
        _workflow.id, tool_and_state_name, user_input=json.dumps(prompt)
    )

    similarity_check.check_similarity(response, expected_response, 75)


@pytest.mark.api
@pytest.mark.parametrize(
    "tool, prompt, expected_response",
    notification_tools_test_data,
    ids=[NotificationTool.EMAIL, NotificationTool.TELEGRAM],
)
def test_workflow_with_notification_tools_with_hardcoded_args(
    request,
    workflow_utils,
    similarity_check,
    workflow_with_tool,
    tool,
    prompt,
    expected_response,
):
    tool_and_state_name = get_random_name()

    _integration = request.getfixturevalue(notification_integrations[tool])
    _workflow = workflow_with_tool(
        tool_and_state_name, tool, integration=_integration, tool_args=prompt
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        _workflow.id, tool_and_state_name
    )

    similarity_check.check_similarity(response, expected_response, 75)


@pytest.mark.api
@pytest.mark.parametrize(
    "tool, prompt, expected_response",
    notification_tools_test_data,
    ids=[NotificationTool.EMAIL, NotificationTool.TELEGRAM],
)
def test_workflow_with_notification_tools_with_overriding_args(
    request,
    workflow_utils,
    similarity_check,
    workflow_with_tool,
    tool,
    prompt,
    expected_response,
):
    tool_and_state_name = get_random_name()

    _integration = request.getfixturevalue(notification_integrations[tool])

    args_copy = copy.deepcopy(prompt) if isinstance(prompt, dict) else prompt
    # Optionally, mutate args_copy as needed for overriding logic
    _workflow = workflow_with_tool(
        tool_and_state_name,
        tool,
        integration=_integration,
        tool_args=args_copy,
    )

    response = workflow_utils.execute_workflow_without_prompt_modification(
        _workflow.id, tool_and_state_name, user_input=json.dumps(prompt)
    )

    similarity_check.check_similarity(response, expected_response, 75)
