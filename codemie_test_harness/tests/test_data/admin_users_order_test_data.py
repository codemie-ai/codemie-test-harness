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

"""Test data for the default A to Z order of the admin users list.

Users are created per test (see OrderedUsersBuilder). Every user's email carries a per-run
search token, so a search by that token returns exactly the users of one scenario.
`rank` is the position the user must take in the default order; the specs are listed in the
order they are created, which differs from the expected order on purpose (the previous
default was newest first).

On identity-provider stands the username is the lower-cased email, so the case-insensitive
username order (UNNAMED_USERS_BY_USERNAME) is only fully exercised on local-auth stands.

A NULL display name cannot be built through the API: creation stores the username when no
name is given, and an update never writes NULL. The empty name is built by an update.
"""

from dataclasses import dataclass
from typing import List, Optional

from codemie_sdk.models.user import CodeMieUserDetail


@dataclass(frozen=True)
class OrderedUserSpec:
    label: str  # username prefix (case kept) and e-mail local-part prefix (lower-cased); the
    # e-mail doubles as the username of an identity-provider user, so it starts with the label
    name: Optional[str]  # display name; None = not given, "" = emptied after creation
    rank: int  # expected 0-based position in the default order

    def username(self, token: str) -> str:
        return f"{self.label}-{token}"

    def email(self, token: str) -> str:
        return f"{self.label.lower()}-{token}-autotest@email.com"


@dataclass(frozen=True)
class OrderScenario:
    id: str
    users: List[OrderedUserSpec]


MIXED_CASE_NAMES = OrderScenario(
    id="mixed-case names",
    users=[
        OrderedUserSpec("delta", "Delta", rank=3),
        OrderedUserSpec("alpha", "alpha", rank=0),
        OrderedUserSpec("charlie", "charlie", rank=2),
        OrderedUserSpec("bravo", "Bravo", rank=1),
    ],
)

EMPTY_NAME_FALLS_BACK_TO_USERNAME = OrderScenario(
    id="empty name falls back to username",
    users=[
        OrderedUserSpec("charlie", "", rank=1),
        OrderedUserSpec("delta", "Delta", rank=2),
        OrderedUserSpec("bravo", "Bravo", rank=0),
    ],
)

SAME_NAME_TIES_BREAK_BY_EMAIL = OrderScenario(
    id="same name ties break by email",
    users=[
        OrderedUserSpec("tie3", "Echo", rank=3),
        OrderedUserSpec("tie1", "Echo", rank=1),
        OrderedUserSpec("foxtrot", "Foxtrot", rank=4),
        OrderedUserSpec("tie2", "Echo", rank=2),
        OrderedUserSpec("alpha", "Alpha", rank=0),
    ],
)


@dataclass(frozen=True)
class OrderedUsers:
    token: str  # search token present in every created user's email and username
    users: List[CodeMieUserDetail]  # created users in their expected order

    @property
    def emails(self) -> List[str]:
        return [user.email for user in self.users]

    @property
    def usernames(self) -> List[str]:
        return [user.username for user in self.users]


# Users without a display name: the order follows the username, ignoring case.
UNNAMED_USERS_BY_USERNAME = OrderScenario(
    id="users without display name",
    users=[
        OrderedUserSpec("Charlie", None, rank=2),
        OrderedUserSpec("alpha", None, rank=0),
        OrderedUserSpec("Bravo", None, rank=1),
    ],
)

# Members of a project, shown in the Members tab (page size 10, the project creator is
# listed too, so keep the count small).
PROJECT_MEMBERS = OrderScenario(
    id="project members",
    users=[
        OrderedUserSpec("yankee", "Yankee", rank=3),
        OrderedUserSpec("alpha", "Alpha", rank=0),
        OrderedUserSpec("xray", "xray", rank=2),
        OrderedUserSpec("bravo", "bravo", rank=1),
    ],
)

default_order_scenarios = [
    MIXED_CASE_NAMES,
    EMPTY_NAME_FALLS_BACK_TO_USERNAME,
    SAME_NAME_TIES_BREAK_BY_EMAIL,
]
