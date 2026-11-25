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

"""Headroom compresses LangGraph assistant chats and workflow runs with the saved config.

Needs a stand with the features:headroom flag on and HEADROOM_MODE sdk or sidecar.
"""

import uuid

import pytest
from codemie_sdk import HeadroomStrategy
from codemie_sdk.models.conversation import ConversationMetrics
from hamcrest import assert_that, equal_to, greater_than, has_length

from codemie_test_harness.tests.test_data.headroom_test_data import (
    ANALYTICS_POLL_TIMEOUT,
    METRICS_POLL_TIMEOUT,
    NO_SAVINGS_WINDOW,
    POLL_INTERVAL,
    TOOL_OUTPUTS_OFF_LARGE_TOOL_OUTPUT,
    TOOL_OUTPUTS_ON_LARGE_TOOL_OUTPUT,
    USER_INPUT_OFF_LONG_USER_MESSAGE,
    USER_INPUT_ON_LONG_USER_MESSAGE,
    WORKFLOW_TASK,
    chat_headroom,
    json_array_prompt,
    repetitive_log_prompt,
    strategy_metric,
    summary_metric,
    workflow_headroom,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_tool_triggered,
    get_random_name,
    poll_until,
)

# Each strategy is its own test: no ordering across strategies is asserted. Lossless
# compresses pure JSON content only, so it gets a message that is only a JSON array and
# is sent without the REQUEST_UUID suffix (with the suffix it saves nothing). The third
# value says whether the harness appends that suffix.
STRATEGIES = [
    pytest.param(HeadroomStrategy.LOSSLESS, json_array_prompt(), False, id="lossless"),
    pytest.param(
        HeadroomStrategy.BALANCED, repetitive_log_prompt(), True, id="balanced"
    ),
    pytest.param(
        HeadroomStrategy.AGGRESSIVE, repetitive_log_prompt(), True, id="aggressive"
    ),
]


# Analytics reads are scoped to the test user (``users=current_user_id``): on a shared
# stand another user's Headroom traffic would otherwise raise the totals and let the
# "grew past the baseline" checks pass without this test's own chat or run.


def _saved_tokens(metrics: ConversationMetrics) -> int:
    """Tokens Headroom saved in a conversation; the field is None when it saved none."""
    return metrics.headroom_tokens_saved or 0


# @case headroom-per-assistant-workflow-configuration_TC_009
@pytest.mark.parametrize("strategy, prompt, add_request_uuid", STRATEGIES)
@pytest.mark.assistant
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_assistant_chat_with_headroom_reports_saved_tokens(
    strategy,
    prompt,
    add_request_uuid,
    assistant_factory,
    assistant_utils,
    analytics_utils,
    default_llm,
    current_user_id,
):
    baseline = analytics_utils.get_headroom_by_strategy(users=current_user_id)
    baseline_requests = strategy_metric(baseline, strategy, "request_count")
    baseline_saved = strategy_metric(baseline, strategy, "tokens_saved")

    assistant = assistant_factory.create(
        llm_model_type=default_llm.base_name, headroom_config=chat_headroom(strategy)
    )
    conversation_id = str(uuid.uuid4())

    answer = assistant_utils.ask_assistant(
        assistant,
        prompt,
        conversation_id=conversation_id,
        add_request_uuid=add_request_uuid,
    )
    assert_that(answer, has_length(greater_than(0)), "Assistant gave no answer")

    metrics = poll_until(
        lambda: assistant_utils.get_conversation_metrics(conversation_id),
        lambda body: _saved_tokens(body) > 0,
        timeout=METRICS_POLL_TIMEOUT,
        interval=POLL_INTERVAL,
    )
    saved = _saved_tokens(metrics)
    assert_that(
        saved,
        greater_than(0),
        f"Conversation metrics report no Headroom savings: {metrics}",
    )
    assert_that(
        metrics.headroom_tokens_original or 0,
        greater_than(saved),
        f"Headroom original tokens are not above the saved tokens: {metrics}",
    )

    by_strategy = poll_until(
        lambda: analytics_utils.get_headroom_by_strategy(users=current_user_id),
        lambda response: strategy_metric(response, strategy, "request_count")
        > baseline_requests
        and strategy_metric(response, strategy, "tokens_saved") > baseline_saved,
        timeout=ANALYTICS_POLL_TIMEOUT,
        interval=POLL_INTERVAL,
    )
    assert_that(
        strategy_metric(by_strategy, strategy, "request_count"),
        greater_than(baseline_requests),
        f"Savings by strategy did not count the chat under {strategy.value}",
    )
    assert_that(
        strategy_metric(by_strategy, strategy, "tokens_saved"),
        greater_than(baseline_saved),
        f"Savings by strategy did not add the chat's saved tokens to {strategy.value}",
    )


