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

The accounts are built from `AccountSpec` rows by `Provisioner.account`, several at the same
time. The run-wide account world (`account_world`) holds the shared project, an account of each
kind and the external users and service account of TC-004; the corporate list is the run's
(`classification_run`). The account checks that need an absence window are in
test_cli_analytics_unlisted_sessions.py.
"""

import pytest
from hamcrest import assert_that, empty, equal_to, has_length

from codemie_test_harness.tests.test_data.cli_account_test_data import (
    LISTS_OWN_SHARED,
    LISTS_PROJECT_SESSIONS,
    READ_ROWS,
    REGISTRATION_RIGHTS_ROWS,
    WORK_PROJECT_SENDER_KINDS,
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
    detail_status,
    LINKED,
    REPOSITORIES_PATH,
    assert_rejected,
    expected_routing,
    listed_session_ids_with,
    new_remote,
    new_session,
    repository_key,
    repository_keys,
    routing_of,
    send_evidence,
    session_rows,
    wait_for_session_row,
)

# Kinds that read only the shared sessions they sent themselves.
SHARED_ORIGIN_PERSONAL = expected_routing(PERSONAL, LINKED_FOLDER)


# ── TC-027: reading by account kind ─────────────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_027
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("row", READ_ROWS)
@pytest.mark.api
def test_reading_cli_analytics_follows_the_account_kind(
    account_world, account_sessions, row
):
    """Every kind reads the aggregates; the shared sessions list and the shared-session detail
    give the project's sessions to those allowed to read the project and otherwise only the
    account's own; another user's private Personal session is never in the shared list, and only
    a global admin, a maintainer and an auditor open it or find it in the personal_only list."""
    world, sessions = account_world, account_sessions
    api = world.api(row.account)
    shared_ids = {sent.batch.session_id for sent in sessions.shared}
    expected_listing = {
        LISTS_PROJECT_SESSIONS: shared_ids,
        LISTS_OWN_SHARED: sessions.shared_sent_by(row.account),
    }[row.listing]
    private = sessions.private.batch
    # other tests of this module store sessions of their own in the project, so the listing is
    # compared on the sessions the module world sent
    world_session_ids = {
        sent.batch.session_id
        for sent in (*sessions.shared, sessions.private, *sessions.personal.values())
    }

    aggregate = api.request("GET", COST_PATH, params={"projects": world.project})
    listed = listed_session_ids_with(api, projects=world.project)
    shared_details = {
        sent.batch.session_id: detail_status(api, sent.batch.session_id)
        for sent in sessions.shared
    }
    private_detail = detail_status(api, sessions.private.batch.session_id)
    private_listed = session_rows(api, private.session_id, private.repo)
    private_listed_as_own = session_rows(
        api, private.session_id, private.repo, personal_only="true"
    )

    assert_that(
        aggregate.status_code,
        equal_to(200),
        f"every account kind reads the aggregates: {aggregate.text[:200]}",
    )
    assert_that(
        listed & world_session_ids,
        equal_to(expected_listing),
        "sessions of the module world listed for the project",
    )
    assert_that(
        shared_details,
        equal_to(
            {session_id: 200 for session_id in expected_listing}
            | {session_id: 404 for session_id in shared_ids - expected_listing}
        ),
        "the detail of a shared-project session opens exactly for the sessions listed",
    )
    assert_that(
        private_detail,
        equal_to(row.private_detail_status),
        "detail of another user's private session",
    )
    assert_that(
        private_listed, empty(), "another user's private session in the shared list"
    )
    assert_that(
        private_listed_as_own,
        has_length(row.private_rows_as_own),
        "another user's private session in the personal_only list",
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
    path = REPOSITORIES_PATH.format(project=world.project)
    existing, attempted = new_remote(), new_remote()
    world.provisioner.register(world.project, existing)

    registered = api.request("PUT", path, json={"remote": attempted})
    listed = api.request("GET", path)
    unregistered = api.request("DELETE", path, json={"remote": existing})
    stored = world.admin_api.request("GET", path)

    assert_that(
        [registered.status_code, listed.status_code, unregistered.status_code],
        equal_to([row.status] * 3),
        f"register, list and unregister: {registered.text[:100]} {unregistered.text[:100]}",
    )
    keys = repository_keys(stored)
    assert_that(
        (repository_key(existing) in keys, repository_key(attempted) in keys),
        equal_to((not row.allowed, row.allowed)),
        "the registrations left behind must be those the allowed calls made",
    )


# ── TC-004: external users and service accounts ─────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_004
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("spec", specs_named(*WORK_PROJECT_SENDER_KINDS))
@pytest.mark.api
def test_personal_session_of_an_external_user_or_service_account_is_stored_in_a_work_project(
    account_world, account_sessions, spec
):
    """A non-matching organization makes the session Personal. For a user type that cannot have a
    personal project it is stored in the linked work project with a shared origin (never
    personal), the admin reads it under the project rights, and no personal project is created
    for a service account while an external user's old personal project stays unused."""
    world = account_world
    account = world.work_project_senders[spec.name]
    sent = account_sessions.work_project[spec.name]
    batch = sent.batch

    assert_accepted(sent.response, "event-hooks", CT_NDJSON)
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
        sorted(name.lower() for name in world.provisioner.project_names_of(account)),
        equal_to(spec.project_names(account.email, world.project)),
        "no personal project may be created for the account by sending the session",
    )


# @case classify-cli-sessions-by-subscription_TC_004
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_external_user_without_projects_is_retried_after_joining_a_work_project(
    account_world,
):
    """An external user with no project at all gets a retryable 503 default_project_unavailable
    for a Personal session (the link names a project it does not belong to); once it joins the
    work project the same session is accepted and stored there as personal with a shared origin."""
    world = account_world
    account = world.no_projects
    batch = new_session()
    evidence = dict(
        organization=world.organizations.other, project=world.project, **LINKED
    )

    before = send_evidence(account.client, batch, **evidence)
    world.provisioner.join(account, world.project)
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
        [name.lower() for name in world.provisioner.project_names_of(account)],
        equal_to([world.project.lower()]),
        "joining the work project must not create a personal project",
    )
