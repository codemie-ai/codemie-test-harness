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

"""Shared pieces of the CLI session classification and routing tests.

The SDK has no classification headers, repository registration or subscription_type /
project_origin filters, so these helpers use the harness's raw-HTTP CliAnalyticsApi and IngestClient
(see cli_analytics_api_utils). An "evidence request" is an event-hooks POST that carries at least
one classification header and always X-CodeMie-Session-Id.

What a test can read back, and how:
- shared (work-project) sessions: an admin lists them (`projects=<name>` proves the stored project);
- Personal sessions of an ordinary user: only their owner lists them (own-only scope);
- a session row carries subscription_type, project_origin and route_note.
"""

import base64
import secrets
import uuid
from dataclasses import dataclass

import requests
from codemie_sdk import CodeMieClient
from hamcrest import assert_that, contains_string, empty, equal_to, has_length

from codemie_test_harness.tests.test_data.cli_account_test_data import (
    PROJECT_ADMIN,
    REGULAR,
    AccountSpec,
)
from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    E7,
    PRESENCE_POLL_S,
    PRESENCE_TIMEOUT_S,
    STABLE_SESSION_FIELDS,
)
from codemie_test_harness.tests.test_data.projects_test_data import (
    get_project_create_data,
)
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CT_NDJSON,
    INGEST_PREFIX,
    CliAnalyticsApi,
    IngestClient,
    delete_projects_strict,
    wait_until_accessible,
)
from codemie_test_harness.tests.utils.cli_gate_utils import Batch, make_batch
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.project_utils import ProjectUtils

CLASSIFICATION_POLICY_PATH = f"{INGEST_PREFIX}/classification-policy"
SESSIONS_PATH = f"{INGEST_PREFIX}/sessions"
COST_PATH = f"{INGEST_PREFIX}/cost"

HEADER_SESSION_ID = "X-CodeMie-Session-Id"
HEADER_ROUTED_VIA_CODEMIE = "X-CodeMie-Routed-Via-CodeMie"
HEADER_ORGANIZATION = "X-CodeMie-Organization"
HEADER_ORGANIZATION_ENCODED = "X-CodeMie-Organization-Encoded"
HEADER_PROJECT = "X-CodeMie-Project"
HEADER_PROJECT_SOURCE = "X-CodeMie-Project-Source"
HEADER_SUBSCRIPTION_TYPE = "X-CodeMie-Subscription-Type"
HEADER_POLICY_VERSION = "X-CodeMie-Policy-Version"
HEADER_REPO_REMOTE = "X-CodeMie-Repo-Remote"

ORGANIZATION_ENCODING = "utf8-b64u.v1"
ROUTING_FIELDS = ("subscription_type", "project_origin", "route_note")
_POLICY_STREAK = 3
_PROFILE_STREAK = 4


# ── Names, remotes, organizations ───────────────────────────────────────────────


def unique_organization() -> str:
    """A fresh organization name that no other test or stand setting uses."""
    return f"autotest-org-{secrets.token_hex(6)}"


def new_remote() -> str:
    """A fresh repository remote on a placeholder host."""
    return f"https://example.com/autotest/{uuid.uuid4().hex}.git"


def cli_repo_key(remote: str) -> str:
    """The repository as the CLI sends it: the credential-free `host[:port]/path` form, with no
    scheme, no `.git` and no trailing slash (the CLI's `repoKeyFromRemote`)."""
    return remote.split("://", 1)[-1].rstrip("/").removesuffix(".git")


def encode_organization(organization: str) -> str:
    """The value of X-CodeMie-Organization-Encoded: utf8-b64u.v1:<unpadded base64url>."""
    payload = base64.urlsafe_b64encode(organization.encode("utf-8")).decode()
    return f"{ORGANIZATION_ENCODING}:{payload.rstrip('=')}"


# ── Sending ─────────────────────────────────────────────────────────────────────


def new_session() -> Batch:
    """A fresh four-event hook session (id, repository and body) that carries no project name."""
    return make_batch(E7)


