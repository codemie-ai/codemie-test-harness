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

"""Test data for the deactivate / reactivate user tests."""

import uuid
from dataclasses import dataclass
from typing import Callable

from codemie_test_harness.tests.utils.user_utils import UserUtils


@dataclass(frozen=True)
class StatusAction:
    """A user status change and the call that performs it."""

    name: str
    perform: Callable[[UserUtils, str], object]


DEACTIVATE = StatusAction("deactivate", UserUtils.deactivate_user)
REACTIVATE = StatusAction("reactivate", UserUtils.reactivate_user)
STATUS_ACTIONS = [DEACTIVATE, REACTIVATE]


@dataclass(frozen=True)
class ReactivationRejection:
    """A reactivation target the backend refuses and the error it answers with."""

    label: str
    target_id: Callable[
        [str], str
    ]  # maps the id of an active user to the id to reactivate
    expected_status: int
    message: str


def active_user_target() -> ReactivationRejection:
    return ReactivationRejection(
        label="active-user",
        target_id=lambda active_user_id: active_user_id,
        expected_status=409,
        message="User is already active",
    )


def unknown_user_id() -> str:
    """A well-formed user id that belongs to nobody."""
    return str(uuid.uuid4())


REACTIVATION_REJECTIONS = [active_user_target()]

USER_DEACTIVATED_MESSAGE = "User deactivated successfully"
ACCOUNT_DEACTIVATED_MESSAGE = "Account is deactivated"
USER_IS_DEACTIVATED_MESSAGE = "User is deactivated"
USER_IS_ALREADY_ACTIVE_MESSAGE = "User is already active"
REACTIVATE_VIA_UPDATE_MESSAGE = (
    "Cannot reactivate user via update. Use POST /v1/admin/users/{user_id}/reactivate."
)
