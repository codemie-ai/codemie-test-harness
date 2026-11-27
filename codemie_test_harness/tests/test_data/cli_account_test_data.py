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

    def project_names(self, email: str, *shared: str) -> list[str]:
        """Lower-case, sorted names of the projects an account of this kind with `email` is a
        member of after joining `shared`: those and, when it has one, its personal project."""
        personal = (email,) if self.has_personal_project else ()
        return sorted(name.lower() for name in (*shared, *personal))


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

# Every account kind reads the aggregates and the sessions list; the kind decides what they hold.
# The aggregates and the shared sessions list never hold a private Personal session. A global
# admin (a maintainer is one) and an auditor read every shared session; a project admin those of
# their own projects; every account also reads the shared sessions it sent itself. A
# Personal-paid session on a work project is project activity, not a private session.
#
# What a reader lists in the shared sessions list narrowed to the shared project:
LISTS_PROJECT_SESSIONS = "project sessions"  # every shared session of the project
LISTS_OWN_SHARED = "own shared sessions"  # only the shared sessions it sent itself

GLOBAL_ADMIN = "global-admin"

# A private Personal session is read (detail, and the personal_only list) by its owner and by
# the kinds that read every user's private sessions: a global admin, a maintainer and an auditor.
PRIVATE_DETAIL_STATUS = {
    "regular-member": 404,
    "project-admin": 404,
    "maintainer": 200,
    "auditor": 200,
    "service-account": 404,
    GLOBAL_ADMIN: 200,
}


@dataclass(frozen=True)
class ReadRow:
    account: str  # key of AccountWorld.accounts, or GLOBAL_ADMIN
    listing: str
    private_detail_status: int  # detail of another user's private Personal session
    private_rows_as_own: int  # rows of that session in the reader's personal_only list


READ_ROWS = [
    pytest.param(
        ReadRow("regular-member", LISTS_OWN_SHARED, 404, 0), id="regular-member"
    ),
    pytest.param(
        ReadRow("project-admin", LISTS_PROJECT_SESSIONS, 404, 0), id="project-admin"
    ),
    pytest.param(
        ReadRow("maintainer", LISTS_PROJECT_SESSIONS, 200, 1), id="maintainer"
    ),
    pytest.param(ReadRow("auditor", LISTS_PROJECT_SESSIONS, 200, 1), id="auditor"),
    pytest.param(
        ReadRow("service-account", LISTS_OWN_SHARED, 404, 0), id="service-account"
    ),
    pytest.param(
        ReadRow(GLOBAL_ADMIN, LISTS_PROJECT_SESSIONS, 200, 1), id="global-admin"
    ),
]


# ── Repository registration rights by account kind ──────────────────────────────


@dataclass(frozen=True)
class RegistrationRightsRow:
    account: str
    allowed: bool
    status: int  # of each of the register, list and unregister calls


# Global admins, maintainers and the project's own admin may register repositories; the route
# answers 404 to everybody else, so it does not reveal the project.
REGISTRATION_ALLOWED_STATUS = 200
REGISTRATION_REFUSED_STATUS = 404

REGISTRATION_RIGHTS_ROWS = [
    pytest.param(
        RegistrationRightsRow("regular-member", False, REGISTRATION_REFUSED_STATUS),
        id="regular-member",
    ),
    pytest.param(
        RegistrationRightsRow("project-admin", True, REGISTRATION_ALLOWED_STATUS),
        id="project-admin",
    ),
    pytest.param(
        RegistrationRightsRow("maintainer", True, REGISTRATION_ALLOWED_STATUS),
        id="maintainer",
    ),
    pytest.param(
        RegistrationRightsRow("auditor", False, REGISTRATION_REFUSED_STATUS),
        id="auditor",
    ),
    pytest.param(
        RegistrationRightsRow("service-account", False, REGISTRATION_REFUSED_STATUS),
        id="service-account",
    ),
]
