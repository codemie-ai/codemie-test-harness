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

"""Raw HTTP helpers for the CLI Analytics tests.

The SDK models turn a missing key into None, so key-presence and null checks must look at the
raw JSON. These helpers send plain `requests` calls with the client's own token and never raise
on an error status. API_DOMAIN and VERIFY_SSL come from the harness settings, as for RequestHandler
and the other raw-HTTP utils: they target the one configured stand, whatever backend the client
object was built for (private SDK attributes are not read on purpose). A second backend origin
is reached through the explicit `post_body_to(domain, ...)` in cli_gate_utils (TC-004).

Two kinds of ingest assertions, so a test says what it expects:
- accepted: `assert_accepted` / `assert_not_discarded` fail with a message quoting reason,
  dropped and partial_success when the backend answered with a discard body;
- expected discard: `parse_discard_response` returns the parsed `Discard` and the test asserts
  the reason and the rejected count itself (`assert_discard` does that for the common case).
"""

from typing import NamedTuple, Optional
from urllib.parse import urljoin, urlsplit

import requests
from codemie_sdk import CodeMieClient
from hamcrest import assert_that, empty, equal_to, equal_to_ignoring_case, is_, is_in

from codemie_test_harness.ingest_sender import post_ingest
from codemie_test_harness.otlp_builder import parse_discard
from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.utils.base_utils import BaseUtils, poll_until

INGEST_PREFIX = "/v1/analytics/cli-analytics"
CT_PROTOBUF = "application/x-protobuf"
CT_JSON = "application/json"
CT_NDJSON = "application/x-ndjson"
_PROTOBUF_MEDIA_TYPES = {"application/x-protobuf", "application/protobuf"}
REQUEST_TIMEOUT = 60
_SSO_REDIRECT_STATUSES = (302, 303, 307)


class Discard(NamedTuple):
    """What an ingest reply reports as discarded: records rejected and the reason."""

    rejected: int
    reason: str


def _media_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


class CliAnalyticsApi(BaseUtils):
    """`requests` with the token of a CodeMieClient; one call, no raising, no retries."""

    def _auth(self) -> dict:
        # No placeholder identity: the suite runs against real users (local-auth or Keycloak), and
        # a missing token must fail here instead of being mistaken for a role failure later.
        assert_that(
            bool(self.client.token),
            is_(True),
            "the client has no token; these tests need a really authenticated user",
        )
        return {"Authorization": f"Bearer {self.client.token}"}

    def request(
        self,
        method: str,
        path: str,
        json=None,
        headers: Optional[dict] = None,
        data=None,
        params: Optional[dict] = None,
    ) -> requests.Response:
        """Send one request. `headers` overrides the defaults; no status check is made."""
        all_headers = {**self._auth(), **(headers or {})}
        if json is not None:
            all_headers.setdefault("Content-Type", CT_JSON)
        return requests.request(
            method,
            f"{API_DOMAIN.rstrip('/')}{path}",
            json=json,
            data=data,
            params=params,
            headers=all_headers,
            verify=VERIFY_SSL,
            timeout=REQUEST_TIMEOUT,
        )


class IngestClient(CliAnalyticsApi):
    """POSTs to the four CLI Analytics ingest endpoints (logs, metrics, traces, event-hooks)."""

    def post_signal(
        self,
        signal: str,
        body: bytes,
        content_type: str,
        project: Optional[str] = None,
        extra_headers: Optional[dict] = None,
        auth: str = "default",
    ) -> requests.Response:
        """signal is logs | metrics | traces | event-hooks. project=None sends no header.

        auth: "default" (the client's token), "none" (no Authorization header) or
        "invalid" (a bogus bearer token). Only explicit negative-auth probes disable
        redirects; ordinary authenticated calls keep the transport's existing behavior.
        """
        headers = {"Content-Type": content_type}
        if auth == "invalid":
            headers["Authorization"] = "Bearer invalid-token"
        elif auth == "default":
            headers.update(self._auth())
        # explicit headers win over the defaults, Authorization included, as in request()
        headers.update(extra_headers or {})
        return post_ingest(
            f"{API_DOMAIN.rstrip('/')}{INGEST_PREFIX}/{signal}",
            body,
            headers,
            project,
            VERIFY_SSL,
            REQUEST_TIMEOUT,
            allow_redirects=auth not in ("none", "invalid"),
        )