# @case headroom-per-assistant-workflow-configuration_TC_010
@pytest.mark.parametrize("strategy, prompt, add_request_uuid", STRATEGIES)
@pytest.mark.workflow
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_workflow_run_with_headroom_block_adds_to_headroom_savings(
    strategy,
    prompt,
    add_request_uuid,
    workflow_with_virtual_assistant,
    workflow_utils,
    analytics_utils,
    current_user_id,
):
    baseline = analytics_utils.get_headroom_summary(users=current_user_id)
    baseline_requests = summary_metric(baseline, "request_count")
    baseline_saved = summary_metric(baseline, "tokens_saved")
    baseline_by_strategy = analytics_utils.get_headroom_by_strategy(
        users=current_user_id
    )
    baseline_strategy_requests = strategy_metric(
        baseline_by_strategy, strategy, "request_count"
    )
    baseline_strategy_saved = strategy_metric(
        baseline_by_strategy, strategy, "tokens_saved"
    )

    state_name = get_random_name()
    workflow = workflow_with_virtual_assistant(
        state_name, task=WORKFLOW_TASK, headroom=workflow_headroom(strategy)
    )
    # modify_prompt=False leaves a JSON array as given; the run puts it in its own
    # HumanMessage, apart from the node task (workflow.py, LangGraphAgent._get_inputs).
    output = workflow_utils.execute_workflow(
        workflow.id, state_name, user_input=prompt, modify_prompt=add_request_uuid
    )
    assert_that(output, has_length(greater_than(0)), "Workflow run gave no output")

    summary = poll_until(
        lambda: analytics_utils.get_headroom_summary(users=current_user_id),
        lambda response: summary_metric(response, "request_count") > baseline_requests
        and summary_metric(response, "tokens_saved") > baseline_saved,
        timeout=ANALYTICS_POLL_TIMEOUT,
        interval=POLL_INTERVAL,
    )
    assert_that(
        summary_metric(summary, "request_count"),
        greater_than(baseline_requests),
        "Headroom compacted requests did not grow after the workflow run",
    )
    assert_that(
        summary_metric(summary, "tokens_saved"),
        greater_than(baseline_saved),
        "Headroom saved tokens did not grow after the workflow run",
    )

    by_strategy = poll_until(
        lambda: analytics_utils.get_headroom_by_strategy(users=current_user_id),
        lambda response: strategy_metric(response, strategy, "request_count")
        > baseline_strategy_requests
        and strategy_metric(response, strategy, "tokens_saved")
        > baseline_strategy_saved,
        timeout=ANALYTICS_POLL_TIMEOUT,
        interval=POLL_INTERVAL,
    )
    assert_that(
        strategy_metric(by_strategy, strategy, "request_count"),
        greater_than(baseline_strategy_requests),
        f"Savings by strategy did not count the workflow run under {strategy.value}",
    )
    assert_that(
        strategy_metric(by_strategy, strategy, "tokens_saved"),
        greater_than(baseline_strategy_saved),
        f"Savings by strategy did not add the run's saved tokens to {strategy.value}",
    )


# @case headroom-per-assistant-workflow-configuration_TC_018
@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(USER_INPUT_ON_LONG_USER_MESSAGE, id="user_input_on-long_message"),
        pytest.param(
            TOOL_OUTPUTS_ON_LARGE_TOOL_OUTPUT, id="tool_outputs_on-large_tool_output"
        ),
    ],
)
@pytest.mark.assistant
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_headroom_compresses_the_message_kind_its_flag_turns_on(
    scenario, assistant_factory, assistant_utils, default_llm
):
    assistant = assistant_factory.create(
        llm_model_type=default_llm.base_name,
        system_prompt=scenario.system_prompt,
        toolkits=scenario.toolkits,
        headroom_config=scenario.headroom,
    )
    conversation_id = str(uuid.uuid4())

    answer, triggered_tools = assistant_utils.ask_assistant(
        assistant,
        scenario.prompt,
        conversation_id=conversation_id,
        minimal_response=False,
    )
    assert_that(answer, has_length(greater_than(0)), "Assistant gave no answer")
    # The tool-output cases mean something only when the tool actually ran.
    assert_tool_triggered(scenario.expected_tools, triggered_tools)

    metrics = poll_until(
        lambda: assistant_utils.get_conversation_metrics(conversation_id),
        lambda body: _saved_tokens(body) > 0,
        timeout=METRICS_POLL_TIMEOUT,
        interval=POLL_INTERVAL,
    )
    assert_that(
        _saved_tokens(metrics),
        greater_than(0),
        f"Headroom saved nothing on the message kind its flag turns on: {metrics}",
    )


# @case headroom-per-assistant-workflow-configuration_TC_018
@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            USER_INPUT_OFF_LONG_USER_MESSAGE, id="user_input_off-long_message"
        ),
        pytest.param(
            TOOL_OUTPUTS_OFF_LARGE_TOOL_OUTPUT, id="tool_outputs_off-large_tool_output"
        ),
    ],
)
@pytest.mark.assistant
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_headroom_leaves_the_message_kind_its_flag_turns_off(
    scenario, assistant_factory, assistant_utils, default_llm
):
    assistant = assistant_factory.create(
        llm_model_type=default_llm.base_name,
        system_prompt=scenario.system_prompt,
        toolkits=scenario.toolkits,
        headroom_config=scenario.headroom,
    )
    conversation_id = str(uuid.uuid4())

    answer, triggered_tools = assistant_utils.ask_assistant(
        assistant,
        scenario.prompt,
        conversation_id=conversation_id,
        minimal_response=False,
    )
    assert_that(answer, has_length(greater_than(0)), "Assistant gave no answer")
    # The tool-output cases mean something only when the tool actually ran.
    assert_tool_triggered(scenario.expected_tools, triggered_tools)

    # Watch the window a compressed chat would have reported savings in.
    metrics = poll_until(
        lambda: assistant_utils.get_conversation_metrics(conversation_id),
        lambda body: _saved_tokens(body) > 0,
        timeout=NO_SAVINGS_WINDOW,
        interval=POLL_INTERVAL,
    )
    assert_that(
        _saved_tokens(metrics),
        equal_to(0),
        f"Headroom saved tokens on a message kind its flag turns off: {metrics}",
    )
