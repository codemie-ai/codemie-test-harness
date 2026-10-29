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

"""
Regression tests: litellm.UnsupportedParamsError during
OpenCode context compaction on Bedrock-backed Claude models.

When context compaction sends a request to a Bedrock-backed model that includes
a prior tool_use/tool_result exchange but no top-level tools array, Bedrock
rejects the request with UnsupportedParamsError. Setting modify_params: true in
litellm_settings causes LiteLLM to auto-inject a dummy tools array and
satisfy Bedrock requirements, so these requests must return HTTP 200.
"""

import uuid

import pytest
from hamcrest import assert_that, equal_to, has_key

from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

pytestmark = [
    pytest.mark.skipif(
        EnvironmentResolver.is_sandbox(),
        reason="LiteLLM is not configured for sandbox environments",
    ),
    pytest.mark.enterprise,
]


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_messages_succeeds_with_tool_use_history_and_no_tools_on_bedrock(proxy_utils):
    """
    Regression: Bedrock rejects tool-less requests when prior
    messages contain a tool_use block.

    Simulates an OpenCode context compaction request: the messages history
    includes an assistant tool_use block and a corresponding tool_result, but the
    request carries no top-level tools array. With modify_params: true configured
    for the Bedrock model group, LiteLLM auto-injects a dummy tools array and the
    request must succeed with HTTP 200.
    """
    messages = [
        {
            "role": "user",
            "content": f"REQUEST_UUID: {uuid.uuid4()}; What is the capital of France?",
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_01",
                    "name": "web_search",
                    "input": {"query": "capital of France"},
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_01",
                    "content": "Paris",
                },
                {
                    "type": "text",
                    "text": "Summarize the conversation so far.",
                },
            ],
        },
    ]

    # No tools array — this is the exact payload pattern that triggered the bug
    response = proxy_utils.send_messages_request(
        model=ModelTypes.CLAUDE_4_5_HAIKU.value,
        messages=messages,
        max_tokens=100,
    )

    assert_that(
        response.status_code,
        equal_to(200),
        "Expected HTTP 200 — modify_params should auto-inject dummy tools for Bedrock",
    )
    assert_that(response.json(), has_key("type"))
