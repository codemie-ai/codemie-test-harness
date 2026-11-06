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

"""CLI session classification: how an ingest request is classified as CodeMie, Corporate,
Personal or Unknown, what a Personal session exposes, and the classification header contract.

A session is read back through the sessions list: an admin lists the shared (work-project)
sessions, `projects=<name>` proves the stored project; only the owner lists their own Personal
sessions. The corporate organization list is shared stand configuration, so the tests that
change it are not_for_parallel_run and put it back in the fixture teardown.
"""

import time

import pytest
from hamcrest import assert_that, empty, equal_to, has_item, is_not

from codemie_test_harness.tests.test_data.cli_classification_test_data import (
    CLAIMED_TYPES_NEEDING_ORGANIZATION,
    CODEMIE,
    CORPORATE,
    DEFAULT_PROJECT,
    INVALID_ORGANIZATION_ENVELOPES,
    LINKED_FOLDER,
    ORGANIZATION_ENVELOPES_AT_THE_LIMIT,
    ORGANIZATION_INVALID,
    ORGANIZATION_REQUIRED,
    ORGANIZATION_SPELLINGS,
    PERSONAL,
    PROFILE,
    REGISTERED_REPOSITORY,
    ROUTED_CASES,
    SESSION_PROJECT_CONFLICT,
    STALE_POLICY,
    UNKNOWN,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CT_NDJSON,
    CliAnalyticsApi,
    assert_accepted,
)
from codemie_test_harness.tests.utils.cli_classification_utils import (
    ORGANIZATION_ENCODING,
    assert_rejected,
    assert_session_discarded,
    further_event,
    listed_rows,
    listed_session_ids_with,
    new_remote,
    new_session,
    read_policy,
    routing_of,
    send_evidence,
    session_rows,
    unique_organization,
    wait_for_cost_sessions,
    wait_for_session_row,
)
from codemie_test_harness.tests.utils.cli_gate_utils import (
    SESSION_PREFIX,
    observe_absence_window,
)

LINKED = {"project_source": "linked_folder"}


def _routing(subscription_type, project_origin, route_note=None):
    return {
        "subscription_type": subscription_type,
        "project_origin": project_origin,
        "route_note": route_note,
    }


# ── TC-001: routed through CodeMie ──────────────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_001
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("case", ROUTED_CASES)
@pytest.mark.api
def test_session_routed_via_codemie_is_classified_codemie_whatever_the_organization(
    classification_world, organizations, case
):
    """CodeMie routing precedes any Claude account: the routed header gives subscription_type
    codemie for an organization in the corporate list, one outside it and none at all."""
    world = classification_world
    batch = new_session()

    response = send_evidence(
        world.sender.client,
        batch,
        routed=case.routed_value,
        organization=organizations.pick(case.organization),
        project=world.project,
        **LINKED,
    )

    assert_accepted(response, "event-hooks", CT_NDJSON)
    row = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project,
    )
    assert_that(
        routing_of(row),
        equal_to(_routing(CODEMIE, LINKED_FOLDER)),
        "a session routed through CodeMie must be classified codemie",
    )


# ── TC-002: organization matches the corporate list ─────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_002
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("spelling", ORGANIZATION_SPELLINGS)
@pytest.mark.api
def test_organization_matching_the_corporate_list_is_classified_corporate(
    classification_world, organizations, spelling
):
    """The policy lists the configured organization, and the plain name, its upper-case spelling,
    its utf8-b64u.v1 encoding and the encoding of a padded upper-case spelling (a value the plain
    header cannot carry) all give subscription_type corporate."""
    world = classification_world
    policy = read_policy(world.sender.api)
    batch = new_session()

    response = send_evidence(
        world.sender.client,
        batch,
        project=world.project,
        **LINKED,
        **spelling(organizations.corporate),
    )

    assert_that(
        policy["organizations"],
        equal_to([organizations.corporate]),
        "the classification policy must list the configured organization",
    )
    assert_that(
        policy["organization_encodings"],
        has_item(ORGANIZATION_ENCODING),
        "the policy must announce the encoded organization header",
    )
    assert_accepted(response, "event-hooks", CT_NDJSON)
    row = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project,
    )
    assert_that(
        routing_of(row),
        equal_to(_routing(CORPORATE, LINKED_FOLDER)),
        "an organization in the corporate list must be classified corporate",
    )


