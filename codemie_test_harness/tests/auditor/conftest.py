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

"""Fixtures for the auditor role test package."""

import uuid

import pytest

from codemie_test_harness.tests.utils.admin_budget_utils import AdminBudgetUtils
from codemie_test_harness.tests.utils.analytics_utils import AnalyticsUtils
from codemie_test_harness.tests.utils.auditor_write_check_utils import (
    AuditorWriteCheckUtils,
)
from codemie_test_harness.tests.utils.project_utils import ProjectUtils
from codemie_test_harness.tests.utils.user_utils import UserUtils


# ── Utility fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def auditor_analytics_utils(auditor_client):
    """AnalyticsUtils wrapping the auditor client."""
    return AnalyticsUtils(auditor_client)


@pytest.fixture(scope="session")
def auditor_project_utils(auditor_client):
    """ProjectUtils wrapping the auditor client."""
    return ProjectUtils(auditor_client)


@pytest.fixture(scope="session")
def auditor_user_utils(auditor_client):
    """UserUtils wrapping the auditor client."""
    return UserUtils(auditor_client)


@pytest.fixture(scope="session")
def auditor_write_check_utils(auditor_client):
    """AuditorWriteCheckUtils wrapping the auditor client (write-denial assertions)."""
    return AuditorWriteCheckUtils(auditor_client)


@pytest.fixture(scope="session")
def regular_write_check_utils(regular_client):
    """AuditorWriteCheckUtils wrapping the regular client (write-denial baseline)."""
    return AuditorWriteCheckUtils(regular_client)


# ── Setup fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def auditor_test_project(client):
    """Real project created by admin for write-denial tests; deleted on teardown."""
    utils = ProjectUtils(client)
    name = f"autotest-auditor-wr-{uuid.uuid4().hex[:8]}"
    utils.create_project(name=name, description="Auditor write-denial test project")
    yield name
    try:
        utils.remove_all_project_members(name)
        utils.delete_project(name)
    except Exception:
        pass


@pytest.fixture(scope="session")
def auditor_test_user_id(regular_client):
    """Real user_id (the regular test user's own ID) for write-denial tests."""
    user = regular_client.users.about_me()
    return str(user.user_id)


@pytest.fixture(scope="session")
def auditor_test_budget_id(client):
    """Real platform budget_id for write-denial tests."""
    admin_budget_utils = AdminBudgetUtils(client)
    budgets = admin_budget_utils.list_budgets(per_page=10)
    if budgets:
        return budgets[0]["budget_id"]
    budget_id = f"autotest-test-{uuid.uuid4().hex[:8]}"
    admin_budget_utils.create_budget(budget_id=budget_id, category="platform")
    return budget_id
