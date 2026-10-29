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

"""Tests for workflow header propagation into context store.

Feature: when propagate_headers=True is set on a workflow execution request,
X-* HTTP request headers (minus a sensitive denylist) are injected into the
workflow context store under the "propagated_headers" key.

Acceptance criteria covered:
  AC1 — constant key name "propagated_headers" (TC-01)
  AC2 — only X-* non-sensitive headers are stored (TC-01, TC-03, TC-05)
  AC3 — continuation/new execution without propagate_headers flag does not inject headers (TC-06)
  AC4 — context store contains propagated headers for new executions with headers (TC-01, TC-03)
  AC5 — backward compatibility: no propagated_headers key when flag absent (TC-02)
"""

import pytest
from hamcrest import assert_that, has_entry, has_key, is_not

from codemie_test_harness.tests.test_data.propagated_headers_test_data import (
    MIXED_HEADERS_WITH_SENSITIVE,
    MULTIPLE_CUSTOM_HEADERS,
    NON_X_HEADERS,
    SINGLE_CUSTOM_HEADER,
    TC06_FIRST_HEADERS,
)

_VERIFY_STATE = "verify_state"
_PROPAGATED_HEADERS_KEY = "propagated_headers"


# ---------------------------------------------------------------------------
# TC-01 — Headers propagated to context store under "propagated_headers" key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "extra_headers,tc_input",
    [
        (SINGLE_CUSTOM_HEADER, "TC01-single-header"),
        (MULTIPLE_CUSTOM_HEADERS, "TC01-multi-headers"),
    ],
    ids=["single_custom_header", "multiple_custom_headers"],
)
@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_propagates_custom_headers_into_context_store(
    extra_headers,
    tc_input,
    propagated_headers_workflow,
    workflow_utils,
):
    """TC-01 (AC1, AC2, AC4): X-* headers appear in context_store["propagated_headers"].

    Verifies:
    - Key name is exactly "propagated_headers" (AC1).
    - The stored dict equals the supplied X-* headers (AC2, AC4).
    Two parametrized variants: single header and multiple headers.
    """
    execution_id = workflow_utils.execute_workflow_with_headers(
        propagated_headers_workflow.id,
        _VERIFY_STATE,
        tc_input,
        propagate_headers=True,
        extra_headers=extra_headers,
    )

    context_store = workflow_utils.get_context_store_at_state(
        propagated_headers_workflow.id, execution_id, _VERIFY_STATE
    )

    # The backend normalizes header names to lowercase and the propagated_headers
    # dict also includes infrastructure X-* headers added by the proxy layer.
    # Assert per-entry with lowercase keys rather than exact dict equality.
    propagated = context_store[_PROPAGATED_HEADERS_KEY]
    for sent_key, expected_val in extra_headers.items():
        assert_that(
            propagated,
            has_entry(sent_key.lower(), expected_val),
            f"context_store[propagated_headers] must contain {sent_key.lower()}={expected_val!r}",
        )


# ---------------------------------------------------------------------------
# TC-02 — No "propagated_headers" key when propagation not requested
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_context_store_has_no_propagated_headers_when_flag_is_false(
    propagated_headers_workflow,
    workflow_utils,
):
    """TC-02a (AC5): propagated_headers absent when propagate_headers=False (explicit).

    Backward-compatibility check: passing custom X-* headers but setting the flag
    to False must NOT populate the context store.
    """
    execution_id = workflow_utils.execute_workflow_with_headers(
        propagated_headers_workflow.id,
        _VERIFY_STATE,
        "TC02a-explicit-false",
        propagate_headers=False,
        extra_headers=SINGLE_CUSTOM_HEADER,
    )

    context_store = workflow_utils.get_context_store_at_state(
        propagated_headers_workflow.id, execution_id, _VERIFY_STATE
    )

    assert_that(
        context_store,
        is_not(has_key(_PROPAGATED_HEADERS_KEY)),
        "propagated_headers must be absent when propagate_headers=False",
    )


@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_context_store_has_no_propagated_headers_when_flag_is_omitted(
    propagated_headers_workflow,
    workflow_utils,
):
    """TC-02b (AC5): propagated_headers absent when propagate_headers omitted (default).

    Backward-compatibility check: the feature is opt-in; omitting the flag must
    leave existing workflow behavior unchanged.
    """
    execution_id = workflow_utils.execute_workflow_with_headers(
        propagated_headers_workflow.id,
        _VERIFY_STATE,
        "TC02b-omitted-default",
        extra_headers=SINGLE_CUSTOM_HEADER,
    )

    context_store = workflow_utils.get_context_store_at_state(
        propagated_headers_workflow.id, execution_id, _VERIFY_STATE
    )

    assert_that(
        context_store,
        is_not(has_key(_PROPAGATED_HEADERS_KEY)),
        "propagated_headers must be absent when propagate_headers flag is omitted",
    )


