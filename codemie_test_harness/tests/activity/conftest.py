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

"""Fixtures for activity events tests."""

import contextlib
import secrets
from dataclasses import dataclass
from typing import List

import pytest
from codemie_sdk.models.activity_event import ActivityEventListItem

from codemie_test_harness.tests.utils.activity_utils import ActivityUtils
from codemie_test_harness.tests.utils.admin_budget_utils import AdminBudgetUtils
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.project_utils import ProjectUtils
from codemie_test_harness.tests.utils.user_lifecycle_utils import (
    get_user_lifecycle_utils,
)
from codemie_test_harness.tests.test_data.budget_test_data import (
    project_key_alias,
)
from codemie_test_harness.tests.test_data.project_activity_test_data import (
    ADMIN_UPDATES,
)


@pytest.fixture(scope="session")
def maintainer_client():
    """Session-scoped CodeMieClient authenticated with maintainer credentials.

    AUTH_USERNAME / AUTH_PASSWORD in .env are the maintainer-role user.
    """
    return get_client(
        username=CredentialsManager.get_parameter("AUTH_USERNAME"),
        password=CredentialsManager.get_parameter("AUTH_PASSWORD"),
    )


@pytest.fixture(scope="session")
def activity_utils(maintainer_client):
    """ActivityUtils wrapping the session-scoped maintainer client."""
    return ActivityUtils(maintainer_client)


@pytest.fixture(scope="session")
def activity_project(maintainer_client):
    """Session-scoped project for activity event tests.

    Creates one project at session start and deletes it on teardown.
    Yields the project name (str).
    """
    project_utils = ProjectUtils(maintainer_client)
    name = get_random_name()
    project_utils.create_project(name)
    yield name
    try:
        project_utils.delete_project_cascade(name)
    except Exception:
        pass


@pytest.fixture(scope="session")
def keycloak_utils(maintainer_client):
    """Session-scoped user-lifecycle helper.

    Same choice as the root fixture (by domain), but local-IdP users are created
    through the maintainer client.
    """
    return get_user_lifecycle_utils(maintainer_client)


@pytest.fixture(scope="session")
def project_utils(maintainer_client):
    """Session-scoped ProjectUtils wrapping the maintainer client."""
    return ProjectUtils(maintainer_client)


@pytest.fixture(scope="session")
def admin_budget_utils(maintainer_client):
    """Session-scoped AdminBudgetUtils wrapping the maintainer client."""
    return AdminBudgetUtils(maintainer_client)


@pytest.fixture(scope="session")
def admin_project_budget_utils(maintainer_client):
    """Session-scoped AdminProjectBudgetUtils wrapping the maintainer client."""
    return AdminProjectBudgetUtils(maintainer_client)


@pytest.fixture
def disposable_budget(admin_budget_utils):
    """Function-scoped platform budget"""
    budget_id = f"autotest-act-{secrets.token_hex(4)}"
    admin_budget_utils.create_budget(budget_id, "platform")
    return budget_id


@pytest.fixture
def disposable_project_budget(
    admin_project_budget_utils, lite_llm_budget_utils, activity_project
):
    """Function-scoped project budget group tied to activity_project; deleted after each test."""
    admin_project_budget_utils.cleanup_active_budget_groups(activity_project)
    group_response = admin_project_budget_utils.create_budget_group(
        activity_project, name=f"autotest-pb-{secrets.token_hex(4)}"
    )
    group_id = group_response["group_id"]
    budget_id = admin_project_budget_utils.budget_ids_by_category(group_response)[
        "platform"
    ]
    yield budget_id
    admin_project_budget_utils.delete_budget_group(group_id)
    lite_llm_budget_utils.delete_key_by_alias(
        project_key_alias(activity_project, "platform")
    )


@dataclass(frozen=True)
class TrailProject:
    name: str
    instance_id: str
    """``project_instance_id`` of the project detail; the project trail is addressed by it."""


@pytest.fixture
def trail_project(project_utils):
    """A fresh shared project created by the maintainer, deleted after the test.

    The project may already be deleted by the test itself; its activity events stay.
    """
    name = get_random_name()
    project_utils.create_project(name, description="Activity trail test")
    detail = project_utils.get_project_detail(name)
    yield TrailProject(name=name, instance_id=str(detail.project_instance_id))
    with contextlib.suppress(Exception):
        project_utils.delete_project_cascade(name)


@pytest.fixture
def trail_project_admin(trail_project, platform_user, project_utils):
    """platform_user, made administrator of trail_project; unassigned again on teardown."""
    project_utils.assign_user_to_project(
        trail_project.name, platform_user.user_id, is_project_admin=True
    )
    yield platform_user
    with contextlib.suppress(Exception):
        project_utils.remove_user_from_project(
            trail_project.name, platform_user.user_id
        )


@pytest.fixture
def trail_project_member(trail_project, platform_user, project_utils):
    """platform_user, a plain member (not administrator) of trail_project."""
    project_utils.assign_user_to_project(
        trail_project.name, platform_user.user_id, is_project_admin=False
    )
    yield platform_user
    with contextlib.suppress(Exception):
        project_utils.remove_user_from_project(
            trail_project.name, platform_user.user_id
        )


@pytest.fixture
def fresh_maintainer_client(maintainer_user):
    """A login of maintainer_user made after the maintainer flag was set.

    Unlike the session ``maintainer_client`` this user is not a member of any test project.
    """
    return get_client(username=maintainer_user.email, password=maintainer_user.password)


@dataclass(frozen=True)
class PopulatedTrail:
    project: TrailProject
    admin_user_id: str
    """Project administrator who made ADMIN_UPDATES of the project's updates."""
    events: List[ActivityEventListItem]
    """The whole trail read as maintainer, newest first."""


@pytest.fixture
def populated_trail(trail_project, trail_project_admin, project_utils, activity_utils):
    """A project whose trail has events of two actors in project_management and user_management.

    The maintainer creates the project, assigns the administrator, updates the description
    twice and turns member spend enforcement on; the administrator updates the description
    ADMIN_UPDATES times. Project categories: Settings, Members and Budget.
    """
    name = trail_project.name
    project_utils.update_project(name, description="Maintainer update 1")
    project_utils.update_project(name, description="Maintainer update 2")
    project_utils.set_enforce_member_spend_limits(name, True)
    admin_projects = ProjectUtils(trail_project_admin.client)
    for number in range(1, ADMIN_UPDATES + 1):
        admin_projects.update_project(name, description=f"Admin update {number}")
    return PopulatedTrail(
        project=trail_project,
        admin_user_id=trail_project_admin.user_id,
        events=activity_utils.list_all_project_events(trail_project.instance_id),
    )
