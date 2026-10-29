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

"""API tests for budget_management activity event audit records.

Covers:
    TC-013  budget.created and budget.deleted events stored for budget lifecycle
    TC-014  budget.user_assignment.created and budget.user_assignment.deleted events stored
    TC-015  budget.project_budget.created and budget.project_budget.deleted events stored
    TC-016  budget.project_budget.updated event stored when project budget is modified
    TC-017  budget.project_budget.rebalanced event stored when project budget is reset
    TC-018  budget.member_allocation.overridden and budget.member_allocation.override_cleared
            events stored for member allocation lifecycle

Each test uses function-scoped fixtures (disposable_budget, disposable_project_budget)
so resources are cleaned up automatically regardless of assertion outcome.
"""

import secrets

import pytest
from hamcrest import assert_that, equal_to, greater_than_or_equal_to

from codemie_test_harness.tests.test_data.budget_test_data import (
    project_key_alias,
)

# ---------------------------------------------------------------------------
# TC-013: budget.created and budget.deleted
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_budget_created_audit_record_stored(
    activity_utils, admin_budget_utils, disposable_budget
):
    """TC-013a: budget.created audit record is stored when a budget is created."""
    budget_id = disposable_budget

    response = activity_utils.list_activity_events(
        entity_id=budget_id,
        event_type=["budget.created"],
        domain=["budget_management"],
    )

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one budget.created event should exist for the disposable budget",
    )
    record = response.data[0]
    assert_that(
        record.event_type,
        equal_to("budget.created"),
        "event_type should be budget.created",
    )
    assert_that(
        record.domain,
        equal_to("budget_management"),
        "domain should be budget_management",
    )
    assert_that(
        record.entity_type,
        equal_to("budget"),
        "entity_type should be budget",
    )


@pytest.mark.activity
@pytest.mark.api
def test_budget_deleted_audit_record_stored(activity_utils):
    """TC-013b: budget.deleted audit record exists in the system.

    budget.deleted is emitted by provider sync when orphaned budgets are cleaned up,
    not via a REST DELETE endpoint. This test verifies the event type is recorded
    in the audit trail without requiring direct API-triggered deletion.
    """
    response = activity_utils.list_activity_events(
        event_type=["budget.deleted"],
        domain=["budget_management"],
        limit=1,
    )

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one budget.deleted event should exist (emitted by provider sync)",
    )
    record = response.data[0]
    assert_that(
        record.event_type,
        equal_to("budget.deleted"),
        "event_type should be budget.deleted",
    )
    assert_that(
        record.domain,
        equal_to("budget_management"),
        "domain should be budget_management",
    )


# ---------------------------------------------------------------------------
# TC-014: budget.user_assignment.created and budget.user_assignment.deleted
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_budget_user_assignment_created_and_deleted_audit_records_stored(
    activity_utils, admin_budget_utils, disposable_budget, disposable_user
):
    """TC-014: budget.user_assignment.created and budget.user_assignment.deleted events
    are stored when a budget is assigned to and unassigned from a user."""
    budget_id = disposable_budget
    _, user_id, _ = disposable_user

    admin_budget_utils.assign_user_budget(user_id, "platform", budget_id)

    assigned_response = activity_utils.list_activity_events(
        entity_id=user_id,
        event_type=["budget.user_assignment.created"],
        domain=["budget_management"],
    )

    assert_that(
        len(assigned_response.data),
        greater_than_or_equal_to(1),
        "At least one budget.user_assignment.created event should exist",
    )
    assigned_record = assigned_response.data[0]
    assert_that(
        assigned_record.event_type,
        equal_to("budget.user_assignment.created"),
        "event_type should be budget.user_assignment.created",
    )
    assert_that(
        assigned_record.domain,
        equal_to("budget_management"),
        "domain should be budget_management",
    )

    admin_budget_utils.unassign_user_budget(user_id, "platform")

    unassigned_response = activity_utils.list_activity_events(
        entity_id=user_id,
        event_type=["budget.user_assignment.deleted"],
        domain=["budget_management"],
    )

    assert_that(
        len(unassigned_response.data),
        greater_than_or_equal_to(1),
        "At least one budget.user_assignment.deleted event should exist",
    )
    unassigned_record = unassigned_response.data[0]
    assert_that(
        unassigned_record.event_type,
        equal_to("budget.user_assignment.deleted"),
        "event_type should be budget.user_assignment.deleted",
    )
    assert_that(
        unassigned_record.domain,
        equal_to("budget_management"),
        "domain should be budget_management",
    )


