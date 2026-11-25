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

"""API tests for the Creator column of the marketplace Cleanup list.

``GET /v1/marketplace-management/entities/assistants/cleanup`` reads the latest finished
audit run and lists only published assistants. A row's ``creator`` is the latest submitter's
display name (the Review queue's ``submitted_by``), else the author's display name; it is
never the generic "System".

One module-scoped fixture publishes the assistants and runs one audit after them, so the
audit (minutes long, one active per deployment) is paid once for the module. The tests pin to
one xdist worker for the same reason (``--dist=loadgroup``, see strategy.md).
"""

from dataclasses import dataclass

import pytest
from codemie_sdk.models.marketplace_management import (
    MarketplaceAuditRunStatus,
    MarketplaceCleanupBucket,
)
from hamcrest import assert_that, equal_to, has_item, has_length, is_not

from codemie_test_harness.tests.test_data.marketplace_approval_gate_test_data import (
    build_marketplace_submission,
)
from codemie_test_harness.tests.test_data.marketplace_cleanup_test_data import (
    CLEANUP_ITEM_KEYS,
    CLEANUP_RESPONSE_KEYS,
    SYSTEM_CREATOR,
)
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.marketplace_management_utils import (
    CLEANUP_PAGE_SIZE,
    delete_submitter_assistant,
    poll_marketplace_listing,
)

pytestmark = pytest.mark.skipif(
    EnvironmentResolver.is_production(),
    reason="publishes to the live marketplace and replaces the latest finished audit run, "
    "which production treats as read-only",
)


@dataclass
class CleanupAudit:
    """What the module's published assistants and the audit run after them look like."""

    approved_id: str
    approved_name: str
    submitter_name: str
    queue_submitted_by: str
    admin_published_id: str
    admin_name: str | None


@pytest.fixture(scope="module")
def cleanup_audit(
    client,
    default_llm,
    assistant_utils,
    marketplace_submitter,
    marketplace_management_utils,
    marketplace_core_gates,
):
    """Two published assistants, then one audit run that started after both were published.

    The submitter's assistant is read in the Review queue, then approved by the admin (it
    has a submission record). The admin publishes the other one directly, which skips the
    queue (no submission record, so its creator comes from the author's name).
    """
    submitted = marketplace_submitter.create_assistant(
        build_marketplace_submission(marketplace_core_gates)
    )
    admin_submission = build_marketplace_submission(marketplace_core_gates)
    admin_assistant = None
    try:
        marketplace_submitter.submit_for_review(submitted)
        queued = [
            row
            for row in marketplace_management_utils.list_all_pending()
            if row.assistant_id == submitted.id
        ]
        assert_that(
            queued,
            has_length(1),
            "the submitted assistant must be listed once in the Review queue",
        )
        assert_that(
            bool(queued[0].submitted_by),
            equal_to(True),
            "the Review queue entry must carry submitted_by",
        )
        version = marketplace_management_utils.get_detail(
            submitted.id
        ).marketplace_version
        marketplace_management_utils.approve(submitted.id, expected_version=version)
        listed = poll_marketplace_listing(assistant_utils, submitted.id, listed=True)
        assert_that(
            listed,
            has_item(submitted.id),
            "the approved assistant did not appear in the marketplace listing in time",
        )

        admin_assistant = assistant_utils.create_assistant(
            llm_model_type=default_llm.base_name,
            assistant_name=admin_submission.name,
            description=admin_submission.description,
            system_prompt=admin_submission.system_prompt,
        )
        assistant_utils.publish_assistant_to_marketplace(
            admin_assistant.id,
            categories=admin_submission.categories,
            ignore_recommendations=True,
        )
        admin_listed = poll_marketplace_listing(
            assistant_utils, admin_assistant.id, listed=True
        )
        assert_that(
            admin_listed,
            has_item(admin_assistant.id),
            "the admin-published assistant did not appear in the marketplace listing in time",
        )

        audit = marketplace_management_utils.run_audit()
        assert_that(
            audit.is_running, equal_to(False), "the audit run must have finished"
        )
        assert_that(
            audit.error,
            equal_to(None),
            f"the audit run must end without an error (status {audit.status})",
        )
        assert_that(
            audit.status,
            equal_to(MarketplaceAuditRunStatus.SUCCEEDED),
            f"the audit run must complete (degraded_reason: {audit.degraded_reason})",
        )
        assert_that(
            audit.degraded,
            equal_to(False),
            f"the audit run must not be degraded (degraded_reason: {audit.degraded_reason})",
        )
        yield CleanupAudit(
            approved_id=submitted.id,
            approved_name=submitted.name,
            submitter_name=marketplace_submitter.display_name,
            queue_submitted_by=queued[0].submitted_by,
            admin_published_id=admin_assistant.id,
            admin_name=client.users.about_me().name,
        )
    finally:
        delete_submitter_assistant(marketplace_submitter, client, submitted.id)
        if admin_assistant:
            delete_submitter_assistant(
                marketplace_submitter, client, admin_assistant.id
            )


