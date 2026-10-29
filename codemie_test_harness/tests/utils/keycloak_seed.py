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

"""Seed data for Keycloak tool tests: a persistent, known marker user.

Pure logic only (no HTTP); KeycloakUtils performs the requests. The "get all
users" tests used to assert the exact list of two realm users (UUIDs, emails,
creation timestamps), so any change to the shared realm broke them. The seed
user is created once in the realm the Keycloak tool is configured for and
reused by every later run. Tests assert on that one user instead of the whole
realm.
"""

import json
from dataclasses import asdict, dataclass
from typing import Optional

SEED_FIRST_NAME = "CodeMie"
SEED_LAST_NAME = "Test Harness Seed"
# Keycloak lowercases usernames; some realms also force username == email.
SEED_USERNAME = "codemie-test-harness-seed@example.com"
SEED_EMAIL = SEED_USERNAME

KEYCLOAK_SEED_USER = "keycloak_seed_user"


@dataclass(frozen=True)
class SeedUser:
    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    enabled: bool
    email_verified: bool
    created_timestamp: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedUser":
        return cls(**data)

    @classmethod
    def from_representation(cls, user: dict) -> "SeedUser":
        """Build from a Keycloak ``UserRepresentation``."""
        return cls(
            id=user["id"],
            username=user["username"],
            email=user.get("email") or "",
            first_name=user.get("firstName") or "",
            last_name=user.get("lastName") or "",
            enabled=bool(user.get("enabled")),
            email_verified=bool(user.get("emailVerified")),
            created_timestamp=int(user["createdTimestamp"]),
        )


def seed_user_payload() -> dict:
    """``UserRepresentation`` used to create the seed user."""
    return {
        "username": SEED_USERNAME,
        "email": SEED_EMAIL,
        "firstName": SEED_FIRST_NAME,
        "lastName": SEED_LAST_NAME,
        "enabled": True,
        "emailVerified": False,
    }


def find_seed_user(users: list[dict], username: str = SEED_USERNAME) -> Optional[dict]:
    """The oldest user whose username equals ``username`` (case-insensitive)."""
    matches = [
        user
        for user in users
        if (user.get("username") or "").lower() == username.lower()
    ]
    if not matches:
        return None
    return min(matches, key=lambda user: user.get("createdTimestamp", 0))


def render_seed_user_response(seed: SeedUser) -> str:
    """Expected assistant answer for the seed user, built from the live user."""
    return f"""
        **User:**
          - **ID:** {seed.id}
          - **Username:** {seed.username}
          - **First Name:** {seed.first_name}
          - **Last Name:** {seed.last_name}
          - **Email:** {seed.email}
          - **Email Verified:** {str(seed.email_verified).lower()}
          - **Created Timestamp:** {seed.created_timestamp}
          - **Enabled:** {str(seed.enabled).lower()}
"""


def render_seed_user_json(seed: SeedUser) -> str:
    """Expected raw tool output for ``GET /users?username=<seed>&exact=true``."""
    return json.dumps(
        [
            {
                "id": seed.id,
                "username": seed.username,
                "firstName": seed.first_name,
                "lastName": seed.last_name,
                "email": seed.email,
                "emailVerified": seed.email_verified,
                "enabled": seed.enabled,
                "createdTimestamp": seed.created_timestamp,
            }
        ],
        indent=4,
    )
