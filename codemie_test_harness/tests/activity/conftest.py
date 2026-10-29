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

import secrets

import pytest

from codemie_test_harness.tests.utils.activity_utils import ActivityUtils
from codemie_test_harness.tests.utils.admin_budget_utils import AdminBudgetUtils
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.keycloak_utils import KeycloakUtils
from codemie_test_harness.tests.utils.local_user_utils import LocalUserUtils
from codemie_test_harness.tests.utils.project_utils import ProjectUtils
from codemie_test_harness.tests.test_data.budget_test_data import (
    project_key_alias,
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

    Uses LocalUserUtils on localhost, KeycloakUtils elsewhere.
    """
    if EnvironmentResolver.is_localhost():
        return LocalUserUtils(maintainer_client)
    return KeycloakUtils()


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
