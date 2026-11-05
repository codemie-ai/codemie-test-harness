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

"""CLI session classification for the account kinds: external users and service accounts,
ordinary accounts with a global role or a project role, what each kind may read and what each
may register.

The accounts are built from `AccountSpec` rows by `Provisioner.account`. A module-scoped world
holds the shared project, the corporate list and the accounts the read and registration tests
share; the external users of TC-004 are built per test because they change during it.
"""

import time

import pytest
from hamcrest import assert_that, empty, equal_to

from codemie_test_harness.tests.test_data.cli_account_test_data import (
    EXTERNAL_FORMER_REGULAR,
    EXTERNAL_NO_PROJECTS,
    GLOBAL_ADMIN,
    LISTS_NOTHING,
    LISTS_OWN_PRIVATE,
    LISTS_PROJECT_SESSIONS,
    PERSONAL_SENDER_KINDS,
    READ_ROWS,
    REGISTRATION_ALLOWED_STATUS,
    REGISTRATION_REFUSED_STATUS,
    REGISTRATION_RIGHTS_ROWS,
    specs_named,
)
from codemie_test_harness.tests.test_data.cli_classification_test_data import (
    DEFAULT_PROJECT_UNAVAILABLE,
    LINKED_FOLDER,
    PERSONAL,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CT_NDJSON,
    assert_accepted,
)
from codemie_test_harness.tests.utils.cli_classification_utils import (
    COST_PATH,
    LINKED,
    SESSIONS_PATH,
    assert_rejected,
    expected_routing,
    listed_session_ids_with,
    new_remote,
    new_session,
    routing_of,
    send_evidence,
    session_rows,
    wait_for_session_row,
)
from codemie_test_harness.tests.utils.cli_gate_utils import observe_absence_window

OWN_SESSIONS_ONLY_KINDS = ("regular-member", "auditor")
REPOSITORIES = "/v1/projects/{project}/repositories"
SHARED_ORIGIN_PERSONAL = expected_routing(PERSONAL, LINKED_FOLDER)


def _detail_status(api, session) -> int:
    return api.request("GET", f"{SESSIONS_PATH}/{session.batch.session_id}").status_code


# ── TC-004: external users and service accounts ─────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_004
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize(
    "spec", specs_named("external-former-regular", "service-account")
)
@pytest.mark.api
def test_personal_session_of_an_external_user_or_service_account_is_stored_in_a_work_project(
    provisioner, account_world, spec
):
    """A non-matching organization makes the session Personal. For a user type that cannot have a
    personal project it is stored in the linked work project with a shared origin (never
    personal), the admin reads it under the project rights, and no personal project is created
    for a service account while an external user's old personal project stays unused."""
    world = account_world
    account = provisioner.account(spec, world.project)
    expected_projects = [world.project.lower()] + (
        [account.email.lower()] if spec.has_personal_project else []
    )
    batch = new_session()

    response = send_evidence(
        account.client,
        batch,
        organization=world.organizations.other,
        project=world.project,
        **LINKED,
    )

    assert_accepted(response, "event-hooks", CT_NDJSON)
    stored = wait_for_session_row(
        world.admin_api, batch.session_id, batch.repo, projects=world.project
    )
    assert_that(
        routing_of(stored),
        equal_to(SHARED_ORIGIN_PERSONAL),
        "a Personal session of this account must be stored in the linked work project as personal "
        "with a shared origin",
    )
    assert_that(
        sorted(name.lower() for name in provisioner.project_names_of(account)),
        equal_to(sorted(expected_projects)),
        "no personal project may be created for the account by sending the session",
    )