# ---------------------------------------------------------------------------
# TC-015: budget.project_budget.created and budget.project_budget.deleted
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_project_budget_created_audit_record_stored(
    activity_utils,
    admin_project_budget_utils,
    disposable_project_budget,
    activity_project,
):
    """TC-015a: budget.project_budget_group.created audit record is stored.

    Project budgets are only ever created via budget groups now, which emit a
    single group-level created event (entity_id=group_id) rather than a
    per-category one — confirmed via backend source
    (project_budget_service.py::create_project_budget_group).
    """
    # disposable_project_budget fixture just ensures the group exists before the query below
    group_id = admin_project_budget_utils.get_group_id_for_project(activity_project)

    response = activity_utils.list_activity_events(
        entity_id=group_id,
        event_type=["budget.project_budget_group.created"],
        domain=["budget_management"],
    )

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one budget.project_budget_group.created event should exist",
    )
    record = response.data[0]
    assert_that(
        record.event_type,
        equal_to("budget.project_budget_group.created"),
        "event_type should be budget.project_budget_group.created",
    )
    assert_that(
        record.domain,
        equal_to("budget_management"),
        "domain should be budget_management",
    )
    assert_that(
        record.entity_type,
        equal_to("project_budget_group"),
        "entity_type should be project_budget_group",
    )


@pytest.mark.activity
@pytest.mark.api
def test_project_budget_deleted_audit_record_stored(
    activity_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    activity_project,
):
    """TC-015b: budget.project_budget.deleted audit record is stored."""
    admin_project_budget_utils.cleanup_active_budget_groups(activity_project)
    group_response = admin_project_budget_utils.create_budget_group(
        activity_project, name=f"autotest-pbdel-{secrets.token_hex(4)}"
    )
    group_id = group_response["group_id"]
    budget_id = admin_project_budget_utils.budget_ids_by_category(group_response)[
        "platform"
    ]
    admin_project_budget_utils.delete_budget_group(group_id)
    lite_llm_budget_utils.delete_key_by_alias(
        project_key_alias(activity_project, "platform")
    )

    response = activity_utils.list_activity_events(
        entity_id=budget_id,
        event_type=["budget.project_budget.deleted"],
        domain=["budget_management"],
    )

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one budget.project_budget.deleted event should exist",
    )
    record = response.data[0]
    assert_that(
        record.event_type,
        equal_to("budget.project_budget.deleted"),
        "event_type should be budget.project_budget.deleted",
    )
    assert_that(
        record.domain,
        equal_to("budget_management"),
        "domain should be budget_management",
    )


# ---------------------------------------------------------------------------
# TC-016: budget.project_budget.updated
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_project_budget_updated_audit_record_stored(
    activity_utils,
    admin_project_budget_utils,
    disposable_project_budget,
    activity_project,
):
    """TC-016: budget.project_budget.updated audit record is stored when budget is modified."""
    budget_id = disposable_project_budget

    group_id = admin_project_budget_utils.get_group_id_for_project(activity_project)
    admin_project_budget_utils.update_budget_group_category(
        group_id, "platform", soft_budget=60.0
    )

    response = activity_utils.list_activity_events(
        entity_id=budget_id,
        event_type=["budget.project_budget.updated"],
        domain=["budget_management"],
    )

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one budget.project_budget.updated event should exist",
    )
    record = response.data[0]
    assert_that(
        record.event_type,
        equal_to("budget.project_budget.updated"),
        "event_type should be budget.project_budget.updated",
    )
    assert_that(
        record.domain,
        equal_to("budget_management"),
        "domain should be budget_management",
    )


