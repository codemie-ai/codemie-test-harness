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

"""Creates the users of an OrderScenario on any stand and removes them afterwards.

Local-auth stands: users are created through the admin API (LocalUserUtils).
Identity-provider stands: users are created in the auth server (KeycloakUtils) and appear in
the platform on their first login, which the helper performs; the display name is then set
through the admin API (name is editable in every auth mode).

Every email carries the per-run token, so a search by it selects exactly these users on a
shared stand.
"""

import secrets
from typing import List

from hamcrest import assert_that, equal_to, starts_with

from codemie_test_harness.tests.test_data.admin_users_order_test_data import (
    OrderScenario,
    OrderedUsers,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.keycloak_utils import KeycloakUtils
from codemie_test_harness.tests.utils.local_user_utils import LocalUserUtils
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)


class OrderedUsersBuilder:
    def __init__(self, client, user_utils) -> None:
        self._client = client
        self._user_utils = user_utils
        self._local = EnvironmentResolver.is_localhost()
        self._local_users = LocalUserUtils(client) if self._local else None
        self._keycloak = None if self._local else KeycloakUtils()
        self._created: List[tuple] = []  # (user id, email)

    def create(self, scenario: OrderScenario) -> OrderedUsers:
        token = secrets.token_hex(4)
        created = []
        for spec in scenario.users:
            email = spec.email(token)
            user_id = (
                self._create_local(spec, token, email)
                if self._local
                else self._create_idp(email)
            )
            created.append((spec, self._finish(user_id, spec)))
        created.sort(key=lambda pair: pair[0].rank)
        return OrderedUsers(token=token, users=[user for _, user in created])

    def _create_local(self, spec, token, email) -> str:
        user = self._local_users.create_user(
            email=email, username=spec.username(token), name=spec.name or None
        )
        self._created.append((user.id, email))
        return user.id

    def _create_idp(self, email) -> str:
        # Recorded before the auth-server call: a failure part-way (user created, password or
        # role mapping not) must still be cleaned up. The platform id is filled in after login.
        self._created.append((None, email))
        password = self._keycloak.create_platform_user(email=email)
        user_id = get_client(username=email, password=password).users.about_me().user_id
        self._created[-1] = (user_id, email)
        return user_id

    def _finish(self, user_id, spec):
        """Set the display name the scenario needs and read the user back to verify it.

        spec.name None means "no display name": local creation then stores the username itself,
        while an identity-provider user arrives with a name from the token and must be emptied.
        """
        emptied = spec.name == "" or (spec.name is None and not self._local)
        if emptied or (spec.name and not self._local):
            self._user_utils.update_admin_user(user_id, name=spec.name or "")
        detail = self._user_utils.get_admin_user(user_id)
        if spec.name:
            assert_that(
                detail.name, equal_to(spec.name), f"Display name of {detail.email}"
            )
        if emptied:
            assert_that(
                detail.name or "",
                equal_to(""),
                f"The name of {detail.email} must really be empty for the username fallback",
            )
            assert_that(
                detail.username.lower(),
                starts_with(spec.label.lower()),
                "The username that replaces the empty name must sort where the scenario expects",
            )
        return detail

    def delete_all(self) -> None:
        """Remove every recorded user; a user that was never fully created is not an error."""
        for user_id, email in self._created:
            try:
                user_id = user_id or self._find_platform_user_id(email)
                if user_id:
                    self._client.admin.delete_user(user_id)
            except Exception as e:
                logger.warning(f"Failed to deactivate user {email}: {e}")
            if not self._local:
                try:
                    self._keycloak.delete_user(
                        email
                    )  # no-op when the user is not there
                except Exception as e:
                    logger.warning(f"Failed to delete auth-server user {email}: {e}")

    def _find_platform_user_id(self, email):
        """Id of the platform user with this email, None when it never reached the platform."""
        users = self._client.admin.list_users(search=email)
        return next((u.id for u in users if u.email == email), None)
