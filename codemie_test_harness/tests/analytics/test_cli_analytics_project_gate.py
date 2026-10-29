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

"""Project gate of the four CLI Analytics ingest POSTs (plan TC-001 .. TC-005).

Scenarios: TC-001 enabled accepted / disabled discarded, TC-002 project-context classes, TC-003
request validation unchanged, TC-004 instance flag off, TC-005 gate storage. Endpoint combinations
(logs, metrics and traces as OTLP protobuf and JSON, event-hooks as NDJSON) are parameters named
like logs-protobuf, event-hooks-ndjson; plan and matrix ids stay in docstrings.

Evidence limits, stated once:
- OTLP rows prove the HTTP response only (status, reason, rejected count), never storage. Only the
  hook endpoint has a read side, so only hook sessions are checked for storage (TC-005).
- Absence is "not observed within the window": ABSENCE_WINDOW_S is a bounded test heuristic derived
  from the backend rollup settings, not an ingestion SLA and no upper bound under a backlog. It
  counts only when the accepted control of the same shape became visible. Row-level proof that a
  discard writes nothing is backend testing.
- NOT TESTABLE black-box: padded and whitespace-only project headers. The HTTP transport strips
  them before the application sees them; the backend unit tests cover the matching. The
  empty-string header is testable (TC-002).
- Not covered here: AC-1 migration default of existing projects, AC-7 HTTP 503 on a policy-lookup
  failure (no fault injection in the harness), AC-8 real-agent queued delivery, AC-11 proxy
  continuity.
- Auth rejection is a direct 401 or a 302/303/307 to this stand's /oauth2/start, independent of hostname.
  Redirects are not followed; an SSO result proves rejection at the ingress, not a backend 401.

Every test is self-contained and parallel-safe: fresh batches and session ids, projects that no test
of this module changes, nothing handed from one test to another.
"""

import pytest
from hamcrest import assert_that, empty, equal_to, is_not

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    ALL,
    AUTH_FAILURES,
    CONTEXT_PARAMS,
    DISABLED,
    E1,
    E2,
    E7,
    ENABLED_OR_DISABLED,
    FLAG_OFF_DOMAIN,
    HOOK_SESSION_EVENTS,
    MAX_BODY_BYTES,
    NO_FLAG_OFF_BACKEND,
    PROJECT_STATES,
    REQUIRED,
    STORAGE_CASES,
    combo_id,
    malformed_body,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CT_JSON,
    CliAnalyticsApi,
    IngestClient,
    assert_accepted,
    assert_authentication_rejected,
    assert_discard,
)
from codemie_test_harness.tests.utils.cli_gate_utils import (
    assert_context_outcome,
    make_batch,
    observe_absence_window,
    post_batch,
    post_body_to,
    resolve_project,
    send_context_case,
    send_storage_probe,
)

pytestmark = [
    pytest.mark.api,
    pytest.mark.cli_analytics,
]


# ── TC-001: enabled accepted, disabled discarded with 200 and an explicit reason ──


@pytest.mark.parametrize("combo", ALL, ids=combo_id)
@pytest.mark.parametrize(
    "named", [True, False], ids=["body-names-project", "body-names-nothing"]
)
def test_enabled_project_batch_is_accepted(gate_context, combo, named):
    """TC-001 (AC-6): HTTP 200, no reason, nothing rejected; the body may name the project."""
    batch = make_batch(combo, names=[gate_context.p_on] if named else [])
    response = post_batch(
        gate_context.clients["member"], combo, batch, gate_context.p_on
    )
    assert_accepted(response, combo.signal, combo.ct)


@pytest.mark.parametrize("combo", ALL, ids=combo_id)
@pytest.mark.parametrize("records", [1, 3], ids=["one-record", "three-records"])
def test_disabled_project_batch_is_discarded_with_200_and_the_wire_count(
    gate_context, combo, records
):
    """TC-001 (AC-6, AC-7): HTTP 200 (never 403), reason cli_analytics_disabled and a rejected
    count equal to the number of records sent, not of requests."""
    batch = make_batch(combo, n=records, names=[gate_context.p_off])
    assert_that(
        batch.wire_count, equal_to(records), "the batch must hold the requested records"
    )
    response = post_batch(
        gate_context.clients["member"], combo, batch, gate_context.p_off
    )
    assert_discard(response, combo.signal, combo.ct, batch.wire_count, DISABLED)


