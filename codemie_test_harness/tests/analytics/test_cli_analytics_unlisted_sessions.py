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

"""Sessions that must never be listed: the absence checks of the classification, routing and
account tests.

Absence is "not observed within the window" (observe_absence_window): ABSENCE_WINDOW_S measured
from the send. The sessions are sent when the run starts (`classification_run`, `stranded_probe`)
and this module is named to run after the other CLI analytics modules, so the windows pass while
those run instead of being waited out here. Run on its own it is still correct, only slower.
"""

import pytest
from hamcrest import assert_that, equal_to, has_item, is_not

from codemie_test_harness.tests.test_data.cli_account_test_data import (
    GLOBAL_ADMIN,
    PERSONAL_SENDER_KINDS,
    PRIVATE_DETAIL_STATUS,
    specs_named,
)
from codemie_test_harness.tests.test_data.cli_classification_test_data import (
    DEFAULT_PROJECT_UNAVAILABLE,
    PERSONAL,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CT_NDJSON,
    CliAnalyticsApi,
    assert_accepted,
)
from codemie_test_harness.tests.utils.cli_classification_utils import (
    assert_rejected,
    detail_status,
    expected_routing,
    listed_session_ids_with,
    routing_of,
    wait_for_cost_sessions,
    wait_for_session_row,
)
from codemie_test_harness.tests.utils.cli_gate_utils import (
    SESSION_PREFIX,
    observe_absence_window,
)

# Kinds that read only the shared sessions they sent themselves.
OWN_SESSIONS_ONLY_KINDS = ("regular-member",)


# ── TC-003: Personal session of an ordinary user ────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_003
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_non_matching_organization_is_personal_owner_only_and_outside_company_spend(
    classification_run, classification_admin_client
):
    """An ordinary user's session with an organization outside a non-empty corporate list is
    Personal: the owner lists it with origin personal in its personal_only list, another ordinary
    user does not, the shared list never holds it (not even an admin's), and the admin's cost
    view counts only the owner's shared session, not the Personal one.
    Absence is 'not observed within the window' (observe_absence_window); the sessions were sent
    when the run started (`classification_run`), so the window has passed by now."""
    probes = classification_run.probes
    owner, other = probes.owner, probes.other
    personal, others_personal = probes.personal.batch, probes.others_personal.batch
    admin_api = CliAnalyticsApi(classification_admin_client)

    for sent in (probes.personal, probes.shared, probes.others_personal):
        assert_accepted(sent.response, "event-hooks", CT_NDJSON)
    owner_row = wait_for_session_row(
        owner.api, personal.session_id, personal.repo, personal_only="true"
    )
    assert_that(
        routing_of(owner_row),
        equal_to(expected_routing(PERSONAL, PERSONAL)),
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
        probes.sent_at,
        filters={"personal_only": "true"},
    )
    assert_that(
        listed_session_ids_with(admin_api, search=SESSION_PREFIX),
        is_not(has_item(personal.session_id)),
        "the shared list must not hold a Personal session, not even an admin's",
    )
    kpis = wait_for_cost_sessions(admin_api, 1, users=owner.email)
    assert_that(
        kpis["total_sessions"],
        equal_to(1),
        "the cost view must count the owner's shared session only, not the Personal one",
    )


# ── TC-026: Personal sessions of the ordinary account kinds ─────────────────────


def _markers_for(sessions, reader: str) -> dict:
    """A session the reader must see in the shared list: its own shared one when it reads its
    own sessions only, otherwise the owner's Corporate session of the shared project."""
    sent = sessions.member if reader in OWN_SESSIONS_ONLY_KINDS else sessions.corporate
    return {sent.batch.session_id: sent.batch.repo}


def _observe_private_session_absent(
    world, sessions, owner_kind: str, sent, sent_at: float, readers
) -> None:
    """None of the readers lists the private session `sent` of the `owner_kind` account in the
    shared list within the absence window (from `sent_at`), while each of them lists a session
    there that proves the listing works."""
    for reader in readers:
        observe_absence_window(
            world.api(reader),
            _markers_for(sessions, reader),
            {
                f"private session of the {owner_kind} account": {
                    sent.batch.session_id: sent.batch.repo
                }
            },
            sent_at,
        )


