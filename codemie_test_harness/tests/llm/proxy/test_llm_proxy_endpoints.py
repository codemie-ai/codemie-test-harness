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
E2E tests for LLM proxy endpoints (/v1/messages, /v1/messages/count_tokens, /v1/embeddings).
"""

import uuid

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than,
    not_none,
    has_key,
    less_than_or_equal_to,
)

from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

pytestmark = [
    pytest.mark.skipif(
        EnvironmentResolver.is_sandbox(),
        reason="LiteLLM is not configured for sandbox environments",
    ),
    pytest.mark.enterprise,
]
# /v1/messages endpoint tests


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_messages_endpoint_with_valid_request(proxy_utils, default_llm):
    messages = [
        {
            "role": "user",
            "content": f"REQUEST_UUID: {uuid.uuid4()}; Say 'Hello' in one word",
        }
    ]
    response = proxy_utils.send_messages_request(
        model=default_llm.base_name, messages=messages, max_tokens=100
    )

    assert_that(response.status_code, equal_to(200))
    response_data = response.json()

    assert_that(response_data, has_key("id"))
    assert_that(response_data, has_key("type"))
    assert_that(response_data, has_key("content"))
    assert_that(response_data, has_key("model"))
    assert_that(response_data, has_key("usage"))
    assert_that(response_data["content"], not_none())
    assert_that(len(response_data["content"]), greater_than(0))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_messages_endpoint_streaming(proxy_utils, sonnet_46_llm):
    messages = [
        {
            "role": "user",
            "content": f"REQUEST_UUID: {uuid.uuid4()}; Count from 1 to 5, one number per line",
        }
    ]
    response = proxy_utils.send_messages_request(
        model=sonnet_46_llm.base_name, messages=messages, max_tokens=2000, stream=True
    )

    assert_that(response.status_code, equal_to(200))

    chunks = proxy_utils.parse_streaming_response(response)
    assert_that(len(chunks), greater_than(1))

    for chunk in chunks:
        assert_that(chunk, has_key("type"))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_messages_endpoint_without_authentication(proxy_utils, default_llm):
    payload = {
        "model": default_llm.base_name,
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "Hello"}],
    }
    response = proxy_utils.send_unauthenticated_request(
        proxy_utils.messages_url, payload
    )

    assert_that(response.status_code, equal_to(302))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_messages_endpoint_with_invalid_model(proxy_utils):
    messages = [{"role": "user", "content": "Hello"}]
    response = proxy_utils.send_messages_request(
        model="non-existent-model-12345", messages=messages, max_tokens=100, timeout=10
    )

    assert_that(response.status_code, equal_to(400))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_messages_endpoint_with_integration_header(
    proxy_utils, lite_llm_integration, default_llm
):
    messages = [
        {"role": "user", "content": f"REQUEST_UUID: {uuid.uuid4()}; Say 'Hello'"}
    ]
    response = proxy_utils.send_messages_request(
        model=default_llm.base_name,
        messages=messages,
        max_tokens=100,
        integration_id=lite_llm_integration.id,
    )

    assert_that(response.status_code, equal_to(200))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_count_tokens_endpoint_with_valid_request(proxy_utils, default_llm):
    messages = [
        {
            "role": "user",
            "content": "This is a test message to count tokens. It has several words.",
        }
    ]
    response = proxy_utils.send_count_tokens_request(
        model=default_llm.base_name, messages=messages
    )

    assert_that(response.status_code, equal_to(200))
    response_data = response.json()

    assert_that(response_data, has_key("input_tokens"))
    assert_that(response_data["input_tokens"], greater_than(0))
    assert_that(response_data["input_tokens"], less_than_or_equal_to(100))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_count_tokens_endpoint_with_integration_header(
    proxy_utils, default_llm, lite_llm_integration
):
    messages = [
        {
            "role": "user",
            "content": "This is a test message to count tokens. It has several words.",
        }
    ]
    response = proxy_utils.send_count_tokens_request(
        model=default_llm.base_name,
        messages=messages,
        integration_id=lite_llm_integration.id,
    )

    assert_that(response.status_code, equal_to(200))
    response_data = response.json()

    assert_that(response_data, has_key("input_tokens"))
    assert_that(response_data["input_tokens"], greater_than(0))
    assert_that(response_data["input_tokens"], less_than_or_equal_to(100))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_count_tokens_endpoint_without_authentication(proxy_utils, default_llm):
    payload = {
        "model": default_llm.base_name,
        "messages": [{"role": "user", "content": "Hello"}],
    }
    response = proxy_utils.send_unauthenticated_request(
        proxy_utils.count_tokens_url, payload
    )

    assert_that(response.status_code, equal_to(302))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_count_tokens_endpoint_with_multiple_messages(
    proxy_utils, default_llm, lite_llm_integration
):
    messages_single = [{"role": "user", "content": "Hello"}]
    response_single = proxy_utils.send_count_tokens_request(
        model=default_llm.base_name,
        messages=messages_single,
        integration_id=lite_llm_integration.id,
    )
    assert_that(response_single.status_code, equal_to(200))
    single_tokens = response_single.json()["input_tokens"]

    messages_multi = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]
    response_multi = proxy_utils.send_count_tokens_request(
        model=default_llm.base_name,
        messages=messages_multi,
        integration_id=lite_llm_integration.id,
    )
    assert_that(response_multi.status_code, equal_to(200))
    multi_tokens = response_multi.json()["input_tokens"]

    assert_that(multi_tokens, greater_than(single_tokens))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_embeddings_endpoint_with_valid_request(proxy_utils, default_embedding_llm):
    input_text = "The quick brown fox jumps over the lazy dog"
    response = proxy_utils.send_embeddings_request(
        model=default_embedding_llm.base_name, input_text=input_text
    )

    assert_that(response.status_code, equal_to(200))
    response_data = response.json()

    assert_that(response_data, has_key("object"))
    assert_that(response_data["object"], equal_to("list"))
    assert_that(response_data, has_key("data"))
    assert_that(response_data, has_key("model"))
    assert_that(response_data, has_key("usage"))

    assert_that(len(response_data["data"]), greater_than(0))
    embedding = response_data["data"][0]
    assert_that(embedding, has_key("object"))
    assert_that(embedding["object"], equal_to("embedding"))
    assert_that(embedding, has_key("embedding"))
    assert_that(embedding, has_key("index"))

    embedding_vector = embedding["embedding"]
    assert_that(len(embedding_vector), greater_than(100))
    assert_that(
        all(isinstance(v, (int, float)) for v in embedding_vector), equal_to(True)
    )


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_embeddings_endpoint_with_multiple_inputs(proxy_utils, default_embedding_llm):
    inputs = [
        "First test sentence",
        "Second test sentence",
        "Third test sentence",
    ]
    response = proxy_utils.send_embeddings_request(
        model=default_embedding_llm.base_name, input_text=inputs
    )

    assert_that(response.status_code, equal_to(200))
    response_data = response.json()

    assert_that(len(response_data["data"]), equal_to(len(inputs)))

    for i, embedding_data in enumerate(response_data["data"]):
        assert_that(embedding_data["index"], equal_to(i))
        assert_that(len(embedding_data["embedding"]), greater_than(100))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_embeddings_endpoint_without_authentication(proxy_utils, default_embedding_llm):
    payload = {
        "model": default_embedding_llm.base_name,
        "input": "Test input",
    }
    response = proxy_utils.send_unauthenticated_request(
        proxy_utils.embeddings_url, payload
    )

    assert_that(response.status_code, equal_to(302))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_embeddings_endpoint_with_empty_input(proxy_utils, default_embedding_llm):
    response = proxy_utils.send_embeddings_request(
        model=default_embedding_llm.base_name, input_text="", timeout=10
    )

    assert_that(response.status_code, equal_to(200))
    response_data = response.json()

    assert_that(response_data, has_key("object"))


@pytest.mark.api
@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.production_check
def test_embeddings_endpoint_with_integration_header(
    proxy_utils, lite_llm_integration, default_embedding_llm
):
    response = proxy_utils.send_embeddings_request(
        model=default_embedding_llm.base_name,
        input_text="Test embedding with integration",
        integration_id=lite_llm_integration.id,
    )

    assert_that(response.status_code, equal_to(200))
    assert_that(response.json(), has_key("data"))
