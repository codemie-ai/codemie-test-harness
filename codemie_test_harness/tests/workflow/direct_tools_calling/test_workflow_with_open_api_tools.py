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

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.test_data.direct_tools.open_api_tools_test_data import (
    open_api_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.http_utils import RequestHandler

pytestmark = pytest.mark.skipif(
    EnvironmentResolver.is_azure(),
    reason="Still have an issue with encoding long strings",
)


def _resolve_expected_response(expected_response: str, client) -> str:
    """Fill the "{version}" placeholder from a live GET /v1/info call.

    Avoids hardcoding the platform's own version, which changes on every
    release. No-op when the expected text doesn't reference it.
    """
    if "{version}" not in expected_response:
        return expected_response
    api = RequestHandler(API_DOMAIN, client.token, VERIFY_SSL)
    live_version = api.get("/v1/info").json()["version"]
    return expected_response.replace("{version}", live_version)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.openapi
@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize(
    "toolkit, tool_name, prompt, expected_response",
    open_api_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in open_api_tools_test_data],
)
def test_workflow_with_open_api_tools_direct(
    workflow_with_tool,
    workflow_utils,
    open_api_integration,
    client,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    similarity_check,
):
    expected_response = _resolve_expected_response(expected_response, client)
    tool_and_state_name = get_random_name()
    test_workflow = workflow_with_tool(
        tool_and_state_name, tool_name, integration=open_api_integration
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, tool_and_state_name, json.dumps(prompt)
    )

    similarity_check.check_similarity(response, expected_response, 90)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.openapi
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, prompt, expected_response",
    open_api_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in open_api_tools_test_data],
)
def test_workflow_with_open_api_tools_with_hardcoded_args(
    workflow_with_tool,
    workflow_utils,
    open_api_integration,
    client,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    similarity_check,
):
    expected_response = _resolve_expected_response(expected_response, client)
    tool_and_state_name = get_random_name()
    test_workflow = workflow_with_tool(
        tool_and_state_name,
        tool_name,
        tool_args=prompt,
        integration=open_api_integration,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, tool_and_state_name
    )

    similarity_check.check_similarity(response, expected_response, 90)


@pytest.mark.workflow
@pytest.mark.direct_tool
@pytest.mark.openapi
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit, tool_name, prompt, expected_response",
    open_api_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[1]}" for row in open_api_tools_test_data],
)
def test_workflow_with_open_api_tools_with_overriding_args(
    workflow_with_tool,
    workflow_utils,
    open_api_integration,
    client,
    toolkit,
    tool_name,
    prompt,
    expected_response,
    similarity_check,
):
    expected_response = _resolve_expected_response(expected_response, client)
    tool_and_state_name = get_random_name()

    args_copy = copy.deepcopy(prompt)
    args_copy = {key: random.randint(1, 10) for key in args_copy}

    test_workflow = workflow_with_tool(
        tool_and_state_name,
        tool_name,
        tool_args=args_copy,
        integration=open_api_integration,
    )
    response = workflow_utils.execute_workflow_without_prompt_modification(
        test_workflow.id, tool_and_state_name, json.dumps(prompt)
    )

    similarity_check.check_similarity(response, expected_response, 90)
