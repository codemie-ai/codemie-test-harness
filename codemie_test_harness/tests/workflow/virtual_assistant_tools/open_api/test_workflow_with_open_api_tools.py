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

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.test_data.open_api_tools_test_data import (
    open_api_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.http_utils import RequestHandler


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
@pytest.mark.virtual_workflow
@pytest.mark.openapi
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_azure(),
    reason="Still have an issue with encoding long strings",
)
@pytest.mark.parametrize(
    "tool_name, prompt, expected_response",
    open_api_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in open_api_tools_test_data],
)
def test_workflow_with_open_api_tools(
    workflow_with_virtual_assistant,
    open_api_integration,
    workflow_utils,
    similarity_check,
    client,
    tool_name,
    prompt,
    expected_response,
):
    expected_response = _resolve_expected_response(expected_response, client)
    assistant_and_state_name = get_random_name()
    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        tool_name,
        integration=open_api_integration,
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
