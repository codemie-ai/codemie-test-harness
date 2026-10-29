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

"""Auditor role — Budgets API access and write-denial tests.

Covers:
  TC-006  Auditor can access budget data via API (API leg)
  TC-012  Auditor budget write requests denied at API layer (API)

UI tests (sidebar, budget list) live in tests/ui/auditor/test_auditor_administration_ui.py.
"""

import pytest
from hamcrest import assert_that, equal_to

# ── TC-012 ────────────────────────────────────────────────────────────────────


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_create_budget_returns_403(auditor_write_check_utils):
    """TC-012: Auditor POST /admin/budgets returns HTTP 403.

    AC-13: The auditor role does not carry write permissions for budgets.
    """
    status = auditor_write_check_utils.attempt_create_budget()
    assert_that(
        status, equal_to(403), "Auditor budget create must be denied with HTTP 403"
    )


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_edit_budget_returns_403(
    auditor_test_budget_id, auditor_write_check_utils
):
    """TC-012: Auditor PATCH /admin/budgets/{id} returns HTTP 403.

    AC-13: The auditor role does not carry write permissions for budgets.
    """
    status = auditor_write_check_utils.attempt_edit_budget(auditor_test_budget_id)
    assert_that(
        status, equal_to(403), "Auditor budget edit must be denied with HTTP 403"
    )


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_sync_budgets_returns_403(auditor_write_check_utils):
    """TC-012: Auditor POST /admin/budgets/sync returns HTTP 403.

    AC-13: The auditor role does not carry budget sync permissions.
    """
    status = auditor_write_check_utils.attempt_sync_budgets()
    assert_that(
        status, equal_to(403), "Auditor budget sync must be denied with HTTP 403"
    )


@pytest.mark.auditor
@pytest.mark.api
def test_auditor_assign_budget_returns_403(
    auditor_test_user_id, auditor_test_budget_id, auditor_write_check_utils
):
    """TC-012: Auditor PUT /admin/users/{id}/budgets returns HTTP 403.

    AC-13: The auditor role does not carry budget assignment permissions.
    """
    status = auditor_write_check_utils.attempt_assign_budget(
        auditor_test_user_id, auditor_test_budget_id
    )
    assert_that(
        status, equal_to(403), "Auditor budget assign must be denied with HTTP 403"
    )
