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

"""Fixtures for CLI Analytics tests (/v1/analytics/cli-analytics/*)."""

import secrets
from dataclasses import dataclass

import pytest
from codemie_sdk import CodeMieClient
from hamcrest import assert_that, empty

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    CLI_ANALYTICS_USERS,
    E7,
    FLAG_OFF_DOMAIN,
    CliSessionSeed,
    priced_model,
)
from codemie_test_harness.tests.test_data.projects_test_data import (
    get_project_create_data,
)
from codemie_test_harness.tests.utils.analytics_utils import AnalyticsUtils
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CliAnalyticsApi,
    assert_project_deleted,
    assert_roles_are_real,
    delete_projects_strict,
    wait_until_accessible,
)
from codemie_test_harness.tests.utils.cli_gate_utils import (
    assert_sent_accepted,
    send_tracked,
    wait_until_listed,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.logger_util import setup_logger
from codemie_test_harness.tests.utils.project_utils import ProjectUtils

logger = setup_logger(__name__)


@dataclass
class CliAnalyticsUser:
    """A disposable user that reports CLI sessions under its own email."""

    email: str
    user_id: str
    analytics_utils: AnalyticsUtils


@pytest.fixture(scope="session")
def cli_analytics_enabled(analytics_utils):
    """Skip CLI Analytics tests where the features:cliAnalytics flag is off."""
    if not analytics_utils.is_cli_analytics_enabled():
        pytest.skip("features:cliAnalytics is disabled on this environment")


@pytest.fixture(scope="module")
def create_cli_analytics_project(cli_analytics_enabled, project_utils):
    """Factory of projects that live as long as the test module."""
    names = []

    def _create() -> str:
        project_data = get_project_create_data()
        # The BE stores CLI analytics only for projects that enable it.
        project_utils.create_project(**project_data, cli_analytics_enabled=True)
        names.append(project_data["name"])
        return project_data["name"]

    yield _create
    # the senders were removed by ingest_cli_sessions while they still existed
    delete_projects_strict(project_utils, names)


@dataclass
class GateProjects:
    p_on: str
    p_off: str


@pytest.fixture(scope="module")
def gate_projects(
    admin_utils,
    project_utils,
    user_utils,
    gate_admin_client,
    gate_member_client,
    gate_outsider_client,
):
    """Two isolated projects: p_on (CLI analytics explicitly enabled) and p_off (explicitly
    disabled). The member sender is granted membership in BOTH, so a sender result of
    project_context_required can only mean a defect, never missing access. Also asserts the
    real-roles precondition (an unrelated user gets 404, i.e. the BE is not ENV=local)
    before any grant.
    """
    names = [get_project_create_data()["name"] for _ in range(2)]
    try:
        for name, enabled in zip(names, (True, False)):
            admin_utils.create_project(name)
            ProjectUtils(gate_admin_client).update_project(
                name, cli_analytics_enabled=enabled
            )
        assert_roles_are_real(gate_outsider_client, names[0])
        member_id = gate_member_client.users.about_me().user_id
        for name in names:
            user_utils.assign_user_to_project(member_id, name)
        wait_until_accessible(gate_member_client, names)
        yield GateProjects(p_on=names[0], p_off=names[1])
    finally:
        delete_projects_strict(project_utils, names)


@dataclass
class GateContext:
    """Read-only world of the gate response checks: two fixed projects, a deleted one and the
    senders by role."""

    p_on: str
    p_off: str
    deleted: str
    clients: dict  # member, outsider, admin


@pytest.fixture(scope="module")
def gate_context(
    cli_analytics_enabled,  # skips where features:cliAnalytics is off
    gate_projects,
    admin_utils,
    user_utils,
    project_utils,
    gate_admin_client,
    gate_member_client,
    gate_outsider_client,
):
    """gate_projects plus a project that existed and was deleted (the member was its member).
    The deletion is verified (404 for the global admin), so a failed one is a setup error and
    not a gate assertion about a project that still exists."""
    deleted = get_project_create_data()["name"]
    try:
        admin_utils.create_project(deleted)
        user_utils.assign_user_to_project(
            gate_member_client.users.about_me().user_id, deleted
        )
    finally:
        delete_projects_strict(project_utils, [deleted])
    assert_project_deleted(gate_admin_client, deleted)
    return GateContext(
        gate_projects.p_on,
        gate_projects.p_off,
        deleted,
        {
            "member": gate_member_client,
            "outsider": gate_outsider_client,
            "admin": gate_admin_client,
        },
    )


@dataclass
class LifecycleProjects:
    x: str
    y: str
    admin: ProjectUtils  # the global admin's project API, toggles the setting


@pytest.fixture
def lifecycle_projects(
    cli_analytics_enabled,
    admin_utils,
    user_utils,
    project_utils,
    gate_admin_client,
    gate_member_client,
):
    """Two fresh projects X and Y, both enabled, the member sender granted in both."""
    names = [get_project_create_data()["name"] for _ in range(2)]
    admin = ProjectUtils(gate_admin_client)
    try:
        member_id = gate_member_client.users.about_me().user_id
        for name in names:
            admin_utils.create_project(name)
            admin.update_project(name, cli_analytics_enabled=True)
            user_utils.assign_user_to_project(member_id, name)
        wait_until_accessible(gate_member_client, names)
        yield LifecycleProjects(names[0], names[1], admin)
    finally:
        delete_projects_strict(project_utils, names)


@dataclass
class ProjectWorld:
    project: str  # fresh, CLI analytics enabled
    clients: dict  # admin, member (a plain member), project_admin, unrelated
    admin_projects: ProjectUtils


@pytest.fixture
def project_world(
    cli_analytics_enabled,
    admin_utils,
    user_utils,
    project_utils,
    keycloak_utils,
    gate_admin_client,
    gate_member_client,
    unrelated_client,
):
    """A fresh enabled project with a plain member and a project admin of its own."""
    name = get_project_create_data()["name"]
    admin_email = f"autotest_cliprojadmin_{secrets.token_hex(4)}@email.com"
    try:
        admin_utils.create_project(name)
        admin_projects = ProjectUtils(gate_admin_client)
        admin_projects.update_project(name, cli_analytics_enabled=True)
        # before any grant: a user without membership must get 404, else the BE runs with
        # ENV=local (everyone is a global admin) and no role check proves anything
        assert_roles_are_real(unrelated_client, name)
        password = keycloak_utils.create_platform_user(email=admin_email)
        project_admin = get_client(username=admin_email, password=password)
        user_utils.assign_user_to_project(
            gate_member_client.users.about_me().user_id, name
        )
        user_utils.assign_user_to_project(
            project_admin.users.about_me().user_id, name, is_project_admin=True
        )
        wait_until_accessible(gate_member_client, [name])
        wait_until_accessible(project_admin, [name])
        yield ProjectWorld(
            name,
            {
                "admin": gate_admin_client,
                "member": gate_member_client,
                "project_admin": project_admin,
                "unrelated": unrelated_client,
            },
            admin_projects,
        )
    finally:
        try:
            delete_projects_strict(project_utils, [name])
        finally:
            keycloak_utils.delete_user(admin_email)


@dataclass
class HistorySession:
    world: ProjectWorld
    session_id: str
    repo: str


@pytest.fixture
def history_session(project_world, gate_member_client, gate_admin_client):
    """An accepted hook session of the world's project, waited for until it is listed."""
    sent = send_tracked(gate_member_client, project_world.project, E7)
    assert_sent_accepted(sent, "the history session sent to the enabled project")
    pending = wait_until_listed(
        CliAnalyticsApi(gate_admin_client), {sent.batch.session_id: sent.batch.repo}
    )
    assert_that(pending, empty(), "the history session never became listed")
    return HistorySession(project_world, sent.batch.session_id, sent.batch.repo)


@pytest.fixture
def role_client(request, history_session):
    """The client of the role named by the (indirect) parameter. The maintainer and the auditor
    are provisioned and verified only when a case needs them; neither uses a shared account."""
    role = request.param
    if role == "maintainer":
        return request.getfixturevalue("verified_maintainer_client")
    if role == "auditor":
        return request.getfixturevalue("verified_auditor_client")
    return history_session.world.clients[role]


@pytest.fixture(scope="module")
def flag_off_client():
    """A client of the separately configured flag-off backend (CODEMIE_API_DOMAIN_FLAG_OFF),
    logged in with the harness account (AUTH_USERNAME / AUTH_PASSWORD) read through
    CredentialsManager. Never used against the shared flag-on stand."""
    get = CredentialsManager.get_parameter
    return CodeMieClient(
        auth_server_url=get("AUTH_SERVER_URL", ""),
        auth_client_id=get("AUTH_CLIENT_ID", ""),
        auth_client_secret=get("AUTH_CLIENT_SECRET", ""),
        auth_realm_name=get("AUTH_REALM_NAME", ""),
        codemie_api_domain=FLAG_OFF_DOMAIN,
        verify_ssl=get("VERIFY_SSL", "false").lower() == "true",
        username=get("AUTH_USERNAME"),
        password=get("AUTH_PASSWORD"),
    )


@pytest.fixture(scope="module")
def cli_analytics_project(create_cli_analytics_project):
    """A project of its own per test module: filtering analytics by it selects the
    module's seeded sessions only, whatever else the environment holds."""
    return create_cli_analytics_project()


@pytest.fixture(scope="module")
def cli_analytics_users(cli_analytics_enabled, keycloak_utils):
    """Fresh users keyed by role; sessions are attributed to the user that sends them."""
    users = {}
    try:
        for role in CLI_ANALYTICS_USERS:
            email = f"autotest_clia_{secrets.token_hex(4)}@email.com"
            password = keycloak_utils.create_platform_user(email=email)
            user_client = get_client(username=email, password=password)
            user_id = user_client.users.about_me().user_id
            users[role] = CliAnalyticsUser(email, user_id, AnalyticsUtils(user_client))
        yield users
    finally:
        failed = {}
        for user in users.values():
            try:
                keycloak_utils.delete_user(user.email)
            except Exception as e:
                failed[user.email] = e
        if failed:
            raise AssertionError(f"users left behind on the stand: {failed}")


@pytest.fixture(scope="module")
def ingest_cli_sessions(
    cli_analytics_project, cli_analytics_users, user_utils, project_utils
):
    """Factory that sends the events of session seeds to a project (the module's
    project unless another is named), each seed as its own user. It does not wait
    for the rollup.

    The BE accepts a batch only for an enabled project the sender may use and named in
    X-CodeMie-Project, so a sender is made a member of the project once
    and the project is sent as the header. The memberships are removed at teardown, before
    the users (a fixture this one depends on) and the projects are deleted."""
    members: set[tuple[str, str]] = set()  # (user id, project)

    def _ensure_member(user: CliAnalyticsUser, project: str) -> None:
        if (user.user_id, project) in members:
            return
        user_utils.assign_user_to_project(user.user_id, project)
        members.add((user.user_id, project))
        wait_until_accessible(user.analytics_utils.client, [project])

    def _ingest(seeds: list[CliSessionSeed], project_name: str | None = None) -> None:
        project = project_name or cli_analytics_project
        for seed in seeds:
            user = cli_analytics_users[seed.user]
            _ensure_member(user, project)
            user.analytics_utils.ingest_cli_event_hooks(
                seed.events(project), project=project
            )
            otlp_logs = seed.otlp_logs(user.email)
            if otlp_logs:
                user.analytics_utils.ingest_cli_otlp_logs(otlp_logs, project=project)

    yield _ingest

    failed = {}
    for user_id, project in members:
        try:
            project_utils.remove_user_from_project(project, user_id)
        except Exception as e:
            failed[(user_id, project)] = e
    if failed:
        raise AssertionError(f"project memberships left behind on the stand: {failed}")


@pytest.fixture(scope="module")
def catalog_priced_model(client):
    """A model the stand's catalog prices, or None when there is none. Seeds that
    check no money can still use it; tests that check money take ``cost_model``."""
    return priced_model(client.llms.list())


@pytest.fixture(scope="module")
def cost_model(catalog_priced_model):
    """A model the stand's catalog prices: CLI Analytics money is tokens × its price."""
    if catalog_priced_model is None:
        pytest.skip("no LLM with an input and output price in the catalog")
    return catalog_priced_model


@pytest.fixture(scope="module")
def seed_cli_sessions(analytics_utils, ingest_cli_sessions):
    """Factory that ingests session seeds and waits until all of them are rolled up.

    Returns the seeds keyed by ``CliSessionSeed.key``.
    """

    def _seed(
        seeds: list[CliSessionSeed], project_name: str | None = None
    ) -> dict[str, CliSessionSeed]:
        ingest_cli_sessions(seeds, project_name)
        for seed in seeds:
            analytics_utils.wait_for_cli_session(seed.session_id)
        return {seed.key: seed for seed in seeds}

    return _seed