# ---------------------------------------------------------------------------
# TC-017: budget.project_budget.rebalanced
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_project_budget_rebalanced_audit_record_stored(
    activity_utils,
    admin_project_budget_utils,
    disposable_project_budget,
    activity_project,
):
    """TC-017: budget.project_budget.rebalanced audit record is stored when budget is reset."""
    budget_id = disposable_project_budget

    group_id = admin_project_budget_utils.get_group_id_for_project(activity_project)
    admin_project_budget_utils.rebalance_budget_group(group_id)

    response = activity_utils.list_activity_events(
        entity_id=budget_id,
        event_type=["budget.project_budget.rebalanced"],
        domain=["budget_management"],
    )

    assert_that(
        len(response.data),
        greater_than_or_equal_to(1),
        "At least one budget.project_budget.rebalanced event should exist",
    )
    record = response.data[0]
    assert_that(
        record.event_type,
        equal_to("budget.project_budget.rebalanced"),
        "event_type should be budget.project_budget.rebalanced",
    )
    assert_that(
        record.domain,
        equal_to("budget_management"),
        "domain should be budget_management",
    )


# ---------------------------------------------------------------------------
# TC-018: budget.member_allocation.overridden and budget.member_allocation.override_cleared
# ---------------------------------------------------------------------------


@pytest.mark.activity
@pytest.mark.api
def test_budget_member_allocation_overridden_and_cleared_audit_records_stored(
    activity_utils,
    admin_project_budget_utils,
    disposable_project_budget,
    project_utils,
    disposable_user,
    activity_project,
):
    """TC-018: budget.member_allocation.overridden and budget.member_allocation.override_cleared
    audit records are stored in sequence for project member budget allocation lifecycle."""
    budget_id = disposable_project_budget
    _, user_id, _ = disposable_user
    project_name = activity_project

    project_utils.assign_user_to_project(project_name, user_id, is_project_admin=False)
    admin_project_budget_utils.override_member(
        budget_id, user_id, allocated_max_budget=20.0, allocated_soft_budget=10.0
    )

    overridden_response = activity_utils.list_activity_events(
        entity_id=budget_id,
        event_type=["budget.member_allocation.overridden"],
        domain=["budget_management"],
    )

    assert_that(
        len(overridden_response.data),
        greater_than_or_equal_to(1),
        "At least one budget.member_allocation.overridden event should exist",
    )
    overridden_record = overridden_response.data[0]
    assert_that(
        overridden_record.event_type,
        equal_to("budget.member_allocation.overridden"),
        "event_type should be budget.member_allocation.overridden",
    )
    assert_that(
        overridden_record.domain,
        equal_to("budget_management"),
        "domain should be budget_management",
    )

    admin_project_budget_utils.clear_member_override(budget_id, user_id)

    cleared_response = activity_utils.list_activity_events(
        entity_id=budget_id,
        event_type=["budget.member_allocation.override_cleared"],
        domain=["budget_management"],
    )

    assert_that(
        len(cleared_response.data),
        greater_than_or_equal_to(1),
        "At least one budget.member_allocation.override_cleared event should exist",
    )
    cleared_record = cleared_response.data[0]
    assert_that(
        cleared_record.event_type,
        equal_to("budget.member_allocation.override_cleared"),
        "event_type should be budget.member_allocation.override_cleared",
    )
    assert_that(
        cleared_record.domain,
        equal_to("budget_management"),
        "domain should be budget_management",
    )

    project_utils.remove_user_from_project(project_name, user_id)