def evidence_headers(
    session_id: str | None,
    *,
    routed: str | None = None,
    organization: str | None = None,
    organization_encoded: str | None = None,
    project: str | None = None,
    project_source: str | None = None,
    repo_remote: str | None = None,
    claimed_type: str | None = None,
    policy_version: str | None = None,
) -> dict:
    """The classification headers of one request; every argument left as None sends no header."""
    candidates = {
        HEADER_SESSION_ID: session_id,
        HEADER_ROUTED_VIA_CODEMIE: routed,
        HEADER_ORGANIZATION: organization,
        HEADER_ORGANIZATION_ENCODED: organization_encoded,
        HEADER_PROJECT: project,
        HEADER_PROJECT_SOURCE: project_source,
        HEADER_REPO_REMOTE: repo_remote,
        HEADER_SUBSCRIPTION_TYPE: claimed_type,
        HEADER_POLICY_VERSION: policy_version,
    }
    return {name: value for name, value in candidates.items() if value is not None}


def send_with_headers(client, body: bytes, headers: dict) -> requests.Response:
    """POST an event-hooks body with exactly these extra headers (no project header is added)."""
    return IngestClient(client).post_signal(
        "event-hooks", body, CT_NDJSON, extra_headers=headers
    )


def send_evidence(client, batch: Batch, **evidence) -> requests.Response:
    """POST a session's batch as an evidence request; `evidence` as for evidence_headers."""
    return send_with_headers(
        client, batch.body, evidence_headers(batch.session_id, **evidence)
    )


def further_event(batch: Batch) -> Batch:
    """A batch holding only the second event of the session (a later event of the same session)."""
    second_event = batch.body.splitlines(keepends=True)[1]
    return Batch(second_event, 1, batch.session_id, batch.repo)


def mixed_session_batch() -> Batch:
    """One batch declared for the first session that also carries the events of a second one."""
    first, second = new_session(), new_session()
    return Batch(
        first.body + second.body,
        first.wire_count + second.wire_count,
        first.session_id,
        first.repo,
    )


def discard_reason(response: requests.Response) -> str:
    """The discard reason of an event-hooks reply, empty when it holds none."""
    return response.json().get("reason", "") if response.status_code == 200 else ""


def post_until_discarded(
    client, batch: Batch, reason: str, timeout=90, interval=3, **evidence
) -> requests.Response:
    """Send until the reply discards for `reason` (a revoked grant reaches every replica after a
    short lag); returns the last reply, so the caller asserts what it finally is."""
    return poll_until(
        lambda: send_evidence(client, batch, **evidence),
        lambda response: discard_reason(response) == reason,
        timeout,
        interval,
    )


def assert_session_discarded(
    response: requests.Response, dropped: int, reason: str, other_sessions: int = 0
) -> None:
    """HTTP 200 and the whole body of a session-guard discard of an event-hooks request."""
    assert_that(
        response.status_code,
        equal_to(200),
        f"{response.status_code}: {response.text[:200]}",
    )
    assert_that(
        response.json(),
        equal_to(
            {
                "accepted": 0,
                "dropped": dropped,
                "reason": reason,
                "other_sessions_dropped": other_sessions,
            }
        ),
        f"expected the request discarded for {reason}",
    )


def assert_rejected(response: requests.Response, status: int, identifier: str) -> None:
    """The exact HTTP status and an error body that names `identifier`."""
    assert_that(
        response.status_code,
        equal_to(status),
        f"{response.status_code}: {response.text[:200]}",
    )
    assert_that(
        response.text,
        contains_string(identifier),
        f"the HTTP {status} body does not name {identifier}",
    )


# ── Reading ─────────────────────────────────────────────────────────────────────


def session_rows(api: CliAnalyticsApi, session_id: str, repo: str, **filters) -> list:
    """Rows of the session `session_id` in the sessions list the caller sees, narrowed by
    `filters` (projects, subscription_type, project_origin, ...). Empty when it is not listed."""
    response = api.request(
        "GET", SESSIONS_PATH, params={"search": repo, "per_page": 50, **filters}
    )
    assert_that(
        response.status_code,
        equal_to(200),
        f"sessions: {response.status_code} {response.text[:200]}",
    )
    return [
        row
        for row in response.json()["data"]["sessions"]
        if row["trace_id"] == session_id
    ]