# ── TC-003: Personal session of an ordinary user ────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_003
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_non_matching_organization_is_personal_owner_only_and_outside_company_spend(
    provisioner, organizations, gate_admin_client
):
    """An ordinary user's session with an organization outside a non-empty corporate list is
    Personal: the owner lists it with origin personal, another user and an admin do not, and the
    admin's cost view counts only the owner's shared session, not the Personal one.
    Absence is 'not observed within the window' (observe_absence_window)."""
    owner, other = provisioner.sender(), provisioner.sender()
    shared = provisioner.project(owner, other)
    admin_api = CliAnalyticsApi(gate_admin_client)
    personal, shared_session = new_session(), new_session()
    others_personal = new_session()

    personal_response = send_evidence(
        owner.client, personal, organization=organizations.other
    )
    shared_response = send_evidence(
        owner.client, shared_session, routed="1", project=shared, **LINKED
    )
    others_response = send_evidence(
        other.client, others_personal, organization=organizations.other
    )

    for response in (personal_response, shared_response, others_response):
        assert_accepted(response, "event-hooks", CT_NDJSON)
    owner_row = wait_for_session_row(owner.api, personal.session_id, personal.repo)
    assert_that(
        routing_of(owner_row),
        equal_to(_routing(PERSONAL, PERSONAL)),
        "the owner must read the session as Personal in the personal project",
    )
    observe_absence_window(
        other.api,
        {others_personal.session_id: others_personal.repo},
        {
            "owner's Personal session seen by another user": {
                personal.session_id: personal.repo
            }
        },
        time.monotonic(),
    )
    assert_that(
        listed_session_ids_with(admin_api, search=SESSION_PREFIX),
        is_not(has_item(personal.session_id)),
        "an admin must not list another user's Personal session",
    )
    kpis = wait_for_cost_sessions(admin_api, 1, users=owner.email)
    assert_that(
        kpis["total_sessions"],
        equal_to(1),
        "the cost view must count the owner's shared session only, not the Personal one",
    )


# ── TC-011: Unknown is never Personal ───────────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_011
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_session_with_an_organization_but_an_empty_corporate_list_is_unknown(
    classification_world, corporate_list
):
    """With no corporate organization configured an organization cannot be judged: the session is
    Unknown, never Personal, and is routed to the work project like a Corporate one."""
    world = classification_world
    corporate_list([])
    batch = new_session()

    response = send_evidence(
        world.sender.client,
        batch,
        organization=unique_organization(),
        project=world.project,
        **LINKED,
    )

    assert_accepted(response, "event-hooks", CT_NDJSON)
    row = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project,
    )
    assert_that(
        routing_of(row),
        equal_to(_routing(UNKNOWN, LINKED_FOLDER)),
        "an empty corporate list must give an Unknown session in the linked work project",
    )


# @case classify-cli-sessions-by-subscription_TC_011
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_session_without_an_organization_is_unknown_even_with_a_corporate_list(
    classification_world, organizations
):
    """A missing organization is Unknown, never Personal, whatever the corporate list holds, and
    the session follows the same work-project routing as a Corporate one."""
    world = classification_world
    batch = new_session()

    response = send_evidence(
        world.sender.client, batch, project=world.project, **LINKED
    )

    assert_accepted(response, "event-hooks", CT_NDJSON)
    row = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project,
    )
    assert_that(
        routing_of(row),
        equal_to(_routing(UNKNOWN, LINKED_FOLDER)),
        "a missing organization must give an Unknown session in the linked work project",
    )


# @case classify-cli-sessions-by-subscription_TC_011
@pytest.mark.cli_analytics
@pytest.mark.parametrize("claimed_type", CLAIMED_TYPES_NEEDING_ORGANIZATION)
@pytest.mark.api
def test_claimed_personal_or_corporate_type_without_organization_is_rejected_with_400(
    classification_world, claimed_type
):
    """A client that claims Personal or Corporate but sends no organization lost the header on the
    way: the backend answers 400 organization_required instead of classifying Unknown."""
    world = classification_world

    response = send_evidence(
        world.sender.client,
        new_session(),
        claimed_type=claimed_type,
        project=world.project,
        **LINKED,
    )

    assert_rejected(response, 400, ORGANIZATION_REQUIRED)