def assert_authentication_rejected(response: requests.Response) -> None:
    """Accept a direct 401 or an SSO redirect to this stand's /oauth2/start.

    Inspect the first response, as ProxyUtils.send_unauthenticated_request does. A login
    page with HTTP 200 or a redirect to an unrelated URL must never count as rejection.
    Local IDP can run on a remote stand too; the hostname does not determine the status.
    """
    assert_that(
        response.status_code,
        is_in((401, *_SSO_REDIRECT_STATUSES)),
        f"expected auth rejection HTTP 401 or an SSO redirect, got {response.status_code}: "
        f"{response.text[:200]}",
    )
    if response.status_code in _SSO_REDIRECT_STATUSES:
        location = response.headers.get("Location", "")
        assert_that(bool(location), is_(True), "SSO redirect has no Location header")
        destination = urlsplit(urljoin(response.url, location))
        expected_destination = urlsplit(urljoin(API_DOMAIN, "/oauth2/start"))
        assert_that(
            (destination.scheme, destination.netloc, destination.path),
            equal_to(
                (
                    expected_destination.scheme,
                    expected_destination.netloc,
                    expected_destination.path,
                )
            ),
            "auth rejection must redirect to this stand's /oauth2/start",
        )


def wait_until_accessible(client, project_names, consecutive=3, timeout=120) -> None:
    """Wait until the client reads every project (a grant is visible on all replicas).

    Uses GET /v1/projects/{name} (404 without access, 200 for a member): the legacy
    /v1/application/{name} route is only mounted when Elasticsearch is configured.
    """
    api = CliAnalyticsApi(client)
    streak = [0]

    def _read_all():
        statuses = [
            api.request("GET", f"/v1/projects/{name}").status_code
            for name in project_names
        ]
        streak[0] = streak[0] + 1 if all(s == 200 for s in statuses) else 0
        return statuses, streak[0]

    statuses, reached = poll_until(
        _read_all, lambda v: v[1] >= consecutive, timeout=timeout, interval=2
    )
    if reached < consecutive:
        raise TimeoutError(
            f"access to {project_names} did not become effective, last statuses: {statuses}"
        )


def delete_projects_strict(project_utils, project_names) -> None:
    """Delete every project (members first) and fail naming the ones that remain.

    A failure does not stop the others. Unlike the shared best-effort cleanup it is raised, so
    a leaked project on the shared stand is an error of the run. The creator of a project made
    through the public API cannot be unassigned, but does not block the deletion.
    """
    remaining = {}
    for name in project_names:
        try:
            project_utils.remove_all_project_members(name)
            project_utils.delete_project(name)
        except Exception as e:
            remaining[name] = e
    if remaining:
        raise AssertionError(
            "projects left behind on the stand: "
            + "; ".join(f"{n}: {e}" for n, e in remaining.items())
        )


def assert_project_deleted(client: CodeMieClient, project_name: str) -> None:
    """Fail unless a privileged client gets 404 for the project (waits for all replicas)."""
    api = CliAnalyticsApi(client)
    status = poll_until(
        lambda: api.request("GET", f"/v1/projects/{project_name}").status_code,
        lambda s: s == 404,
        timeout=30,
        interval=2,
    )
    assert_that(
        status,
        equal_to(404),
        f"setup: project {project_name} still answers HTTP {status}, it was not deleted",
    )


def assert_roles_are_real(unrelated_client: CodeMieClient, project_name: str) -> None:
    """Fail unless a user without any membership gets 404 for the project.

    With ENV=local the BE makes every user a global admin (the user would get 200), which
    makes every role case meaningless.
    """
    status = (
        CliAnalyticsApi(unrelated_client)
        .request("GET", f"/v1/projects/{project_name}")
        .status_code
    )
    assert_that(
        status,
        equal_to(404),
        f"an unrelated user got HTTP {status} for GET /v1/projects/{project_name}; "
        "expected 404. The BE runs with ENV=local (every user is a global admin) or the "
        "user is not unrelated: the role matrix cannot be tested on this instance",
    )


def assert_principal_is(client: CodeMieClient, username: str, not_admin: bool = False):
    """Fail unless the client really is `username`. An empty username never passes, so a client
    built without credentials cannot fall back to the harness admin."""
    assert_that(bool(username), is_(True), "the expected username is empty")
    me = client.users.about_me()
    assert_that(
        me.username,
        equal_to_ignoring_case(username),
        f"the client authenticated as {me.username!r}, expected {username!r}",
    )
    if not_admin:
        assert_that(me.is_admin, is_(False), f"{me.username!r} is a global admin")


def wait_until_auditor_effective(client: CodeMieClient, timeout: int = 120) -> None:
    """Wait for the assigned auditor flag to propagate through the backend's user caches."""
    api = CliAnalyticsApi(client)
    streak = 0

    def read_role() -> int:
        nonlocal streak
        response = api.request("GET", "/v1/user")
        assert_that(
            response.status_code, equal_to(200), "cannot read the new auditor's profile"
        )
        streak = streak + 1 if response.json().get("is_auditor") is True else 0
        return streak

    seen = poll_until(read_role, lambda count: count >= 3, timeout=timeout, interval=2)
    assert_that(
        seen >= 3, is_(True), "new auditor role did not become effective in time"
    )


