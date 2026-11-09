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

"""API tests for the marketplace review queue reads.

With the approval gate on, a plain user's publish queues the assistant as
PENDING_REVIEW. An admin reads that queue through
GET /v1/marketplace-management/entities/assistants/{pending,overview,{id}}.
The submitter is a plain user created by the `marketplace_submitter` fixture;
the admin is the harness `client`.
"""

from dataclasses import dataclass

import pytest
from hamcrest import (
    anything,
    assert_that,
    empty,
    equal_to,
    greater_than,
    greater_than_or_equal_to,
    has_item,
    has_items,
    has_key,
    has_properties,
    instance_of,
    less_than,
    less_than_or_equal_to,
    not_,
    only_contains,
    starts_with,
)

from codemie_test_harness.tests.test_data.marketplace_approval_gate_test_data import (
    CATEGORY_FILTER_PARAMS,
    CRITICAL,
    DESCRIPTION_LENGTH_RULE,
    GATE_RESULT_PARAMS,
    ORDER_BY_PARAMS,
    PENDING_REVIEW,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.marketplace_management_utils import PAGE_SIZE


@dataclass
class PendingPair:
    """Two queued assistants: `first` is clean, `second` was submitted later and has a CRITICAL finding."""

    first: object
    second: object


@pytest.fixture
def two_categories(categories_utils):
    """Ids of two different assistant categories."""
    ids = [category.id for category in categories_utils.get_categories()]
    assert_that(len(ids), greater_than_or_equal_to(2), "the stand needs two categories")
    return ids[:2]


@pytest.fixture
def ordered_pending_pair(pending_assistant, critical_pending_assistant, two_categories):
    """First (clean, category one, name ...-a) is submitted before second (CRITICAL, category two, name ...-b)."""
    base = get_random_name()
    first = pending_assistant(name=f"{base}-a", categories=[two_categories[0]])
    second = critical_pending_assistant(
        name=f"{base}-b", categories=[two_categories[1]]
    )
    return PendingPair(first=first, second=second)


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_admin_sees_submitted_assistant_in_pending_queue(
    pending_assistant, marketplace_submitter, marketplace_management_utils
):
    # @case marketplace-admin-approval-gate_TC_001
    submitted = pending_assistant()

    first_page = marketplace_management_utils.get_pending()
    queue = marketplace_management_utils.list_all_pending()

    assert_that(
        first_page,
        has_properties(page=1, page_size=PAGE_SIZE, total=greater_than_or_equal_to(1)),
    )
    assert_that(first_page.items, not_(empty()))
    assert_that(len(first_page.items), less_than_or_equal_to(PAGE_SIZE))
    rows = {item.assistant_id: item for item in queue}
    assert_that(
        rows, has_key(submitted.id), "the submitted assistant is missing from the queue"
    )
    row = rows[submitted.id]
    assert_that(row.name, equal_to(submitted.name))
    assert_that(row.marketplace_status, equal_to(PENDING_REVIEW))
    assert_that(
        row.submitted_by,
        equal_to(marketplace_submitter.display_name),
        "the row must name the submitter",
    )
    assert_that(row.submitted_at, greater_than(0), "the row must carry submitted_at")


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_overview_reports_pending_count_and_waiting_over_seven_days(
    pending_assistant, marketplace_management_utils
):
    # @case marketplace-admin-approval-gate_TC_003
    pending_assistant()

    pending = marketplace_management_utils.get_overview().pending

    assert_that(
        pending.model_fields_set,
        has_items("count", "waiting_over_7d", "avg_wait_days"),
        "the overview must report the pending stats, not fall back to the SDK defaults",
    )
    assert_that(pending.waiting_over_7d, greater_than_or_equal_to(0))
    assert_that(pending.avg_wait_days, greater_than_or_equal_to(0))
    assert_that(
        pending.count,
        greater_than_or_equal_to(1),
        "the new submission must be counted",
    )
    assert_that(pending.waiting_over_7d, instance_of(int))
    assert_that(pending.waiting_over_7d, greater_than_or_equal_to(0))
    assert_that(pending.waiting_over_7d, less_than_or_equal_to(pending.count))


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("gate_result, included, excluded", GATE_RESULT_PARAMS)
def test_pending_queue_filters_by_gate_result(
    ordered_pending_pair, marketplace_management_utils, gate_result, included, excluded
):
    # @case marketplace-admin-approval-gate_TC_004
    queue = marketplace_management_utils.list_all_pending(gate_result=gate_result)

    ids = [item.assistant_id for item in queue]
    assert_that(ids, has_item(getattr(ordered_pending_pair, included).id))
    assert_that(ids, not_(has_item(getattr(ordered_pending_pair, excluded).id)))


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("included, excluded", CATEGORY_FILTER_PARAMS)
def test_pending_queue_filters_by_category(
    ordered_pending_pair, marketplace_management_utils, included, excluded
):
    # @case marketplace-admin-approval-gate_TC_004
    category = getattr(ordered_pending_pair, included).categories[0]

    queue = marketplace_management_utils.list_all_pending(category=category)

    ids = [item.assistant_id for item in queue]
    assert_that(ids, has_item(getattr(ordered_pending_pair, included).id))
    assert_that(ids, not_(has_item(getattr(ordered_pending_pair, excluded).id)))


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("order_by, expected_order", ORDER_BY_PARAMS)
def test_pending_queue_sorts_by_order_by(
    ordered_pending_pair, marketplace_management_utils, order_by, expected_order
):
    # @case marketplace-admin-approval-gate_TC_004
    earlier, later = (getattr(ordered_pending_pair, key).id for key in expected_order)

    queue = marketplace_management_utils.list_all_pending(order_by=order_by)

    ids = [item.assistant_id for item in queue]
    assert_that(ids, has_item(earlier))
    assert_that(ids, has_item(later))
    assert_that(
        ids.index(earlier),
        less_than(ids.index(later)),
        f"order_by={order_by} must list the assistant {earlier} before {later}",
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_queue_detail_returns_configuration_and_gate_findings(
    critical_pending_assistant,
    marketplace_submitter,
    marketplace_management_utils,
    marketplace_short_description,
):
    # @case marketplace-admin-approval-gate_TC_007
    submitted = critical_pending_assistant()

    detail = marketplace_management_utils.get_detail(submitted.id)

    assert_that(
        detail,
        has_properties(
            id=submitted.id,
            name=submitted.name,
            description=marketplace_short_description,
            categories=submitted.categories,
            project=marketplace_submitter.project,
            marketplace_status=PENDING_REVIEW,
            is_verified=False,
            system_prompt_length=len(submitted.system_prompt),
        ),
    )
    findings = detail.gate_findings
    assert_that(
        findings,
        only_contains(
            has_properties(rule=anything(), severity=anything(), message=anything())
        ),
    )
    assert_that(
        findings,
        has_item(
            has_properties(
                rule=DESCRIPTION_LENGTH_RULE,
                severity=CRITICAL,
                message=starts_with(
                    f"Description is {len(marketplace_short_description)} chars, minimum is "
                ),
            )
        ),
    )
    critical_findings = [f for f in findings if f.severity == CRITICAL]
    assert_that(detail.critical_count, equal_to(len(critical_findings)))
