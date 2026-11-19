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
from contextlib import ExitStack

import pytest

from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    html_artifact,
)
from codemie_test_harness.tests.utils.activity_utils import ActivityUtils
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.hosted_application_utils import (
    HostedApplicationUtils,
    HostedUser,
)
from codemie_test_harness.tests.utils.hosted_sharing_utils import SharingWorld
from codemie_test_harness.tests.utils.user_lifecycle_utils import (
    new_logged_in_user,
    new_user,
    user_email,
)

logger = logging.getLogger(__name__)


def cleanup_applications(user: HostedUser) -> None:
    """Delete the applications ``user`` created; a failure is logged and never stops the teardown."""
    try:
        user.apps.cleanup()
    except Exception as error:
        logger.warning(f"Failed to clean up applications of {user.email}: {error}")


@pytest.fixture
def hosted_user_factory(keycloak_utils):
    """Factory: create a plain user (or a platform admin) who can use hosted applications.

    Each user is created with the shared user helpers. The applications a user created are
    deleted before that user is, and the user is deleted even when that cleanup fails.
    """
    with ExitStack() as cleanup:

        def create(admin: bool = False) -> HostedUser:
            logged_in = cleanup.enter_context(
                new_logged_in_user(keycloak_utils, user_email("hosted"), admin=admin)
            )
            user = HostedUser(
                email=logged_in.email,
                user_id=logged_in.user_id,
                client=logged_in.client,
                apps=HostedApplicationUtils(logged_in.client),
            )
            # Registered after the user, so it runs before the user is deleted.
            cleanup.callback(cleanup_applications, user)
            return user

        yield create


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

    On teardown the applications of those users are deleted first, because an application in
    the project blocks its deletion; then the project goes. The fixture depends on
    ``hosted_user_factory``, so both happen before the users are deleted.
    """
    projects: list[tuple[str, tuple[HostedUser, ...]]] = []

    def create(*users: HostedUser) -> str:
        name = get_random_name()
        admin_utils.create_project(name)
        projects.append((name, users))
        for user in users:
            user_utils.assign_user_to_project(user.user_id, name)
        return name

    yield create
    for name, users in projects:
        for user in users:
            cleanup_applications(user)
        try:
            project_utils.delete_project_with_all_members(name)
        except Exception as error:
            logger.warning(f"Failed to delete project {name}: {error}")


@pytest.fixture
def external_account_hosted(keycloak_utils):
    """Hosted-application service called as an external user, an account the feature does not serve.

    The user is created for the test and deleted after it.
    """
    email = user_email("external")
    with new_user(keycloak_utils, email, admin=False, external=True) as password:
        yield get_client(username=email, password=password).hosted_applications


@pytest.fixture
def sharing_world(hosted_people):
    """Factory: a live application of a plain user in a fresh shared project; see ``SharingWorld``.

    ``shared`` and ``published`` shape the application; the people in each role are created on
    first use and removed after the test.
    """

    def create(shared: bool = True, published: bool = False) -> SharingWorld:
        return SharingWorld(hosted_people, shared=shared, published=published)

    return create


@pytest.fixture
def hosted_activity(maintainer_client):
    """Activity log of the platform, read by a maintainer created for the test."""
    return ActivityUtils(maintainer_client)
