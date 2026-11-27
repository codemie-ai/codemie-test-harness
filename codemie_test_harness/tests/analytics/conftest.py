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

import time
from contextlib import ExitStack
from dataclasses import dataclass

import pytest
import requests
from codemie_sdk import CodeMieClient
from hamcrest import assert_that, empty, equal_to

from codemie_test_harness.tests.test_data.cli_account_test_data import (
    EXTERNAL,
    EXTERNAL_FORMER_REGULAR,
    EXTERNAL_NO_PROJECTS,
    GLOBAL_ADMIN,
    PERSONAL_SENDER_KINDS,
    WORK_PROJECT_SENDERS,
    WORLD_ACCOUNT_KINDS,
    spec_named,
)
from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    CLI_ANALYTICS_USERS,
    DISABLED,
    E7,
    FLAG_OFF_DOMAIN,
    CliSessionSeed,
    priced_model,
)
from codemie_test_harness.tests.test_data.cli_classification_test_data import (
    ORGANIZATION_ENVELOPES_AT_THE_LIMIT,
    ORGANIZATION_SPELLINGS,
    PLACEMENT_ROWS,
    PROFILE_ROWS,
    ROUTED_CASES,
)
from codemie_test_harness.tests.test_data.projects_test_data import (
    get_project_create_data,
)
from codemie_test_harness.tests.utils.analytics_utils import (
    CLI_ANALYTICS_FEATURE_ID,
    AnalyticsUtils,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    CT_NDJSON,
    CliAnalyticsApi,
    assert_accepted,
    assert_project_deleted,
    assert_roles_are_real,
    delete_projects_strict,
    wait_until_accessible,
)
from codemie_test_harness.tests.utils.cli_gate_utils import (
    Batch,
    assert_sent_accepted,
    send_tracked,
    wait_until_ingest_ready,
    wait_until_listed,
)
from codemie_test_harness.tests.utils.cli_classification_utils import (
    LINKED,
    ClassifiedSender,
    CorporateList,
    OrganizationPlan,
    Provisioner,
    classification_headers,
    in_parallel,
    new_remote,
    new_session,
    read_policy,
    send_evidence,
    unique_organization,
    wait_for_policy,
    wait_for_session_row,
)
from codemie_test_harness.tests.utils.user_lifecycle_utils import (
    new_logged_in_user,
    user_email,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.logger_util import setup_logger
from codemie_test_harness.tests.utils.project_utils import ProjectUtils
from codemie_test_harness.tests.utils.user_utils import UserUtils

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
        wait_until_ingest_ready(gate_member_client, {names[0]: "", names[1]: DISABLED})
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
        wait_until_ingest_ready(gate_member_client, dict.fromkeys(names, ""))
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
    with ExitStack() as cleanup:
        # Created before the project so that its cleanup runs after the project's.
        project_admin = cleanup.enter_context(
            new_logged_in_user(
                keycloak_utils, user_email("cliprojadmin"), admin=False, strict=True
            )
        )
        cleanup.callback(delete_projects_strict, project_utils, [name])
        admin_utils.create_project(name)
        admin_projects = ProjectUtils(gate_admin_client)
        admin_projects.update_project(name, cli_analytics_enabled=True)
        # before any grant: a user without membership must get 404, else the BE runs with
        # ENV=local (everyone is a global admin) and no role check proves anything
        assert_roles_are_real(unrelated_client, name)
        user_utils.assign_user_to_project(
            gate_member_client.users.about_me().user_id, name
        )
        user_utils.assign_user_to_project(
            project_admin.user_id, name, is_project_admin=True
        )
        wait_until_accessible(gate_member_client, [name])
        wait_until_accessible(project_admin.client, [name])
        wait_until_ingest_ready(gate_member_client, {name: ""})
        yield ProjectWorld(
            name,
            {
                "admin": gate_admin_client,
                "member": gate_member_client,
                "project_admin": project_admin.client,
                "unrelated": unrelated_client,
            },
            admin_projects,
        )


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
    # strict: a user that cannot be deleted fails the teardown instead of being left behind.
    with ExitStack() as cleanup:
        users = {}
        for role in CLI_ANALYTICS_USERS:
            user = cleanup.enter_context(
                new_logged_in_user(
                    keycloak_utils, user_email("clia"), admin=False, strict=True
                )
            )
            users[role] = CliAnalyticsUser(
                user.email, user.user_id, AnalyticsUtils(user.client)
            )
        yield users


@pytest.fixture(scope="module")
def ingest_cli_sessions(
    cli_analytics_project, cli_analytics_users, user_utils, project_utils
):
    """Factory that sends the events of session seeds to a project (the module's
    project unless another is named), each seed as its own user: hook events, OTLP logs
    and, for a seed with an ``otlp_traces()`` payload, OTLP traces. It does not wait
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
            otlp_traces = getattr(seed, "otlp_traces", None)
            traces = otlp_traces() if otlp_traces else None
            if traces:
                user.analytics_utils.ingest_cli_otlp_traces(traces, project=project)

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
#
# The classification, routing and account tests spend their time waiting: for a setting to reach
# every replica, for a session to show up on the next rollup refresh, and for an absence window
# to pass. So the waits are shared: the corporate list is set once for the run, the sessions of
# the parametrized rows are sent together when a module starts, users and projects are made at
# the same time, and the sessions whose absence the run checks are sent first, so that their
# windows run while the other tests do. The tests that observe an absence come last in their
# modules.


@pytest.fixture(scope="session")
def classification_admin_client(keycloak_utils, user_utils):
    """Global admin of the classification tests, one for the run: it makes their projects and
    lists the shared sessions."""
    with new_logged_in_user(
        keycloak_utils, user_email("clsadmin"), admin=False
    ) as user:
        user_utils.update_admin_user(user.user_id, is_admin=True)
        UserUtils(user.client).wait_until_user_management_effective()
        yield user.client


def _provisioner(keycloak_utils, admin_utils, user_utils, project_utils, admin_client):
    created = Provisioner(
        keycloak_utils, admin_utils, user_utils, project_utils, admin_client
    )
    yield created
    created.cleanup()


@pytest.fixture
def provisioner(
    cli_analytics_enabled,
    keycloak_utils,
    admin_utils,
    user_utils,
    project_utils,
    classification_admin_client,
):
    """Users, shared projects and repository registrations made by one test, all removed after it."""
    yield from _provisioner(
        keycloak_utils,
        admin_utils,
        user_utils,
        project_utils,
        classification_admin_client,
    )


@pytest.fixture(scope="module")
def module_provisioner(
    cli_analytics_enabled,
    keycloak_utils,
    admin_utils,
    user_utils,
    project_utils,
    classification_admin_client,
):
    """Like `provisioner`, for worlds shared by the tests of one module."""
    yield from _provisioner(
        keycloak_utils,
        admin_utils,
        user_utils,
        project_utils,
        classification_admin_client,
    )


@pytest.fixture(scope="session")
def run_provisioner(
    cli_analytics_enabled,
    keycloak_utils,
    admin_utils,
    user_utils,
    project_utils,
    classification_admin_client,
):
    """Like `provisioner`, for the run-wide world of `classification_run`."""
    yield from _provisioner(
        keycloak_utils,
        admin_utils,
        user_utils,
        project_utils,
        classification_admin_client,
    )


@dataclass
class SentSession:
    batch: Batch
    response: requests.Response


def _send(account: ClassifiedSender, **evidence) -> SentSession:
    batch = new_session()
    return SentSession(batch, send_evidence(account.client, batch, **evidence))


def _corporate_list_scope(customer_config_utils, admin_client):
    """Generator body of the corporate-list fixtures: yields a setter, then puts back the setting
    found when the fixture started (an own override kept, a default restored)."""
    declaration = customer_config_utils.get_declaration(CLI_ANALYTICS_FEATURE_ID)
    original = declaration["value"]
    api = CliAnalyticsApi(admin_client)
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
def corporate_list(
    cli_analytics_enabled, customer_config_utils, classification_admin_client
):
    """The installation's corporate organization list for one test: `.set(organizations)` writes
    it through the customer config and waits until the classification policy shows it; the list
    the test started with (the run's list, when `classification_run` set it) is put back after."""
    yield from _corporate_list_scope(customer_config_utils, classification_admin_client)


@pytest.fixture(scope="session")
def run_corporate_list(
    cli_analytics_enabled, customer_config_utils, classification_admin_client
):
    """Like `corporate_list`, for the whole run."""
    yield from _corporate_list_scope(customer_config_utils, classification_admin_client)


def _stranded_sender(provisioner: Provisioner, user_utils) -> ClassifiedSender:
    """A user whose only project is the personal project it can no longer receive sessions in.

    An administrator cannot detach a user from its personal project (the membership endpoint
    answers 403 for it), so the user is changed to the external user type instead: such a user
    never receives a new session in a personal project, and has no other project, so neither a
    link, a registration nor a default project is usable.
    """
    sender = provisioner.sender()
    for project_name in user_utils.get_user_project_names(sender.user_id):
        if project_name.lower() != sender.email.lower():
            user_utils.remove_user_from_project(sender.user_id, project_name)
    user_utils.update_admin_user(sender.user_id, user_type=EXTERNAL)
    assert_that(
        [name.lower() for name in user_utils.get_user_project_names(sender.user_id)],
        equal_to([sender.email.lower()]),
        "setup: the user must keep only its personal project, so it has no other default project",
    )
    assert_that(
        user_utils.get_admin_user(sender.user_id).user_type,
        equal_to(EXTERNAL),
        "setup: the user must be of the external type, which has no usable personal project",
    )
    return sender


@dataclass
class StrandedProbe:
    """TC-015: stranded is a CodeMie session of an external user whose only project is the
    personal project it can no longer receive sessions in, so no destination is usable; control
    is a CodeMie session of an ordinary user, stored in its default project."""

    stranded: SentSession
    control: SentSession
    sent_at: float


@pytest.fixture(scope="session")
def stranded_probe(run_provisioner, user_utils):
    """Sent once for the run (and at its start when `classification_run` is used), so that the
    absence window of `stranded` passes while the other tests run. It needs no corporate list."""
    provisioner = run_provisioner

    def _member() -> ClassifiedSender:
        member = provisioner.sender()
        provisioner.set_default(member, provisioner.project(member))
        return member

    stranded_sender, member = in_parallel(
        lambda: _stranded_sender(provisioner, user_utils), _member
    )
    probe = StrandedProbe(
        stranded=_send(stranded_sender, routed="1"),
        control=_send(member, routed="1"),
        sent_at=0.0,
    )
    probe.sent_at = time.monotonic()
    return probe


@dataclass
class AbsenceProbes:
    """Sessions whose absence the run checks, sent when the run's corporate list is set, so that
    their absence windows (ABSENCE_WINDOW_S from `sent_at`) pass while the other tests run.

    owner and other: ordinary members of `project`. personal: the owner's Personal session;
    shared: the owner's CodeMie session in `project`, listed in the shared list; others_personal:
    the other user's Personal session. former_regular: an external user that was regular at its
    first login, a member of `project`; no_destination: its Personal session without a link,
    for which no project is usable. kind_owners: an account of each kind of
    PERSONAL_SENDER_KINDS, a member (the project admin: an admin) of `project`; kind_personal:
    the Personal session each of them sent with a link to `project`.
    """

    project: str
    owner: ClassifiedSender
    other: ClassifiedSender
    former_regular: ClassifiedSender
    kind_owners: dict
    personal: SentSession
    shared: SentSession
    others_personal: SentSession
    no_destination: SentSession
    kind_personal: dict
    sent_at: float


@dataclass
class ClassificationRun:
    """What the tests that need the corporate list share for the whole run: the list names
    `organizations.corporate` only, and the absence probes were sent under it."""

    organizations: OrganizationPlan
    probes: AbsenceProbes


@pytest.fixture(scope="session")
def classification_run(run_corporate_list, run_provisioner, stranded_probe):
    """Sets the run's corporate list and sends the absence probes under it. It takes
    `stranded_probe` too, so that probe is also sent when a run with these tests starts."""
    provisioner = run_provisioner
    plan = OrganizationPlan(unique_organization(), unique_organization())
    project = provisioner.project()

    def _member() -> ClassifiedSender:
        sender = provisioner.sender()
        provisioner.add_member(sender, project)
        return sender

    _, owner, other, former_regular, *kind_owners = in_parallel(
        lambda: run_corporate_list([plan.corporate]),
        _member,
        _member,
        lambda: provisioner.account(EXTERNAL_FORMER_REGULAR, project),
        *(
            lambda name=name: provisioner.account(spec_named(name), project)
            for name in PERSONAL_SENDER_KINDS
        ),
    )
    kind_owners = dict(zip(PERSONAL_SENDER_KINDS, kind_owners))
    linked = {"project": project, **LINKED}
    probes = AbsenceProbes(
        project=project,
        owner=owner,
        other=other,
        former_regular=former_regular,
        kind_owners=kind_owners,
        personal=_send(owner, organization=plan.other),
        shared=_send(owner, routed="1", **linked),
        others_personal=_send(other, organization=plan.other),
        no_destination=_send(former_regular, organization=plan.other),
        kind_personal={
            name: _send(account, organization=plan.other, **linked)
            for name, account in kind_owners.items()
        },
        sent_at=0.0,
    )
    probes.sent_at = time.monotonic()
    return ClassificationRun(plan, probes)


@pytest.fixture
def organizations(classification_run):
    """The run's two organization names; the corporate list names the first one only."""
    return classification_run.organizations


@dataclass
class FilterWorld:
    """TC-013: a sender with two projects, `default` (its default) and `registered`, to which
    `remote` is registered."""

    sender: ClassifiedSender
    default: str
    registered: str
    remote: str


def _filter_world(provisioner: Provisioner) -> FilterWorld:
    sender = provisioner.sender()
    default, registered = provisioner.projects(2, sender)
    provisioner.set_default(sender, default)
    remote = new_remote()
    provisioner.register(registered, remote)
    return FilterWorld(sender, default, registered, remote)


@dataclass
class ClassificationWorld:
    """sender: an ordinary user, a member of `project` (shared, CLI analytics enabled);
    admin_api: a global admin that lists the shared sessions; filters: the TC-013 world."""

    sender: ClassifiedSender
    project: str
    admin_api: CliAnalyticsApi
    filters: FilterWorld


@pytest.fixture(scope="module")
def classification_world(module_provisioner, classification_admin_client):
    provisioner = module_provisioner

    def _sender_project() -> tuple:
        sender = provisioner.sender()
        return sender, provisioner.project(sender)

    (sender, project), filters = in_parallel(
        _sender_project, lambda: _filter_world(provisioner)
    )
    return ClassificationWorld(
        sender, project, CliAnalyticsApi(classification_admin_client), filters
    )


def _params(rows) -> list:
    """The values of a list of single-value pytest.param rows."""
    return [row.values[0] for row in rows]


@dataclass
class ClassificationSessions:
    """The sessions of the classification module, sent together and all listed.

    routed, spellings, at_the_limit: keyed by the row of ROUTED_CASES, ORGANIZATION_SPELLINGS and
    ORGANIZATION_ENVELOPES_AT_THE_LIMIT; without_organization: the session that names no
    organization; corporate_bound (TC-021): a Corporate session bound to the project, sent under
    `corporate_policy`; filtered (TC-013): the filter world's sessions keyed "linked",
    "profile", "registered", "default" and "personal".
    """

    routed: dict
    spellings: dict
    at_the_limit: dict
    without_organization: SentSession
    corporate_bound: SentSession
    corporate_policy: dict
    filtered: dict


@pytest.fixture(scope="module")
def classification_sessions(classification_world, classification_run):
    world, plan = classification_world, classification_run.organizations
    linked = {"project": world.project, **LINKED}
    sent = ClassificationSessions(
        routed={
            case: _send(
                world.sender,
                routed=case.routed_value,
                organization=plan.pick(case.organization),
                **linked,
            )
            for case in _params(ROUTED_CASES)
        },
        spellings={
            spelling: _send(world.sender, **linked, **spelling(plan.corporate))
            for spelling in _params(ORGANIZATION_SPELLINGS)
        },
        at_the_limit={
            envelope: _send(world.sender, organization_encoded=envelope, **linked)
            for envelope in _params(ORGANIZATION_ENVELOPES_AT_THE_LIMIT)
        },
        without_organization=_send(world.sender, **linked),
        corporate_bound=_send(world.sender, organization=plan.corporate, **linked),
        corporate_policy=read_policy(world.sender.api),
        filtered=_send_filtered(world.filters, plan),
    )
    shared = [
        *sent.routed.values(),
        *sent.spellings.values(),
        sent.without_organization,
        sent.corporate_bound,
    ]
    for session in shared:
        wait_for_session_row(
            world.admin_api,
            session.batch.session_id,
            session.batch.repo,
            projects=world.project,
        )
    filters = world.filters
    for key in ("linked", "profile", "registered", "default"):
        wait_for_session_row(
            world.admin_api,
            sent.filtered[key].batch.session_id,
            sent.filtered[key].batch.repo,
            users=filters.sender.email,
        )
    for session in sent.at_the_limit.values():
        wait_for_session_row(
            world.sender.api,
            session.batch.session_id,
            session.batch.repo,
            personal_only="true",
        )
    wait_for_session_row(
        filters.sender.api,
        sent.filtered["personal"].batch.session_id,
        sent.filtered["personal"].batch.repo,
        personal_only="true",
    )
    return sent


def _send_filtered(filters: FilterWorld, plan: OrganizationPlan) -> dict:
    """TC-013: one session of each origin, and a Personal one, from the filter world's sender."""
    sender = filters.sender
    return {
        "linked": _send(
            sender, organization=plan.corporate, project=filters.default, **LINKED
        ),
        "profile": _send(
            sender, routed="1", project=filters.default, project_source="profile"
        ),
        "registered": _send(sender, repo_remote=filters.remote),
        "default": _send(sender, organization=plan.corporate),
        "personal": _send(sender, organization=plan.other),
    }


@dataclass
class RoutingWorld:
    """Projects A, B and D are the sender's (D is the default); N is enabled but the sender is
    no member. The remotes of B and N are registered to them.

    bound: two sessions bound to a project of their own senders, keyed "membership" and
    "project" by what the TC-020 test that uses it takes away; owner_conflict: the TC-018 owner,
    intruder and session. Both are made and sent with the world, so the wait for them to be
    listed overlaps with the module's other sessions."""

    sender: ClassifiedSender
    admin_api: CliAnalyticsApi
    projects: dict
    remotes: dict
    bound: dict
    owner_conflict: "OwnerConflict"

    def project(self, key: str | None) -> str | None:
        return self.projects.get(key)

    def remote(self, key: str | None) -> str | None:
        return self.remotes.get(key)


@dataclass
class BoundSession:
    sender: ClassifiedSender
    project: str  # the project the session is bound to
    default: str  # the sender's default project
    sent: SentSession
    history: dict | None = None  # the session's row as first listed (`bound_sessions`)


def _bound_session(provisioner: Provisioner) -> BoundSession:
    """A session bound to a project; the sender also has another project, its default."""
    sender = provisioner.sender()
    project, default = provisioner.projects(2, sender)
    provisioner.set_default(sender, default)
    sent = _send(sender, routed="1", project=project, **LINKED)
    return BoundSession(sender, project, default, sent)


@dataclass
class OwnerConflict:
    """TC-018: owner and intruder are members of `project`; sent is the owner's CodeMie session
    in it, naming an unrelated organization."""

    owner: ClassifiedSender
    intruder: ClassifiedSender
    project: str
    sent: SentSession


def _owner_conflict(provisioner: Provisioner) -> OwnerConflict:
    owner, intruder = provisioner.senders(2)
    project = provisioner.project(owner, intruder)
    sent = _send(
        owner,
        routed="1",
        organization="unrelated-claude-account",
        project=project,
        **LINKED,
    )
    return OwnerConflict(owner, intruder, project, sent)


@pytest.fixture(scope="module")
def routing_world(module_provisioner, classification_admin_client):
    provisioner = module_provisioner

    def _sender_projects() -> tuple:
        sender = provisioner.sender()
        return sender, provisioner.projects(3, sender), provisioner.project()

    (sender, (a, b, d), n), membership, project, owner_conflict = in_parallel(
        _sender_projects,
        lambda: _bound_session(provisioner),
        lambda: _bound_session(provisioner),
        lambda: _owner_conflict(provisioner),
    )
    projects = {"A": a, "B": b, "D": d, "N": n}
    provisioner.set_default(sender, projects["D"])
    remotes = {"B": new_remote(), "N": new_remote()}
    provisioner.register(projects["B"], remotes["B"])
    provisioner.register(projects["N"], remotes["N"])
    return RoutingWorld(
        sender,
        CliAnalyticsApi(classification_admin_client),
        projects,
        remotes,
        {"membership": membership, "project": project},
        owner_conflict,
    )


@dataclass
class RoutingSessions:
    """The sessions of the parametrized routing rows, sent together and all listed: keyed by the
    row of PLACEMENT_ROWS and PROFILE_ROWS; personal is the ordinary user's Personal session sent
    with a profile project."""

    placement: dict
    profile: dict
    personal: SentSession


@pytest.fixture(scope="module")
def routing_sessions(routing_world, classification_run):
    world, plan = routing_world, classification_run.organizations
    sent = RoutingSessions(
        placement={
            row: _send(
                world.sender,
                project=world.project(row.link),
                project_source=row.project_source,
                repo_remote=world.remote(row.registered),
                **classification_headers(row.subscription, plan),
            )
            for row in _params(PLACEMENT_ROWS)
        },
        profile={
            row: _send(
                world.sender,
                organization=plan.corporate,
                project=world.project(row.profile_project),
                project_source=row.project_source,
                repo_remote=world.remote(row.registered),
            )
            for row in _params(PROFILE_ROWS)
        },
        personal=_send(
            world.sender,
            organization=plan.other,
            project=world.project("A"),
            project_source="profile",
            repo_remote=world.remote("B"),
        ),
    )
    for row, session in (*sent.placement.items(), *sent.profile.items()):
        wait_for_session_row(
            world.admin_api,
            session.batch.session_id,
            session.batch.repo,
            projects=world.project(row.project),
        )
    wait_for_session_row(
        world.sender.api,
        sent.personal.batch.session_id,
        sent.personal.batch.repo,
        personal_only="true",
    )
    return sent


@pytest.fixture(scope="module")
def bound_sessions(routing_world):
    """The world's bound sessions, each accepted and listed in its project (`history`)."""
    for bound in routing_world.bound.values():
        assert_accepted(bound.sent.response, "event-hooks", CT_NDJSON)
        bound.history = wait_for_session_row(
            routing_world.admin_api,
            bound.sent.batch.session_id,
            bound.sent.batch.repo,
            projects=bound.project,
        )
    return routing_world.bound


@dataclass
class AccountWorld:
    """One shared project with CLI analytics on, one account of each kind that is a member of it
    (keyed by the kind's name), an ordinary owner who is a member too, and the run's corporate
    list, which names `organizations.corporate` only.

    TC-004: work_project_senders, keyed by the names of WORK_PROJECT_SENDERS, are accounts that
    cannot have a personal project, members of the project; no_projects is an external user with
    no project at all, which its test joins to the project."""

    provisioner: Provisioner
    admin_api: CliAnalyticsApi
    project: str
    organizations: OrganizationPlan
    owner: ClassifiedSender
    accounts: dict
    work_project_senders: dict
    no_projects: ClassifiedSender

    def api(self, account: str) -> CliAnalyticsApi:
        """The read API of an account kind, or of the global admin."""
        if account == GLOBAL_ADMIN:
            return self.admin_api
        return self.accounts[account].api


@pytest.fixture(scope="session")
def account_world(run_provisioner, classification_run, classification_admin_client):
    """One for the run: the account tests and their absence checks in
    test_cli_analytics_unlisted_sessions.py share it."""
    provisioner = run_provisioner
    project = provisioner.project()

    def _owner() -> ClassifiedSender:
        owner = provisioner.sender()
        provisioner.join(owner, project)
        return owner

    specs = [
        *(spec_named(name) for name in WORLD_ACCOUNT_KINDS),
        *WORK_PROJECT_SENDERS,
    ]
    owner, no_projects, *accounts = in_parallel(
        _owner,
        lambda: provisioner.account(EXTERNAL_NO_PROJECTS),
        *(lambda spec=spec: provisioner.account(spec, project) for spec in specs),
    )
    kinds = len(WORLD_ACCOUNT_KINDS)
    return AccountWorld(
        provisioner,
        CliAnalyticsApi(classification_admin_client),
        project,
        classification_run.organizations,
        owner,
        dict(zip(WORLD_ACCOUNT_KINDS, accounts[:kinds])),
        {
            spec.name: account
            for spec, account in zip(WORK_PROJECT_SENDERS, accounts[kinds:])
        },
        no_projects,
    )


@dataclass
class AccountSessions:
    """The sessions the account kinds sent once, all listed before any test reads them.

    personal: a Personal session of each ordinary kind (regular member, project admin,
    maintainer, auditor) with a link to the shared project; corporate: the owner's Corporate
    session in the shared project; private: the owner's Personal session; service: the Personal
    session of the service account with a link to the shared project; member: the regular
    member's Corporate session in the shared project; work_project (TC-004): the Personal
    session of each work-project sender, linked to the shared project.
    """

    personal: dict
    corporate: SentSession
    private: SentSession
    service: SentSession
    member: SentSession
    work_project: dict
    sent_at: float

    @property
    def shared(self) -> list[SentSession]:
        """The sessions stored in the shared project (none of them private)."""
        return [self.corporate, self.service, self.member]

    def shared_sent_by(self, kind: str) -> set[str]:
        """Ids of the shared-project sessions the account kind sent itself."""
        senders = {"service-account": self.service, "regular-member": self.member}
        return {senders[kind].batch.session_id} if kind in senders else set()


@pytest.fixture(scope="session")
def account_sessions(account_world):
    world = account_world
    other = world.organizations.other
    linked = {"project": world.project, **LINKED}
    personal = {
        name: _send(world.accounts[name], organization=other, **linked)
        for name in PERSONAL_SENDER_KINDS
    }
    corporate = _send(world.owner, organization=world.organizations.corporate, **linked)
    private = _send(world.owner, organization=other)
    service = _send(world.accounts["service-account"], organization=other, **linked)
    member = _send(
        world.accounts["regular-member"],
        organization=world.organizations.corporate,
        **linked,
    )
    work_project = {
        name: _send(account, organization=other, **linked)
        for name, account in world.work_project_senders.items()
    }
    sent_at = time.monotonic()
    for sent in (corporate, service, member, *work_project.values()):
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
    return AccountSessions(
        personal, corporate, private, service, member, work_project, sent_at
    )