def wait_for_session_row(
    api: CliAnalyticsApi, session_id: str, repo: str, **filters
) -> dict:
    """The session's row once the caller's list shows it for `filters`; fails when it never does."""
    rows = poll_until(
        lambda: session_rows(api, session_id, repo, **filters),
        bool,
        PRESENCE_TIMEOUT_S,
        PRESENCE_POLL_S,
    )
    assert_that(
        rows,
        has_length(1),
        f"session {session_id} was not listed for filters {filters} within {PRESENCE_TIMEOUT_S}s",
    )
    return rows[0]


def listed_rows(api: CliAnalyticsApi, **filters) -> list:
    """Rows of one filtered sessions listing (one page of up to 100 rows)."""
    response = api.request(
        "GET", SESSIONS_PATH, params={"per_page": 100, "page": 0, **filters}
    )
    assert_that(
        response.status_code,
        equal_to(200),
        f"sessions: {response.status_code} {response.text[:200]}",
    )
    data = response.json()["data"]
    assert_that(
        data["total"],
        equal_to(len(data["sessions"])),
        "the listing is longer than a page",
    )
    return data["sessions"]


def listed_session_ids_with(api: CliAnalyticsApi, **filters) -> set:
    """Ids of the sessions of one filtered listing."""
    return {row["trace_id"] for row in listed_rows(api, **filters)}


LINKED = {"project_source": "linked_folder"}


def expected_routing(subscription_type, project_origin, route_note=None) -> dict:
    """The routing fields a session row must carry, as `routing_of` returns them."""
    return {
        "subscription_type": subscription_type,
        "project_origin": project_origin,
        "route_note": route_note,
    }


def routing_of(row: dict) -> dict:
    """subscription_type, project_origin and route_note of a session row."""
    return {field: row.get(field) for field in ROUTING_FIELDS}


def stable_projection(row: dict) -> dict:
    """The fixed part of a session row (identity, owner, usage) plus its routing fields."""
    return {key: row.get(key) for key in (*STABLE_SESSION_FIELDS, *ROUTING_FIELDS)}


def cost_kpis(api: CliAnalyticsApi, **filters) -> dict:
    response = api.request("GET", COST_PATH, params=filters)
    assert_that(
        response.status_code,
        equal_to(200),
        f"cost: {response.status_code} {response.text[:200]}",
    )
    return response.json()["data"]["kpis"]


def wait_for_cost_sessions(api: CliAnalyticsApi, expected: int, **filters) -> dict:
    """The cost KPIs once they count at least `expected` sessions (the rollup is periodic)."""
    return poll_until(
        lambda: cost_kpis(api, **filters),
        lambda kpis: kpis["total_sessions"] >= expected,
        PRESENCE_TIMEOUT_S,
        PRESENCE_POLL_S,
    )


# ── Classification policy (the corporate organization list) ─────────────────────


def read_policy(api: CliAnalyticsApi) -> dict:
    response = api.request("GET", CLASSIFICATION_POLICY_PATH)
    assert_that(
        response.status_code,
        equal_to(200),
        f"classification-policy: {response.status_code} {response.text[:200]}",
    )
    return response.json()


def wait_for_policy(api: CliAnalyticsApi, organizations: list[str]) -> dict:
    """The policy once several consecutive reads list exactly `organizations` (every replica has
    the new setting); fails with the last policy seen otherwise."""
    streak = [0]

    def _read() -> dict:
        policy = read_policy(api)
        streak[0] = streak[0] + 1 if policy["organizations"] == organizations else 0
        return policy

    policy = poll_until(_read, lambda _: streak[0] >= _POLICY_STREAK, 90, 2)
    assert_that(
        policy["organizations"],
        equal_to(organizations),
        "the corporate organization list did not become effective",
    )
    return policy


@dataclass(frozen=True)
class OrganizationPlan:
    """Organization names of one test: `corporate` is in the list, `other` is not."""

    corporate: str
    other: str

    def pick(self, key: str | None) -> str | None:
        """The name a test row refers to by key ("corporate", "other" or None for no organization)."""
        return {"corporate": self.corporate, "other": self.other, None: None}[key]


class CorporateList:
    """Sets the installation's corporate organization list through the customer config and
    waits until the classification policy shows it."""

    def __init__(self, customer_config_utils, component_id: str, original: dict):
        self._config = customer_config_utils
        self._component_id = component_id
        self._original = original

    def set(self, api: CliAnalyticsApi, organizations: list[str]) -> dict:
        """Save the list (one organization per line); returns the policy once it is effective."""
        self._config.save_setting(
            self._component_id,
            {**self._original, "corporateOrganizations": "\n".join(organizations)},
        )
        return wait_for_policy(api, organizations)