# @case classify-cli-sessions-by-subscription_TC_004
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_external_user_without_projects_is_retried_after_joining_a_work_project(
    provisioner, account_world
):
    """An external user with no project at all gets a retryable 503 default_project_unavailable
    for a Personal session (the link names a project it does not belong to); once it joins the
    work project the same session is accepted and stored there as personal with a shared origin."""
    world = account_world
    account = provisioner.account(EXTERNAL_NO_PROJECTS)
    batch = new_session()
    evidence = dict(
        organization=world.organizations.other, project=world.project, **LINKED
    )

    before = send_evidence(account.client, batch, **evidence)
    provisioner.join(account, world.project)
    after = send_evidence(account.client, batch, **evidence)

    assert_rejected(before, 503, DEFAULT_PROJECT_UNAVAILABLE)
    assert_accepted(after, "event-hooks", CT_NDJSON)
    stored = wait_for_session_row(
        world.admin_api, batch.session_id, batch.repo, projects=world.project
    )
    assert_that(
        routing_of(stored),
        equal_to(SHARED_ORIGIN_PERSONAL),
        "the retried session must be stored in the work project as personal with a shared origin",
    )
    assert_that(
        [name.lower() for name in provisioner.project_names_of(account)],
        equal_to([world.project.lower()]),
        "joining the work project must not create a personal project",
    )


# @case classify-cli-sessions-by-subscription_TC_004
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_old_personal_project_of_an_external_user_never_receives_a_session(
    provisioner, account_world, account_sessions
):
    """An external user who was regular at its first login has its old personal project as the
    default project, and that project is never a destination: a session without a link gets a
    retryable 503 default_project_unavailable and is stored nowhere, while a control session
    of the project is listed."""
    world = account_world
    account = provisioner.account(EXTERNAL_FORMER_REGULAR, world.project)
    batch = new_session()

    response = send_evidence(
        account.client, batch, organization=world.organizations.other
    )

    assert_rejected(response, 503, DEFAULT_PROJECT_UNAVAILABLE)
    observe_absence_window(
        world.admin_api,
        {
            account_sessions.corporate.batch.session_id: account_sessions.corporate.batch.repo
        },
        {
            "session sent with the old personal project as default": {
                batch.session_id: batch.repo
            }
        },
        time.monotonic(),
    )


# ── TC-026: Personal sessions of the ordinary account kinds ─────────────────────


def _markers_for(sessions, reader: str) -> dict:
    """A session the reader must see: its own private one when it reads its own sessions only,
    otherwise the Corporate session of the shared project."""
    sent = (
        sessions.personal[reader]
        if reader in OWN_SESSIONS_ONLY_KINDS
        else sessions.corporate
    )
    return {sent.batch.session_id: sent.batch.repo}


def _observe_private_session_absent(world, sessions, owner_kind: str, readers) -> None:
    """None of the readers lists the private session of `owner_kind` within the absence window,
    while each of them lists a session of its own that proves the listing works."""
    sent = sessions.personal[owner_kind]
    for reader in readers:
        observe_absence_window(
            world.api(reader),
            _markers_for(sessions, reader),
            {
                f"private session of the {owner_kind} account": {
                    sent.batch.session_id: sent.batch.repo
                }
            },
            sessions.sent_at,
        )


# @case classify-cli-sessions-by-subscription_TC_026
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("spec", specs_named(*PERSONAL_SENDER_KINDS))
@pytest.mark.api
def test_personal_session_of_an_ordinary_account_stays_in_its_personal_project_and_private(
    account_world, account_sessions, spec
):
    """A Personal session sent with a link to the shared project is stored in the owner's personal
    project whatever the account's role (member, project admin, maintainer, auditor); the owner
    reads it, and neither the other kinds nor the global admin list it or open its detail."""
    world, sessions = account_world, account_sessions
    sent = sessions.personal[spec.name]
    owner = world.accounts[spec.name]
    readers = [
        kind for kind in (*PERSONAL_SENDER_KINDS, GLOBAL_ADMIN) if kind != spec.name
    ]

    owned = wait_for_session_row(
        owner.api, sent.batch.session_id, sent.batch.repo, personal_only="true"
    )
    details = {kind: _detail_status(world.api(kind), sent) for kind in readers}
    _observe_private_session_absent(world, sessions, spec.name, readers)

    assert_accepted(sent.response, "event-hooks", CT_NDJSON)
    assert_that(
        routing_of(owned),
        equal_to(expected_routing(PERSONAL, PERSONAL)),
        "the owner must read the session as personal in its personal project",
    )
    assert_that(
        _detail_status(owner.api, sent),
        equal_to(200),
        "the owner must open the detail of its own private session",
    )
    assert_that(
        details,
        equal_to({kind: 404 for kind in readers}),
        "no other account may open the detail of a private Personal session",
    )