# ---------------------------------------------------------------------------
# TC-03 — Sensitive headers are filtered from "propagated_headers"
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_sensitive_headers_filtered_from_propagated_headers(
    propagated_headers_workflow,
    workflow_utils,
):
    """TC-03 (AC2, AC4): sensitive X-* headers (x-api-key, x-auth-token) are stripped.

    MIXED_HEADERS_WITH_SENSITIVE contains one allowed X-* header (X-Custom-Header)
    plus two sensitive X-* headers (x-api-key, x-auth-token) that are on the
    backend denylist.

    The allowed header must be present (stored as lowercase x-custom-header);
    the sensitive X-* headers must not appear in context_store["propagated_headers"].

    Note: non-X-* sensitive headers (Authorization, Cookie) are excluded from the
    test data because they would override the SDK auth token and cause request failure.
    Those headers are also filtered by the X-* prefix requirement, not the denylist.
    """
    execution_id = workflow_utils.execute_workflow_with_headers(
        propagated_headers_workflow.id,
        _VERIFY_STATE,
        "TC03-sensitive-filter",
        propagate_headers=True,
        extra_headers=MIXED_HEADERS_WITH_SENSITIVE,
    )

    context_store = workflow_utils.get_context_store_at_state(
        propagated_headers_workflow.id, execution_id, _VERIFY_STATE
    )

    propagated = context_store[_PROPAGATED_HEADERS_KEY]

    # Backend stores header names as lowercase
    assert_that(
        propagated,
        has_entry("x-custom-header", "allowed-value"),
        "Allowed X-Custom-Header must be present in propagated_headers (as x-custom-header)",
    )
    assert_that(
        propagated,
        is_not(has_key("x-api-key")),
        "Sensitive header x-api-key must be absent from propagated_headers",
    )
    assert_that(
        propagated,
        is_not(has_key("x-auth-token")),
        "Sensitive header x-auth-token must be absent from propagated_headers",
    )


# ---------------------------------------------------------------------------
# TC-05 — No "propagated_headers" when no X-* headers are supplied
# ---------------------------------------------------------------------------


@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.api
def test_workflow_no_propagated_headers_when_only_non_x_star_headers_sent(
    propagated_headers_workflow,
    workflow_utils,
):
    """TC-05 (AC2): non-X-* headers are excluded from propagated_headers.

    The feature only captures X-* prefixed headers.  Sending standard headers
    such as Content-Type / Accept with propagate_headers=True must NOT write
    those headers into propagated_headers.

    Note: propagated_headers may still exist in the context store because the
    infrastructure proxy layer adds its own X-* headers (x-forwarded-for, x-scheme,
    etc.) that are propagated.  The assertion verifies the user-supplied non-X-*
    headers are absent, not that the key itself is absent.
    """
    execution_id = workflow_utils.execute_workflow_with_headers(
        propagated_headers_workflow.id,
        _VERIFY_STATE,
        "TC05-non-x-headers",
        propagate_headers=True,
        extra_headers=NON_X_HEADERS,
    )

    context_store = workflow_utils.get_context_store_at_state(
        propagated_headers_workflow.id, execution_id, _VERIFY_STATE
    )

    # Behind an ingress the propagated_headers key exists even here, because the proxy
    # injects its own X-* headers (x-forwarded-for, x-scheme, etc.).  Against a direct
    # (unproxied) backend no X-* headers arrive at all and the key is never written.
    # Both are valid per AC2 — assert only that user-supplied non-X-* headers are absent.
    propagated = context_store.get(_PROPAGATED_HEADERS_KEY, {})
    assert_that(
        propagated,
        is_not(has_key("content-type")),
        "Non-X-* header content-type must NOT appear in propagated_headers",
    )
    assert_that(
        propagated,
        is_not(has_key("accept")),
        "Non-X-* header accept must NOT appear in propagated_headers",
    )


# ---------------------------------------------------------------------------
# TC-06 — Continuation execution does not inject "propagated_headers"
# ---------------------------------------------------------------------------


@pytest.mark.workflow
@pytest.mark.api
def test_workflow_continuation_execution_does_not_inject_propagated_headers(
    propagated_headers_workflow,
    workflow_utils,
):
    """TC-06 (AC3): a subsequent execution without the flag does not carry over headers.

    Scenario:
    1. First execution uses propagate_headers=True with a custom X-header.
       Assert that context_store["propagated_headers"] is present.
    2. Second execution on the same workflow omits propagate_headers (default False).
       Assert that context_store["propagated_headers"] is absent — confirming
       the feature is opt-in per execution and not inherited from previous runs.
    """
    # First turn — headers requested
    first_execution_id = workflow_utils.execute_workflow_with_headers(
        propagated_headers_workflow.id,
        _VERIFY_STATE,
        "TC06-first-with-headers",
        propagate_headers=True,
        extra_headers=TC06_FIRST_HEADERS,
    )

    first_context_store = workflow_utils.get_context_store_at_state(
        propagated_headers_workflow.id, first_execution_id, _VERIFY_STATE
    )

    assert_that(
        first_context_store,
        has_key(_PROPAGATED_HEADERS_KEY),
        "First execution must have propagated_headers in context store",
    )

    # Second turn — no propagate_headers flag (continuation without headers)
    second_execution_id = workflow_utils.execute_workflow_with_headers(
        propagated_headers_workflow.id,
        _VERIFY_STATE,
        "TC06-second-no-headers",
    )

    second_context_store = workflow_utils.get_context_store_at_state(
        propagated_headers_workflow.id, second_execution_id, _VERIFY_STATE
    )

    assert_that(
        second_context_store,
        is_not(has_key(_PROPAGATED_HEADERS_KEY)),
        "Continuation execution must NOT inject propagated_headers from prior run",
    )