# ── Waiting for an account change to be active ──────────────────────────────────


def wait_until_profile(client: CodeMieClient, matches, what: str) -> None:
    """Wait until several consecutive profile reads (GET /v1/user, each possibly served by another
    replica) satisfy `matches(profile)`; fails naming `what` otherwise."""
    api = CliAnalyticsApi(client)
    streak = [0]

    def _read() -> dict:
        response = api.request("GET", "/v1/user")
        assert_that(
            response.status_code,
            equal_to(200),
            f"profile: {response.status_code} {response.text[:200]}",
        )
        profile = response.json()
        streak[0] = streak[0] + 1 if matches(profile) else 0
        return profile

    poll_until(_read, lambda _: streak[0] >= _PROFILE_STREAK, 120, 2)
    assert_that(
        streak[0] >= _PROFILE_STREAK,
        equal_to(True),
        f"{what} did not become effective on every replica",
    )


# ── Disposable users, projects and repository registrations ─────────────────────


@dataclass
class ClassifiedSender:
    """A disposable ordinary user that sends CLI sessions under its own email."""

    client: CodeMieClient
    email: str
    user_id: str

    @property
    def api(self) -> CliAnalyticsApi:
        return CliAnalyticsApi(self.client)


class Provisioner:
    """Creates users, shared projects and repository registrations and removes all of them.

    `cleanup` is called from the teardown of the fixture that owns the instance. It tries
    every removal, registrations first, then projects (members first), then users, and raises
    one error naming whatever is left on the stand.
    """

    def __init__(
        self, keycloak_utils, admin_utils, user_utils, project_utils, admin_client
    ):
        self._keycloak = keycloak_utils
        self._admin_utils = admin_utils
        self._user_utils = user_utils
        self._project_utils = project_utils
        self._admin_client = admin_client
        self._admin_api = CliAnalyticsApi(admin_client)
        self._emails: list[str] = []
        self._projects: list[str] = []
        self._registrations: list[tuple[str, str]] = []

    def sender(self) -> ClassifiedSender:
        """A fresh ordinary user."""
        email = f"autotest_clicls_{secrets.token_hex(4)}@email.com"
        password = self._keycloak.create_platform_user(email=email)
        self._emails.append(email)
        client = get_client(username=email, password=password)
        return ClassifiedSender(client, email, client.users.about_me().user_id)

    def project(self, *members: ClassifiedSender, enabled: bool = True) -> str:
        """A fresh shared project with CLI analytics on or off; the members can use it."""
        name = get_project_create_data()["name"]
        self._admin_utils.create_project(name)
        self._projects.append(name)
        ProjectUtils(self._admin_client).update_project(
            name, cli_analytics_enabled=enabled
        )
        for member in members:
            self._user_utils.assign_user_to_project(member.user_id, name)
            wait_until_accessible(member.client, [name])
        return name

    def account(
        self, spec: AccountSpec, project: str | None = None
    ) -> ClassifiedSender:
        """A fresh user of the kind `spec`, joined to `project` when one is given.

        Returns once the user type, global roles and project role are active on every replica
        and the stored state (admin view of the user and of its memberships) shows exactly the
        kind: the assertions fail naming the difference, so a test never runs on a wrong kind.
        """
        email = f"autotest_clicls_{secrets.token_hex(4)}@email.com"
        if spec.first_login_type == REGULAR:
            password = self._keycloak.create_platform_user(email=email)
        else:
            password = self._keycloak.create_platform_user_of_type(
                email, spec.first_login_type
            )
        self._emails.append(email)
        client = get_client(username=email, password=password)
        account = ClassifiedSender(
            email=email, client=client, user_id=client.users.about_me().user_id
        )
        changes = {}
        if spec.user_type != spec.first_login_type:
            changes["user_type"] = spec.user_type
        if spec.is_maintainer:
            changes["is_maintainer"] = True
        if spec.is_auditor:
            changes["is_auditor"] = True
        if changes:
            self._user_utils.update_admin_user(account.user_id, **changes)
        if project:
            self._assign(account, project, spec.project_role == PROJECT_ADMIN)
        self._wait_until_profile_shows(account, spec, project)
        self._assert_stored_state(account, spec, project)
        return account

    def project_names_of(self, account: ClassifiedSender) -> list[str]:
        """The names of the projects the account is a member of (the admin view)."""
        return self._user_utils.get_user_project_names(account.user_id)

    def join(
        self, account: ClassifiedSender, project: str, project_admin: bool = False
    ) -> None:
        """Make an existing account a member (or admin) of `project` and wait until it is active."""
        self._assign(account, project, project_admin)
        wait_until_profile(
            account.client,
            lambda profile: project in profile["applications"]
            and (project in profile["applications_admin"]) == project_admin,
            f"membership of {project}",
        )

    def _assign(
        self, account: ClassifiedSender, project: str, project_admin: bool
    ) -> None:
        self._user_utils.assign_user_to_project(
            account.user_id, project, is_project_admin=project_admin
        )
        wait_until_accessible(account.client, [project])

    def _wait_until_profile_shows(
        self, account: ClassifiedSender, spec: AccountSpec, project: str | None
    ) -> None:
        wait_until_profile(
            account.client,
            lambda profile: (
                profile["user_type"],
                profile["is_maintainer"],
                profile["is_auditor"],
                bool(project) and project in profile["applications_admin"],
            )
            == (
                spec.user_type,
                spec.is_maintainer,
                spec.is_auditor,
                bool(project) and spec.project_role == PROJECT_ADMIN,
            ),
            f"the {spec.name} account",
        )

    def _assert_stored_state(
        self, account: ClassifiedSender, spec: AccountSpec, project: str | None
    ) -> None:
        response = self._admin_api.request("GET", f"/v1/admin/users/{account.user_id}")
        assert_that(
            response.status_code,
            equal_to(200),
            f"setup: reading the {spec.name} account: {response.status_code}",
        )
        stored = response.json()
        assert_that(
            {
                field: stored.get(field)
                for field in ("user_type", "is_maintainer", "is_auditor", "is_admin")
            },
            equal_to(
                {
                    "user_type": spec.user_type,
                    "is_maintainer": spec.is_maintainer,
                    "is_auditor": spec.is_auditor,
                    # a maintainer is stored as a global admin as well
                    "is_admin": spec.is_maintainer,
                }
            ),
            f"setup: the stored user type and global roles of the {spec.name} account",
        )
        memberships = {
            membership.project_name.lower(): membership.is_project_admin
            for membership in self._user_utils.get_user_projects(account.user_id)
        }
        expected = {account.email.lower(): False} if spec.has_personal_project else {}
        if project:
            expected[project.lower()] = spec.project_role == PROJECT_ADMIN
        assert_that(
            memberships,
            equal_to(expected),
            f"setup: the stored project memberships of the {spec.name} account",
        )

    def set_default(self, sender: ClassifiedSender, project: str) -> None:
        self._user_utils.set_default_project(sender.user_id, project)

    def register(self, project: str, remote: str) -> dict:
        """Register `remote` to the project; returns the registration the API answered."""
        response = self._admin_api.request(
            "PUT", f"/v1/projects/{project}/repositories", json={"remote": remote}
        )
        assert_that(
            response.status_code,
            equal_to(200),
            f"setup: registering a repository to {project}: {response.status_code} "
            f"{response.text[:200]}",
        )
        self._registrations.append((project, remote))
        return response.json()

    def delete_project(self, project: str) -> None:
        """Delete a project of this instance now (cleanup then skips it)."""
        delete_projects_strict(self._project_utils, [project])
        self._projects.remove(project)

    def cleanup(self) -> None:
        failures = []
        for project, remote in self._registrations:
            try:
                self._admin_api.request(
                    "DELETE",
                    f"/v1/projects/{project}/repositories",
                    json={"remote": remote},
                )
            except Exception as e:
                failures.append(f"registration {remote} of {project}: {e}")
        try:
            delete_projects_strict(self._project_utils, self._projects)
        except AssertionError as e:
            failures.append(str(e))
        for email in self._emails:
            try:
                self._keycloak.delete_user(email)
            except Exception as e:
                failures.append(f"user {email}: {e}")
        assert_that(failures, empty(), "left behind on the stand")
