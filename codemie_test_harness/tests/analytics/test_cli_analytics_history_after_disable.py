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

"""The project setting over time (plan TC-006 and TC-007).

TC-006 setting lifecycle: two projects stay independent while one is toggled, the change takes
effect at once in both directions, a batch discarded while disabled is not replayed after enabling
and an explicit resend of the same batch is processed.
TC-007 history after disable: the seeded session stays readable with unchanged permissions.

Every test owns its projects (fixtures in conftest) and uses fresh session ids, so it is parallel-safe
and a rerun never finds the previous attempt's data.

Evidence limits: the HTTP 200 body is the authoritative accept/discard evidence. Absence is "not
observed within the window" (ABSENCE_WINDOW_S, a bounded test heuristic and not an ingestion SLA,
no upper bound under a backlog); it counts only because the accepted control of the same shape
became visible. TC-007 uses positive waits only, no absence window. The SDK sender is checked by
its reply (dropped, reason). Row-level proof that a discard writes nothing is backend testing; the
AC-7 503 on a policy-lookup failure is not covered here.
"""

import time

import pytest
from hamcrest import assert_that, empty, equal_to, is_

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    DISABLED,
    E7,
    HISTORY_ROLES,
    HOOK_SENDERS,
    LIFECYCLE_SENDERS,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi
from codemie_test_harness.tests.utils.cli_gate_utils import (
    assert_sent_accepted,
    assert_sent_discarded,
    is_listed,
    observe_absence_window,
    send_tracked,
    snapshot_session_view,
    wait_until_listed,
)

pytestmark = [
    pytest.mark.api,
    pytest.mark.cli_analytics,
]


@pytest.mark.parametrize(("combo", "sender"), LIFECYCLE_SENDERS)
def test_setting_change_takes_effect_at_once_and_leaves_the_other_project_alone(
    lifecycle_projects, gate_member_client, combo, sender
):
    """TC-006 (AC-9, AC-10, AC-6): project X is toggled disabled, enabled, disabled while project
    Y stays enabled. Each batch is accepted or discarded according to the state at receipt, with
    no waiting; Y is accepted throughout."""
    x, y, admin = lifecycle_projects.x, lifecycle_projects.y, lifecycle_projects.admin
    member = gate_member_client

    assert_sent_accepted(
        send_tracked(member, x, combo, sender), "X enabled at the start"
    )
    assert_sent_accepted(send_tracked(member, y, combo, sender), "Y while X is enabled")

    admin.update_project(x, cli_analytics_enabled=False)
    assert_sent_discarded(
        send_tracked(member, x, combo, sender),
        DISABLED,
        "X right after it was disabled",
    )
    assert_sent_accepted(
        send_tracked(member, y, combo, sender), "Y while X is disabled"
    )

    admin.update_project(x, cli_analytics_enabled=True)
    assert_sent_accepted(
        send_tracked(member, x, combo, sender), "X right after it was enabled"
    )
    assert_sent_accepted(
        send_tracked(member, y, combo, sender), "Y while X is enabled again"
    )

    admin.update_project(x, cli_analytics_enabled=False)
    assert_sent_discarded(
        send_tracked(member, x, combo, sender),
        DISABLED,
        "X right after it was disabled again",
    )
    assert_sent_accepted(send_tracked(member, y, combo, sender), "Y at the end")


@pytest.mark.parametrize("sender", HOOK_SENDERS)
def test_batch_discarded_while_disabled_is_not_replayed_and_a_resend_is_listed(
    lifecycle_projects, gate_member_client, gate_admin_client, sender
):
    """TC-006 (AC-9, AC-6, AC-10): two batches discarded by the disabled project X stay absent
    after X is enabled again (observed over the absence window, with an accepted control of the
    same shape sent to Y after the enable); an explicit resend of the SAME first batch is then
    accepted and listed (positive wait), proving it was not dropped as a duplicate, while the
    second batch, not resent, stays absent."""
    x, y, admin = lifecycle_projects.x, lifecycle_projects.y, lifecycle_projects.admin
    member = gate_member_client
    api = CliAnalyticsApi(gate_admin_client)

    admin.update_project(x, cli_analytics_enabled=False)
    first = send_tracked(member, x, E7, sender)
    second = send_tracked(member, x, E7, sender)
    assert_sent_discarded(first, DISABLED, "first batch to the disabled X")
    assert_sent_discarded(second, DISABLED, "second batch to the disabled X")
    admin.update_project(x, cli_analytics_enabled=True)
    control = send_tracked(member, y, E7, sender)
    assert_sent_accepted(control, "control batch to the enabled Y")

    observe_absence_window(
        api,
        {control.batch.session_id: control.batch.repo},
        {
            "discarded while disabled": {
                first.batch.session_id: first.batch.repo,
                second.batch.session_id: second.batch.repo,
            }
        },
        time.monotonic(),
    )

    resent = send_tracked(member, x, E7, sender, batch=first.batch)
    assert_sent_accepted(resent, "explicit resend of the first batch to the enabled X")
    pending = wait_until_listed(api, {first.batch.session_id: first.batch.repo})
    assert_that(
        pending,
        empty(),
        "the resent batch was never listed (dropped as a duplicate of the discarded one?)",
    )
    assert_that(
        is_listed(api, second.batch.session_id, second.batch.repo),
        is_(False),
        "the second batch, which was not resent, is stored",
    )


@pytest.mark.parametrize(
    ("role_client", "expected_access"), HISTORY_ROLES, indirect=["role_client"]
)
def test_history_stays_accessible_with_unchanged_permissions_after_disable(
    history_session, role_client, gate_member_client, expected_access
):
    """TC-007 (AC-9): the session is seeded and waited for until listed. Per role, the starting
    state is asserted explicitly against the existing contract (the sessions, overview and
    repositories status codes and whether the session is listed: global admin, maintainer and the
    project admin read it with 200, a plain member, an auditor and an unrelated user are refused
    with 403, as the router's admin gate already did before this change), so an unexpected 403 for
    an authorized reader fails before the disable. The project is then disabled, the disable is
    shown to be effective (a new batch is discarded) and the snapshot (the same status codes,
    read with the filter projects=<name>, and the stable fields of the seeded session's row:
    identity, owner, repository, start, model, prompt and token counts) must be identical
    afterwards: disabling neither takes access away, nor grants any, nor drops the retained data.
    Rollup-derived fields (duration, cost, call counts) are left out on purpose; the drift the
    review suspected there was not reproduced."""
    world = history_session.world
    project, session_id, repo = (
        world.project,
        history_session.session_id,
        history_session.repo,
    )

    before = snapshot_session_view(role_client, project, session_id, repo)
    assert_that(
        {key: before[key] for key in expected_access},
        equal_to(expected_access),
        f"starting state: what this role reads is not the existing contract: {before}",
    )
    assert_that(
        (before["row"] or {}).get("trace_id"),
        equal_to(session_id if expected_access["listed"] else None),
        f"starting state: the row is the seeded session for a role that lists it: {before}",
    )

    world.admin_projects.update_project(project, cli_analytics_enabled=False)
    assert_sent_discarded(
        send_tracked(gate_member_client, project, E7),
        DISABLED,
        "a new batch right after the disable",
    )
    after = snapshot_session_view(role_client, project, session_id, repo)

    assert_that(
        after,
        equal_to(before),
        "disabling the project changed what this role reads",
    )
