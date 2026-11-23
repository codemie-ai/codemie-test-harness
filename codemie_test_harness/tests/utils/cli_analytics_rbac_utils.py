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

"""Disposable users, projects and sessions for CLI Analytics access tests."""

from collections import Counter
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass

from hamcrest import assert_that, equal_to, is_, not_none

from codemie_test_harness.otlp_builder import ndjson_bytes
from codemie_test_harness.tests.enums.environment import Environment
from codemie_test_harness.tests.test_data.cli_analytics_rbac_test_data import (
    GLOBAL_READERS,
    ROLE_FLAGS,
    ROLES,
    RoleSession,
)
from codemie_test_harness.tests.utils.analytics_utils import AnalyticsUtils
from codemie_test_harness.tests.utils.base_utils import get_random_name, poll_until
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CT_NDJSON,
    INGEST_PREFIX,
    CliAnalyticsApi,
    IngestClient,
    assert_accepted,
    assert_roles_are_real,
    delete_projects_strict,
    parse_discard_response,
    wait_until_accessible,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.user_lifecycle_utils import (
    new_logged_in_user,
    user_email,
)


def read_data(api, endpoint, **params):
    r = api.request("GET", f"{INGEST_PREFIX}/{endpoint}", params=params)
    assert_that(r.status_code, equal_to(200), f"{endpoint}: {r.text[:300]}")
    data = r.json().get("data")
    assert_that(data, not_none(), f"{endpoint}: missing data envelope")
    return data


def _wait_role(user, role, project):
    expected = (
        role in ("admin", "maintainer"),
        role == "maintainer",
        role == "auditor",
    )
    streak = 0

    def effective():
        nonlocal streak
        r = CliAnalyticsApi(user.client).request("GET", "/v1/user")
        assert_that(
            r.status_code, equal_to(200), "Cannot read the effective role profile"
        )
        p = r.json()
        flags = tuple(
            p.get(k, False) for k in ("is_admin", "is_maintainer", "is_auditor")
        )
        matches = flags == expected and (
            role != "project_admin" or project in (p.get("applications_admin") or [])
        )
        streak = streak + 1 if matches else 0
        return streak >= 3

    assert_that(
        poll_until(effective, bool, timeout=120, interval=2),
        is_(True),
        f"Role {role} did not become effective",
    )


def _send_seed(user, seed, prefix, headers):
    # Keep IDs and timestamps unchanged when waiting out a new grant's ingest cache.
    body = ndjson_bytes(seed.events(prefix))

    def send():
        r = IngestClient(user.client).post_signal(
            "event-hooks", body, CT_NDJSON, seed.project, headers
        )
        return r, parse_discard_response(r, "event-hooks", CT_NDJSON).reason

    r, _ = poll_until(
        send, lambda v: v[1] != "project_context_required", timeout=60, interval=2
    )
    assert_accepted(r, "event-hooks", CT_NDJSON)


@dataclass
class RoleWorld:
    users: dict
    projects: tuple[str, str]
    sessions: dict[str, RoleSession]
    prefix: str

    def api(self, role):
        return CliAnalyticsApi(self.users[role].client)

    @property
    def filters(self):
        return {"projects": ",".join(self.projects)}

    def shared(self, role):
        # Project admins also read their own sessions outside their administered projects.
        return [
            s
            for s in self.sessions.values()
            if not s.private
            and (
                role in GLOBAL_READERS
                or s.owner == role
                or (role == "project_admin" and s.project == self.projects[0])
            )
        ]

    def private(self, role):
        return [
            s
            for s in self.sessions.values()
            if s.private and (role in GLOBAL_READERS or s.owner == role)
        ]

    def repository(self, seed):
        return f"{self.prefix}/{seed.trace_id}"

    def project_counts(self, role):
        return dict(Counter(s.project for s in self.shared(role)))

    def private_rows(self, role, foreign_user_filter):
        params = {"users": self.users["owner"].email} if foreign_user_filter else {}
        return self.rows(role, personal=True, **params)

    def detail_case(self, role, case):
        return self.sessions[
            {
                "own_shared": f"{role}_shared",
                "admin_project": "owner_a",
                "other_project": "owner_b",
                "own_private": f"{role}_private",
                "other_private": "owner_private",
            }[case]
        ]

    def may_read(self, role, seed):
        return seed in (self.private(role) if seed.private else self.shared(role))

    def rows(self, role, personal=False, **params):
        query = {"search": self.prefix, "per_page": 500, **self.filters, **params}
        if personal:
            query["personal_only"] = "true"
        data = read_data(self.api(role), "sessions", **query)
        assert_that(
            len(data["sessions"]), equal_to(data["total"]), "Truncated session list"
        )
        return data["sessions"]


