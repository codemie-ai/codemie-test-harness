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

import requests

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.keycloak_seed import (
    SEED_USERNAME,
    SeedUser,
    find_seed_user,
    seed_user_payload,
)

_ADMIN_REALM = "master"
_CLIENT_ID = "admin-cli"
_SPECIAL_CHARS = "!@#$%&*"


class KeycloakUtils:
    def __init__(self) -> None:
        self._server_url = (
            CredentialsManager.get_parameter("AUTH_SERVER_URL").rstrip("/") + "/"
        )
        self._realm = CredentialsManager.get_parameter("AUTH_REALM_NAME")
        self._session = requests.Session()

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

    @staticmethod
    def _admin_credentials() -> tuple[str, str]:
        """Provisioning account of the platform auth server (master realm)."""
        username = CredentialsManager.get_parameter("KEYCLOAK_ADMIN_USERNAME")
        password = CredentialsManager.get_parameter("KEYCLOAK_KEY")
        if not username or not password:
            raise RuntimeError(
                "KEYCLOAK_ADMIN_USERNAME and KEYCLOAK_KEY must be set to create "
                "or delete test users in the auth server"
            )
        return username, password

    def _get_token(self) -> str:
        username, password = self._admin_credentials()
        url = f"{self._server_url}realms/{_ADMIN_REALM}/protocol/openid-connect/token"
        data = {
            "client_id": _CLIENT_ID,
            "username": username,
            "password": password,
            "grant_type": "password",
        }
        response = self._session.post(url, data=data)
        response.raise_for_status()
        return response.json()["access_token"]

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def create_test_user(self, email: str, project_name: str) -> str:
        return self._create_user(email, project_name, role_names=("developer", "admin"))

    def create_platform_user(self, email: str) -> str:
        """Create a user with developer role only (no platform admin)."""
        return self._create_user(email, email, role_names=("developer",))

    def _create_user(self, email: str, project_name: str, role_names: tuple) -> str:
        password = self._generate_password()
        headers = self._get_headers()

        create_url = f"{self._server_url}admin/realms/{self._realm}/users"
        user_payload = {
            "username": email,
            "email": email,
            "firstName": "AutoTest",
            "lastName": email.split("@")[0],
            "enabled": True,
            "emailVerified": False,
        }
        create_response = self._session.post(
            create_url, json=user_payload, headers=headers
        )
        create_response.raise_for_status()

        location = create_response.headers["Location"]
        user_id = location.rstrip("/").split("/")[-1]

        reset_url = f"{self._server_url}admin/realms/{self._realm}/users/{user_id}/reset-password"
        reset_payload = {"type": "password", "value": password, "temporary": False}
        reset_response = self._session.put(
            reset_url, json=reset_payload, headers=headers
        )
        reset_response.raise_for_status()

        roles = []
        for role_name in role_names:
            role_response = self._session.get(
                f"{self._server_url}admin/realms/{self._realm}/roles/{role_name}",
                headers=headers,
            )
            role_response.raise_for_status()
            roles.append(role_response.json())

        mapping_url = f"{self._server_url}admin/realms/{self._realm}/users/{user_id}/role-mappings/realm"
        mapping_response = self._session.post(mapping_url, json=roles, headers=headers)
        mapping_response.raise_for_status()

        get_user_url = f"{self._server_url}admin/realms/{self._realm}/users/{user_id}"
        get_user_response = self._session.get(get_user_url, headers=headers)
        get_user_response.raise_for_status()
        user_data = get_user_response.json()

        attributes = user_data.get("attributes", {})
        attributes["applications"] = (
            [email, project_name] if project_name != email else [email]
        )
        user_data["attributes"] = attributes

        put_user_response = self._session.put(
            get_user_url, json=user_data, headers=headers
        )
        put_user_response.raise_for_status()

        return password

    def delete_user(self, email: str) -> None:
        headers = self._get_headers()
        search_url = f"{self._server_url}admin/realms/{self._realm}/users"
        search_response = self._session.get(
            search_url, params={"email": email}, headers=headers
        )
        search_response.raise_for_status()
        users = search_response.json()

        if not users:
            return

        user_id = users[0]["id"]
        delete_url = f"{self._server_url}admin/realms/{self._realm}/users/{user_id}"
        delete_response = self._session.delete(delete_url, headers=headers)
        delete_response.raise_for_status()

    def ensure_seed(self) -> SeedUser:
        """Return the seed user, creating it on first use.

        Talks to the Keycloak the Keycloak tool is configured for (KEYCLOAK_*),
        which is not necessarily the platform auth server used by the rest of
        this class, and authenticates with that integration's own client.
        """
        base_url = CredentialsManager.get_parameter("KEYCLOAK_URL").rstrip("/")
        realm = CredentialsManager.get_parameter("KEYCLOAK_REALM")
        token_response = self._session.post(
            f"{base_url}/realms/{realm}/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": CredentialsManager.get_parameter("KEYCLOAK_CLIENT_ID"),
                "client_secret": CredentialsManager.get_parameter(
                    "KEYCLOAK_CLIENT_SECRET"
                ),
            },
        )
        token_response.raise_for_status()
        headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
        users_url = f"{base_url}/admin/realms/{realm}/users"

        def find_existing() -> dict | None:
            response = self._session.get(
                users_url,
                params={"username": SEED_USERNAME, "exact": "true"},
                headers=headers,
            )
            response.raise_for_status()
            return find_seed_user(response.json())

        user = find_existing()
        if user is None:
            create_response = self._session.post(
                users_url, json=seed_user_payload(), headers=headers
            )
            # 409: another run created it between the lookup and the create.
            if create_response.status_code != 409:
                create_response.raise_for_status()
            user = find_existing()
        if user is None:
            raise RuntimeError(
                f"Keycloak seed user '{SEED_USERNAME}' was not found in realm "
                f"'{realm}' after creating it"
            )
        return SeedUser.from_representation(user)
