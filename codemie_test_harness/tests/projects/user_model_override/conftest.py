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

"""Fixtures for the user model override API tests."""

from dataclasses import dataclass

import pytest

from codemie_test_harness.tests.utils.activity_utils import ActivityUtils
from codemie_test_harness.tests.utils.assistant_utils import AssistantUtils
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    wait_until_accessible,
)
from codemie_test_harness.tests.utils.user_lifecycle_utils import (
    new_logged_in_user,
    user_email,
)
from codemie_test_harness.tests.utils.user_model_override_utils import (
    UserModelOverrideUtils,
    pick_override_models,
    platform_default_of,
)


@dataclass
class OverrideAdmin:
    """A project admin of the override project, with the override calls made as that admin."""

    user_id: str
    overrides: UserModelOverrideUtils


@pytest.fixture
def override_utils(client):
    """Override calls made as the harness admin client."""
    return UserModelOverrideUtils(client)


@pytest.fixture
def activity_utils(client):
    """Activity events as the harness admin client, which holds the maintainer role."""
    return ActivityUtils(client)


@pytest.fixture
def outsider_user(keycloak_utils):
    """A user that is a member of no project but their own."""
    with new_logged_in_user(
        keycloak_utils, user_email("outsider"), admin=False
    ) as user:
        yield user


@pytest.fixture
def override_project(platform_user, second_platform_user, project, user_utils):
    """Name of a new project whose plain members are platform_user and second_platform_user.

    The users are requested first, so they outlive the teardown of the project. Members are
    added through the admin user route, which refreshes the member's cached project list; the
    project-scoped assignment route leaves it stale for the auth cache TTL, so the member's
    first calls on the project would answer 403.
    """
    name = project().name
    for member in (platform_user, second_platform_user):
        user_utils.assign_user_to_project(member.user_id, name, False)
    for member in (platform_user, second_platform_user):
        wait_until_accessible(member.client, [name])
    return name


@pytest.fixture
def project_admin_overrides(keycloak_utils, project_utils, override_project):
    """Override calls made as a project admin of override_project, logged in after the grant.

    The first login of the new user is made before the role is assigned, so a backend that
    caches the administered projects per token would not know the role yet.
    """
    with new_logged_in_user(
        keycloak_utils, user_email("overrideadmin"), admin=False
    ) as admin:
        project_utils.assign_user_to_project(
            override_project, admin.user_id, is_project_admin=True
        )
        admin_client = get_client(username=admin.email, password=admin.password)
        wait_until_accessible(admin_client, [override_project])
        yield OverrideAdmin(admin.user_id, UserModelOverrideUtils(admin_client))


@pytest.fixture
def override_models(client, platform_user, second_platform_user):
    """Base names of three enabled chat models that the harness admin and both members see."""
    names = pick_override_models(
        3, client, platform_user.client, second_platform_user.client
    )
    if len(names) < 3:
        pytest.skip("Fewer than three regular enabled chat models on this stand")
    return names


@pytest.fixture
def platform_default(client, platform_user, second_platform_user):
    """Base name of the platform default model, listed for both members as well."""
    name = platform_default_of(client)
    seen_by_members = [
        name in {m.base_name for m in member.client.llms.list()}
        for member in (platform_user, second_platform_user)
    ]
    if name is None or not all(seen_by_members):
        pytest.skip("The platform default model is not listed for the members")
    return name


@pytest.fixture
def member_assistants():
    """Factory creating assistants as a member's client; each is deleted after the test."""
    created = []

    def _create(member_client, **kwargs):
        utils = AssistantUtils(member_client)
        assistant = utils.create_assistant(**kwargs)
        created.append((utils, assistant))
        return assistant

    yield _create

    for utils, assistant in created:
        try:
            utils.delete_assistant(assistant)
        except Exception:
            pass
