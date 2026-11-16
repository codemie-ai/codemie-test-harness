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

"""Provider-native Claude prompt caching (Bedrock), replacing the removed
per-request SmartCacheCallbackHandler.

Needs a Bedrock environment (``AWS_ENVS`` in ``llm_test_data.py``) because only
Claude models on Bedrock/Anthropic/Vertex are cache-eligible.
"""

import uuid

import pytest
from hamcrest import assert_that, greater_than, has_length

from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.test_data.llm_test_data import AWS_ENVS
from codemie_test_harness.tests.utils.env_resolver import get_environment

_AWS_CLAUDE_MODEL = ModelTypes.CLAUDE_4_5_SONNET

# Large enough to clear the provider's per-prefix minimum token count for prompt
# caching (1024 tokens for Claude Sonnet/Opus); its content is otherwise irrelevant.
_STABLE_CONTEXT_BLOCK = (
    "Reference material for this conversation, do not summarize or alter it: "
    + "The quick brown fox jumps over the lazy dog. " * 400
)

# Individually well under the provider's per-message cache minimum; several of
# these combined (across turns) exceed it.
_SHORT_TURN_MESSAGE = (
    "Please acknowledge this note and reply with just 'OK'. "
    + "Note: context padding. " * 40
)

_SKIP_REASON = "Needs a Bedrock environment (AWS_ENVS in llm_test_data.py)"


@pytest.mark.skipif(get_environment() not in AWS_ENVS, reason=_SKIP_REASON)
@pytest.mark.llm
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_repeated_stable_prefix_reuses_bedrock_claude_cache(
    assistant_factory, assistant_utils, conversation_utils
):
    """Repeated stable Claude prefix reuses the provider cache with
    provider-reported accounting (AC-1, AC-5).

    # @case claude-prompt-cache-callback-removes-checkpoints_TC_001
    """
    created_assistant = assistant_factory.create(
        _AWS_CLAUDE_MODEL, system_prompt="You are a helpful assistant."
    )
    conversation_id = str(uuid.uuid4())
    prompt = (
        f"{_STABLE_CONTEXT_BLOCK}\n\n"
        "Based on the reference material above, reply with one word: OK."
    )

    assistant_utils.ask_assistant(
        created_assistant, prompt, conversation_id=conversation_id
    )
    assistant_utils.ask_assistant(
        created_assistant, prompt, conversation_id=conversation_id
    )

    history = conversation_utils.get_conversation_by_id(conversation_id).history
    first_assistant_turn, second_assistant_turn = history[1], history[3]

    assert_that(
        first_assistant_turn.cacheCreationInputTokens,
        greater_than(0),
        "the first request over a large, stable prefix must create a provider "
        "cache checkpoint (cacheCreationInputTokens)",
    )
    assert_that(
        second_assistant_turn.cacheReadInputTokens,
        greater_than(0),
        "resending the same, unchanged stable prefix must reuse the checkpoint "
        "created by the first request (cacheReadInputTokens)",
    )


@pytest.mark.skipif(get_environment() not in AWS_ENVS, reason=_SKIP_REASON)
@pytest.mark.llm
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_cumulative_short_turns_exceeding_minimum_get_cached(
    assistant_factory, assistant_utils, conversation_utils
):
    """Cumulative short-message prefix meets the provider minimum and still gets
    cached — eligibility has no per-message or cumulative token-count gate (AC-3).

    # @case claude-prompt-cache-callback-removes-checkpoints_TC_002
    """
    created_assistant = assistant_factory.create(
        _AWS_CLAUDE_MODEL, system_prompt="You are a helpful assistant."
    )
    conversation_id = str(uuid.uuid4())

    short_turns = 6
    for _ in range(short_turns):
        response = assistant_utils.ask_assistant(
            created_assistant, _SHORT_TURN_MESSAGE, conversation_id=conversation_id
        )
        assert_that(
            response,
            has_length(greater_than(0)),
            "a turn under the provider's per-message minimum must not be "
            "rejected or skipped for caching eligibility purely for being short",
        )

    # One more short turn, reusing the accumulated history built up above.
    assistant_utils.ask_assistant(
        created_assistant, _SHORT_TURN_MESSAGE, conversation_id=conversation_id
    )

    history = conversation_utils.get_conversation_by_id(conversation_id).history
    last_assistant_turn = history[-1]

    assert_that(
        last_assistant_turn.cacheReadInputTokens,
        greater_than(0),
        "once the cumulative short-message prefix clears the provider minimum, "
        "the accumulated history must be read from cache — the cumulative "
        "prefix, not any single message, is what gets evaluated",
    )


@pytest.mark.parametrize("stream", [False, True], ids=["non_streaming", "streaming"])
@pytest.mark.skipif(get_environment() not in AWS_ENVS, reason=_SKIP_REASON)
@pytest.mark.llm
@pytest.mark.assistant
@pytest.mark.conversations
@pytest.mark.api
def test_cache_control_applied_identically_for_stream_and_non_stream(
    assistant_factory, assistant_utils, conversation_utils, stream
):
    """Streaming and non-streaming requests apply the same cache control (AC-4).

    # @case claude-prompt-cache-callback-removes-checkpoints_TC_003
    """
    created_assistant = assistant_factory.create(
        _AWS_CLAUDE_MODEL, system_prompt="You are a helpful assistant."
    )
    conversation_id = str(uuid.uuid4())
    prompt = (
        f"{_STABLE_CONTEXT_BLOCK}\n\n"
        "Based on the reference material above, reply with one word: OK."
    )

    assistant_utils.ask_assistant(
        created_assistant, prompt, conversation_id=conversation_id, stream=stream
    )

    history = conversation_utils.get_conversation_by_id(conversation_id).history
    assistant_turn = history[1]

    assert_that(
        assistant_turn.cacheCreationInputTokens,
        greater_than(0),
        f"a request large enough to clear the provider cache minimum must carry "
        f"the same cache_control whether stream={stream}",
    )
