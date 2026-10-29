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

"""Fixtures for the project API tests."""

import secrets

import pytest

from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.cli_analytics_api_utils import (
    assert_roles_are_real,
    assert_stored_roles,
    delete_projects_strict,
    wait_until_accessible,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.logger_util import setup_logger
from codemie_test_harness.tests.utils.project_visibility_utils import (
    ProjectFlagUtils,
    RolesWorld,
)

logger = setup_logger(__name__)


@pytest.fixture
def extra_platform_user(keycloak_utils):
    """Second plain developer-role user (besides `non_admin_user`); deleted after the test.

    Yields (email, user_id).
    """
    email = f"autotest_extra_{secrets.token_hex(4)}@email.com"
    password = keycloak_utils.create_platform_user(email=email)
    user_id = get_client(username=email, password=password).users.about_me().user_id
    yield email, user_id
    keycloak_utils.delete_user(email)


@pytest.fixture(scope="module")
def roles_world(
    keycloak_utils,
    user_utils,
    admin_utils,
    project_utils,
    gate_admin_client,
    gate_maintainer_client,
    gate_member_client,
    gate_outsider_client,
):
    """Projects `target` and `other` (created through the admin API) and one client per role.

    Before any grant it asserts that the stand has real roles (an unrelated user gets 404; with
    ENV=local every user is a global admin) and that each client holds exactly its role. The
    auditor is not part of the world: `role_api` requests a dedicated module-scoped auditor
    only for cases that need it.
    """
    admin_email = f"autotest_roles_pa_{secrets.token_hex(4)}@email.com"
    other_admin_email = f"autotest_roles_pa2_{secrets.token_hex(4)}@email.com"
    names = [get_random_name() for _ in range(2)]
    try:
        clients = {
            "global_admin": gate_admin_client,
            "maintainer": gate_maintainer_client,
            "project_admin": get_client(
                username=admin_email,
                password=keycloak_utils.create_platform_user(email=admin_email),
            ),
            "other_project_admin": get_client(
                username=other_admin_email,
                password=keycloak_utils.create_platform_user(email=other_admin_email),
            ),
            "member": gate_member_client,
            "unrelated_user": gate_outsider_client,
        }
        for name in names:
            admin_utils.create_project(name)
        assert_roles_are_real(clients["unrelated_user"], names[0])
        ids = {role: c.users.about_me().user_id for role, c in clients.items()}
        assert_stored_roles(user_utils, ids["global_admin"], is_admin=True)
        # the backend stores is_admin=true for every maintainer ("maintainer implies admin")
        assert_stored_roles(
            user_utils, ids["maintainer"], is_maintainer=True, is_admin=True
        )
        for role in (
            "project_admin",
            "other_project_admin",
            "member",
            "unrelated_user",
        ):
            assert_stored_roles(
                user_utils, ids[role], is_maintainer=False, is_admin=False
            )
        for name in names:
            user_utils.assign_user_to_project(ids["member"], name)
        user_utils.assign_user_to_project(
            ids["project_admin"], names[0], is_project_admin=True
        )
        user_utils.assign_user_to_project(
            ids["other_project_admin"], names[1], is_project_admin=True
        )
        wait_until_accessible(clients["member"], names)
        wait_until_accessible(clients["project_admin"], names[:1])
        wait_until_accessible(clients["other_project_admin"], names[1:])
        yield RolesWorld(
            clients=clients,
            target=names[0],
            other=names[1],
            member_email=clients["member"].users.about_me().email,
        )
    finally:
        try:
            delete_projects_strict(project_utils, names)
        finally:
            for email in (admin_email, other_admin_email):
                try:
                    keycloak_utils.delete_user(email)
                except Exception as e:
                    logger.warning(f"Failed to delete user {email}: {e}")


@pytest.fixture
def role_api(request, roles_world, project_utils):
    """Raw project calls as the role named by the indirect parameter. The auditor comes from
    `verified_auditor_client` (freshly provisioned for this module). Projects the role created in the
    test are deleted afterwards."""
    role = request.param
    client = (
        request.getfixturevalue("verified_auditor_client")
        if role == "auditor"
        else roles_world.clients[role]
    )
    api = ProjectFlagUtils(client)
    request.addfinalizer(lambda: delete_projects_strict(project_utils, api.created))
    return api


@pytest.fixture
def ordinary_creator_api(request, unrelated_client, project_utils):
    """Raw project calls as a fresh plain user, the only principal that creates projects as an
    ordinary user (creating a project makes its creator a project admin, which would change
    the role of a shared account for later tests on the same worker)."""
    api = ProjectFlagUtils(unrelated_client)
    request.addfinalizer(lambda: delete_projects_strict(project_utils, api.created))
    return api
