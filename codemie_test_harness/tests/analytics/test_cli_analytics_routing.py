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
"""

import time
from dataclasses import dataclass

import pytest
from hamcrest import assert_that, empty, equal_to, equal_to_ignoring_case

from codemie_test_harness.tests.test_data.cli_classification_test_data import (
    CORPORATE,
    DEFAULT_PROJECT,
    DEFAULT_PROJECT_UNAVAILABLE,
    EVIDENCE_SESSION_CONFLICT,
    FOLDER_NOT_LINKED,
    FOLDER_NOT_LINKED_LABEL,
    PERSONAL,
    PLACEMENT_ROWS,
    PROFILE_ROWS,
    REGISTERED_REPOSITORY,
    SESSION_ID_REQUIRED,
    SESSION_OWNER_CONFLICT,
    SESSION_PROJECT_UNAVAILABLE,
    UNKNOWN,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CT_NDJSON,
    CliAnalyticsApi,
    assert_accepted,
)
from codemie_test_harness.tests.utils.cli_classification_utils import (
    ClassifiedSender,
    assert_rejected,
    assert_session_discarded,
    cli_repo_key,
    evidence_headers,
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
from codemie_test_harness.tests.utils.cli_gate_utils import (
    Batch,
    observe_absence_window,
)

LINKED = {"project_source": "linked_folder"}
EXTERNAL_USER_TYPE = "external"


def _routing(subscription_type, project_origin, route_note=None):
    return {
        "subscription_type": subscription_type,
        "project_origin": project_origin,
        "route_note": route_note,
    }


def _classification(subscription, organizations):
    """The headers that make a session corporate, codemie or unknown."""
    return {
        "corporate": {"organization": organizations.corporate},
        "codemie": {"routed": "1"},
        "unknown": {},
    }[subscription]


# ── TC-005: destination order and accessibility ─────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_005
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("row", PLACEMENT_ROWS)
@pytest.mark.api
def test_destination_follows_link_then_registration_then_default(
    routing_world, organizations, row
):
    """A Corporate, CodeMie or Unknown session goes to the accessible linked project, then to the
    accessible registered repository, then to the default project; an inaccessible link or
    registration is skipped and, when the default is used, noted in route_note."""
    world = routing_world
    batch = new_session()
    link = world.project(row.link)

    response = send_evidence(
        world.sender.client,
        batch,
        project=link,
        project_source="linked_folder" if link else None,
        repo_remote=world.remote(row.registered),
        **_classification(row.subscription, organizations),
    )

    assert_accepted(response, "event-hooks", CT_NDJSON)
    stored = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project(row.project),
    )
    assert_that(
        routing_of(stored),
        equal_to(_routing(row.subscription, row.origin, row.note)),
        f"the session must be stored in project {row.project} with this classification and note",
    )


# @case classify-cli-sessions-by-subscription_TC_005
# @case classify-cli-sessions-by-subscription_TC_009
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize(
    "subscription",
    [
        pytest.param(UNKNOWN, id="native-unknown"),
        pytest.param(CORPORATE, id="managed-corporate"),
    ],
)
@pytest.mark.api
def test_repository_as_the_cli_sends_it_routes_to_the_registered_project(
    routing_world, organizations, subscription
):
    """The CLI names the repository as `host/path` (no scheme, no `.git`), not as the URL that was
    registered. A session with no project header and that repository must still be stored in the
    registered project (origin registered_repository, no route note), not in the default project."""
    world = routing_world
    batch = new_session()

    response = send_evidence(
        world.sender.client,
        batch,
        repo_remote=cli_repo_key(world.remote("B")),
        **_classification(subscription, organizations),
    )

    assert_accepted(response, "event-hooks", CT_NDJSON)
    stored = wait_for_session_row(world.admin_api, batch.session_id, batch.repo)
    assert_that(
        routing_of(stored),
        equal_to(_routing(subscription, REGISTERED_REPOSITORY)),
        "the session must be routed by the registered repository, not left to the default project",
    )
    assert_that(
        len(
            session_rows(
                world.admin_api,
                batch.session_id,
                batch.repo,
                projects=world.project("B"),
            )
        ),
        equal_to(1),
        "the session must be listed in the project the repository is registered to",
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
                _routing(UNKNOWN, DEFAULT_PROJECT, FOLDER_NOT_LINKED),
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
    routing_world, organizations, row
):
    """The project of the selected launch profile (project source profile) beats the registered
    repository; without one the registration applies, then the default project."""
    world = routing_world
    batch = new_session()
    profile_project = world.project(row.profile_project)

    response = send_evidence(
        world.sender.client,
        batch,
        organization=organizations.corporate,
        project=profile_project,
        project_source="profile" if profile_project else None,
        repo_remote=world.remote(row.registered),
    )

    assert_accepted(response, "event-hooks", CT_NDJSON)
    stored = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project(row.project),
    )
    assert_that(
        routing_of(stored),
        equal_to(_routing(CORPORATE, row.origin, row.note)),
        f"the session must be stored in project {row.project} with this origin and note",
    )


# @case classify-cli-sessions-by-subscription_TC_009
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_personal_session_of_an_ordinary_user_ignores_the_profile_project(
    routing_world, organizations
):
    """An ordinary user's Personal session goes to the owner's personal project even when the
    profile names a shared project: the owner lists it with origin personal and the shared
    project's listing does not hold it."""
    world = routing_world
    batch = new_session()

    response = send_evidence(
        world.sender.client,
        batch,
        organization=organizations.other,
        project=world.project("A"),
        project_source="profile",
        repo_remote=world.remote("B"),
    )

    assert_accepted(response, "event-hooks", CT_NDJSON)
    owned = wait_for_session_row(world.sender.api, batch.session_id, batch.repo)
    assert_that(
        routing_of(owned),
        equal_to(_routing(PERSONAL, PERSONAL)),
        "a Personal session must be stored in the owner's personal project",
    )
    assert_that(
        session_rows(
            world.admin_api, batch.session_id, batch.repo, projects=world.project("A")
        ),
        empty(),
        "the profile project must not hold the Personal session",
    )


