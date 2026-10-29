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

import random
import secrets
import string

from codemie_sdk.client.client import CodeMieClient
from codemie_sdk.models.admin import LocalUserDetail

_SPECIAL_CHARS = "!@#$%&*"


class LocalUserUtils:
    """Creates and deletes users via the backend admin API (localhost only)."""

    def __init__(self, client: CodeMieClient) -> None:
        self._client = client

    def _generate_password(self) -> str:
        required = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
            secrets.choice(_SPECIAL_CHARS),
        ]
        alphabet = string.ascii_letters + string.digits + _SPECIAL_CHARS
        filler = [secrets.choice(alphabet) for _ in range(8)]
        chars = required + filler
        random.SystemRandom().shuffle(chars)
        return "".join(chars)

    def create_test_user(self, email: str, project_name: str) -> str:
        password = self._generate_password()
        self._client.admin.create_local_user(
            email=email, username=email, password=password, is_admin=True
        )
        return password

    def create_platform_user(self, email: str) -> str:
        """Create a user with developer role only (no platform admin)."""
        password = self._generate_password()
        self._client.admin.create_local_user(
            email=email, username=email, password=password, is_admin=False
        )
        return password

    def delete_user(self, email: str) -> None:
        users = self._client.admin.list_users(search=email)
        user = next((u for u in users if u.email == email), None)
        if user:
            self._client.admin.delete_user(user.id)

    def create_user(
        self, email: str, username: str, name: str | None = None
    ) -> LocalUserDetail:
        """Create a plain (non-admin) user; the backend stores the username when no name is given."""
        return self._client.admin.create_local_user(
            email=email,
            username=username,
            password=self._generate_password(),
            name=name,
        )

    def delete_user_by_id(self, user_id: str) -> None:
        self._client.admin.delete_user(user_id)
