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

"""Headroom analytics endpoints (summary, by-strategy, timeseries) answer with their shape."""

import pytest
from codemie_sdk.models.analytics import (
    ResponseMetadata,
    SummariesResponse,
    TabularData,
    TabularResponse,
)
from hamcrest import (
    any_of,
    assert_that,
    greater_than,
    has_items,
    has_length,
    instance_of,
    is_in,
    only_contains,
)

from codemie_test_harness.tests.test_data.headroom_test_data import (
    BY_STRATEGY_COLUMN_IDS,
    CHAT_HEADROOM_AGGRESSIVE,
    HEADROOM_MODES,
    POLL_INTERVAL,
    SUMMARY_METRIC_IDS,
    SUMMARY_POLL_TIMEOUT,
    TIMESERIES_COLUMN_IDS,
    repetitive_log_prompt,
    summary_metric,
)
from codemie_test_harness.tests.utils.base_utils import poll_until


# @case headroom-per-assistant-workflow-configuration_TC_001
@pytest.mark.analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_headroom_summary_reports_savings_and_mode_after_a_compressed_chat(
    analytics_utils, assistant_factory, assistant_utils, default_llm, current_user_id
):
    # Scoped to the test user: other users' Headroom traffic on a shared stand would
    # raise the stand-wide totals without this chat being counted.
    baseline = analytics_utils.get_headroom_summary(users=current_user_id)
    baseline_requests = summary_metric(baseline, "request_count")
    baseline_saved = summary_metric(baseline, "tokens_saved")

    # One Headroom event of our own: the summary adds the mode metric only when the
    # period holds Headroom events.
    assistant = assistant_factory.create(
        llm_model_type=default_llm.base_name, headroom_config=CHAT_HEADROOM_AGGRESSIVE
    )
    answer = assistant_utils.ask_assistant(assistant, repetitive_log_prompt())
    assert_that(answer, has_length(greater_than(0)), "Assistant gave no answer")

    response = poll_until(
        lambda: analytics_utils.get_headroom_summary(users=current_user_id),
        lambda summary: summary_metric(summary, "request_count") > baseline_requests
        and summary_metric(summary, "tokens_saved") > baseline_saved,
        timeout=SUMMARY_POLL_TIMEOUT,
        interval=POLL_INTERVAL,
    )

    assert_that(response, instance_of(SummariesResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that(
        [metric.id for metric in response.data.metrics],
        has_items(*SUMMARY_METRIC_IDS),
        "Headroom summary misses one of its savings metrics",
    )
    values = {metric.id: metric.value for metric in response.data.metrics}
    assert_that(
        [values[metric_id] for metric_id in SUMMARY_METRIC_IDS],
        only_contains(any_of(instance_of(int), instance_of(float))),
        "Headroom summary savings metrics do not carry numbers",
    )
    assert_that(
        values["request_count"],
        greater_than(baseline_requests),
        "Headroom compacted requests did not grow after a compressed chat",
    )
    assert_that(
        values["tokens_saved"],
        greater_than(baseline_saved),
        "Headroom saved tokens did not grow after a compressed chat",
    )
    assert_that(
        values.get("mode"),
        is_in(HEADROOM_MODES),
        "Headroom summary does not report the active compression mode",
    )


# @case headroom-per-assistant-workflow-configuration_TC_001
@pytest.mark.parametrize(
    "endpoint_method, column_ids",
    [
        ("get_headroom_by_strategy", BY_STRATEGY_COLUMN_IDS),
        ("get_headroom_timeseries", TIMESERIES_COLUMN_IDS),
    ],
    ids=["by_strategy", "timeseries"],
)
@pytest.mark.analytics
@pytest.mark.api
def test_headroom_tabular_endpoints_return_their_columns(
    analytics_utils, endpoint_method, column_ids
):
    response = getattr(analytics_utils, endpoint_method)()

    assert_that(response, instance_of(TabularResponse))
    assert_that(response.metadata, instance_of(ResponseMetadata))
    assert_that(response.data, instance_of(TabularData))
    assert_that(response.data.rows, instance_of(list))
    assert_that(
        [column.id for column in response.data.columns],
        has_items(*column_ids),
        f"{endpoint_method} misses one of its columns",
    )
