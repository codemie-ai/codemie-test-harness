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

import pytest

from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.user_utils import UserUtils
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.user_lifecycle_utils import (
    new_logged_in_user,
    user_email,
)


@pytest.fixture
def admin_user_utils(admin_user):
    """UserUtils acting as admin_user (a platform admin who is not a maintainer)."""
    return UserUtils(admin_user.client)


@pytest.fixture(scope="session")
def default_user_utils():
    client = get_client(
        username=CredentialsManager.get_parameter("AUTH_USERNAME_DEFAULT"),
        password=CredentialsManager.get_parameter("AUTH_PASSWORD_DEFAULT"),
    )
    return UserUtils(client)


@pytest.fixture
def updated_user(user_utils):
    me = user_utils.get_about_me()
    original_name = me.name
    new_name = get_random_name()
    updated = user_utils.update_admin_user(me.user_id, name=new_name)
    yield me.user_id, new_name, updated
    if original_name is not None:
        user_utils.update_admin_user(me.user_id, name=original_name)


@pytest.fixture
def temp_project(admin_utils, project_utils):
    name = get_random_name()
    admin_utils.create_project(name)
    yield name
    project_utils.delete_project(name)


@pytest.fixture
def temp_project_with_me(user_utils, temp_project):
    me = user_utils.get_about_me()
    user_utils.assign_user_to_project(me.user_id, temp_project)
    yield me, temp_project
    user_utils.remove_user_from_project(me.user_id, temp_project)


@pytest.fixture
def deactivated_user(user_utils, admin_user):
    """(email, user_id, client) of an admin_user that the harness admin has already deactivated."""
    user_utils.deactivate_user(admin_user.user_id)
    return admin_user.email, admin_user.user_id, admin_user.client


@pytest.fixture
def platform_project_user(user_utils, platform_user, temp_project):
    """(email, user_id, client, project) of a platform_user who is a plain member of a
    temporary project."""
    email, user_id, user_client = (
        platform_user.email,
        platform_user.user_id,
        platform_user.client,
    )
    user_utils.assign_user_to_project(user_id, temp_project)
    yield email, user_id, user_client, temp_project
    try:
        user_utils.remove_user_from_project(user_id, temp_project)
    except Exception:
        pass


@pytest.fixture
def second_admin_user(keycloak_utils, user_utils):
    """A second admin_user, for tests that need two distinct ones (e.g. a remap conflict)."""
    with new_logged_in_user(keycloak_utils, user_email("user2"), admin=True) as user:
        user_utils.update_admin_user(user.user_id, is_admin=True)
        yield user


ACTOR_FIXTURES = {
    "admin": "admin_client",
    "maintainer": "maintainer_client",
    "project_admin": "project_admin_client",
    "auditor": "auditor_client",
    "plain_user": "regular_client",
}


@pytest.fixture
def actor_utils(request):
    """UserUtils bound to the platform role named by the indirect parameter (see ACTOR_FIXTURES)."""
    return UserUtils(request.getfixturevalue(ACTOR_FIXTURES[request.param]))