# ── TC-027: reading by account kind ─────────────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_027
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("row", READ_ROWS)
@pytest.mark.api
def test_reading_cli_analytics_follows_the_account_kind(
    account_world, account_sessions, row
):
    """Aggregates need the shared-project read gate; the sessions list returns the shared sessions
    only to those allowed to read the project and otherwise the account's own private sessions;
    the private Personal session of another user is never listed and its detail is 404 for every
    kind, including maintainer, auditor and the global admin."""
    world, sessions = account_world, account_sessions
    api = world.api(row.account)
    shared = [sessions.corporate, sessions.service]
    own_private = {
        sent.batch.session_id
        for kind, sent in sessions.personal.items()
        if kind == row.account
    }
    expected_listing = {
        LISTS_PROJECT_SESSIONS: {sent.batch.session_id for sent in shared},
        LISTS_OWN_PRIVATE: own_private,
        LISTS_NOTHING: set(),
    }[row.listing]
    private = sessions.private.batch
    # other tests of this module store sessions of their own in the project, so the listing is
    # compared on the sessions the module world sent
    world_session_ids = {
        sent.batch.session_id
        for sent in (*shared, sessions.private, *sessions.personal.values())
    }

    aggregate = api.request("GET", COST_PATH, params={"projects": world.project})
    listed = listed_session_ids_with(api, projects=world.project)
    shared_details = [_detail_status(api, sent) for sent in shared]
    private_detail = _detail_status(api, sessions.private)
    private_listed = session_rows(api, private.session_id, private.repo)
    private_listed_as_own = session_rows(
        api, private.session_id, private.repo, personal_only="true"
    )

    assert_that(
        aggregate.status_code,
        equal_to(row.aggregate_status),
        f"aggregate read gate: {aggregate.text[:200]}",
    )
    assert_that(
        listed & world_session_ids,
        equal_to(expected_listing),
        "sessions of the module world listed for the project",
    )
    assert_that(
        shared_details,
        equal_to([row.shared_detail_status] * len(shared)),
        "detail of the shared-project sessions",
    )
    assert_that(
        private_detail, equal_to(404), "detail of another user's private session"
    )
    assert_that(private_listed, empty(), "another user's private session in the list")
    assert_that(
        private_listed_as_own,
        empty(),
        "another user's private session in the own-sessions list",
    )


# ── TC-028: repository registration rights ──────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_028
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("row", REGISTRATION_RIGHTS_ROWS)
@pytest.mark.api
def test_repository_registration_is_allowed_to_admins_and_refused_to_other_kinds(
    account_world, row
):
    """Maintainers and the project's own admin register, list and unregister repositories of the
    project; every other kind gets 404 on all three calls, and its write leaves the registrations
    exactly as they were."""
    world = account_world
    api = world.accounts[row.account].api
    path = REPOSITORIES.format(project=world.project)
    existing, attempted = new_remote(), new_remote()
    world.provisioner.register(world.project, existing)

    registered = api.request("PUT", path, json={"remote": attempted})
    listed = api.request("GET", path)
    unregistered = api.request("DELETE", path, json={"remote": existing})
    stored = world.admin_api.request("GET", path)

    status = REGISTRATION_ALLOWED_STATUS if row.allowed else REGISTRATION_REFUSED_STATUS
    assert_that(
        [registered.status_code, listed.status_code, unregistered.status_code],
        equal_to([status] * 3),
        f"register, list and unregister: {registered.text[:100]} {unregistered.text[:100]}",
    )
    keys = _keys_of(stored)
    assert_that(
        (_key_of(existing) in keys, _key_of(attempted) in keys),
        equal_to((not row.allowed, row.allowed)),
        "the registrations left behind must be those the allowed calls made",
    )


def _key_of(remote: str) -> str:
    return remote.removeprefix("https://").removesuffix(".git")


def _keys_of(response) -> list:
    return [item["key"] for item in response.json()]
