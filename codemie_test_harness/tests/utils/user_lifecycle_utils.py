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

"""Picks the user-lifecycle helper for the current stand and creates disposable users with it.

new_user and new_logged_in_user are context managers: the user exists inside the `with`
block and is deleted on leaving it, also when the block raises. A fixture yields inside the
block; a factory fixture enters one per created user on a contextlib.ExitStack.
"""

import secrets
from contextlib import contextmanager
from typing import Iterator, NamedTuple, Optional

from codemie_sdk import CodeMieClient

from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.keycloak_utils import KeycloakUtils
from codemie_test_harness.tests.utils.local_user_utils import LocalUserUtils
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)

UserLifecycleUtils = LocalUserUtils | KeycloakUtils


def get_user_lifecycle_utils(client: CodeMieClient) -> UserLifecycleUtils:
    """Helper that creates and deletes test users, chosen by CODEMIE_API_DOMAIN.

    Local IdP (localhost, OSS standalone): LocalUserUtils, through the admin API of `client`,
    which must be a platform admin. Every other stand: KeycloakUtils, through the auth server.
    """
    if EnvironmentResolver.uses_local_auth():
        return LocalUserUtils(client)
    return KeycloakUtils()


def user_email(label: str) -> str:
    """Unique e-mail of a test user: autotest_<label>_<random hex>@email.com."""
    return f"autotest_{label}_{secrets.token_hex(4)}@email.com"


class LoggedInUser(NamedTuple):
    email: str
    password: str
    user_id: str
    client: CodeMieClient


@contextmanager
def new_user(
    user_lifecycle: UserLifecycleUtils,
    email: str,
    *,
    admin: bool,
    project_name: Optional[str] = None,
    strict: bool = False,
) -> Iterator[str]:
    """Create the user `email`, yield its password, delete the user on leaving the block.

    `admin` True: a platform admin (create_test_user; `project_name`, default the e-mail,
    is the project the auth server attaches on Keycloak). False: developer role only, no
    platform role (create_platform_user). Nothing logs in here; on Keycloak the backend user
    appears on the first login. A failed deletion is logged, or raised when `strict`.
    """
    if admin:
        password = user_lifecycle.create_test_user(
            email=email, project_name=project_name or email
        )
    else:
        password = user_lifecycle.create_platform_user(email=email)
    try:
        yield password
    finally:
        try:
            user_lifecycle.delete_user(email)
        except Exception as e:
            if strict:
                raise
            logger.warning(f"Failed to delete user {email}: {e}")


@contextmanager
def new_logged_in_user(
    user_lifecycle: UserLifecycleUtils,
    email: str,
    *,
    admin: bool,
    project_name: Optional[str] = None,
    strict: bool = False,
) -> Iterator[LoggedInUser]:
    """new_user, logged in: yield a LoggedInUser. The user is deleted even when the login fails."""
    with new_user(
        user_lifecycle, email, admin=admin, project_name=project_name, strict=strict
    ) as password:
        user_client = get_client(username=email, password=password)
        yield LoggedInUser(
            email, password, user_client.users.about_me().user_id, user_client
        )
