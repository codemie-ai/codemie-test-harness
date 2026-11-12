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

"""Tests for the assistants-requests analytics endpoint (one row per assistant request)."""

import uuid

import pytest
from hamcrest import (
    any_of,
    assert_that,
    close_to,
    contains_exactly,
    empty,
    equal_to,
    greater_than,
    has_item,
    has_items,
    has_length,
    instance_of,
    is_,
    is_not,
    none,
    only_contains,
    contains_string,
)

from codemie_test_harness.tests.test_data.assistants_requests_analytics_test_data import (
    COST_TOLERANCE,
    CORRELATION_COLUMNS,
    ERROR_DETAIL_COLUMN_FRAGMENT,
    FIRST_PROMPT,
    MAX_PER_PAGE,
    REQUEST_METRIC_COLUMNS,
    REQUESTS_TIME_PERIOD,
    SECOND_PROMPT,
    SUCCESS_STATUS,
    UNUSED_CLIENT_SOURCE,
)
from codemie_test_harness.tests.utils.analytics_utils import (
    AnalyticsUtils,
    requests_window_start,
)
from codemie_test_harness.tests.utils.assistant_utils import AssistantUtils
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    assert_principal_is,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.logger_util import setup_logger
from codemie_test_harness.tests.utils.marketplace_management_utils import (
    personal_project_of,
)

logger = setup_logger(__name__)


@pytest.fixture
def regular_user_assistant(regular_client):
    """An assistant owned by the plain test user, created in that user's own project."""
    username = CredentialsManager.get_parameter("AUTH_USERNAME_DEFAULT")
    if not username:
        pytest.skip("AUTH_USERNAME_DEFAULT is not set: no plain test user")
    assert_principal_is(regular_client, username, not_admin=True)
    user = regular_client.users.about_me()
    project = personal_project_of(user) or username
    utils = AssistantUtils(regular_client)
    created = utils.create_assistant(project_name=project)
    yield utils, created
    try:
        utils.delete_assistant(created)
    except Exception as e:
        logger.error(f"Failed to delete assistant {created.id}: {e}")