@contextmanager
def role_world(
    client, keycloak_utils, user_utils, project_utils, *, with_sessions=True
):
    assert_that(
        EnvironmentResolver.get_environment(),
        equal_to(Environment.PREVIEW),
        "Role provisioning requires Preview",
    )
    assert_that(
        AnalyticsUtils(client).is_cli_analytics_enabled(),
        is_(True),
        "CLI analytics is disabled",
    )
    if with_sessions:
        api = CliAnalyticsApi(client)
        r = api.request("GET", f"{INGEST_PREFIX}/classification-policy")
        assert_that(r.status_code, equal_to(200), "Cannot read classification policy")
        policy = r.json()
        assert_that(
            bool(policy["organizations"]),
            is_(True),
            "Private-session checks need a configured organization policy",
        )
        other_org = get_random_name()
        assert_that(
            other_org.casefold()
            in {v.strip().casefold() for v in policy["organizations"]},
            is_(False),
        )
    projects = (get_random_name(), get_random_name())
    users, sessions = {}, {}
    with ExitStack() as cleanup:
        roles = (*ROLES, "owner") if with_sessions else ROLES
        for role in roles:
            user = cleanup.enter_context(
                new_logged_in_user(
                    keycloak_utils, user_email("clirbac"), admin=False, strict=True
                )
            )
            users[role] = user
            # Personal projects cannot be deleted through the projects API.
            cleanup.callback(user_utils.deactivate_user, user.user_id)
            if role in ROLE_FLAGS:
                user_utils.update_admin_user(user.user_id, **ROLE_FLAGS[role])
        cleanup.callback(delete_projects_strict, project_utils, list(projects))
        for name in projects:
            project_utils.create_project(name=name, cli_analytics_enabled=True)
        assert_roles_are_real(users["regular"].client, projects[0])
        for role, user in users.items():
            for name in projects:
                user_utils.assign_user_to_project(
                    user.user_id,
                    name,
                    is_project_admin=role == "project_admin" and name == projects[0],
                )
            fresh = get_client(username=user.email, password=user.password)
            user = user._replace(client=fresh)
            users[role] = user
            wait_until_accessible(fresh, projects)
            _wait_role(user, role, projects[0])
        prefix = get_random_name()
        world = RoleWorld(users, projects, sessions, prefix)
        if not with_sessions:
            yield world
            return

        specs = [(f"{role}_shared", role, projects[1], False) for role in ROLES]
        specs += [
            ("owner_a", "owner", projects[0], False),
            ("owner_b", "owner", projects[1], False),
        ]
        specs += [
            (f"{role}_private", role, user.email.lower(), True)
            for role, user in users.items()
        ]
        for ordinal, (key, role, project, private) in enumerate(specs, 1):
            seed = RoleSession(role, project, private, ordinal)
            headers = {
                "X-CodeMie-Session-Id": seed.trace_id,
                "X-CodeMie-Policy-Version": policy["version"],
                "X-CodeMie-Project-Source": "profile",
            }
            headers.update(
                {"X-CodeMie-Organization": other_org}
                if private
                else {"X-CodeMie-Routed-Via-CodeMie": "true"}
            )
            _send_seed(users[role], seed, prefix, headers)
            sessions[key] = seed

        expected_count = len(world.shared("admin"))

        def ready():
            rows = {
                row["trace_id"]: row
                for row in (*world.rows("admin"), *world.rows("admin", personal=True))
            }
            return (
                all(
                    s.trace_id in rows
                    and rows[s.trace_id].get("input_tokens") == s.ordinal * 101
                    and rows[s.trace_id].get("output_tokens") == s.ordinal * 17
                    and rows[s.trace_id].get("project_origin")
                    == ("personal" if s.private else "profile")
                    for s in sessions.values()
                )
                and read_data(api, "cost", **world.filters)["kpis"]["total_sessions"]
                == expected_count
            )

        assert_that(
            poll_until(ready, bool, timeout=180, interval=3),
            is_(True),
            "Shared/private positive controls did not finish rolling up",
        )
        yield world
