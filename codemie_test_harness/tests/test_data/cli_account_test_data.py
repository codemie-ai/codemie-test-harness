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

"""Account kinds of the CLI session classification tests and what each kind may do.

An account kind is a disposable user built from an `AccountSpec` by `Provisioner.account`. The
expectations of the read and registration tests are grouped per kind in the rows below.
"""

from dataclasses import dataclass

import pytest

REGULAR = "regular"
EXTERNAL = "external"
SERVICE_ACCOUNT = "service_account"

NO_PROJECT_ROLE = "none"
PROJECT_MEMBER = "member"
PROJECT_ADMIN = "admin"


@dataclass(frozen=True)
class AccountSpec:
    """One account kind.

    first_login_type is the user type the identity provider reports at the first login: a
    regular user gets a personal project then, an external user or a service account never
    does. user_type is the type the account has when a test uses it; when it differs, the
    account is changed through the admin user update after its first login (it keeps its old
    personal project). project_role is the role in a shared project once the account joins one.
    """

    name: str
    user_type: str = REGULAR
    first_login_type: str = REGULAR
    is_maintainer: bool = False
    is_auditor: bool = False
    project_role: str = PROJECT_MEMBER

    @property
    def has_personal_project(self) -> bool:
        return self.first_login_type == REGULAR


REGULAR_MEMBER = AccountSpec("regular-member")
PROJECT_ADMIN_OF_A = AccountSpec("project-admin", project_role=PROJECT_ADMIN)
MAINTAINER = AccountSpec("maintainer", is_maintainer=True)
AUDITOR = AccountSpec("auditor", is_auditor=True)
EXTERNAL_NO_PROJECTS = AccountSpec(
    "external-no-projects", user_type=EXTERNAL, first_login_type=EXTERNAL
)
EXTERNAL_FORMER_REGULAR = AccountSpec("external-former-regular", user_type=EXTERNAL)
SERVICE_ACCOUNT_MEMBER = AccountSpec(
    "service-account", user_type=SERVICE_ACCOUNT, first_login_type=SERVICE_ACCOUNT
)

# The seven account kinds, one pytest parameter each (the id is the kind's name).
ACCOUNT_SPECS = [
    pytest.param(spec, id=spec.name)
    for spec in (
        REGULAR_MEMBER,
        PROJECT_ADMIN_OF_A,
        MAINTAINER,
        AUDITOR,
        EXTERNAL_NO_PROJECTS,
        EXTERNAL_FORMER_REGULAR,
        SERVICE_ACCOUNT_MEMBER,
    )
]


# Kinds that exist in the shared module world, and those among them that send a Personal session.
WORLD_ACCOUNT_KINDS = (
    "regular-member",
    "project-admin",
    "maintainer",
    "auditor",
    "service-account",
)
PERSONAL_SENDER_KINDS = ("regular-member", "project-admin", "maintainer", "auditor")


def specs_named(*names: str) -> list:
    """The ACCOUNT_SPECS parameters with these names, in the order given."""
    by_name = {param.id: param for param in ACCOUNT_SPECS}
    return [by_name[name] for name in names]


def spec_named(name: str) -> AccountSpec:
    return specs_named(name)[0].values[0]


# ── Reading CLI analytics by account kind ───────────────────────────────────────

# What a reader lists in the sessions list narrowed to the shared project.
LISTS_PROJECT_SESSIONS = "project sessions"  # the shared sessions of the project
LISTS_OWN_PRIVATE = "own private sessions"  # only its own private Personal sessions
LISTS_NOTHING = "nothing"

GLOBAL_ADMIN = "global-admin"


@dataclass(frozen=True)
class ReadRow:
    account: str  # key of AccountWorld.accounts, or GLOBAL_ADMIN
    aggregate_status: int  # HTTP status of an aggregate route (the cost view)
    listing: str
    shared_detail_status: int  # detail of a shared-project session


# The shared-project read gate lets in a global admin (a maintainer is one), and a project admin
# for their own projects; everybody else gets 403 on aggregate routes and only their own private
# Personal sessions on the sessions list. A Personal-paid session on a work project is project
# activity: it is not a private session of its owner, so its owner reads it only when the
# project rights allow it.
READ_ROWS = [
    pytest.param(
        ReadRow("regular-member", 403, LISTS_OWN_PRIVATE, 404), id="regular-member"
    ),
    pytest.param(
        ReadRow("project-admin", 200, LISTS_PROJECT_SESSIONS, 200), id="project-admin"
    ),
    pytest.param(
        ReadRow("maintainer", 200, LISTS_PROJECT_SESSIONS, 200), id="maintainer"
    ),
    pytest.param(ReadRow("auditor", 403, LISTS_OWN_PRIVATE, 404), id="auditor"),
    pytest.param(
        ReadRow("service-account", 403, LISTS_NOTHING, 404), id="service-account"
    ),
    pytest.param(
        ReadRow(GLOBAL_ADMIN, 200, LISTS_PROJECT_SESSIONS, 200), id="global-admin"
    ),
]


# ── Repository registration rights by account kind ──────────────────────────────


@dataclass(frozen=True)
class RegistrationRightsRow:
    account: str
    allowed: bool


# Global admins, maintainers and the project's own admin may register repositories; the route
# answers 404 to everybody else, so it does not reveal the project.
REGISTRATION_ALLOWED_STATUS = 200
REGISTRATION_REFUSED_STATUS = 404

REGISTRATION_RIGHTS_ROWS = [
    pytest.param(RegistrationRightsRow("regular-member", False), id="regular-member"),
    pytest.param(RegistrationRightsRow("project-admin", True), id="project-admin"),
    pytest.param(RegistrationRightsRow("maintainer", True), id="maintainer"),
    pytest.param(RegistrationRightsRow("auditor", False), id="auditor"),
    pytest.param(RegistrationRightsRow("service-account", False), id="service-account"),
]