@pytest.mark.analytics
@pytest.mark.api
def test_assistants_requests_lists_one_row_per_request_matching_chats_totals(
    assistant, assistant_utils, analytics_utils
):
    """@case individual-assistant-run-analytics_TC_001"""
    window_start = requests_window_start()
    test_assistant = assistant()
    conversation_id = str(uuid.uuid4())
    assistant_utils.ask_assistant(
        test_assistant, FIRST_PROMPT, conversation_id=conversation_id
    )
    assistant_utils.ask_assistant(
        test_assistant, SECOND_PROMPT, conversation_id=conversation_id
    )

    response = analytics_utils.wait_for_assistant_requests(
        2, assistant_id=test_assistant.id
    )
    rows = response.data.rows

    assert_that(rows, has_length(2), "one row per assistant request")
    assert_that(
        [row["conversation_id"] for row in rows],
        only_contains(conversation_id),
        "both requests belong to the one conversation",
    )
    request_ids = [row["request_id"] for row in rows]
    assert_that(request_ids, is_not(has_item(none())), "every row has a request id")
    assert_that(set(request_ids), has_length(2), "request ids are distinct")
    timestamps = [row["timestamp"] for row in rows]
    assert_that(
        timestamps, equal_to(sorted(timestamps, reverse=True)), "rows are newest first"
    )

    chats_row = analytics_utils.wait_for_assistants_chats_row(
        test_assistant.name, test_assistant.id, start_date=window_start
    )
    assert_that(
        chats_row, is_not(none()), "assistants-chats lists the assistant's chat"
    )
    assert_that(chats_row["total_chats"], equal_to(1), "one conversation is one chat")
    assert_that(
        chats_row["total_messages"],
        equal_to(len(rows)),
        "total_messages counts the request rows",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_assistants_requests_filters_by_assistant_id_and_client_source(
    assistant_factory, assistant_utils, analytics_utils
):
    """@case individual-assistant-run-analytics_TC_002"""
    first = assistant_factory.create()
    second = assistant_factory.create()
    assistant_utils.ask_assistant(first, FIRST_PROMPT)
    assistant_utils.ask_assistant(second, FIRST_PROMPT)

    first_response = analytics_utils.wait_for_assistant_requests(
        1, assistant_id=first.id
    )
    second_response = analytics_utils.wait_for_assistant_requests(
        1, assistant_id=second.id
    )

    assert_that(
        first_response.data.rows, has_length(1), "the first assistant's request"
    )
    assert_that(
        [row["assistant_id"] for row in first_response.data.rows],
        only_contains(first.id),
        "no row of the second assistant is returned for the first",
    )
    assert_that(
        second_response.data.rows, has_length(1), "the second assistant's request"
    )
    assert_that(
        [row["assistant_id"] for row in second_response.data.rows],
        only_contains(second.id),
        "no row of the first assistant is returned for the second",
    )
    assert_that(
        [column.id for column in first_response.data.columns],
        has_items(*CORRELATION_COLUMNS),
        "the correlation columns are part of the response",
    )

    first_source = first_response.data.rows[0]["client_source"]
    assert_that(first_source, is_not(none()), "the request row carries a client source")
    same_source = analytics_utils.get_assistants_requests(
        time_period=REQUESTS_TIME_PERIOD,
        per_page=MAX_PER_PAGE,
        assistant_id=first.id,
        client_source=first_source,
    )
    assert_that(
        [row["request_id"] for row in same_source.data.rows],
        has_item(first_response.data.rows[0]["request_id"]),
        "filtering by the request's own client source returns that request",
    )

    other_source = analytics_utils.get_assistants_requests(
        time_period=REQUESTS_TIME_PERIOD,
        per_page=MAX_PER_PAGE,
        assistant_id=first.id,
        client_source=UNUSED_CLIENT_SOURCE,
    )
    assert_that(
        other_source.data.rows,
        empty(),
        "no request of this assistant carries the other client source",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_assistants_requests_plain_user_sees_only_own_rows(regular_user_assistant):
    """@case individual-assistant-run-analytics_TC_004"""
    regular_assistants, test_assistant = regular_user_assistant
    regular_client = regular_assistants.client
    regular_analytics = AnalyticsUtils(regular_client)
    own_user_id = regular_client.users.about_me().user_id
    regular_assistants.ask_assistant(test_assistant, FIRST_PROMPT)

    own_requests = regular_analytics.wait_for_assistant_requests(
        1, assistant_id=test_assistant.id
    )
    assert_that(
        own_requests.data.rows,
        has_length(1),
        "the plain user's own request is returned",
    )

    all_visible = regular_analytics.get_assistants_requests(
        time_period=REQUESTS_TIME_PERIOD, per_page=MAX_PER_PAGE
    )
    assert_that(all_visible.data.rows, is_not(empty()), "the plain user sees rows")
    assert_that(
        [row["user_id"] for row in all_visible.data.rows],
        only_contains(own_user_id),
        "every visible row belongs to the plain user",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_assistants_requests_row_has_tokens_cost_time_and_status_without_error_detail(
    assistant, assistant_utils, analytics_utils
):
    """@case individual-assistant-run-analytics_TC_005"""
    test_assistant = assistant()
    assistant_utils.ask_assistant(test_assistant, FIRST_PROMPT)

    response = analytics_utils.wait_for_assistant_requests(
        1, assistant_id=test_assistant.id
    )
    assert_that(response.data.rows, has_length(1), "the assistant's single request")
    row = response.data.rows[0]

    assert_that(
        list(row),
        has_items(*REQUEST_METRIC_COLUMNS),
        "the row carries tokens, cost, time and status",
    )
    assert_that(row["input_tokens"], greater_than(0), "input tokens are counted")
    assert_that(row["output_tokens"], greater_than(0), "output tokens are counted")
    assert_that(
        row["total_tokens"],
        equal_to(row["input_tokens"] + row["output_tokens"]),
        "total_tokens is input plus output and excludes cache reads",
    )
    assert_that(
        row["money_spent"] is not None or row["spend_unavailable"] is True,
        is_(True),
        "money_spent is a number, or null while flagged spend_unavailable",
    )
    assert_that(
        row["execution_time"],
        any_of(instance_of(int), instance_of(float)),
        "execution time is a number",
    )
    assert_that(row["status"], equal_to(SUCCESS_STATUS), "the request succeeded")
    assert_that(
        [column.id for column in response.data.columns],
        is_not(has_item(contains_string(ERROR_DETAIL_COLUMN_FRAGMENT))),
        "no error message or class column is exposed",
    )


@pytest.mark.analytics
@pytest.mark.api
def test_assistants_requests_cost_sum_equals_assistants_chats_total_cost(
    assistant, assistant_utils, analytics_utils
):
    """@case individual-assistant-run-analytics_TC_006"""
    window_start = requests_window_start()
    test_assistant = assistant()
    assistant_utils.ask_assistant(test_assistant, FIRST_PROMPT)
    assistant_utils.ask_assistant(test_assistant, SECOND_PROMPT)

    response = analytics_utils.wait_for_assistant_requests(
        2, settled=True, assistant_id=test_assistant.id, start_date=window_start
    )
    rows = response.data.rows
    assert_that(rows, has_length(2), "one row per request")
    assert_that(
        [row["spend_unavailable"] for row in rows],
        contains_exactly(False, False),
        "every request cost is recorded by the ledger",
    )

    chats_row = analytics_utils.wait_for_assistants_chats_row(
        test_assistant.name,
        test_assistant.id,
        settled=True,
        start_date=window_start,
    )
    assert_that(
        chats_row, is_not(none()), "assistants-chats lists the assistant's chat"
    )
    assert_that(
        chats_row["total_cost_usd"],
        close_to(sum(row["money_spent"] for row in rows), COST_TOLERANCE),
        "total_cost_usd is the sum of the requests' money_spent",
    )
