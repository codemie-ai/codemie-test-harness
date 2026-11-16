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

"""Resuming a workflow execution forwards its own disable_cache query flag to the
executor, the way the execute-workflow path already did (AC-6).

Needs a Bedrock environment (``AWS_ENVS`` in ``llm_test_data.py``) so the
assistant's model is cache-eligible and provider cache usage is observable on
the resumed turn's history item.
"""

from hamcrest import assert_that, equal_to
import pytest

from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.test_data.llm_test_data import AWS_ENVS
from codemie_test_harness.tests.utils.env_resolver import get_environment

_AWS_CLAUDE_MODEL = ModelTypes.CLAUDE_4_5_SONNET
_USER_INPUT = "Solve it, only answer: 2+2*2"


def _used_provider_cache(history_item) -> bool:
    return bool(history_item.cacheCreationInputTokens) or bool(
        history_item.cacheReadInputTokens
    )


@pytest.mark.skipif(
    get_environment() not in AWS_ENVS,
    reason="Needs a Bedrock environment (AWS_ENVS in llm_test_data.py)",
)
@pytest.mark.workflow
@pytest.mark.workflow_with_assistant
@pytest.mark.conversations
@pytest.mark.api
def test_resume_honors_its_own_disable_cache_query_flag(
    assistant_factory, conversation_utils, workflow_with_assistant, workflow_utils
):
    """Resuming a workflow execution honors its own disable_cache query flag.

    # @case claude-prompt-cache-callback-removes-checkpoints_TC_005
    """
    created_assistant = assistant_factory.create(
        _AWS_CLAUDE_MODEL, system_prompt="You are the math expert."
    )
    created_workflow = workflow_with_assistant(created_assistant, "Run")

    # Resume with no disable_cache query param: the route defaults to
    # disable_cache=True (caching off), so the resumed turn must show no
    # provider cache usage.
    default_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    default_conversation_id = default_conv["id"]
    default_execution = workflow_utils.create_workflow_execution(
        workflow_id=created_workflow.id,
        user_input=_USER_INPUT,
        conversation_id=default_conversation_id,
    )
    workflow_utils.resume_workflow_execution(
        created_workflow.id, default_execution.execution_id
    )
    default_resumed_turn = conversation_utils.get_conversation_by_id(
        default_conversation_id
    ).history[-1]

    # Resume a comparable execution with ?disable_cache=false: the route must
    # forward disable_cache=False, so the resumed turn must show provider
    # cache usage.
    explicit_conv = conversation_utils.create_conversation(
        initial_assistant_id=created_workflow.id,
        is_workflow_conversation=True,
    )
    explicit_conversation_id = explicit_conv["id"]
    explicit_execution = workflow_utils.create_workflow_execution(
        workflow_id=created_workflow.id,
        user_input=_USER_INPUT,
        conversation_id=explicit_conversation_id,
    )
    workflow_utils.resume_workflow_execution(
        created_workflow.id, explicit_execution.execution_id, disable_cache=False
    )
    explicit_resumed_turn = conversation_utils.get_conversation_by_id(
        explicit_conversation_id
    ).history[-1]

    assert_that(
        _used_provider_cache(default_resumed_turn),
        equal_to(False),
        "resume with no disable_cache query param must default to "
        "disable_cache=True, so the resumed turn must show no provider cache "
        "usage",
    )
    assert_that(
        _used_provider_cache(explicit_resumed_turn),
        equal_to(True),
        "resume with ?disable_cache=false must forward disable_cache=False to "
        "the executor, so the resumed turn must show provider cache usage",
    )
