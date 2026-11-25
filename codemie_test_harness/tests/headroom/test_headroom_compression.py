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
from hamcrest import assert_that, greater_than, has_length

from codemie_test_harness.tests.test_data.headroom_test_data import (
    ANALYTICS_POLL_TIMEOUT,
    CHAT_HEADROOM_AGGRESSIVE,
    METRICS_POLL_TIMEOUT,
    POLL_INTERVAL,
    WORKFLOW_HEADROOM_AGGRESSIVE,
    WORKFLOW_TASK,
    repetitive_log_prompt,
    summary_metric,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name, poll_until


# @case headroom-per-assistant-workflow-configuration_TC_009
@pytest.mark.assistant
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_assistant_chat_with_headroom_reports_saved_tokens(
    assistant_factory, assistant_utils, default_llm
):
    assistant = assistant_factory.create(
        llm_model_type=default_llm.base_name, headroom_config=CHAT_HEADROOM_AGGRESSIVE
    )
    conversation_id = str(uuid.uuid4())

    answer = assistant_utils.ask_assistant(
        assistant, repetitive_log_prompt(), conversation_id=conversation_id
    )
    assert_that(answer, has_length(greater_than(0)), "Assistant gave no answer")

    metrics = poll_until(
        lambda: assistant_utils.get_conversation_metrics(conversation_id),
        lambda body: (body.get("headroom_tokens_saved") or 0) > 0,
        timeout=METRICS_POLL_TIMEOUT,
        interval=POLL_INTERVAL,
    )
    saved = metrics.get("headroom_tokens_saved") or 0
    assert_that(
        saved,
        greater_than(0),
        f"Conversation metrics report no Headroom savings: {metrics}",
    )
    assert_that(
        metrics.get("headroom_tokens_original") or 0,
        greater_than(saved),
        f"Headroom original tokens are not above the saved tokens: {metrics}",
    )


# @case headroom-per-assistant-workflow-configuration_TC_010
@pytest.mark.workflow
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_workflow_run_with_headroom_block_adds_to_headroom_savings(
    workflow_with_virtual_assistant, workflow_utils, analytics_utils
):
    baseline = analytics_utils.get_headroom_summary()
    baseline_requests = summary_metric(baseline, "request_count")
    baseline_saved = summary_metric(baseline, "tokens_saved")

    state_name = get_random_name()
    workflow = workflow_with_virtual_assistant(
        state_name, task=WORKFLOW_TASK, headroom=WORKFLOW_HEADROOM_AGGRESSIVE
    )
    output = workflow_utils.execute_workflow(
        workflow.id, state_name, user_input=repetitive_log_prompt()
    )
    assert_that(output, has_length(greater_than(0)), "Workflow run gave no output")

    summary = poll_until(
        analytics_utils.get_headroom_summary,
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
