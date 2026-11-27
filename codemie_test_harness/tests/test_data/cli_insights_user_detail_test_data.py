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

"""Test data for the CLI Insights user detail tests
(GET /v1/analytics/cli-insights-user-detail)."""

from dataclasses import dataclass

import pytest

from codemie_test_harness.tests.utils.base_utils import get_random_name

# A fixed window keeps the request valid; the identifiers below have no activity in it.
USER_DETAIL_TIME_PERIOD = "last_7_days"

# Mirrors the 404 body of the user detail route when no user is found.
USER_NOT_FOUND_HELP = "Verify the user id, name or email and try again."


def user_not_found_message(identifier: str) -> str:
    """The 404 message names the explicit user_id when one was sent, else the name."""
    return f"User {identifier} not found."


@dataclass
class UnmatchedUserQuery:
    """A user detail request whose identifiers match no CodeMie user and no activity."""

    user_name: str
    user_id: str | None

    @property
    def named_in_error(self) -> str:
        return self.user_id or self.user_name

    def params(self) -> dict:
        params = {"user_name": self.user_name, "time_period": USER_DETAIL_TIME_PERIOD}
        if self.user_id:
            params["user_id"] = self.user_id
        return params


def get_unmatched_user_query(with_user_id: bool) -> UnmatchedUserQuery:
    return UnmatchedUserQuery(
        user_name=get_random_name(),
        user_id=get_random_name() if with_user_id else None,
    )


UNMATCHED_USER_QUERIES = [
    pytest.param(True, id="explicit_user_id_and_name"),
    pytest.param(False, id="name_only"),
]


def _by_email(user) -> dict:
    return {"user_name": user.email}


def _by_user_id_and_email(user) -> dict:
    return {"user_name": user.email, "user_id": user.user_id}


# Builders of the identifiers of a freshly created user, who has no activity yet.
# Each takes a LoggedInUser and returns the identifier query parameters.
KNOWN_USER_QUERIES = [
    pytest.param(_by_email, id="email_only"),
    pytest.param(_by_user_id_and_email, id="user_id_and_email"),
]
