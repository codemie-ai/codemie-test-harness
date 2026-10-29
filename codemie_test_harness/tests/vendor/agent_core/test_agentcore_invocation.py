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

"""E2E tests for AgentCore assistant invocation."""

import uuid

import pytest
from hamcrest import (
    assert_that,
    is_not,
    none,
    empty,
    equal_to,
    has_item,
    contains_string,
    not_,
    matches_regexp,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.vendor_endpoint_test_data import (
    vendor_endpoint_test_data,
    NON_STREAMING_CONFIG,
    STREAMING_CONFIG,
    REASONING_CONFIG,
    STREAMING_WITH_EXTRA_TRIGGER_CONFIG,
    STREAMING_REASONING_CONFIG,
    PROMPT_FALLBACK_CONFIG,
    STREAM_TRIGGER_NON_STREAMING_CONFIG,
    RUNTIME_CHAT_PROMPT,
    TOOL_TRIGGER_PROMPT,
    ADD_NUMBERS_RESULT,
    HISTORY_SETUP_PROMPT,
    HISTORY_RECALL_PROMPT,
    HISTORY_EXPECTED_NAME,
    MULTI_TURN_CONFIG,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.vendor.agent_core.helpers import (
    get_prepared_env as _get_prepared_env,
)

_AWS_KEY_PATTERN = r"AKIA[0-9A-Z]{16}|aws_secret|aws_access_key"


class _AssistantRef:
    """Minimal assistant stub accepted by ask_assistant()."""

    def __init__(self, ai_run_id: str):
        self.id = ai_run_id


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_unauthorized_user_rejected(
    vendor_runtime_utils,
    assistant_utils,
    conversation_utils,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """chat with bogus aiRunId rejected before invocation (404)."""
    integration(credential_type, credentials)
    with pytest.raises(HTTPError) as exc_info:
        fake_ref = _AssistantRef(str(uuid.uuid4()))
        assistant_utils.ask_assistant(
            assistant=fake_ref,
            user_prompt=RUNTIME_CHAT_PROMPT,
            minimal_response=True,
        )
    assert_that(exc_info.value.response.status_code, equal_to(404))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_authorized_chat_non_streaming_returns_generated_text(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    managed_conversation,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """non-streaming config produces non-empty generated text."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Non-streaming invocation test",
        **NON_STREAMING_CONFIG,
    )
    conversation = managed_conversation(summary.aiRunId)

    generated = assistant_utils.ask_assistant(
        assistant=_AssistantRef(summary.aiRunId),
        user_prompt=RUNTIME_CHAT_PROMPT,
        minimal_response=True,
        conversation_id=conversation["id"],
    )

    assert_that(generated, is_not(none()))
    assert_that(generated, is_not(empty()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_authorized_chat_streaming_returns_generated_text(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    managed_conversation,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """streaming config produces non-empty generated text."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Streaming invocation test",
        **STREAMING_CONFIG,
    )
    conversation = managed_conversation(summary.aiRunId)

    generated = assistant_utils.ask_assistant(
        assistant=_AssistantRef(summary.aiRunId),
        user_prompt=RUNTIME_CHAT_PROMPT,
        minimal_response=True,
        stream=True,
        conversation_id=conversation["id"],
    )

    assert_that(generated, is_not(none()))
    assert_that(generated, is_not(empty()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_chat_with_reasoning_config_returns_thoughts(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    managed_conversation,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """reasoning config produces non-empty triggered_tools on tool-calling prompt."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Reasoning/thought extraction test",
        **REASONING_CONFIG,
    )
    conversation = managed_conversation(summary.aiRunId)

    generated, triggered_tools = assistant_utils.ask_assistant(
        assistant=_AssistantRef(summary.aiRunId),
        user_prompt=TOOL_TRIGGER_PROMPT,
        minimal_response=False,
        conversation_id=conversation["id"],
    )

    assert_that(generated, is_not(none()))
    assert_that(triggered_tools, is_not(empty()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_response_contains_no_credential_material(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    managed_conversation,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """generated response must not contain AWS credential patterns."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Credential material leak test",
        **NON_STREAMING_CONFIG,
    )
    conversation = managed_conversation(summary.aiRunId)

    generated = assistant_utils.ask_assistant(
        assistant=_AssistantRef(summary.aiRunId),
        user_prompt=RUNTIME_CHAT_PROMPT,
        minimal_response=True,
        conversation_id=conversation["id"],
    )

    assert_that(generated, is_not(none()))
    assert_that(generated, not_(matches_regexp(_AWS_KEY_PATTERN)))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_tool_result_correctness_and_thought_name(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    managed_conversation,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """add_numbers tool produces correct sum in text and tool name appears in thoughts."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Verify add_numbers result and thought name",
        **REASONING_CONFIG,
    )
    conversation = managed_conversation(summary.aiRunId)

    generated, triggered_tools = assistant_utils.ask_assistant(
        assistant=_AssistantRef(summary.aiRunId),
        user_prompt=TOOL_TRIGGER_PROMPT,
        minimal_response=False,
        conversation_id=conversation["id"],
    )

    assert_that(generated, is_not(none()))
    assert_that(generated, contains_string(ADD_NUMBERS_RESULT))
    assert_that(triggered_tools, is_not(empty()))
    assert_that(triggered_tools, has_item(contains_string("add_numbers")))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_multi_turn_conversation_history_retained(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    managed_conversation,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """agent recalls user-provided context from a prior turn in the same conversation."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Verify conversation history passthrough",
        **MULTI_TURN_CONFIG,
    )
    conversation = managed_conversation(summary.aiRunId)

    assistant_utils.ask_assistant(
        assistant=_AssistantRef(summary.aiRunId),
        user_prompt=HISTORY_SETUP_PROMPT,
        minimal_response=True,
        conversation_id=conversation["id"],
    )

    recall_response = assistant_utils.ask_assistant(
        assistant=_AssistantRef(summary.aiRunId),
        user_prompt=HISTORY_RECALL_PROMPT,
        minimal_response=True,
        conversation_id=conversation["id"],
    )

    assert_that(recall_response, is_not(none()))
    assert_that(recall_response, contains_string(HISTORY_EXPECTED_NAME))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_extra_payload_stream_trigger_returns_multiple_chunks(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    managed_conversation,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """extra_payload {"stream": true} triggers AgentCore streaming path and produces multiple response chunks."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Verify extra_payload stream flag produces chunks",
        **STREAMING_WITH_EXTRA_TRIGGER_CONFIG,
    )
    conversation = managed_conversation(summary.aiRunId)

    result = assistant_utils.ask_assistant(
        assistant=_AssistantRef(summary.aiRunId),
        user_prompt=RUNTIME_CHAT_PROMPT,
        stream=True,
        minimal_response=True,
        return_stream_metadata=True,
        conversation_id=conversation["id"],
    )

    assert_that(result["generated"], is_not(none()))
    assert_that(result["generated"], is_not(empty()))
    assert_that(result["chunk_count"], is_not(equal_to(0)))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_streaming_with_reasoning_returns_thoughts_and_text(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    managed_conversation,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """streaming config with reasoning paths produces both generated text and tool thoughts."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Verify streaming thought chunks alongside text",
        **STREAMING_REASONING_CONFIG,
    )
    conversation = managed_conversation(summary.aiRunId)

    result = assistant_utils.ask_assistant(
        assistant=_AssistantRef(summary.aiRunId),
        user_prompt=TOOL_TRIGGER_PROMPT,
        stream=True,
        minimal_response=False,
        return_stream_metadata=True,
        conversation_id=conversation["id"],
    )

    assert_that(result["generated"], is_not(none()))
    assert_that(result["generated"], is_not(empty()))
    assert_that(result["triggered_tools"], is_not(empty()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_non_default_message_path_prompt_fallback(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    managed_conversation,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """message_path='prompt' causes agent to use RequestParser prompt fallback and still respond."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Verify non-default message_path via prompt fallback",
        **PROMPT_FALLBACK_CONFIG,
    )
    conversation = managed_conversation(summary.aiRunId)

    generated = assistant_utils.ask_assistant(
        assistant=_AssistantRef(summary.aiRunId),
        user_prompt=RUNTIME_CHAT_PROMPT,
        minimal_response=True,
        conversation_id=conversation["id"],
    )

    assert_that(generated, is_not(none()))
    assert_that(generated, is_not(empty()))


@pytest.mark.agent_core
@pytest.mark.api
@pytest.mark.parametrize(
    "vendor_type,credential_type,credentials",
    vendor_endpoint_test_data,
)
def test_stream_trigger_without_streaming_config_raises_error(
    vendor_runtime_utils,
    assistant_utils,
    install_endpoint,
    managed_conversation,
    integration,
    vendor_type,
    credential_type,
    credentials,
):
    """extra_payload {"stream": true} with non-streaming config causes error — AgentCore streams but CodeMie expects a body."""
    setting, runtime, endpoints_response = _get_prepared_env(
        vendor_runtime_utils, integration, vendor_type, credential_type, credentials
    )
    unimported = vendor_runtime_utils.find_first_unimported_endpoint(
        endpoints_response.data
    )
    assert_that(unimported, is_not(none()))

    summary = install_endpoint(
        vendor_type,
        runtime_id=runtime.id,
        endpoint_name=unimported.name,
        setting_id=setting.setting_id,
        name=get_random_name(),
        description="Verify mismatch between AgentCore streaming and non-streaming config errors",
        **STREAM_TRIGGER_NON_STREAMING_CONFIG,
    )
    conversation = managed_conversation(summary.aiRunId)

    response = assistant_utils.ask_assistant(
        assistant=_AssistantRef(summary.aiRunId),
        user_prompt=RUNTIME_CHAT_PROMPT,
        minimal_response=True,
        conversation_id=conversation["id"],
    )

    assert_that(
        response, contains_string("AgentCore response could not be decoded as JSON")
    )
