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

"""API tests for the marketplace review decisions of an admin.

Covers approve, reject, force-publish and withdraw on queued assistants
(POST /v1/marketplace-management/entities/assistants/pending/{id}/<action>),
the optimistic-concurrency contract of those calls, and the admin
skip-queue publish through POST /v1/assistants/{id}/marketplace/publish.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_entries,
    has_item,
    has_key,
    has_properties,
    not_,
    starts_with,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.marketplace_approval_gate_test_data import (
    ACCEPTED_REASON_PARAMS,
    ADMIN_SKIP_QUEUE_NOTICE,
    APPROVED,
    CRITICAL,
    DESCRIPTION_LENGTH_RULE,
    PENDING_REVIEW,
    REFUSED_REASON_PARAMS,
    REJECTED,
    REJECTION_REASON,
    UNVERIFIED_STATE_PARAMS,
    VALID_REASON,
    WITHDRAWN,
    build_marketplace_submission,
)
from codemie_test_harness.tests.utils.marketplace_management_utils import (
    poll_marketplace_listing,
)


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_approving_pending_assistant_verifies_it(
    pending_assistant, marketplace_submitter, marketplace_management_utils
):
    # @case marketplace-admin-approval-gate_TC_008
    submitted = pending_assistant()
    version = marketplace_management_utils.get_detail(submitted.id).marketplace_version

    response = marketplace_management_utils.approve(
        submitted.id, expected_version=version
    )

    assert_that(
        response,
        has_properties(ok=True, entity_id=submitted.id, status=APPROVED),
    )
    assistant = marketplace_submitter.management.get_assistant(submitted.id)
    assert_that(
        assistant, has_properties(marketplace_status=APPROVED, is_verified=True)
    )
    verified = marketplace_management_utils.list_all_marketplace_assistants(
        status="VERIFIED"
    )
    assert_that(
        verified,
        has_item(
            has_properties(
                assistant_id=submitted.id, marketplace_status=APPROVED, is_verified=True
            )
        ),
        "the approved assistant must be listed under the VERIFIED filter",
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_rejecting_takes_assistant_down_and_keeps_reason(
    pending_assistant,
    marketplace_submitter,
    marketplace_management_utils,
    assistant_utils,
):
    # @case marketplace-admin-approval-gate_TC_011
    submitted = pending_assistant()
    version = marketplace_management_utils.get_detail(submitted.id).marketplace_version

    response = marketplace_management_utils.reject(
        submitted.id, REJECTION_REASON, expected_version=version
    )

    assert_that(response, has_properties(ok=True, status=REJECTED))
    assistant = marketplace_submitter.management.get_assistant(submitted.id)
    assert_that(
        assistant,
        has_properties(
            marketplace_status=REJECTED,
            marketplace_decision_reason=REJECTION_REASON,
            is_verified=False,
            is_global=False,
        ),
    )
    listed = poll_marketplace_listing(assistant_utils, submitted.id, listed=False)
    assert_that(listed, not_(has_item(submitted.id)))


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("reason", REFUSED_REASON_PARAMS)
def test_reject_refuses_reason_outside_length_bounds(
    pending_assistant, marketplace_management_utils, reason
):
    # @case marketplace-admin-approval-gate_TC_010
    submitted = pending_assistant()
    version = marketplace_management_utils.get_detail(submitted.id).marketplace_version

    with pytest.raises(HTTPError) as exc_info:
        marketplace_management_utils.reject(submitted.id, reason)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(422), response.text)
    error = response.json()["error"]
    assert_that(
        error["message"],
        equal_to(f"reason must be 20-2000 chars (got {len(reason.strip())})."),
    )
    assert_that(error["details"], equal_to({"field": "reason"}))
    detail = marketplace_management_utils.get_detail(submitted.id)
    assert_that(
        detail,
        has_properties(marketplace_status=PENDING_REVIEW, marketplace_version=version),
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("reason", ACCEPTED_REASON_PARAMS)
def test_reject_accepts_reason_at_length_bounds(
    pending_assistant, marketplace_submitter, marketplace_management_utils, reason
):
    # @case marketplace-admin-approval-gate_TC_010
    submitted = pending_assistant()

    marketplace_management_utils.reject(submitted.id, reason)

    assistant = marketplace_submitter.management.get_assistant(submitted.id)
    assert_that(
        assistant,
        has_properties(marketplace_status=REJECTED, marketplace_decision_reason=reason),
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("override_notice", REFUSED_REASON_PARAMS)
def test_force_publish_refuses_notice_outside_length_bounds(
    pending_assistant, marketplace_management_utils, override_notice
):
    # @case marketplace-admin-approval-gate_TC_010
    submitted = pending_assistant()
    version = marketplace_management_utils.get_detail(submitted.id).marketplace_version

    with pytest.raises(HTTPError) as exc_info:
        marketplace_management_utils.force_publish(submitted.id, override_notice)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(422), response.text)
    error = response.json()["error"]
    assert_that(
        error["message"],
        equal_to(
            f"override_notice must be 20-2000 chars (got {len(override_notice.strip())})."
        ),
    )
    assert_that(error["details"], equal_to({"field": "override_notice"}))
    detail = marketplace_management_utils.get_detail(submitted.id)
    assert_that(
        detail,
        has_properties(marketplace_status=PENDING_REVIEW, marketplace_version=version),
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("override_notice", ACCEPTED_REASON_PARAMS)
def test_force_publish_accepts_single_notice_at_length_bounds(
    pending_assistant,
    marketplace_submitter,
    marketplace_management_utils,
    override_notice,
):
    # @case marketplace-admin-approval-gate_TC_010
    submitted = pending_assistant()

    response = marketplace_management_utils.force_publish(submitted.id, override_notice)

    assert_that(
        response,
        has_properties(status=APPROVED, override_notice=override_notice),
    )
    assistant = marketplace_submitter.management.get_assistant(submitted.id)
    assert_that(
        assistant, has_properties(marketplace_status=APPROVED, is_verified=True)
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_force_publish_over_critical_findings_records_attribution(
    critical_pending_assistant,
    marketplace_submitter,
    marketplace_management_utils,
    client,
):
    # @case marketplace-admin-approval-gate_TC_018
    submitted = critical_pending_assistant()
    before = marketplace_management_utils.get_detail(submitted.id)
    critical_rules = sorted(
        finding.rule for finding in before.gate_findings if finding.severity == CRITICAL
    )

    response = marketplace_management_utils.force_publish(
        submitted.id, VALID_REASON, expected_version=before.marketplace_version
    )

    assert_that(
        response,
        has_properties(
            ok=True,
            status=APPROVED,
            override_notice=VALID_REASON,
            bypassed_gate_findings_unavailable=False,
        ),
    )
    assistant = marketplace_submitter.management.get_assistant(submitted.id)
    assert_that(
        assistant, has_properties(marketplace_status=APPROVED, is_verified=True)
    )
    detail = marketplace_management_utils.get_detail(submitted.id)
    assert_that(
        detail,
        has_properties(
            override_notice=VALID_REASON,
            overridden_by=client.users.about_me().email,
            bypassed_gate_findings_unavailable=False,
        ),
    )
    assert_that(
        sorted(finding.rule for finding in detail.bypassed_gate_findings),
        equal_to(critical_rules),
        "the override must list exactly the CRITICAL findings it waived",
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_approve_is_blocked_while_critical_findings_exist(
    critical_pending_assistant, marketplace_submitter, marketplace_management_utils
):
    # @case marketplace-admin-approval-gate_TC_022
    submitted = critical_pending_assistant()
    version = marketplace_management_utils.get_detail(submitted.id).marketplace_version

    with pytest.raises(HTTPError) as exc_info:
        marketplace_management_utils.approve(submitted.id, expected_version=version)

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(422), response.text)
    error = response.json()["error"]
    assert_that(error["message"], starts_with("Assistant cannot be published: "))
    assert_that(error["message"], contains_string(DESCRIPTION_LENGTH_RULE))
    assert_that(error["details"], has_entries(assistant_id=submitted.id))
    assert_that(error["details"]["failed_rules"], has_item(DESCRIPTION_LENGTH_RULE))
    assert_that(
        error["details"]["gate_findings"],
        has_item(has_entries(rule=DESCRIPTION_LENGTH_RULE, severity=CRITICAL)),
    )
    assert_that(error["help"], contains_string("force-publish"))
    assistant = marketplace_submitter.management.get_assistant(submitted.id)
    assert_that(
        assistant, has_properties(marketplace_status=PENDING_REVIEW, is_verified=False)
    )
    detail = marketplace_management_utils.get_detail(submitted.id)
    assert_that(detail.marketplace_version, equal_to(version))


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_approve_with_stale_version_returns_409_with_current_state(
    pending_assistant, marketplace_submitter, marketplace_management_utils
):
    # @case marketplace-admin-approval-gate_TC_023
    submitted = pending_assistant()
    version = marketplace_management_utils.get_detail(submitted.id).marketplace_version
    stale_version = version + 100

    with pytest.raises(HTTPError) as exc_info:
        marketplace_management_utils.approve(
            submitted.id, expected_version=stale_version
        )

    response = exc_info.value.response
    assert_that(response.status_code, equal_to(409), response.text)
    conflict = response.json()["detail"]
    assert_that(
        conflict,
        has_entries(
            decision="APPROVE",
            expected_version=stale_version,
            marketplace_status=PENDING_REVIEW,
            marketplace_version=version,
        ),
    )
    assert_that(conflict, has_key("marketplace_decided_by"))
    assistant = marketplace_submitter.management.get_assistant(submitted.id)
    assert_that(assistant.marketplace_status, equal_to(PENDING_REVIEW))


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_admin_publish_skips_the_review_queue(
    assistant, assistant_utils, marketplace_management_utils, marketplace_core_gates
):
    # @case marketplace-admin-approval-gate_TC_024
    submission = build_marketplace_submission(marketplace_core_gates)
    owned = assistant(
        assistant_name=submission.name,
        description=submission.description,
        system_prompt=submission.system_prompt,
        categories=submission.categories,
        conversation_starters=submission.conversation_starters,
    )

    response = marketplace_management_utils.publish(owned.id, submission.categories)

    assert_that(response["marketplace_status"], equal_to(APPROVED))
    stored = marketplace_management_utils.get_assistant(owned.id)
    assert_that(
        stored,
        has_properties(marketplace_status=APPROVED, is_verified=True, is_global=True),
    )
    detail = marketplace_management_utils.get_detail(owned.id)
    assert_that(detail.override_notice, equal_to(ADMIN_SKIP_QUEUE_NOTICE))
    queue = marketplace_management_utils.list_all_pending()
    assert_that(
        [item.assistant_id for item in queue],
        not_(has_item(owned.id)),
        "an admin publish must not pass through the queue",
    )
    listed = poll_marketplace_listing(assistant_utils, owned.id, listed=True)
    assert_that(listed, has_item(owned.id))


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_withdraw_unpublishes_unverifies_and_delists(
    approved_assistant,
    marketplace_submitter,
    marketplace_management_utils,
    assistant_utils,
):
    # @case marketplace-admin-approval-gate_TC_025
    approved = approved_assistant()
    listed_before = poll_marketplace_listing(assistant_utils, approved.id, listed=True)
    assert_that(
        listed_before,
        has_item(approved.id),
        "the approved assistant must be listed before it is withdrawn",
    )

    response = marketplace_management_utils.withdraw(approved.id)

    assert_that(response, has_properties(ok=True, status=WITHDRAWN))
    assistant = marketplace_submitter.management.get_assistant(approved.id)
    assert_that(
        assistant,
        has_properties(
            marketplace_status=WITHDRAWN, is_verified=False, is_global=False
        ),
    )
    listed_after = poll_marketplace_listing(assistant_utils, approved.id, listed=False)
    assert_that(listed_after, not_(has_item(approved.id)))


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize("state, expected_status", UNVERIFIED_STATE_PARAMS)
def test_unapproved_assistants_are_never_verified(
    assistant_in_marketplace_state, marketplace_submitter, state, expected_status
):
    # @case marketplace-admin-approval-gate_TC_016
    created = assistant_in_marketplace_state(state)

    assistant = marketplace_submitter.management.get_assistant(created.id)

    assert_that(
        assistant,
        has_properties(marketplace_status=expected_status, is_verified=False),
    )
