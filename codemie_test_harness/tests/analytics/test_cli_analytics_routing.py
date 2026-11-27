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

"""CLI session routing: which project a classified session is stored in, session ownership, and
what happens to a session whose destination is lost or missing.

The stored project is proven by listing the session as an admin with `projects=<name>`; the
origin and the route note are read from the same row.

The module's sessions are sent together when it starts (`routing_sessions`, `routing_world`), so
the wait for the rollup is paid once. The absence check of TC-015 is in
test_cli_analytics_unlisted_sessions.py.
"""

import pytest
from hamcrest import assert_that, empty, equal_to, equal_to_ignoring_case

from codemie_test_harness.tests.test_data.cli_classification_test_data import (
    CORPORATE,
    DEFAULT_PROJECT,
    EVIDENCE_SESSION_CONFLICT,
    FOLDER_NOT_LINKED,
    FOLDER_NOT_LINKED_LABEL,
    PERSONAL,
    PLACEMENT_ROWS,
    PROFILE_ROWS,
    SESSION_ID_REQUIRED,
    SESSION_OWNER_CONFLICT,
    SESSION_PROJECT_UNAVAILABLE,
    UNKNOWN,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CT_NDJSON,
    assert_accepted,
)
from codemie_test_harness.tests.utils.cli_classification_utils import (
    LINKED,
    assert_rejected,
    assert_session_discarded,
    evidence_headers,
    expected_routing,
    further_event,
    listed_session_ids_with,
    mixed_session_batch,
    new_remote,
    new_session,
    post_until_discarded,
    routing_of,
    send_evidence,
    send_with_headers,
    session_rows,
    stable_projection,
    wait_for_session_row,
)

# ── TC-005: destination order and accessibility ─────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_005
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("row", PLACEMENT_ROWS)
@pytest.mark.api
def test_destination_follows_link_then_registration_then_default(
    routing_world, routing_sessions, row
):
    """A Corporate, CodeMie or Unknown session goes to the accessible linked project, then to the
    accessible registered repository, then to the default project; an inaccessible link or
    registration is skipped and, when the default is used, noted in route_note."""
    world = routing_world
    sent = routing_sessions.placement[row]
    batch = sent.batch

    assert_accepted(sent.response, "event-hooks", CT_NDJSON)
    stored = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project(row.project),
    )
    assert_that(
        routing_of(stored),
        equal_to(expected_routing(row.subscription, row.origin, row.note)),
        f"the session must be stored in project {row.project} with this classification and note",
    )


# ── TC-007: unlinked native session ─────────────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_007
@pytest.mark.cli_analytics
@pytest.mark.api
def test_unlinked_session_goes_to_the_default_project_and_is_marked(routing_world):
    """With no link and an unregistered repository the session is stored in the user's effective
    default project with origin default_project, the note folder_not_linked and its label."""
    world = routing_world
    batch = new_session()

    response = send_evidence(world.sender.client, batch, repo_remote=new_remote())

    assert_accepted(response, "event-hooks", CT_NDJSON)
    stored = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project("D"),
    )
    assert_that(
        (routing_of(stored), stored["routing_label"]),
        equal_to(
            (
                expected_routing(UNKNOWN, DEFAULT_PROJECT, FOLDER_NOT_LINKED),
                FOLDER_NOT_LINKED_LABEL,
            )
        ),
        "an unlinked session must be marked as routed to the default project",
    )


# ── TC-009: profile project of a managed launch ─────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_009
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("row", PROFILE_ROWS)
@pytest.mark.api
def test_profile_project_wins_for_a_corporate_managed_launch(
    routing_world, routing_sessions, row
):
    """The project of the selected launch profile (project source profile) beats the registered
    repository; without one the registration applies, then the default project."""
    world = routing_world
    sent = routing_sessions.profile[row]
    batch = sent.batch

    assert_accepted(sent.response, "event-hooks", CT_NDJSON)
    stored = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project(row.project),
    )
    assert_that(
        routing_of(stored),
        equal_to(expected_routing(CORPORATE, row.origin, row.note)),
        f"the session must be stored in project {row.project} with this origin and note",
    )


# @case classify-cli-sessions-by-subscription_TC_009
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_personal_session_of_an_ordinary_user_ignores_the_profile_project(
    routing_world, routing_sessions
):
    """An ordinary user's Personal session goes to the owner's personal project even when the
    profile names a shared project: the owner lists it with origin personal in its personal_only
    list and the shared project's listing does not hold it."""
    world = routing_world
    sent = routing_sessions.personal
    batch = sent.batch

    assert_accepted(sent.response, "event-hooks", CT_NDJSON)
    owned = wait_for_session_row(
        world.sender.api, batch.session_id, batch.repo, personal_only="true"
    )
    assert_that(
        routing_of(owned),
        equal_to(expected_routing(PERSONAL, PERSONAL)),
        "a Personal session must be stored in the owner's personal project",
    )
    assert_that(
        session_rows(
            world.admin_api, batch.session_id, batch.repo, projects=world.project("A")
        ),
        empty(),
        "the profile project must not hold the Personal session",
    )


