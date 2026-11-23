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

"""UI fixtures for the project activity history tests.

`login` is overridden so a test chooses who the browser signs in as through the
`acting_credentials` fixture (indirect parametrization): the maintainer by default,
or the project administrator persona (`AS_PROJECT_ADMIN`). The persona is made
administrator of the project under test *before* the browser signs in, because the
frontend reads project admin rights once, at login.

Every project is created through the API by the maintainer and deleted after the test;
the events of the trail are made through the API as well, so a test reads the same
trail the browser shows from the SDK.
"""

import contextlib
from dataclasses import dataclass
from typing import List

import pytest
from codemie_sdk.models.activity_event import ActivityEventListItem
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.project_activity_test_data import (
    ADMIN_UPDATES,
)
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.ui.test_data.project_history_test_data import (
    PAGED_UPDATES,
    RAISED_MAX_BUDGET,
    RAISED_SOFT_BUDGET,
    role_credential_keys,
)
from codemie_test_harness.tests.utils.activity_utils import ActivityUtils
from codemie_test_harness.tests.utils.base_utils import get_random_name, poll_until
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.project_utils import ProjectUtils

# Seconds the persona may need before every instance serves its new membership.
MEMBERSHIP_WAIT = 90


@dataclass(frozen=True)
class HistoryProject:
    name: str
    instance_id: str
    """``project_instance_id`` of the project detail; the project trail is addressed by it."""


@dataclass(frozen=True)
class ProjectAdminPersona:
    user_id: str
    client: object
    """CodeMieClient signed in as the persona."""


@dataclass(frozen=True)
class HistoryTrail:
    project: HistoryProject
    admin_user_id: str
    """Project administrator who made ADMIN_UPDATES of the project's updates."""
    events: List[ActivityEventListItem]
    """The whole trail read as maintainer, newest first."""


@dataclass(frozen=True)
class DeletedActorTrail:
    project: HistoryProject
    actor_id: str
    actor_email: str
    events_by_actor: List[ActivityEventListItem]
    """The events the actor made, read before the account was deleted, newest first."""


@pytest.fixture(scope="session")
def activity_utils(client):
    """ActivityUtils on the maintainer client: reads the trail of any project."""
    return ActivityUtils(client)


@pytest.fixture
def history_project(project_utils):
    """A fresh shared project created by the maintainer; deleted after the test.

    Its events stay readable after the delete, so teardown does not affect the trail.
    """
    name = get_random_name()
    project_utils.create_project(name, description="Project history UI test")
    detail = project_utils.get_project_detail(name)
    yield HistoryProject(name=name, instance_id=str(detail.project_instance_id))
    with contextlib.suppress(Exception):
        project_utils.delete_project_cascade(name)


@pytest.fixture
def project_admin_persona(history_project, project_utils):
    """The configured project administrator persona, made administrator of the project.

    Waits until the persona may read the project's trail (the membership can lag
    behind on instances that cache it), and unassigns the persona on teardown.
    """
    client = get_client(
        username=CredentialsManager.get_parameter("AUTH_USERNAME_PROJECT"),
        password=CredentialsManager.get_parameter("AUTH_PASSWORD_PROJECT"),
    )
    user_id = client.users.about_me().user_id
    project_utils.assign_user_to_project(
        history_project.name, user_id, is_project_admin=True
    )
    reader = ActivityUtils(client)
    status = poll_until(
        lambda: reader.project_events_denial(history_project.instance_id).status_code,
        lambda code: code == 200,
        timeout=MEMBERSHIP_WAIT,
        interval=2.0,
    )
    assert_that(
        status,
        equal_to(200),
        "the project administrator persona should read the trail of its project",
    )
    yield ProjectAdminPersona(user_id=user_id, client=client)
    with contextlib.suppress(Exception):
        project_utils.remove_user_from_project(history_project.name, user_id)


@pytest.fixture
def acting_credentials(request):
    """(username, password) the browser signs in with; the maintainer unless parametrized."""
    role = getattr(request, "param", "maintainer")
    if role == "project_admin":
        # signed in only after the grant: the frontend reads project admin rights at login
        request.getfixturevalue("project_admin_persona")
    username_key, password_key = role_credential_keys(role)
    return (
        CredentialsManager.get_parameter(username_key),
        CredentialsManager.get_parameter(password_key),
    )


