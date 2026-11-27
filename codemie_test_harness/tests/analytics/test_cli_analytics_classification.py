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
depend on it or change it are not_for_parallel_run; the run sets it once (`classification_run`)
and puts it back at the end, and a test that changes it puts the run's list back.

The module's sessions are sent together when it starts (`classification_sessions`), so the wait
for the rollup is paid once. The Personal-session absence check (TC-003) is in
test_cli_analytics_unlisted_sessions.py.
"""

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
    assert_accepted,
)
from codemie_test_harness.tests.utils.cli_classification_utils import (
    LINKED,
    ORGANIZATION_ENCODING,
    assert_rejected,
    assert_session_discarded,
    expected_routing,
    further_event,
    listed_rows,
    listed_session_ids_with,
    new_session,
    read_policy,
    routing_of,
    send_evidence,
    session_rows,
    unique_organization,
    wait_for_cost_sessions,
    wait_for_session_row,
)


# ── TC-001: routed through CodeMie ──────────────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_001
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("case", ROUTED_CASES)
@pytest.mark.api
def test_session_routed_via_codemie_is_classified_codemie_whatever_the_organization(
    classification_world, classification_sessions, case
):
    """CodeMie routing precedes any Claude account: the routed header gives subscription_type
    codemie for an organization in the corporate list, one outside it and none at all."""
    world = classification_world
    sent = classification_sessions.routed[case]
    batch = sent.batch

    assert_accepted(sent.response, "event-hooks", CT_NDJSON)
    row = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project,
    )
    assert_that(
        routing_of(row),
        equal_to(expected_routing(CODEMIE, LINKED_FOLDER)),
        "a session routed through CodeMie must be classified codemie",
    )


# ── TC-002: organization matches the corporate list ─────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_002
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("spelling", ORGANIZATION_SPELLINGS)
@pytest.mark.api
def test_organization_matching_the_corporate_list_is_classified_corporate(
    classification_world, classification_sessions, organizations, spelling
):
    """The policy lists the configured organization, and the plain name, its upper-case spelling,
    its utf8-b64u.v1 encoding and the encoding of a padded upper-case spelling (a value the plain
    header cannot carry) all give subscription_type corporate."""
    world = classification_world
    sent = classification_sessions.spellings[spelling]
    batch = sent.batch

    policy = read_policy(world.sender.api)

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
    assert_accepted(sent.response, "event-hooks", CT_NDJSON)
    row = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project,
    )
    assert_that(
        routing_of(row),
        equal_to(expected_routing(CORPORATE, LINKED_FOLDER)),
        "an organization in the corporate list must be classified corporate",
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
        equal_to(expected_routing(UNKNOWN, LINKED_FOLDER)),
        "an empty corporate list must give an Unknown session in the linked work project",
    )


# @case classify-cli-sessions-by-subscription_TC_011
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_session_without_an_organization_is_unknown_even_with_a_corporate_list(
    classification_world, classification_sessions
):
    """A missing organization is Unknown, never Personal, whatever the corporate list holds, and
    the session follows the same work-project routing as a Corporate one."""
    world = classification_world
    sent = classification_sessions.without_organization
    batch = sent.batch

    assert_accepted(sent.response, "event-hooks", CT_NDJSON)
    row = wait_for_session_row(
        world.admin_api,
        batch.session_id,
        batch.repo,
        projects=world.project,
    )
    assert_that(
        routing_of(row),
        equal_to(expected_routing(UNKNOWN, LINKED_FOLDER)),
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
    classification_world, classification_sessions
):
    """Session rows carry subscription_type and project_origin, the two comma-separated filters
    return exactly the matching sessions (a Personal one only in the owner's personal_only list),
    and the cost view lists the distinct types and origins of the selected sessions. The sessions
    were sent and listed when the module started (`classification_sessions`)."""
    world, admin_api = classification_world.filters, classification_world.admin_api
    sender, sent = world.sender, classification_sessions.filtered
    linked, profile = sent["linked"].batch, sent["profile"].batch
    registered, default = sent["registered"].batch, sent["default"].batch
    personal = sent["personal"].batch
    shared_scope = {
        "users": sender.email,
        "projects": f"{world.default},{world.registered}",
    }
    expected = {
        linked.session_id: (CORPORATE, LINKED_FOLDER),
        profile.session_id: (CODEMIE, PROFILE),
        registered.session_id: (UNKNOWN, REGISTERED_REPOSITORY),
        default.session_id: (CORPORATE, DEFAULT_PROJECT),
    }

    for session in sent.values():
        assert_accepted(session.response, "event-hooks", CT_NDJSON)
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
    own = listed_rows(sender.api, personal_only="true", project_origin="personal")
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
    classification_world, classification_sessions, organizations, corporate_list
):
    """After the list changes so the organization no longer matches, a further event of a session
    bound to a shared project is discarded with session_project_conflict: its history stays
    Corporate, nothing is copied into a personal project, and a new session is classified
    under the current rules. The bound session was sent under the run's list when the module
    started (`classification_sessions`)."""
    world = classification_world
    organization = organizations.corporate
    sent = classification_sessions.corporate_bound
    first_policy = classification_sessions.corporate_policy
    batch = sent.batch
    assert_accepted(sent.response, "event-hooks", CT_NDJSON)
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
        session_rows(
            world.sender.api, batch.session_id, batch.repo, personal_only="true"
        ),
        empty(),
        "no private copy of the shared session may appear for the owner",
    )
    fresh = new_session()
    assert_accepted(
        send_evidence(world.sender.client, fresh, organization=organization),
        "event-hooks",
        CT_NDJSON,
    )
    fresh_row = wait_for_session_row(
        world.sender.api, fresh.session_id, fresh.repo, personal_only="true"
    )
    assert_that(
        routing_of(fresh_row),
        equal_to(expected_routing(PERSONAL, PERSONAL)),
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
    classification_world, classification_sessions, envelope
):
    """A printable encoded organization of exactly 256 code points (and, for four-byte code
    points, exactly 1024 bytes and 1366 payload characters) is not refused: it is decoded,
    does not match the corporate list and so is stored as the owner's Personal session."""
    world = classification_world
    sent = classification_sessions.at_the_limit[envelope]
    batch = sent.batch

    assert_accepted(sent.response, "event-hooks", CT_NDJSON)
    owned = wait_for_session_row(
        world.sender.api, batch.session_id, batch.repo, personal_only="true"
    )
    assert_that(
        routing_of(owned),
        equal_to(expected_routing(PERSONAL, PERSONAL)),
        "a name at the size limits must be accepted and classified personal",
    )