# @case classify-cli-sessions-by-subscription_TC_026
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("spec", specs_named(*PERSONAL_SENDER_KINDS))
@pytest.mark.api
def test_personal_session_of_an_ordinary_account_stays_in_its_personal_project_and_private(
    account_world, account_sessions, classification_run, spec
):
    """A Personal session sent with a link to a shared project is stored in the owner's personal
    project whatever the account's role (member, project admin, maintainer, auditor); the owner
    reads it, no other kind lists it in the shared list, and only a global admin, a maintainer
    and an auditor open its detail. The owner and its session are the run's probes
    (`classification_run`), sent when the run started, so the window has passed by now; the
    readers are the run's account world's accounts of the other kinds."""
    world, sessions, probes = account_world, account_sessions, classification_run.probes
    sent = probes.kind_personal[spec.name]
    owner = probes.kind_owners[spec.name]
    readers = [
        kind for kind in (*PERSONAL_SENDER_KINDS, GLOBAL_ADMIN) if kind != spec.name
    ]

    owned = wait_for_session_row(
        owner.api, sent.batch.session_id, sent.batch.repo, personal_only="true"
    )
    details = {
        kind: detail_status(world.api(kind), sent.batch.session_id) for kind in readers
    }
    _observe_private_session_absent(
        world, sessions, spec.name, sent, probes.sent_at, readers
    )

    assert_accepted(sent.response, "event-hooks", CT_NDJSON)
    assert_that(
        routing_of(owned),
        equal_to(expected_routing(PERSONAL, PERSONAL)),
        "the owner must read the session as personal in its personal project",
    )
    assert_that(
        detail_status(owner.api, sent.batch.session_id),
        equal_to(200),
        "the owner must open the detail of its own private session",
    )
    assert_that(
        details,
        equal_to({kind: PRIVATE_DETAIL_STATUS[kind] for kind in readers}),
        "only a global admin, a maintainer and an auditor open another user's private session",
    )


# @case classify-cli-sessions-by-subscription_TC_004
@pytest.mark.cli_analytics
@pytest.mark.not_for_parallel_run
@pytest.mark.api
def test_old_personal_project_of_an_external_user_never_receives_a_session(
    classification_run, classification_admin_client
):
    """An external user who was regular at its first login has its old personal project as the
    default project, and that project is never a destination: a session without a link gets a
    retryable 503 default_project_unavailable and is stored nowhere, while a control session
    of the user's work project is listed. The session was sent when the run started
    (`classification_run`), so the window has passed by now."""
    probes = classification_run.probes
    rejected, control = probes.no_destination.batch, probes.shared.batch

    assert_rejected(probes.no_destination.response, 503, DEFAULT_PROJECT_UNAVAILABLE)
    observe_absence_window(
        CliAnalyticsApi(classification_admin_client),
        {control.session_id: control.repo},
        {
            "session sent with the old personal project as default": {
                rejected.session_id: rejected.repo
            }
        },
        probes.sent_at,
    )


# ── TC-015: no usable default project ───────────────────────────────────────────


# @case classify-cli-sessions-by-subscription_TC_015
@pytest.mark.cli_analytics
@pytest.mark.api
def test_session_without_any_usable_destination_is_a_retryable_503_and_stored_nowhere(
    stranded_probe, classification_admin_client
):
    """A session of an external user (no personal project to receive it) with no link, no
    registration and no other project gets a retryable 503 default_project_unavailable, and no
    other project receives it: a control session of another user is listed, this one is never
    listed within the window. Both were sent when the run started (`stranded_probe`), so the
    window has passed by now."""
    probe = stranded_probe
    stranded, control = probe.stranded.batch, probe.control.batch

    assert_rejected(probe.stranded.response, 503, DEFAULT_PROJECT_UNAVAILABLE)
    assert_accepted(probe.control.response, "event-hooks", CT_NDJSON)
    observe_absence_window(
        CliAnalyticsApi(classification_admin_client),
        {control.session_id: control.repo},
        {"session without a destination": {stranded.session_id: stranded.repo}},
        probe.sent_at,
    )
