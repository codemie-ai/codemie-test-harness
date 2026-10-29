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

"""Fixtures for the ServiceNow project budget integration API tests.

The integration endpoints are callable only by the ServiceNow service account, which is
provisioned on the environment. Its Keycloak client credentials come from
``SERVICENOW_SERVICE_ACCOUNT_CLIENT_ID`` / ``SERVICENOW_SERVICE_ACCOUNT_CLIENT_SECRET``;
tests that act as the service account are skipped when they are not set.
"""

import logging
import secrets
from dataclasses import dataclass

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.test_data.servicenow_project_budget_test_data import (
    LOOKUP_DISPLAY_NAMES,
    NON_SERVICE_ACCOUNT_CALLERS,
    PERSONAL_PROJECT_TYPE,
    PLATFORM_ONLY_GROUP,
    REJECTED_BUDGET_REQUESTS,
    RejectedBudgetRequest,
    budget_request,
    cost_center_deleted_message,
    INVALID_COST_CENTER_NAME_MESSAGE,
    PERSONAL_PROJECT_MESSAGE,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.cost_center_utils import (
    get_random_cost_center_name,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.project_budget_groups import ProjectBudgetGroups
from codemie_test_harness.tests.utils.servicenow_budget_utils import (
    ServiceAccountTokenSource,
    ServiceNowBudgetUtils,
    ServiceNowCleanup,
    ServiceNowServiceAccount,
)

logger = logging.getLogger(__name__)

SERVICE_ACCOUNT_CLIENT_ID_KEY = "SERVICENOW_SERVICE_ACCOUNT_CLIENT_ID"
SERVICE_ACCOUNT_CLIENT_SECRET_KEY = "SERVICENOW_SERVICE_ACCOUNT_CLIENT_SECRET"


@dataclass(frozen=True)
class RegisteredUser:
    email: str
    user_id: str


@dataclass(frozen=True)
class BudgetedProject:
    name: str
    group_id: str


@dataclass(frozen=True)
class LookupWorld:
    user_a: RegisteredUser
    user_b: RegisteredUser
    unregistered_email: str
    display_names_by_project: dict[str, str | None]
    """Every shared project the two users belong to, in the order the lookup must return."""


@pytest.fixture(scope="session")
def servicenow_account():
    """SDK services acting as the ServiceNow integration service account."""
    client_id = CredentialsManager.get_parameter(SERVICE_ACCOUNT_CLIENT_ID_KEY)
    client_secret = CredentialsManager.get_parameter(SERVICE_ACCOUNT_CLIENT_SECRET_KEY)
    if not (client_id and client_secret):
        pytest.skip(
            f"{SERVICE_ACCOUNT_CLIENT_ID_KEY} / {SERVICE_ACCOUNT_CLIENT_SECRET_KEY} "
            "are not set: no ServiceNow service account credentials"
        )
    token_source = ServiceAccountTokenSource(
        CredentialsManager.get_parameter("AUTH_SERVER_URL"),
        CredentialsManager.get_parameter("AUTH_REALM_NAME"),
        client_id,
        client_secret,
        VERIFY_SSL,
    )
    return ServiceNowServiceAccount(API_DOMAIN, token_source, VERIFY_SSL)


@pytest.fixture(scope="session")
def servicenow_budget_utils(client, lite_llm_budget_utils):
    return ServiceNowBudgetUtils(client, lite_llm_budget_utils)


@pytest.fixture(scope="function")
def servicenow_cleanup(servicenow_budget_utils, cost_center):
    """Removes the projects and cost centers the integration created during a test.

    Depends on ``cost_center`` only so that the cost centers it creates are deleted after
    the projects linked to them, whatever order a test requests the fixtures in.
    """
    cleanup = ServiceNowCleanup(servicenow_budget_utils)
    yield cleanup
    cleanup.cleanup()


@pytest.fixture(scope="function")
def shared_project(project_utils, servicenow_cleanup):
    """Factory creating a shared project as the admin; the project is deleted after the test."""

    def _create(name=None, display_name=None, cost_center_id=None) -> str:
        name = servicenow_cleanup.track_project(name or get_random_name())
        project_utils.create_project(
            name=name, display_name=display_name, cost_center_id=cost_center_id
        )
        return name

    return _create


@pytest.fixture(scope="function")
def budgeted_project(shared_project, project_budget_groups):
    """Factory creating a shared project with an admin-created budget group."""

    def _create(categories: dict) -> BudgetedProject:
        name = shared_project()
        budget = project_budget_groups.create(name, categories)
        return BudgetedProject(name=name, group_id=budget.group_id)

    return _create


@pytest.fixture(scope="module")
def validation_budget_project(
    project_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    servicenow_budget_utils,
):
    """One project with a platform budget, shared by the tests that must leave it untouched."""
    name = get_random_name()
    groups = ProjectBudgetGroups(admin_project_budget_utils, lite_llm_budget_utils)
    try:
        project_utils.create_project(name=name)
        budget = groups.create(name, PLATFORM_ONLY_GROUP)
        yield BudgetedProject(name=name, group_id=budget.group_id)
    finally:
        groups.cleanup()
        servicenow_budget_utils.delete_project(name)


@pytest.fixture(scope="function")
def registered_user(keycloak_utils):
    """Factory creating a plain user who has signed in, so CodeMie knows them; deleted after the test."""
    emails = []

    def _create() -> RegisteredUser:
        email = f"autotest_sn_{secrets.token_hex(4)}@email.com"
        password = keycloak_utils.create_platform_user(email=email)
        emails.append(email)
        user_id = get_client(username=email, password=password).users.about_me().user_id
        return RegisteredUser(email=email, user_id=user_id)

    yield _create
    for email in emails:
        try:
            keycloak_utils.delete_user(email)
        except Exception as e:
            logger.warning(f"Failed to delete user {email}: {e}")


@pytest.fixture(scope="function")
def lookup_world(registered_user, shared_project, user_utils):
    """Two users, each in a project of their own and both in a common one, plus an unknown email.

    The project names differ only in their last letter, so the expected order does not depend
    on how the database collates punctuation.
    """
    token = secrets.token_hex(4)
    user_a, user_b = registered_user(), registered_user()
    names = [f"autotest-sn-{token}-{letter}" for letter in "abc"]
    for name, display_name in zip(names, LOOKUP_DISPLAY_NAMES):
        shared_project(name=name, display_name=display_name)
    user_utils.assign_user_to_project(user_a.user_id, names[0])
    user_utils.assign_user_to_project(user_b.user_id, names[1])
    user_utils.assign_user_to_project(user_a.user_id, names[2])
    user_utils.assign_user_to_project(user_b.user_id, names[2])
    return LookupWorld(
        user_a=user_a,
        user_b=user_b,
        unregistered_email=f"autotest_sn_unknown_{token}@email.com",
        display_names_by_project=dict(zip(names, LOOKUP_DISPLAY_NAMES)),
    )


@pytest.fixture(scope="function")
def rejected_invalid_cost_center_name(
    registered_user, servicenow_cleanup
) -> RejectedBudgetRequest:
    """A new project whose cost center name (the project code) has no '-'."""
    project_name = servicenow_cleanup.track_project(get_random_name())
    return RejectedBudgetRequest(
        request=budget_request(
            codemie_project_name=project_name,
            epam_project_code=f"nodash{secrets.token_hex(4)}",
            admin_emails=[registered_user().email],
        ),
        status_code=400,
        message=INVALID_COST_CENTER_NAME_MESSAGE,
        project_name=project_name,
        project_exists=False,
    )


@pytest.fixture(scope="function")
def rejected_personal_project(
    registered_user, servicenow_budget_utils
) -> RejectedBudgetRequest:
    """The personal project of a user, which is named after the user's email."""
    owner = registered_user()
    personal_project = servicenow_budget_utils.find_project(owner.email)
    assert_that(
        personal_project.project_type,
        equal_to(PERSONAL_PROJECT_TYPE),
        "Precondition: the user's own project must be personal",
    )
    return RejectedBudgetRequest(
        request=budget_request(
            codemie_project_name=owner.email,
            admin_emails=[registered_user().email],
        ),
        status_code=403,
        message=PERSONAL_PROJECT_MESSAGE,
        project_name=owner.email,
        project_exists=True,
        member_ids=[owner.user_id],
    )


@pytest.fixture(scope="function")
def rejected_deleted_cost_center(
    registered_user, servicenow_cleanup, cost_center, cost_center_utils
) -> RejectedBudgetRequest:
    """A new project whose project code names a cost center that has been deleted."""
    cost_center_name = get_random_cost_center_name()
    cost_center_utils.delete_cost_center(cost_center(name=cost_center_name))
    project_name = servicenow_cleanup.track_project(get_random_name())
    return RejectedBudgetRequest(
        request=budget_request(
            codemie_project_name=project_name,
            epam_project_code=cost_center_name,
            admin_emails=[registered_user().email],
        ),
        status_code=409,
        message=cost_center_deleted_message(cost_center_name),
        project_name=project_name,
        project_exists=False,
    )


@pytest.fixture(params=REJECTED_BUDGET_REQUESTS)
def rejected_budget_request(request) -> RejectedBudgetRequest:
    return request.getfixturevalue(request.param)


@pytest.fixture(params=NON_SERVICE_ACCOUNT_CALLERS)
def non_service_account_client(request):
    """A platform admin client and a plain user client; neither is the service account."""
    return request.getfixturevalue(request.param)