# ── TC-002: project-context classes ──────────────────────────────────────────────


@pytest.mark.parametrize(("case", "combo"), CONTEXT_PARAMS)
def test_project_context_class_is_discarded_or_accepted(gate_context, case, combo):
    """TC-002 (AC-6, AC-8, AC-10): unusable contexts (missing, empty, unknown, deleted, no access,
    header against body, mixed projects, conflict in a resource or a record attribute) are
    discarded with 200, an explicit reason and the whole batch counted; a global admin does not
    bypass a disabled project; allowed variants (global admin into an enabled project without
    membership, header in another case, body name in another case) are accepted."""
    response, batch = send_context_case(gate_context, case, combo)
    assert_context_outcome(response, combo, batch, case.reason)


@pytest.mark.parametrize("combo", [E1, E2, E7], ids=combo_id)
def test_existing_project_without_access_is_indistinguishable_from_unknown(
    gate_context, combo
):
    """TC-002 (AC-8): a user without access naming an existing project gets exactly the answer
    given for an unknown project, so the existence of the project is not disclosed."""
    unknown = get_random_name()
    known_batch = make_batch(combo, n=3)
    unknown_batch = make_batch(combo, n=3)
    unknown_response = post_batch(
        gate_context.clients["member"], combo, unknown_batch, unknown
    )
    outsider_response = post_batch(
        gate_context.clients["outsider"], combo, known_batch, gate_context.p_on
    )
    assert_discard(outsider_response, combo.signal, combo.ct, 3, REQUIRED)
    assert_discard(unknown_response, combo.signal, combo.ct, 3, REQUIRED)
    assert_that(
        (
            outsider_response.status_code,
            outsider_response.headers.get("Content-Type"),
            outsider_response.content,
        ),
        equal_to(
            (
                unknown_response.status_code,
                unknown_response.headers.get("Content-Type"),
                unknown_response.content,
            )
        ),
        "the answer for an existing project without access differs from the one for an unknown project",
    )


@pytest.mark.parametrize("combo", [E1, E7], ids=combo_id)
def test_maintainer_does_not_bypass_a_disabled_project(
    gate_context, verified_maintainer_client, combo
):
    """TC-002 (AC-6, AC-8): a global writer other than the admin is discarded too."""
    batch = make_batch(combo)
    response = post_batch(verified_maintainer_client, combo, batch, gate_context.p_off)
    assert_discard(response, combo.signal, combo.ct, batch.wire_count, DISABLED)


# ── TC-003: request validation unchanged by the gate ─────────────────────────────


@pytest.mark.parametrize("combo", [E1, E7], ids=combo_id)
@pytest.mark.parametrize("project_ref", ENABLED_OR_DISABLED)
@pytest.mark.parametrize("auth", AUTH_FAILURES)
def test_missing_or_invalid_credentials_are_rejected(
    gate_context, combo, project_ref, auth
):
    """TC-003 (AC-6): local BE / SSO ingress rejects the request before the project gate."""
    project = resolve_project(project_ref, gate_context)
    batch = make_batch(combo, names=[project])
    response = IngestClient(gate_context.clients["member"]).post_signal(
        combo.signal, batch.body, combo.ct, project=project, auth=auth
    )
    assert_authentication_rejected(response)


@pytest.mark.parametrize("combo", [E1, E7], ids=combo_id)
@pytest.mark.parametrize("project_ref", PROJECT_STATES)
def test_body_over_the_size_limit_is_rejected_with_413(
    gate_context, combo, project_ref
):
    """TC-003 (AC-6): the body size limit applies before the gate, whatever the header says."""
    response = IngestClient(gate_context.clients["member"]).post_signal(
        combo.signal,
        b"x" * (MAX_BODY_BYTES + 1),
        combo.ct,
        project=resolve_project(project_ref, gate_context),
    )
    assert_that(
        response.status_code,
        equal_to(413),
        f"{response.status_code}: {response.text[:200]}",
    )