# ── TC-015: no usable default project ───────────────────────────────────────────


@pytest.fixture
def stranded_sender(provisioner, user_utils):
    """A user whose only project is the personal project it can no longer receive sessions in.

    An administrator cannot detach a user from its personal project (the membership endpoint
    answers 403 for it), so the user is changed to the external user type instead: such a user
    never receives a new session in a personal project, and has no other project, so neither a
    link, a registration nor a default project is usable.
    """
    sender = provisioner.sender()
    for project_name in user_utils.get_user_project_names(sender.user_id):
        if project_name.lower() != sender.email.lower():
            user_utils.remove_user_from_project(sender.user_id, project_name)
    user_utils.update_admin_user(sender.user_id, user_type=EXTERNAL_USER_TYPE)
    assert_that(
        [name.lower() for name in user_utils.get_user_project_names(sender.user_id)],
        equal_to([sender.email.lower()]),
        "setup: the user must keep only its personal project, so it has no other default project",
    )
    assert_that(
        user_utils.get_admin_user(sender.user_id).user_type,
        equal_to(EXTERNAL_USER_TYPE),
        "setup: the user must be of the external type, which has no usable personal project",
    )
    return sender


# @case classify-cli-sessions-by-subscription_TC_015
@pytest.mark.cli_analytics
@pytest.mark.api
def test_session_without_any_usable_destination_is_a_retryable_503_and_stored_nowhere(
    provisioner, stranded_sender, gate_admin_client
):
    """A session of an external user (no personal project to receive it) with no link, no
    registration and no other project gets a retryable 503 default_project_unavailable, and no
    other project receives it: a control session of another user is listed, this one is never
    listed within the window."""
    admin_api = CliAnalyticsApi(gate_admin_client)
    member = provisioner.sender()
    reachable = provisioner.project(member)
    provisioner.set_default(member, reachable)
    stranded, control = new_session(), new_session()

    stranded_response = send_evidence(stranded_sender.client, stranded, routed="1")
    control_response = send_evidence(member.client, control, routed="1")

    assert_rejected(stranded_response, 503, DEFAULT_PROJECT_UNAVAILABLE)
    assert_accepted(control_response, "event-hooks", CT_NDJSON)
    observe_absence_window(
        admin_api,
        {control.session_id: control.repo},
        {"session without a destination": {stranded.session_id: stranded.repo}},
        time.monotonic(),
    )


# ── TC-018: the owner is the authenticated user ─────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_018
@pytest.mark.cli_analytics
@pytest.mark.api
def test_session_owner_is_the_authenticated_user_not_the_claude_account(
    provisioner, gate_admin_client
):
    """The owner of a session is the user who sent it whatever organization the request names; a
    second member of the project that sends an event for that session is discarded with
    session_owner_conflict."""
    admin_api = CliAnalyticsApi(gate_admin_client)
    owner, intruder = provisioner.sender(), provisioner.sender()
    project = provisioner.project(owner, intruder)
    batch = new_session()

    owner_response = send_evidence(
        owner.client,
        batch,
        routed="1",
        organization="unrelated-claude-account",
        project=project,
        **LINKED,
    )

    assert_accepted(owner_response, "event-hooks", CT_NDJSON)
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


@dataclass
class BoundSession:
    sender: ClassifiedSender
    project: str  # the project the session is bound to
    default: str  # the sender's default project
    batch: Batch
    admin_api: CliAnalyticsApi
    history: dict  # the session's row as first listed


@pytest.fixture
def bound_session(provisioner, gate_admin_client):
    """A session bound to a project; the sender also has another project, its default."""
    sender = provisioner.sender()
    project, default = provisioner.project(sender), provisioner.project(sender)
    provisioner.set_default(sender, default)
    batch = new_session()
    assert_accepted(
        send_evidence(sender.client, batch, routed="1", project=project, **LINKED),
        "event-hooks",
        CT_NDJSON,
    )
    admin_api = CliAnalyticsApi(gate_admin_client)
    history = wait_for_session_row(
        admin_api, batch.session_id, batch.repo, projects=project
    )
    return BoundSession(sender, project, default, batch, admin_api, history)


# @case classify-cli-sessions-by-subscription_TC_020
@pytest.mark.cli_analytics
@pytest.mark.api
def test_bound_session_is_rejected_after_the_owner_loses_membership(
    user_utils, bound_session
):
    """Once the owner is removed from the session's project, a further event is finally discarded
    with session_project_unavailable, the stored history is unchanged and the session is not
    moved to the owner's default project."""
    sender, project = bound_session.sender, bound_session.project
    batch, admin_api = bound_session.batch, bound_session.admin_api
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
    provisioner, bound_session
):
    """Once the session's project is deleted, a further event is finally discarded with
    session_project_unavailable and the session is not moved to the owner's default project."""
    sender, project = bound_session.sender, bound_session.project
    batch, admin_api = bound_session.batch, bound_session.admin_api
    provisioner.delete_project(project)

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
