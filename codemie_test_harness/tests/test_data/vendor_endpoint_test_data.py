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

"""Test data for vendor service endpoint tests."""

import pytest
from codemie_sdk.models.vendor_assistant import VendorType
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

RUNTIME_CHAT_PROMPT = "Just say one word: 'Hello'"
RUNTIME_CHAT_EXPECTED = "Hello"

# Test data for vendor endpoint tests
# Extensible for AWS Bedrock, Azure AI, and GCP Vertex AI
vendor_endpoint_test_data = [
    pytest.param(
        VendorType.AWS,
        CredentialTypes.AWS,
        CredentialsManager.aws_credentials(),
        marks=[pytest.mark.aws, pytest.mark.bedrock],
        id="AWS_Bedrock",
    ),
    # Future: Azure AI endpoints
    # pytest.param(
    #     VendorType.AZURE,
    #     CredentialTypes.AZURE,
    #     CredentialsManager.azure_credentials(),
    #     marks=[pytest.mark.azure],
    #     id="Azure_AI",
    # ),
    # Future: GCP Vertex AI endpoints
    # pytest.param(
    #     VendorType.GCP,
    #     CredentialTypes.GCP,
    #     CredentialsManager.gcp_credentials(),
    #     marks=[pytest.mark.gcp],
    #     id="GCP_Vertex_AI",
    # ),
]

# Structured config presets for AgentCore wrapper CRUD and invocation tests
NON_STREAMING_CONFIG = dict(message_path="message", streaming=False, text_path="text")
STREAMING_CONFIG = dict(message_path="message", streaming=True, chunk_text_path="text")
REASONING_CONFIG = dict(
    message_path="message",
    streaming=False,
    text_path="text",
    thoughts_path="thoughts",
    thought_text_path="thinking",
    thought_name_path="tool",
    thought_args_path="args",
    thought_active_path="active",
)
EXTRA_PAYLOAD_CONFIG = dict(
    message_path="message",
    streaming=False,
    text_path="text",
    extra_payload={"sessionId": "test-123"},
)

# Prompts used by invocation tests against the deployed agent
TOOL_TRIGGER_PROMPT = "Add 5 and 6"

# Test: add_numbers tool result correctness
ADD_NUMBERS_RESULT = "11"

# Test: multi-turn conversation history
HISTORY_SETUP_PROMPT = "My name is Alice. Just say: 'Got it, Alice'"
HISTORY_RECALL_PROMPT = "What is my name? Just say my name, nothing else."
HISTORY_EXPECTED_NAME = "Alice"

# history_path="messages" matches AgentCore SDK DEFAULT_CONFIG — tells CodeMie to include
# conversation history in the payload under the "messages" key
MULTI_TURN_CONFIG = dict(
    message_path="message",
    streaming=False,
    text_path="text",
    history_path="messages",
)

# Test: extra_payload {"stream": true} triggers AgentCore streaming path
STREAMING_WITH_EXTRA_TRIGGER_CONFIG = dict(
    message_path="message",
    streaming=True,
    chunk_text_path="text",
    extra_payload={"stream": True},
)

# Test: streaming + reasoning paths combined
STREAMING_REASONING_CONFIG = dict(
    message_path="message",
    streaming=True,
    chunk_text_path="text",
    extra_payload={"stream": True},
    thought_text_path="thinking",
    thought_name_path="tool",
    thought_args_path="args",
    thought_active_path="active",
)

# Test: non-default message_path forces agent to fall back to "prompt" field
PROMPT_FALLBACK_CONFIG = dict(
    message_path="prompt",
    streaming=False,
    text_path="text",
)

# Test: extra_payload triggers AgentCore streaming but CodeMie expects a body — mismatch → error
STREAM_TRIGGER_NON_STREAMING_CONFIG = dict(
    message_path="message",
    streaming=False,
    text_path="text",
    extra_payload={"stream": True},
)
