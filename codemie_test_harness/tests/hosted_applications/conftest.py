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

"""Fixtures for the hosted application API tests.

Every test owns its users and applications: users are created fresh for the test, the
applications they created are deleted while those users still exist, and then the users go.
"""

import logging
import secrets

import pytest

from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    html_artifact,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.hosted_application_utils import (
    HostedApplicationUtils,
    HostedUser,
)
from codemie_test_harness.tests.utils.user_utils import UserUtils

logger = logging.getLogger(__name__)


@pytest.fixture
def hosted_user_factory(keycloak_utils, user_utils):
    """Factory: create a plain user (or a platform admin) who can use hosted applications.

    The applications each user created are deleted first, then the users.
    """
    users: list[HostedUser] = []
    emails: list[str] = []

    def create(admin: bool = False) -> HostedUser:
        email = f"autotest_hosted_{secrets.token_hex(4)}@email.com"
        password = keycloak_utils.create_platform_user(email=email)
        emails.append(email)
        client = get_client(username=email, password=password)
        user = HostedUser(
            email=email,
            user_id=client.users.about_me().user_id,
            client=client,
            apps=HostedApplicationUtils(client),
        )
        users.append(user)
        if admin:
            user_utils.update_admin_user(user.user_id, is_admin=True)
            UserUtils(client).wait_until_user_management_effective()
        return user

    yield create
    for user in users:
        user.apps.cleanup()
    for email in emails:
        try:
            keycloak_utils.delete_user(email)
        except Exception as error:
            logger.warning(f"Failed to delete user {email}: {error}")


@pytest.fixture
def hosted_owner(hosted_user_factory):
    """A plain user who owns the applications of the test, in their personal project."""
    return hosted_user_factory()


@pytest.fixture
def hosted_reader(hosted_user_factory):
    """A second plain user with no relation to the owner's applications."""
    return hosted_user_factory()


@pytest.fixture
def hosted_live_app(hosted_owner):
    """A private application of ``hosted_owner`` whose live version is a single HTML page.

    Yields ``(application, artifact)``.
    """
    artifact = html_artifact()
    app = hosted_owner.apps.create_app(hosted_owner.personal_project)
    hosted_owner.apps.go_live(app.id, artifact)
    return hosted_owner.apps.get_app(app.id), artifact


@pytest.fixture
def hosted_project_factory(hosted_user_factory, admin_utils, project_utils, user_utils):
    """Factory: create a shared project and add the given users to it.

    It depends on ``hosted_user_factory``, so the project is deleted before its users.
    """
    names: list[str] = []

    def create(*users: HostedUser) -> str:
        name = get_random_name()
        admin_utils.create_project(name)
        names.append(name)
        for user in users:
            user_utils.assign_user_to_project(user.user_id, name)
        return name

    yield create
    for name in names:
        try:
            project_utils.delete_project_with_all_members(name)
        except Exception as error:
            logger.warning(f"Failed to delete project {name}: {error}")


@pytest.fixture
def external_account_hosted(keycloak_utils):
    """Hosted-application service called as an external user, an account the feature does not serve.

    The user is created for the test and deleted after it.
    """
    email = f"autotest_external_{secrets.token_hex(4)}@email.com"
    password = keycloak_utils.create_external_user(email=email)
    try:
        yield get_client(username=email, password=password).hosted_applications
    finally:
        try:
            keycloak_utils.delete_user(email)
        except Exception as error:
            logger.warning(f"Failed to delete user {email}: {error}")
