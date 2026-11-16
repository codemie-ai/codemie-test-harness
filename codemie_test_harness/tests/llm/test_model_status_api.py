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

"""API tests for platform-wide model status management.

An administrator sets a model to Enabled, Disabled or Deprecated; the status is
stored once for the whole platform and every catalog reads it. Tests that change
a status or the global default restore them in a fixture teardown and run outside
parallel mode (``not_for_parallel_run``).
"""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_entries,
    has_key,
    is_,
    is_not,
    none,
)
from requests import HTTPError

from codemie_sdk.models.llm import ModelStatus

from codemie_test_harness.tests.test_data.llm_model_status_test_data import (
    ADMIN_STATUS_ROUTES,
    ALL_STATUSES,
    CATALOG_STATUS_BY_STATUS,
    DEFAULT_REFUSAL_REASON,
    INVALID_BULK_REQUESTS,
    NON_SELECTABLE_STATUSES,
    STATUS_TRANSITION_IDS,
    STATUS_TRANSITIONS,
    unknown_model_name,
)


# @case platform-model-management_TC_001
@pytest.mark.not_for_parallel_run
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.parametrize(
    "initial_status, status", STATUS_TRANSITIONS, ids=STATUS_TRANSITION_IDS
)
def test_admin_sets_model_status_and_it_persists(
    llm_model_status_utils, status_test_model, initial_status, status
):
    base_name = status_test_model.base_name
    llm_model_status_utils.set_status(base_name, initial_status)
    assert_that(
        llm_model_status_utils.status_of(base_name),
        equal_to(initial_status),
        "the starting status must be stored before the change under test",
    )

    updated = llm_model_status_utils.set_status(base_name, status)

    assert_that(updated.base_name, equal_to(base_name))
    assert_that(
        updated.status,
        equal_to(status),
        "the PUT response must carry the requested status",
    )
    assert_that(
        llm_model_status_utils.status_of(base_name),
        equal_to(status),
        "the admin model list must show the stored status",
    )


# @case platform-model-management_TC_002
@pytest.mark.not_for_parallel_run
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.parametrize("status", ALL_STATUSES, ids=lambda s: s.value)
def test_regular_user_catalog_reflects_persisted_status(
    llm_model_status_utils, status_test_model, regular_client, status
):
    base_name = status_test_model.base_name
    llm_model_status_utils.apply_status(base_name, status, regular_client)

    catalog = llm_model_status_utils.catalog_of(regular_client)

    assert_that(
        getattr(catalog.get(base_name), "status", None),
        equal_to(CATALOG_STATUS_BY_STATUS[status]),
        f"status the regular user's catalog shows for a {status.value} model "
        "(None: the model is not listed)",
    )


# @case platform-model-management_TC_003
@pytest.mark.not_for_parallel_run
@pytest.mark.llm
@pytest.mark.api
def test_bulk_status_update_reports_per_item_results(
    llm_model_status_utils, status_test_models
):
    first, second = (model.base_name for model in status_test_models)
    unknown = unknown_model_name()

    summary = llm_model_status_utils.bulk_set_statuses(
        [
            (first, ModelStatus.DEPRECATED),
            (second, ModelStatus.DEPRECATED),
            (unknown, ModelStatus.DEPRECATED),
        ]
    )

    assert_that(summary.total, equal_to(3), "total items")
    assert_that(summary.succeeded, equal_to(2), "succeeded items")
    assert_that(summary.failed, equal_to(1), "failed items")
    results = {item.base_name: item for item in summary.results}
    assert_that(results[first].success, is_(True), f"result of {first}")
    assert_that(results[second].success, is_(True), f"result of {second}")
    assert_that(results[unknown].success, is_(False), "result of the unknown model")
    assert_that(
        results[unknown].error,
        contains_string(unknown),
        "the failed item must say which model was not found",
    )
    stored = {m.base_name: m.status for m in llm_model_status_utils.list_statuses()}
    assert_that(
        stored,
        has_entries({first: ModelStatus.DEPRECATED, second: ModelStatus.DEPRECATED}),
        "the valid items must be stored although another item failed",
    )
    assert_that(stored, is_not(has_key(unknown)))


# @case platform-model-management_TC_003
@pytest.mark.llm
@pytest.mark.api
def test_admin_status_update_of_unknown_model_is_rejected(llm_model_status_utils):
    unknown = unknown_model_name()

    with pytest.raises(HTTPError) as exc_info:
        llm_model_status_utils.set_status(unknown, ModelStatus.DISABLED)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "a model that is in no catalog must be reported as not found",
    )
    assert_that(
        llm_model_status_utils.status_of(unknown),
        is_(none()),
        "the unknown model must not appear in the admin list",
    )


# @case platform-model-management_TC_004
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.parametrize(
    "call", list(ADMIN_STATUS_ROUTES.values()), ids=list(ADMIN_STATUS_ROUTES)
)
def test_non_admin_is_refused_on_model_status_routes(regular_client, call):
    # An unknown model name: were the route open, it would answer 404, never change data.
    with pytest.raises(HTTPError) as exc_info:
        call(regular_client.admin, unknown_model_name())

    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        "a regular user must be forbidden on the model status routes",
    )


# @case platform-model-management_TC_016
@pytest.mark.not_for_parallel_run
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.parametrize("status", NON_SELECTABLE_STATUSES, ids=lambda s: s.value)
def test_global_default_rejects_non_selectable_model(
    llm_model_status_utils, status_test_model, saved_global_default, status
):
    base_name = status_test_model.base_name
    before = llm_model_status_utils.get_default()
    llm_model_status_utils.apply_status(base_name, status)

    with pytest.raises(HTTPError) as exc_info:
        llm_model_status_utils.set_default(base_name)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    assert_that(response.text, contains_string(DEFAULT_REFUSAL_REASON[status]))
    after = llm_model_status_utils.get_default()
    assert_that(
        after.saved_base_name,
        equal_to(before.saved_base_name),
        "a refused default must not change the saved default",
    )
    assert_that(
        after.effective_base_name,
        equal_to(before.effective_base_name),
        "a refused default must not change the effective default",
    )


# @case platform-model-management_TC_016
@pytest.mark.not_for_parallel_run
@pytest.mark.llm
@pytest.mark.api
def test_global_default_rejects_unknown_model(
    llm_model_status_utils, saved_global_default
):
    unknown = unknown_model_name()
    before = llm_model_status_utils.get_default()

    with pytest.raises(HTTPError) as exc_info:
        llm_model_status_utils.set_default(unknown)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(400), response.text)
    assert_that(response.text, contains_string(unknown))
    after = llm_model_status_utils.get_default()
    assert_that(after.saved_base_name, equal_to(before.saved_base_name))
    assert_that(after.effective_base_name, equal_to(before.effective_base_name))


# @case platform-model-management_TC_017
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.parametrize(
    "build_items, expected_text",
    list(INVALID_BULK_REQUESTS.values()),
    ids=list(INVALID_BULK_REQUESTS),
)
def test_bulk_status_request_rejects_invalid_input(
    llm_model_status_utils, build_items, expected_text
):
    with pytest.raises(HTTPError) as exc_info:
        llm_model_status_utils.bulk_set_statuses(build_items())

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(422), response.text)
    assert_that(response.json()["error"]["message"], contains_string(expected_text))