# ── TC-018: the owner is the authenticated user ─────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_018
@pytest.mark.cli_analytics
@pytest.mark.api
def test_session_owner_is_the_authenticated_user_not_the_claude_account(
    routing_world,
):
    """The owner of a session is the user who sent it whatever organization the request names; a
    second member of the project that sends an event for that session is discarded with
    session_owner_conflict. The owner's session was sent with the module world."""
    conflict, admin_api = routing_world.owner_conflict, routing_world.admin_api
    owner, intruder, project = conflict.owner, conflict.intruder, conflict.project
    batch = conflict.sent.batch

    assert_accepted(conflict.sent.response, "event-hooks", CT_NDJSON)
    stored = wait_for_session_row(
        admin_api, batch.session_id, batch.repo, projects=project
    )
    assert_that(
        stored["user_email"],
        equal_to_ignoring_case(owner.email),
        "the session owner must be the authenticated sender",
    )
    intruder_response = send_evidence(
        intruder.client, batch, routed="1", project=project, **LINKED
    )
    assert_session_discarded(
        intruder_response, batch.wire_count, SESSION_OWNER_CONFLICT
    )


# ── TC-020: a bound session is not moved ────────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_020
@pytest.mark.cli_analytics
@pytest.mark.api
def test_bound_session_is_rejected_after_the_owner_loses_membership(
    user_utils, routing_world, bound_sessions
):
    """Once the owner is removed from the session's project, a further event is finally discarded
    with session_project_unavailable, the stored history is unchanged and the session is not
    moved to the owner's default project."""
    bound_session = bound_sessions["membership"]
    sender, project = bound_session.sender, bound_session.project
    batch, admin_api = bound_session.sent.batch, routing_world.admin_api
    user_utils.remove_user_from_project(sender.user_id, project)

    response = post_until_discarded(
        sender.client,
        further_event(batch),
        SESSION_PROJECT_UNAVAILABLE,
        routed="1",
        project=project,
        **LINKED,
    )

    assert_session_discarded(response, 1, SESSION_PROJECT_UNAVAILABLE)
    history = wait_for_session_row(
        admin_api, batch.session_id, batch.repo, projects=project
    )
    assert_that(
        stable_projection(history),
        equal_to(stable_projection(bound_session.history)),
        "the earlier history must stay as it was",
    )
    assert_that(
        listed_session_ids_with(admin_api, projects=bound_session.default),
        empty(),
        "the session must not be re-routed to the owner's default project",
    )


# @case classify-cli-sessions-by-subscription_TC_020
@pytest.mark.cli_analytics
@pytest.mark.api
def test_bound_session_is_rejected_after_its_project_is_deleted(
    module_provisioner, routing_world, bound_sessions
):
    """Once the session's project is deleted, a further event is finally discarded with
    session_project_unavailable and the session is not moved to the owner's default project."""
    bound_session = bound_sessions["project"]
    sender, project = bound_session.sender, bound_session.project
    batch, admin_api = bound_session.sent.batch, routing_world.admin_api
    module_provisioner.delete_project(project)

    response = post_until_discarded(
        sender.client,
        further_event(batch),
        SESSION_PROJECT_UNAVAILABLE,
        routed="1",
        project=project,
        **LINKED,
    )

    assert_session_discarded(response, 1, SESSION_PROJECT_UNAVAILABLE)
    assert_that(
        listed_session_ids_with(admin_api, projects=bound_session.default),
        empty(),
        "the session must not be re-routed to the owner's default project",
    )


# ── TC-023: the evidence session boundary ───────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_023
@pytest.mark.cli_analytics
@pytest.mark.api
def test_evidence_request_without_a_session_id_is_400_session_id_required(
    classification_world,
):
    """A request that carries classification headers but no X-CodeMie-Session-Id is refused with
    400 session_id_required."""
    world = classification_world
    batch = new_session()

    response = send_with_headers(
        world.sender.client,
        batch.body,
        evidence_headers(None, routed="1", project=world.project, **LINKED),
    )

    assert_rejected(response, 400, SESSION_ID_REQUIRED)


# @case classify-cli-sessions-by-subscription_TC_023
@pytest.mark.cli_analytics
@pytest.mark.api
def test_batch_mixing_two_sessions_is_discarded_with_evidence_session_conflict(
    classification_world,
):
    """A batch that holds the events of another session next to the declared one is discarded
    whole, naming one other session."""
    world = classification_world
    mixed = mixed_session_batch()

    response = send_evidence(
        world.sender.client, mixed, routed="1", project=world.project, **LINKED
    )

    assert_session_discarded(
        response, mixed.wire_count, EVIDENCE_SESSION_CONFLICT, other_sessions=1
    )