@pytest.fixture(autouse=True)
def login(page, acting_credentials):
    """Override tests/ui/conftest.py login: sign in as the acting role."""
    username, password = acting_credentials
    user_id = get_client(username=username, password=password).users.about_me().user_id
    LoginPage(page).login_suppressing_popups(
        username,
        password,
        user_id,
        CredentialsManager.get_parameter("FRONTEND_URL", ""),
    )


def read_trail(activity_utils, project, admin_user_id) -> HistoryTrail:
    """The project's whole trail as it is now."""
    return HistoryTrail(
        project=project,
        admin_user_id=admin_user_id,
        events=activity_utils.list_all_project_events(project.instance_id),
    )


@pytest.fixture
def history_trail(
    history_project, project_admin_persona, project_utils, activity_utils
):
    """A project whose trail has events of two actors, in three categories.

    The maintainer creates the project, assigns the project administrator, updates the
    description twice and turns member spend enforcement on; the administrator updates
    the description ADMIN_UPDATES times. Categories: Settings, Members and Budget.
    """
    name = history_project.name
    project_utils.update_project(name, description="Maintainer update 1")
    project_utils.update_project(name, description="Maintainer update 2")
    project_utils.set_enforce_member_spend_limits(name, True)
    admin_projects = ProjectUtils(project_admin_persona.client)
    for number in range(1, ADMIN_UPDATES + 1):
        admin_projects.update_project(name, description=f"Admin update {number}")
    return read_trail(activity_utils, history_project, project_admin_persona.user_id)


@pytest.fixture
def long_history_trail(history_trail, project_utils, activity_utils):
    """history_trail plus PAGED_UPDATES description updates: more Settings events than
    the smallest page size (10)."""
    for number in range(1, PAGED_UPDATES + 1):
        project_utils.update_project(
            history_trail.project.name, description=f"Paged update {number}"
        )
    return read_trail(
        activity_utils, history_trail.project, history_trail.admin_user_id
    )


@pytest.fixture
def budget_history_trail(history_trail, project_budget_groups, activity_utils):
    """history_trail plus a project budget group: budget events beside the enforcement one."""
    budget = project_budget_groups.create(history_trail.project.name)
    return (
        read_trail(activity_utils, history_trail.project, history_trail.admin_user_id),
        budget,
    )


@pytest.fixture
def raised_budget_trail(
    budget_history_trail, admin_project_budget_utils, activity_utils
):
    """budget_history_trail after the platform budget limits were raised through the API."""
    trail, budget = budget_history_trail
    admin_project_budget_utils.update_budget_group_category(
        budget.group_id,
        "platform",
        max_budget=RAISED_MAX_BUDGET,
        soft_budget=RAISED_SOFT_BUDGET,
    )
    return read_trail(activity_utils, trail.project, trail.admin_user_id)


@pytest.fixture
def trail_outside_maintainer_membership(
    history_trail, project_utils, client, activity_utils
):
    """history_trail of a project the maintainer is not a member of (a creator is a member
    of the project they create; reading the history must not depend on it)."""
    maintainer_id = client.users.about_me().user_id
    member_ids = {
        member.user_id
        for member in project_utils.get_project_detail(
            history_trail.project.name
        ).members
    }
    if maintainer_id in member_ids:
        project_utils.remove_user_from_project(
            history_trail.project.name, maintainer_id
        )
    return history_trail


@pytest.fixture
def delete_account(client, keycloak_utils):
    """Factory ``(LoggedInUser) -> None``: deactivate the account in the platform (the soft
    delete the admin API offers) and remove it from the identity provider."""

    def _delete(user):
        client.admin.delete_user(user.user_id)
        keycloak_utils.delete_user(user.email)

    return _delete


@pytest.fixture
def deleted_actor_trail(history_project, platform_user, project_utils, activity_utils):
    """A project whose trail holds events made by `platform_user` (project administrator)
    before the test deletes that account; the events are read before any deletion."""
    name = history_project.name
    project_utils.assign_user_to_project(
        name, platform_user.user_id, is_project_admin=True
    )
    actor_projects = ProjectUtils(platform_user.client)
    for number in range(1, ADMIN_UPDATES + 1):
        actor_projects.update_project(name, description=f"Actor update {number}")
    events = activity_utils.list_all_project_events(
        history_project.instance_id, actor_id=platform_user.user_id
    )
    yield DeletedActorTrail(
        project=history_project,
        actor_id=platform_user.user_id,
        actor_email=platform_user.email,
        events_by_actor=events,
    )
    with contextlib.suppress(Exception):
        project_utils.remove_user_from_project(name, platform_user.user_id)
