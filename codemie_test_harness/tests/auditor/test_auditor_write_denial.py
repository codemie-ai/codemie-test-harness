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

"""Auditor role — API write-denial parity tests.

Covers:
  TC-014  Pure auditor write requests denied identically to regular user across domains (API)

UI tests (no write controls visible) live in tests/ui/auditor/test_auditor_administration_ui.py.
"""

import pytest
from hamcrest import assert_that, equal_to

# ── TC-014 ────────────────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_and_regular_user_both_get_403_on_user_edit(
    auditor_test_user_id, auditor_write_check_utils, regular_write_check_utils
):
    """TC-014: User edit returns 403 for auditor and for regular user identically.

    AC-16: The auditor role provides the same write-denial behaviour as a plain user.
    """
    auditor_status = auditor_write_check_utils.attempt_edit_user(auditor_test_user_id)
    regular_status = regular_write_check_utils.attempt_edit_user(auditor_test_user_id)
    assert_that(
        auditor_status,
        equal_to(regular_status),
        "Auditor and regular user must receive the same HTTP status for user edit",
    )
    assert_that(
        auditor_status,
        equal_to(403),
        "User edit must be denied (HTTP 403) for both auditor and regular user",
    )


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_and_regular_user_both_get_403_on_budget_create(
    auditor_write_check_utils, regular_write_check_utils
):
    """TC-014: Budget create returns 403 for auditor and for regular user identically.

    AC-16: The auditor role provides the same write-denial behaviour as a plain user.
    """
    auditor_status = auditor_write_check_utils.attempt_create_budget()
    regular_status = regular_write_check_utils.attempt_create_budget()
    assert_that(
        auditor_status,
        equal_to(regular_status),
        "Auditor and regular user must receive the same HTTP status for budget create",
    )
    assert_that(
        auditor_status,
        equal_to(403),
        "Budget create must be denied (HTTP 403) for both auditor and regular user",
    )
