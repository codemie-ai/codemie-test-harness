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
    assert_that,
    equal_to,
    greater_than,
    has_items,
    has_length,
    instance_of,
    only_contains,
)

from codemie_test_harness.tests.test_data.headroom_test_data import (
    BY_STRATEGY_COLUMN_IDS,
    CHAT_HEADROOM_AGGRESSIVE,
    EXPECTED_HEADROOM_MODE,
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
    analytics_utils, assistant_factory, assistant_utils, default_llm
):
    baseline = analytics_utils.get_headroom_summary()
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
        analytics_utils.get_headroom_summary,
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
        only_contains(instance_of((int, float))),
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
        equal_to(EXPECTED_HEADROOM_MODE),
        "Headroom summary does not report the active compression mode",
    )


# @case headroom-per-assistant-workflow-configuration_TC_001
@pytest.mark.analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "endpoint_method, column_ids",
    [
        ("get_headroom_by_strategy", BY_STRATEGY_COLUMN_IDS),
        ("get_headroom_timeseries", TIMESERIES_COLUMN_IDS),
    ],
    ids=["by_strategy", "timeseries"],
)
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