# ── TC-013: stored and filterable ───────────────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_013
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_subscription_type_and_project_origin_are_stored_and_filterable(
    provisioner, organizations, gate_admin_client
):
    """Session rows carry subscription_type and project_origin, the two comma-separated filters
    return exactly the matching sessions (a Personal one to its owner only), and the cost view
    lists the distinct types and origins of the selected sessions."""
    admin_api = CliAnalyticsApi(gate_admin_client)
    sender = provisioner.sender()
    project_a, project_b = provisioner.project(sender), provisioner.project(sender)
    provisioner.set_default(sender, project_a)
    remote = new_remote()
    provisioner.register(project_b, remote)
    linked, profile, registered, default, personal = (new_session() for _ in range(5))
    shared_scope = {"users": sender.email, "projects": f"{project_a},{project_b}"}
    sent = [
        send_evidence(
            sender.client,
            linked,
            organization=organizations.corporate,
            project=project_a,
            **LINKED,
        ),
        send_evidence(
            sender.client,
            profile,
            routed="1",
            project=project_a,
            project_source="profile",
        ),
        send_evidence(sender.client, registered, repo_remote=remote),
        send_evidence(sender.client, default, organization=organizations.corporate),
        send_evidence(sender.client, personal, organization=organizations.other),
    ]
    expected = {
        linked.session_id: (CORPORATE, LINKED_FOLDER),
        profile.session_id: (CODEMIE, PROFILE),
        registered.session_id: (UNKNOWN, REGISTERED_REPOSITORY),
        default.session_id: (CORPORATE, DEFAULT_PROJECT),
    }

    for response in sent:
        assert_accepted(response, "event-hooks", CT_NDJSON)
    for batch in (linked, profile, registered, default):
        wait_for_session_row(admin_api, batch.session_id, batch.repo, **shared_scope)
    wait_for_session_row(sender.api, personal.session_id, personal.repo)

    rows = {
        row["trace_id"]: (row["subscription_type"], row["project_origin"])
        for row in listed_rows(admin_api, **shared_scope)
    }
    assert_that(
        rows,
        equal_to(expected),
        "every shared session row must carry its subscription_type and project_origin",
    )
    assert_that(
        listed_session_ids_with(
            admin_api, subscription_type="codemie,corporate", **shared_scope
        ),
        equal_to({linked.session_id, profile.session_id, default.session_id}),
        "the subscription_type filter must return the codemie and corporate sessions only",
    )
    assert_that(
        listed_session_ids_with(
            admin_api, project_origin="linked_folder,profile", **shared_scope
        ),
        equal_to({linked.session_id, profile.session_id}),
        "the project_origin filter must return the linked_folder and profile sessions only",
    )
    own = listed_rows(sender.api, project_origin="personal")
    assert_that(
        [(row["trace_id"], row["subscription_type"]) for row in own],
        equal_to([(personal.session_id, PERSONAL)]),
        "the owner's project_origin=personal listing must hold the Personal session only",
    )
    kpis = wait_for_cost_sessions(admin_api, 4, **shared_scope)
    assert_that(
        (kpis["subscription_types"], kpis["project_origins"]),
        equal_to(
            (
                [CODEMIE, CORPORATE, UNKNOWN],
                [DEFAULT_PROJECT, LINKED_FOLDER, PROFILE, REGISTERED_REPOSITORY],
            )
        ),
        "the cost view must list the distinct types and origins of the shared sessions",
    )


# ── TC-021: a later Personal classification never moves a shared-bound session ──