def _row_of(rows: list, assistant_id: str):
    """The one Cleanup row of an assistant."""
    matching = [row for row in rows if row.id == assistant_id]
    assert_that(
        matching,
        has_length(1),
        f"the Cleanup list must hold one row for assistant {assistant_id}",
    )
    return matching[0]


# @case marketplace-cleanup-queue-creator_TC_001
@pytest.mark.xdist_group(name="marketplace_cleanup_audit")
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_cleanup_row_of_approved_assistant_shows_submitter_display_name(
    cleanup_audit, marketplace_management_utils
):
    rows = marketplace_management_utils.list_all_cleanup(
        bucket=MarketplaceCleanupBucket.ALL
    )

    row = _row_of(rows, cleanup_audit.approved_id)

    assert_that(
        row.creator,
        equal_to(cleanup_audit.submitter_name),
        "the Cleanup creator of an approved assistant must be the submitter's display name",
    )
    assert_that(
        row.creator,
        is_not(SYSTEM_CREATOR),
        "the Cleanup creator must not be the generic System",
    )


# @case marketplace-cleanup-queue-creator_TC_001
@pytest.mark.xdist_group(name="marketplace_cleanup_audit")
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_cleanup_row_of_admin_published_assistant_shows_author_display_name(
    cleanup_audit, marketplace_management_utils
):
    assert_that(
        bool(cleanup_audit.admin_name),
        equal_to(True),
        "the admin profile must have a display name for the author fallback to be observable",
    )
    rows = marketplace_management_utils.list_all_cleanup(
        bucket=MarketplaceCleanupBucket.ALL
    )

    row = _row_of(rows, cleanup_audit.admin_published_id)

    assert_that(
        row.creator,
        equal_to(cleanup_audit.admin_name),
        "without a submission the Cleanup creator must be the author's display name",
    )
    assert_that(
        row.creator,
        is_not(SYSTEM_CREATOR),
        "the Cleanup creator must not be the generic System",
    )


# @case marketplace-cleanup-queue-creator_TC_002
@pytest.mark.xdist_group(name="marketplace_cleanup_audit")
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_cleanup_creator_equals_review_queue_submitted_by(
    cleanup_audit, marketplace_management_utils
):
    rows = marketplace_management_utils.list_all_cleanup(
        bucket=MarketplaceCleanupBucket.ALL
    )

    row = _row_of(rows, cleanup_audit.approved_id)

    assert_that(
        row.creator,
        equal_to(cleanup_audit.queue_submitted_by),
        "the Cleanup creator must equal the submitted_by the Review queue showed before approval",
    )


# @case marketplace-cleanup-queue-creator_TC_003
@pytest.mark.xdist_group(name="marketplace_cleanup_audit")
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_cleanup_response_keeps_envelope_and_item_keys(
    cleanup_audit, marketplace_management_utils
):
    response = marketplace_management_utils.get_cleanup(
        bucket=MarketplaceCleanupBucket.ALL, page_size=CLEANUP_PAGE_SIZE
    )

    assert_that(
        response.model_fields_set,
        equal_to(CLEANUP_RESPONSE_KEYS),
        "the Cleanup response must keep the {total, page, page_size, items} shape",
    )
    assert_that(
        {frozenset(row.model_fields_set) for row in response.items},
        equal_to({CLEANUP_ITEM_KEYS}),
        "every Cleanup row must keep the same key set",
    )


# @case marketplace-cleanup-queue-creator_TC_003
@pytest.mark.xdist_group(name="marketplace_cleanup_audit")
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_cleanup_q_filter_narrows_to_published_assistant(
    cleanup_audit, marketplace_management_utils
):
    response = marketplace_management_utils.get_cleanup(
        bucket=MarketplaceCleanupBucket.ALL, q=cleanup_audit.approved_name
    )

    assert_that(
        [row.id for row in response.items],
        equal_to([cleanup_audit.approved_id]),
        "the q filter must narrow the Cleanup list to the published assistant",
    )
    assert_that(response.total, equal_to(1), "total must count the filtered set")