def assert_auditor_without_admin_roles(client: CodeMieClient) -> None:
    """Check effective roles, including flags that the SDK User model does not expose."""
    response = CliAnalyticsApi(client).request("GET", "/v1/user")
    assert_that(
        response.status_code,
        equal_to(200),
        "auditor setup: cannot read the authenticated user's effective roles",
    )
    profile = response.json()
    flags = {
        key: profile.get(key) for key in ("is_admin", "is_maintainer", "is_auditor")
    }
    assert_that(
        flags,
        equal_to({"is_admin": False, "is_maintainer": False, "is_auditor": True}),
        "auditor setup: use a dedicated auditor account without global admin or maintainer roles",
    )
    assert_that(
        profile.get("applications_admin"),
        equal_to([]),
        "auditor setup: this account also administers projects; use a dedicated auditor "
        "without project admin assignments (the test cannot assert auditor-only denial)",
    )
    project_admins = [
        project["name"]
        for project in profile.get("projects", [])
        if project.get("is_project_admin")
    ]
    assert_that(
        project_admins,
        empty(),
        "auditor setup: project memberships grant administrator rights; "
        "use a dedicated auditor without project admin assignments",
    )


def assert_stored_roles(user_utils, user_id: str, **expected: bool) -> None:
    """Fail unless the admin user detail shows exactly the expected flags, for example
    is_maintainer=True, is_admin=True (the backend stores is_admin as true for every maintainer),
    or is_maintainer=False, is_admin=False for a plain user."""
    detail = user_utils.get_admin_user(user_id)
    actual = {flag: getattr(detail, flag) for flag in expected}
    assert_that(actual, equal_to(expected), f"roles of user {user_id}")


def parse_discard_response(
    response: requests.Response, signal: str, request_content_type: str
) -> Discard:
    """Expected-discard helper: HTTP 200 required, returns what the reply reports as discarded.

    A reply with nothing discarded gives Discard(0, ""). The test asserts the reason and the
    rejected count itself. OTLP replies prove the response only, never storage.
    """
    assert_that(response.status_code, equal_to(200), f"status, body={response.text!r}")
    if signal == "event-hooks":
        body = response.json()
        return Discard(body.get("dropped", 0), body.get("reason", ""))
    _assert_response_media_type(response, request_content_type)
    return Discard(*parse_discard(response.content, request_content_type, signal))


def assert_discard(
    response: requests.Response,
    signal: str,
    request_content_type: str,
    count: int,
    reason: str,
) -> None:
    """HTTP 200 and a body that reports `count` records discarded for `reason`."""
    if signal == "event-hooks":
        assert_that(response.status_code, equal_to(200), response.text)
        assert_that(
            response.json(),
            equal_to({"accepted": 0, "dropped": count, "reason": reason}),
        )
        return
    assert_that(
        parse_discard_response(response, signal, request_content_type),
        equal_to(Discard(count, reason)),
    )


def assert_accepted(
    response: requests.Response, signal: str, request_content_type: str
) -> None:
    """Accepted-send helper: HTTP 200 and nothing discarded (NDJSON `{}`, OTLP empty
    partial_success). On a discard body it fails quoting reason and the rejected count."""
    discard = parse_discard_response(response, signal, request_content_type)
    assert_that(
        discard,
        equal_to(Discard(0, "")),
        f"batch was discarded, expected it accepted: reason={discard.reason!r} "
        f"rejected/dropped={discard.rejected} body={response.text[:300]!r}",
    )
    if signal == "event-hooks":
        assert_that(response.json(), equal_to({}), f"unexpected body {response.text!r}")


def assert_not_discarded(result: Optional[dict], what: str) -> None:
    """Accepted-send helper for a reply parsed by the SDK (an event-hooks body or an OTLP JSON
    response): fails quoting reason, dropped and partial_success when it carries a discard."""
    result = result or {}
    partial = result.get("partial_success") or result.get("partialSuccess")
    discarded = bool(result.get("reason") or result.get("dropped") or partial)
    assert_that(
        discarded,
        is_(False),
        f"{what} was discarded, expected it accepted: reason={result.get('reason')!r} "
        f"dropped={result.get('dropped')!r} partial_success={partial!r}",
    )


def _assert_response_media_type(response: requests.Response, request_content_type: str):
    got = _media_type(response.headers.get("Content-Type", ""))
    if _media_type(request_content_type) == CT_JSON:
        assert_that(got, equal_to(CT_JSON))
    else:
        assert_that(got, is_in(_PROTOBUF_MEDIA_TYPES))
