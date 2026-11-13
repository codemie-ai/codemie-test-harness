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

"""Run attributes in the analytics: request and execution rows, the attributes filter and attributes-usage."""

import pytest
from hamcrest import assert_that, empty, equal_to, none, not_none
from requests import HTTPError

from codemie_test_harness.tests.test_data.run_attributes_test_data import (
    ANALYTICS_PAGE_SIZE,
    ANALYTICS_PERIOD,
    ANALYTICS_ROW_INTERVAL,
    ANALYTICS_ROW_TIMEOUT,
    ATTRIBUTES_USAGE_KEY_ERRORS,
    INVALID_FILTER_MESSAGE,
    MALFORMED_FILTER,
    RUN_SURFACES,
    RUN_SURFACES_BY_KIND,
    get_attribute_key,
    get_attribute_value,
    get_attributes,
)
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.run_attributes_utils import (
    assert_error_message,
    usage_counts,
)


@pytest.mark.analytics
@pytest.mark.api
def test_analytics_request_row_exposes_the_attributes_of_the_chat(chat_surface):
    # @case allow-callers-to-associate-custom_TC_005
    attributes = get_attributes(count=2)
    conversation_id = chat_surface.start(attributes)

    row = chat_surface.wait_for_row(conversation_id)

    assert_that(row, not_none(), "the request of the chat must reach the analytics")
    assert_that(
        row["attributes"],
        equal_to(attributes),
        "the attributes column must hold the attributes of the chat",
    )


@pytest.mark.analytics
@pytest.mark.workflow
@pytest.mark.api
def test_analytics_execution_row_exposes_the_attributes_of_the_run(workflow_surface):
    # @case allow-callers-to-associate-custom_TC_006
    attributes = get_attributes(count=2)
    execution_id = workflow_surface.start(attributes)

    row = workflow_surface.wait_for_row(execution_id)

    assert_that(
        row, not_none(), "the execution must reach the workflow executions analytics"
    )
    assert_that(
        row["attributes"],
        equal_to(attributes),
        "the attributes column must hold the attributes of the execution",
    )


@pytest.mark.parametrize("run_surface", RUN_SURFACES, indirect=True)
@pytest.mark.analytics
@pytest.mark.api
def test_attributes_filter_returns_only_matching_runs(run_surface):
    """Three runs share one key: value A, value B, and value A with a second attribute.

    A filter on value A matches the first and the third, a filter on both attributes
    only the third (AND), and a filter on value B only the second.
    """
    # @case allow-callers-to-associate-custom_TC_007
    key, extra_key = get_attribute_key(), get_attribute_key()
    value_a, value_b, extra_value = (get_attribute_value() for _ in range(3))
    run_a = run_surface.start({key: value_a})
    run_b = run_surface.start({key: value_b})
    run_a_with_extra = run_surface.start({key: value_a, extra_key: extra_value})

    matching_a = run_surface.wait_for_run_ids({run_a, run_a_with_extra}, {key: value_a})
    matching_a_and_extra = run_surface.wait_for_run_ids(
        {run_a_with_extra}, {key: value_a, extra_key: extra_value}
    )
    matching_b = run_surface.wait_for_run_ids({run_b}, {key: value_b})

    assert_that(
        matching_a,
        equal_to({run_a, run_a_with_extra}),
        "an exact key=value filter must return the runs with that value and no other",
    )
    assert_that(
        matching_a_and_extra,
        equal_to({run_a_with_extra}),
        "a filter with two attributes must return only the runs that carry both",
    )
    assert_that(
        matching_b,
        equal_to({run_b}),
        "the filter must tell two values of the same key apart",
    )
    with pytest.raises(HTTPError) as rejected:
        run_surface.analytics_rows(MALFORMED_FILTER)
    assert_error_message(rejected.value.response, 422, INVALID_FILTER_MESSAGE)


@pytest.mark.analytics
@pytest.mark.api
def test_attributes_usage_groups_runs_by_the_values_of_one_key(
    chat_surface, workflow_surface, analytics_utils
):
    # @case allow-callers-to-associate-custom_TC_008
    key = get_attribute_key()
    value_a, value_b = get_attribute_value(), get_attribute_value()
    chat_surface.start({key: value_a})
    chat_surface.start({key: value_b})
    workflow_surface.start({key: value_a})
    chat_surface.start()

    expected_counts = {value_a: (1, 1), value_b: (1, 0)}
    rows = poll_until(
        lambda: analytics_utils.get_attributes_usage(
            key, time_period=ANALYTICS_PERIOD, per_page=ANALYTICS_PAGE_SIZE
        ).data.rows,
        lambda found: usage_counts(found) == expected_counts,
        timeout=ANALYTICS_ROW_TIMEOUT,
        interval=ANALYTICS_ROW_INTERVAL,
    )

    assert_that(
        usage_counts(rows),
        equal_to(expected_counts),
        "one row per value of the key with the runs of each kind, and no row for the run without attributes",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_attributes_usage_of_an_unknown_key_is_an_empty_table(analytics_utils):
    # @case allow-callers-to-associate-custom_TC_008
    response = analytics_utils.get_attributes_usage(
        get_attribute_key(), time_period=ANALYTICS_PERIOD
    )

    assert_that(response.data.rows, empty(), "an unknown key has no value to group by")


@pytest.mark.parametrize("attribute_key, message", ATTRIBUTES_USAGE_KEY_ERRORS)
@pytest.mark.analytics
@pytest.mark.api
def test_attributes_usage_rejects_a_missing_or_malformed_key(
    analytics_utils, attribute_key, message
):
    # @case allow-callers-to-associate-custom_TC_008
    with pytest.raises(HTTPError) as rejected:
        analytics_utils.get_attributes_usage(attribute_key)

    assert_error_message(rejected.value.response, 422, message)


@pytest.mark.parametrize("run_surface", RUN_SURFACES_BY_KIND, indirect=True)
@pytest.mark.analytics
@pytest.mark.api
def test_run_without_attributes_has_null_attributes_on_the_record_and_in_analytics(
    run_surface,
):
    # @case allow-callers-to-associate-custom_TC_009
    run_id = run_surface.start()

    stored_attributes = run_surface.stored_attributes(run_id)

    assert_that(
        stored_attributes, none(), "a run started without attributes has none stored"
    )
    row = run_surface.wait_for_row(run_id)
    assert_that(row, not_none(), "the run must reach the analytics")
    assert_that(
        row["attributes"], none(), "the attributes column of such a run is null"
    )