@pytest.mark.parametrize("project_ref", ENABLED_OR_DISABLED)
def test_event_hooks_with_another_content_type_is_rejected_with_415(
    gate_context, project_ref
):
    """TC-003 (AC-6): event-hooks accepts NDJSON only."""
    project = resolve_project(project_ref, gate_context)
    batch = make_batch(E7, names=[project])
    response = IngestClient(gate_context.clients["member"]).post_signal(
        "event-hooks", batch.body, CT_JSON, project=project
    )
    assert_that(
        response.status_code,
        equal_to(415),
        f"{response.status_code}: {response.text[:200]}",
    )


@pytest.mark.parametrize("combo", ALL, ids=combo_id)
@pytest.mark.parametrize("project_ref", PROJECT_STATES)
def test_malformed_payload_stays_400_in_every_header_state(
    gate_context, combo, project_ref
):
    """TC-003 (AC-6): decoding precedes the gate, so a malformed body is a 400, not a discard."""
    response = IngestClient(gate_context.clients["member"]).post_signal(
        combo.signal,
        malformed_body(combo),
        combo.ct,
        project=resolve_project(project_ref, gate_context),
    )
    assert_that(
        response.status_code,
        equal_to(400),
        f"{response.status_code}: {response.text[:200]}",
    )


# ── TC-004: instance feature flag off ────────────────────────────────────────────


@pytest.mark.skipif(not FLAG_OFF_DOMAIN, reason=NO_FLAG_OFF_BACKEND)
@pytest.mark.parametrize("combo", ALL, ids=combo_id)
@pytest.mark.parametrize(
    "has_header", [False, True], ids=["no-header", "unknown-project-header"]
)
@pytest.mark.parametrize("payload", ["valid", "malformed"])
def test_instance_flag_off_answers_404_whatever_the_request(
    flag_off_client, combo, has_header, payload
):
    """TC-004 (AC-10): with features:cliAnalytics off every ingest POST answers 404, independent
    of the header and of the payload. Runs only against the separately configured flag-off
    backend (CODEMIE_API_DOMAIN_FLAG_OFF); the flag of the shared stand is never toggled. The
    projects of the flag-on stand do not exist there, so the header is absent or unknown."""
    body = make_batch(combo).body if payload == "valid" else malformed_body(combo)
    response = post_body_to(
        FLAG_OFF_DOMAIN,
        flag_off_client,
        combo,
        body,
        get_random_name() if has_header else None,
    )
    assert_that(
        response.status_code,
        equal_to(404),
        f"{response.status_code}: {response.text[:200]}",
    )


# ── TC-005: gate storage ─────────────────────────────────────────────────────────


def test_accepted_sessions_are_listed_and_no_discard_class_is_ever_stored(
    gate_context, gate_admin_client
):
    """TC-005 (AC-6, AC-8, AC-10): one full 4-event hook session per context class. Accepted ones
    (global admin into an enabled project without membership, header and body name in another
    case) are the control of the same shape and must be listed; every discarded class (disabled,
    missing or empty header, unknown, deleted, no access, conflicts, mixed projects) must not be
    observed within the absence window. A leak at any poll fails at once naming its class.
    Black-box evidence only, see the module docstring."""
    probe = send_storage_probe(gate_context, STORAGE_CASES)
    assert_that(
        set(probe.wire_counts.values()),
        equal_to({HOOK_SESSION_EVENTS}),
        f"every probe must be a full {HOOK_SESSION_EVENTS}-event session: {probe.wire_counts}",
    )
    assert_that(probe.markers, is_not(empty()), "no accepted control session was sent")
    observe_absence_window(
        CliAnalyticsApi(gate_admin_client),
        probe.markers,
        probe.leaks,
        probe.last_send_at,
    )
