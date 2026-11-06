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

"""UI tests for the Marketplace management Review queue.

Assistants are submitted through the API by a plain user and the admin works the
queue in the browser. Tests only touch their own rows: they search for or tick
specific assistants and never use select-all.

The search, selection, approve and reject tests are marked `prod_regression`: they only
touch assistants that the test created (found by their unique name or row id) and delete
them at the end, so they are safe next to the real submissions of a production queue.
The bulk reject test is not marked: a wrong selection would reject other people's rows.
"""

import pytest
from hamcrest import assert_that, equal_to, has_properties

from codemie_test_harness.tests.test_data.marketplace_approval_gate_test_data import (
    APPROVED,
    REJECTED,
)
from codemie_test_harness.tests.ui.pageobject.administration.marketplace_review_queue_page import (
    MarketplaceReviewQueuePage,
)
from codemie_test_harness.tests.ui.test_data.marketplace_management_test_data import (
    BULK_REJECT_REASON,
    MINIMUM_REJECT_REASON,
    SHORT_REJECT_REASON,
)


def open_row_in_queue(page, assistant_id: str, assistant_name: str):
    """Open the Review queue, narrow it to the assistant by name and wait for its row."""
    queue = MarketplaceReviewQueuePage(page).navigate_to()
    queue.search_for(assistant_name)
    queue.should_see_row(assistant_id)
    return queue


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_review_queue_search_narrows_rows_and_clear_all_restores_them(
    page, pending_assistant
):
    # @case marketplace-admin-approval-gate_TC_005
    searched = pending_assistant()
    other = pending_assistant()
    queue = MarketplaceReviewQueuePage(page).navigate_to()
    queue.should_see_row(searched.id).should_see_row(other.id)
    queue.should_not_see_clear_all_button()

    queue.search_for(searched.name)

    queue.should_list_only_row(searched.id)
    queue.should_see_clear_all_button()

    queue.clear_all_filters()

    queue.should_see_row(searched.id).should_see_row(other.id)
    queue.should_not_see_clear_all_button()


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_review_queue_selection_swaps_filter_row_for_bulk_actions(
    page, pending_assistant
):
    # @case marketplace-admin-approval-gate_TC_006
    first = pending_assistant()
    second = pending_assistant()

    queue = MarketplaceReviewQueuePage(page).navigate_to()

    queue.should_see_review_queue_tab()
    queue.should_see_table_columns()
    queue.should_see_row(first.id).should_see_row(second.id)
    queue.should_see_filter_bar()

    queue.select_rows(first.id, second.id)

    queue.should_see_bulk_actions()
    queue.should_not_see_filter_bar()


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_approve_from_drawer_removes_assistant_from_queue(
    page, pending_assistant, marketplace_submitter, delete_marketplace_assistant
):
    # @case marketplace-admin-approval-gate_TC_009
    submitted = pending_assistant()
    queue = open_row_in_queue(page, submitted.id, submitted.name)
    queue.should_show_row_details(
        submitted.id, submitted.name, marketplace_submitter.display_name
    )

    queue.open_drawer(submitted.id)
    queue.should_see_drawer_actions()
    queue.approve_from_drawer()

    queue.should_not_see_row(submitted.id)
    stored = marketplace_submitter.management.get_assistant(submitted.id)
    # An approved assistant is public: delete it as soon as its state has been read.
    # The fixture teardown deletes it too if an assertion below the read fails.
    delete_marketplace_assistant(submitted)
    assert_that(stored, has_properties(marketplace_status=APPROVED, is_verified=True))


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
@pytest.mark.prod_regression
def test_reject_from_drawer_enforces_reason_bound_in_form(
    page, pending_assistant, marketplace_submitter
):
    # @case marketplace-admin-approval-gate_TC_012
    submitted = pending_assistant()
    queue = open_row_in_queue(page, submitted.id, submitted.name)
    queue.should_show_row_details(
        submitted.id, submitted.name, marketplace_submitter.display_name
    )
    queue.open_drawer(submitted.id)
    queue.should_see_drawer_actions()
    queue.start_reject_from_drawer()

    queue.type_drawer_reject_reason(SHORT_REJECT_REASON)

    queue.should_have_drawer_reject_submit_disabled()
    queue.should_see_drawer_reject_counter(len(SHORT_REJECT_REASON))

    queue.type_drawer_reject_reason(MINIMUM_REJECT_REASON)

    queue.should_have_drawer_reject_submit_enabled()
    queue.submit_drawer_reject()

    queue.should_not_see_row(submitted.id)
    stored = marketplace_submitter.management.get_assistant(submitted.id)
    assert_that(
        stored,
        has_properties(
            marketplace_status=REJECTED,
            is_verified=False,
            marketplace_decision_reason=MINIMUM_REJECT_REASON,
        ),
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.ui
def test_bulk_reject_applies_one_shared_reason_to_selected_rows(
    page, pending_assistant, marketplace_submitter
):
    # @case marketplace-admin-approval-gate_TC_013
    submitted = [pending_assistant() for _ in range(3)]
    queue = MarketplaceReviewQueuePage(page).navigate_to()
    for assistant in submitted:
        queue.should_see_row(assistant.id)
    queue.select_rows(*(assistant.id for assistant in submitted))

    queue.reject_selected_with_reason(BULK_REJECT_REASON)

    queue.should_see_toast("3 assistant(s) rejected.")
    for assistant in submitted:
        queue.should_not_see_row(assistant.id)
    stored = [
        marketplace_submitter.management.get_assistant(assistant.id)
        for assistant in submitted
    ]
    assert_that(
        [item.marketplace_status for item in stored],
        equal_to([REJECTED] * 3),
    )
    assert_that(
        [item.marketplace_decision_reason for item in stored],
        equal_to([BULK_REJECT_REASON] * 3),
    )