# @case classify-cli-sessions-by-subscription_TC_021
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_later_personal_classification_of_a_shared_bound_session_is_rejected(
    classification_world, corporate_list
):
    """After the list changes so the organization no longer matches, a further event of a session
    bound to a shared project is discarded with session_project_conflict: its history stays
    Corporate, nothing is copied into a personal project, and a new session is classified
    under the current rules."""
    world = classification_world
    organization = unique_organization()
    first_policy = corporate_list([organization])
    batch = new_session()
    assert_accepted(
        send_evidence(
            world.sender.client,
            batch,
            organization=organization,
            project=world.project,
            **LINKED,
        ),
        "event-hooks",
        CT_NDJSON,
    )
    bound = wait_for_session_row(
        world.admin_api, batch.session_id, batch.repo, projects=world.project
    )

    second_policy = corporate_list([unique_organization()])
    response = send_evidence(
        world.sender.client,
        further_event(batch),
        organization=organization,
        project=world.project,
        **LINKED,
    )

    assert_that(
        second_policy["version"],
        is_not(equal_to(first_policy["version"])),
        "changing the list must change the policy version",
    )
    assert_session_discarded(response, 1, SESSION_PROJECT_CONFLICT)
    after = wait_for_session_row(
        world.admin_api, batch.session_id, batch.repo, projects=world.project
    )
    assert_that(
        routing_of(after),
        equal_to(routing_of(bound)),
        "the shared session's classification must not be rewritten",
    )
    assert_that(
        session_rows(world.sender.api, batch.session_id, batch.repo),
        empty(),
        "no private copy of the shared session may appear for the owner",
    )
    fresh = new_session()
    assert_accepted(
        send_evidence(world.sender.client, fresh, organization=organization),
        "event-hooks",
        CT_NDJSON,
    )
    fresh_row = wait_for_session_row(world.sender.api, fresh.session_id, fresh.repo)
    assert_that(
        routing_of(fresh_row),
        equal_to(_routing(PERSONAL, PERSONAL)),
        "a new session must be classified under the current list",
    )


# ── TC-022: classification header validation ────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_022
@pytest.mark.cli_analytics
@pytest.mark.api
def test_stale_policy_version_with_a_differing_type_is_409(classification_world):
    """A client that states a classification and an out-of-date policy version, and whose
    classification differs from the derived one, gets 409 stale_policy with the current version."""
    world = classification_world
    policy = read_policy(world.sender.api)

    response = send_evidence(
        world.sender.client,
        new_session(),
        organization=unique_organization(),
        claimed_type="corporate",
        policy_version="out-of-date-policy",
        project=world.project,
        **LINKED,
    )

    assert_that(
        response.status_code,
        equal_to(409),
        f"{response.status_code}: {response.text[:200]}",
    )
    assert_that(
        response.json(),
        equal_to({"reason": STALE_POLICY, "policy_version": policy["version"]}),
        "the 409 body must name stale_policy and the current policy version",
    )


# @case classify-cli-sessions-by-subscription_TC_022
@pytest.mark.cli_analytics
@pytest.mark.parametrize("envelope", INVALID_ORGANIZATION_ENVELOPES)
@pytest.mark.api
def test_invalid_organization_envelope_is_400_organization_invalid(
    classification_world, envelope
):
    """A malformed, oversized, control-character or wrong-version encoded organization is refused
    with 400 organization_invalid before anything is classified or stored."""
    world = classification_world

    response = send_evidence(
        world.sender.client,
        new_session(),
        organization_encoded=envelope,
        project=world.project,
        **LINKED,
    )

    assert_rejected(response, 400, ORGANIZATION_INVALID)


# @case classify-cli-sessions-by-subscription_TC_022
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("envelope", ORGANIZATION_ENVELOPES_AT_THE_LIMIT)
@pytest.mark.api
def test_encoded_organization_at_the_size_limits_is_accepted_and_classified(
    classification_world, organizations, envelope
):
    """A printable encoded organization of exactly 256 code points (and, for four-byte code
    points, exactly 1024 bytes and 1366 payload characters) is not refused: it is decoded,
    does not match the corporate list and so is stored as the owner's Personal session."""
    world = classification_world
    batch = new_session()

    response = send_evidence(
        world.sender.client,
        batch,
        organization_encoded=envelope,
        project=world.project,
        **LINKED,
    )

    assert_accepted(response, "event-hooks", CT_NDJSON)
    owned = wait_for_session_row(world.sender.api, batch.session_id, batch.repo)
    assert_that(
        routing_of(owned),
        equal_to(_routing(PERSONAL, PERSONAL)),
        "a name at the size limits must be accepted and classified personal",
    )
