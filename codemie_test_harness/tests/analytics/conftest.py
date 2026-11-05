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
import time
from dataclasses import dataclass

import pytest
import requests
from codemie_sdk import CodeMieClient
from hamcrest import assert_that, empty

from codemie_test_harness.tests.test_data.cli_account_test_data import (
    GLOBAL_ADMIN,
    PERSONAL_SENDER_KINDS,
    WORLD_ACCOUNT_KINDS,
    spec_named,
)
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
from codemie_test_harness.tests.utils.analytics_utils import (
    CLI_ANALYTICS_FEATURE_ID,
    AnalyticsUtils,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CliAnalyticsApi,
    assert_project_deleted,
    assert_roles_are_real,
    delete_projects_strict,
    wait_until_accessible,
)
from codemie_test_harness.tests.utils.cli_gate_utils import (
    Batch,
    assert_sent_accepted,
    send_tracked,
    wait_until_listed,
)
from codemie_test_harness.tests.utils.cli_classification_utils import (
    ClassifiedSender,
    CorporateList,
    OrganizationPlan,
    Provisioner,
    new_remote,
    new_session,
    send_evidence,
    unique_organization,
    wait_for_policy,
    wait_for_session_row,
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

    Safe to call again with the same keys. pytest-rerunfailures reruns a module fixture
    whose setup failed, and that fixture builds new seeds with new session ids; sending
    them would add a second copy of every session that was already stored. So a key sent
    to a project before keeps its first seed. Seeds are sent one at a time: a seed whose
    send was accepted is not sent again, and only the seed whose send failed part-way is
    sent again, unchanged (the BE drops replayed events).

    A key therefore names one session per project and module: calling again with a key
    already used for that project returns the first seed, whatever the new seed holds.
    Give a deliberately different session its own key.
    """
    known: dict[tuple[str | None, str], CliSessionSeed] = {}
    accepted: set[tuple[str | None, str]] = set()

    def _seed(
        seeds: list[CliSessionSeed], project_name: str | None = None
    ) -> dict[str, CliSessionSeed]:
        seeds = [known.setdefault((project_name, seed.key), seed) for seed in seeds]
        for seed in seeds:
            if (project_name, seed.key) not in accepted:
                ingest_cli_sessions([seed], project_name)
                accepted.add((project_name, seed.key))
        for seed in seeds:
            analytics_utils.wait_for_cli_session(seed.session_id)
        return {seed.key: seed for seed in seeds}

    return _seed


# ── Session classification and routing ──────────────────────────────────────────


@pytest.fixture
def provisioner(
    cli_analytics_enabled,
    keycloak_utils,
    admin_utils,
    user_utils,
    project_utils,
    gate_admin_client,
):
    """Users, shared projects and repository registrations made by one test, all removed after it."""
    created = Provisioner(
        keycloak_utils, admin_utils, user_utils, project_utils, gate_admin_client
    )
    yield created
    created.cleanup()


@pytest.fixture(scope="module")
def module_provisioner(
    cli_analytics_enabled,
    keycloak_utils,
    admin_utils,
    user_utils,
    project_utils,
    gate_admin_client,
):
    """Like `provisioner`, for worlds shared by the tests of one module."""
    created = Provisioner(
        keycloak_utils, admin_utils, user_utils, project_utils, gate_admin_client
    )
    yield created
    created.cleanup()


@dataclass
class ClassificationWorld:
    sender: ClassifiedSender  # an ordinary user, a member of `project`
    project: str  # shared, CLI analytics enabled
    admin_api: CliAnalyticsApi  # a global admin: lists the shared sessions


@pytest.fixture(scope="module")
def classification_world(module_provisioner, gate_admin_client):
    sender = module_provisioner.sender()
    project = module_provisioner.project(sender)
    return ClassificationWorld(sender, project, CliAnalyticsApi(gate_admin_client))


@dataclass
class RoutingWorld:
    """Projects A, B and D are the sender's (D is the default); N is enabled but the sender is
    no member. The remotes of B and N are registered to them."""

    sender: ClassifiedSender
    admin_api: CliAnalyticsApi
    projects: dict
    remotes: dict

    def project(self, key: str | None) -> str | None:
        return self.projects.get(key)

    def remote(self, key: str | None) -> str | None:
        return self.remotes.get(key)


@pytest.fixture(scope="module")
def routing_world(module_provisioner, gate_admin_client):
    sender = module_provisioner.sender()
    projects = {key: module_provisioner.project(sender) for key in ("A", "B", "D")}
    projects["N"] = module_provisioner.project()
    module_provisioner.set_default(sender, projects["D"])
    remotes = {"B": new_remote(), "N": new_remote()}
    module_provisioner.register(projects["B"], remotes["B"])
    module_provisioner.register(projects["N"], remotes["N"])
    return RoutingWorld(sender, CliAnalyticsApi(gate_admin_client), projects, remotes)


def _corporate_list_scope(customer_config_utils, gate_admin_client):
    """Generator body of the corporate-list fixtures: yields a setter, restores the setting."""
    declaration = customer_config_utils.get_declaration(CLI_ANALYTICS_FEATURE_ID)
    original = declaration["value"]
    api = CliAnalyticsApi(gate_admin_client)
    handle = CorporateList(customer_config_utils, CLI_ANALYTICS_FEATURE_ID, original)
    yield lambda organizations: handle.set(api, organizations)
    if declaration["overridden"]:
        customer_config_utils.save_setting(CLI_ANALYTICS_FEATURE_ID, original)
    else:
        customer_config_utils.reset_setting(CLI_ANALYTICS_FEATURE_ID)
    wait_for_policy(
        api,
        [
            line.strip()
            for line in str(original.get("corporateOrganizations") or "").splitlines()
            if line.strip()
        ],
    )


@pytest.fixture
def corporate_list(cli_analytics_enabled, customer_config_utils, gate_admin_client):
    """The installation's corporate organization list: `.set(organizations)` writes it through
    the customer config and waits until the classification policy shows it; the setting is put
    back (an own override kept, a default restored) when the test ends."""
    yield from _corporate_list_scope(customer_config_utils, gate_admin_client)


@pytest.fixture(scope="module")
def module_corporate_list(
    cli_analytics_enabled, customer_config_utils, gate_admin_client
):
    """Like `corporate_list`, for worlds shared by the tests of one module."""
    yield from _corporate_list_scope(customer_config_utils, gate_admin_client)


@pytest.fixture
def organizations(corporate_list):
    """Two fresh organization names; the corporate list is set to the first one only."""
    plan = OrganizationPlan(unique_organization(), unique_organization())
    corporate_list([plan.corporate])
    return plan


@pytest.fixture(scope="module")
def module_organizations(module_corporate_list):
    """Like `organizations`, for worlds shared by the tests of one module."""
    plan = OrganizationPlan(unique_organization(), unique_organization())
    module_corporate_list([plan.corporate])
    return plan


@dataclass
class AccountWorld:
    """One shared project with CLI analytics on, one account of each kind that is a member of it
    (keyed by the kind's name), an ordinary owner who is a member too, and a corporate list that
    names `organizations.corporate` only."""

    provisioner: Provisioner
    admin_api: CliAnalyticsApi
    project: str
    organizations: OrganizationPlan
    owner: ClassifiedSender
    accounts: dict

    def api(self, account: str) -> CliAnalyticsApi:
        """The read API of an account kind, or of the global admin."""
        if account == GLOBAL_ADMIN:
            return self.admin_api
        return self.accounts[account].api


@pytest.fixture(scope="module")
def account_world(module_provisioner, module_organizations, gate_admin_client):
    project = module_provisioner.project()
    owner = module_provisioner.sender()
    module_provisioner.join(owner, project)
    accounts = {
        name: module_provisioner.account(spec_named(name), project)
        for name in WORLD_ACCOUNT_KINDS
    }
    return AccountWorld(
        module_provisioner,
        CliAnalyticsApi(gate_admin_client),
        project,
        module_organizations,
        owner,
        accounts,
    )


@dataclass
class SentSession:
    batch: Batch
    response: requests.Response


@dataclass
class AccountSessions:
    """The sessions the account kinds sent once, all listed before any test reads them.

    personal: a Personal session of each ordinary kind (regular member, project admin,
    maintainer, auditor) with a link to the shared project; corporate: the owner's Corporate
    session in the shared project; private: the owner's Personal session; service: the Personal
    session of the service account with a link to the shared project.
    """

    personal: dict
    corporate: SentSession
    private: SentSession
    service: SentSession
    sent_at: float


@pytest.fixture(scope="module")
def account_sessions(account_world):
    world = account_world
    other = world.organizations.other
    linked = {"project": world.project, "project_source": "linked_folder"}

    def _send(account, **evidence) -> SentSession:
        batch = new_session()
        return SentSession(batch, send_evidence(account.client, batch, **evidence))

    personal = {
        name: _send(world.accounts[name], organization=other, **linked)
        for name in PERSONAL_SENDER_KINDS
    }
    corporate = _send(world.owner, organization=world.organizations.corporate, **linked)
    private = _send(world.owner, organization=other)
    service = _send(world.accounts["service-account"], organization=other, **linked)
    sent_at = time.monotonic()
    for sent in (corporate, service):
        wait_for_session_row(
            world.admin_api,
            sent.batch.session_id,
            sent.batch.repo,
            projects=world.project,
        )
    own_sessions = [
        (world.owner, private),
        *[(world.accounts[name], personal[name]) for name in PERSONAL_SENDER_KINDS],
    ]
    for account, sent in own_sessions:
        wait_for_session_row(
            account.api,
            sent.batch.session_id,
            sent.batch.repo,
            personal_only="true",
        )
    return AccountSessions(personal, corporate, private, service, sent_at)
