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

"""Helpers for the ServiceNow project budget integration tests."""

import logging
import time

import requests
from hamcrest import all_of, close_to, has_entries, has_length
from requests import HTTPError

from codemie_sdk.models.cost_center import CostCenterResponse
from codemie_sdk.models.project import ProjectDetailResponse, ProjectListItem
from codemie_sdk.services.project import ProjectService
from codemie_sdk.services.servicenow_integration import ServiceNowIntegrationService
from codemie_sdk.services.user import UserService
from codemie_test_harness.tests.test_data.budget_test_data import project_key_alias
from codemie_test_harness.tests.test_data.servicenow_project_budget_test_data import (
    AMOUNT_TOLERANCE,
    BUDGET_CATEGORIES,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils
from codemie_test_harness.tests.utils.cost_center_utils import CostCenterUtils
from codemie_test_harness.tests.utils.project_utils import ProjectUtils

logger = logging.getLogger(__name__)


def error_body(exc_info) -> dict:
    """The ``error`` object (message, details, help) of an HTTPError raised by the SDK."""
    return exc_info.value.response.json()["error"]


def amounts_close_to(expected: dict[str, float]):
    """Matches a ``{category: amount}`` dict holding exactly the expected categories and amounts."""
    return all_of(
        has_length(len(expected)),
        has_entries(
            {
                category: close_to(amount, AMOUNT_TOLERANCE)
                for category, amount in expected.items()
            }
        ),
    )


def budget_amounts(budget) -> dict[str, float]:
    """``{category: max_budget}`` of a budget block returned by the integration."""
    return {category.category: category.max_budget for category in budget.categories}


def group_amounts(group: dict) -> dict[str, float]:
    """``{category: max_budget}`` of a budget group returned by the admin API."""
    return {item["category"]: item["max_budget"] for item in group["categories"]}


TOKEN_REFRESH_MARGIN_SECONDS = 60
TOKEN_REQUEST_TIMEOUT_SECONDS = 30


class ServiceAccountTokenSource:
    """Mints Keycloak access tokens for a client with the client-credentials grant and renews them."""

    def __init__(
        self,
        auth_server_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        verify_ssl: bool,
    ):
        self._token_url = f"{auth_server_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"
        self._credentials = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        self._verify_ssl = verify_ssl
        self._token = ""
        self._expires_at = 0.0

    def token(self) -> str:
        if time.monotonic() >= self._expires_at:
            response = requests.post(
                self._token_url,
                data=self._credentials,
                verify=self._verify_ssl,
                timeout=TOKEN_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
            self._token = body["access_token"]
            self._expires_at = (
                time.monotonic() + body["expires_in"] - TOKEN_REFRESH_MARGIN_SECONDS
            )
        return self._token


class ServiceNowServiceAccount:
    """SDK services authenticated as the ServiceNow integration service account."""

    def __init__(
        self, api_domain: str, token_source: ServiceAccountTokenSource, verify_ssl: bool
    ):
        self._api_domain = api_domain
        self._token_source = token_source
        self._verify_ssl = verify_ssl
        self._built_for_token = ""
        self._integration = None
        self._users = None
        self._projects = None

    def _services(self) -> None:
        token = self._token_source.token()
        if token != self._built_for_token:
            self._integration = ServiceNowIntegrationService(
                self._api_domain, token, verify_ssl=self._verify_ssl
            )
            self._users = UserService(
                self._api_domain, token, verify_ssl=self._verify_ssl
            )
            self._projects = ProjectService(
                self._api_domain, token, verify_ssl=self._verify_ssl
            )
            self._built_for_token = token

    @property
    def integration(self) -> ServiceNowIntegrationService:
        self._services()
        return self._integration

    def request_admin_users(self):
        """GET /v1/admin/users."""
        self._services()
        return self._users.list_admin_users()

    def request_projects(self):
        """GET /v1/projects."""
        self._services()
        return self._projects.list_projects()


class ServiceNowBudgetUtils(BaseUtils):
    """Reads back and removes what the integration created, as the platform admin."""

    def __init__(self, client, lite_llm_budget_utils):
        super().__init__(client)
        self._projects = ProjectUtils(client)
        self._budget_admin = AdminProjectBudgetUtils(client)
        self._cost_centers = CostCenterUtils(client)
        self._lite_llm = lite_llm_budget_utils

    def find_project(self, project_name: str) -> ProjectDetailResponse | None:
        """The project with its members, or None when it does not exist."""
        try:
            return self._projects.get_project_detail(project_name)
        except HTTPError as error:
            if error.response is not None and error.response.status_code == 404:
                return None
            raise

    def member_ids(self, project_name: str) -> list[str]:
        """User ids of the project's members; empty when the project does not exist."""
        project = self.find_project(project_name)
        return [] if project is None else [member.user_id for member in project.members]

    def projects_named(self, project_name: str) -> list[ProjectListItem]:
        """Every project whose name equals ``project_name``, ignoring letter case."""
        return [
            project
            for project in self._projects.list_all_projects(search=project_name)
            if project.name.lower() == project_name.lower()
        ]

    def cost_centers_named(self, cost_center_name: str) -> list[CostCenterResponse]:
        """Every active cost center whose name equals ``cost_center_name``, ignoring letter case."""
        return [
            cost_center
            for cost_center in self._cost_centers.list_cost_centers()
            if cost_center.name.lower() == cost_center_name.lower()
        ]

    def active_budget_groups(self, project_name: str) -> list[dict]:
        """The project's budget groups that are not deleted (the listing includes history)."""
        return [
            group
            for group in self._budget_admin.list_budget_groups(project_name)
            if group.get("deleted_at") is None
        ]

    def delete_project(self, project_name: str) -> None:
        """Delete the project with its LiteLLM keys, budget groups and every member."""
        if self.find_project(project_name) is None:
            return
        for category in BUDGET_CATEGORIES:
            try:
                self._lite_llm.delete_key_by_alias(
                    project_key_alias(project_name, category)
                )
            except Exception as e:
                logger.warning(
                    "Failed to delete LiteLLM key of %s (%s): %s",
                    project_name,
                    category,
                    e,
                )
        try:
            self._projects.delete_project_budgets(project_name)
            self._projects.delete_project_with_all_members(project_name)
        except Exception as e:
            logger.warning("Failed to delete project %s: %s", project_name, e)

    def delete_cost_center(self, cost_center_name: str) -> None:
        for cost_center in self.cost_centers_named(cost_center_name):
            try:
                self._cost_centers.delete_cost_center(cost_center.id)
            except Exception as e:
                logger.warning(
                    "Failed to delete cost center %s: %s", cost_center_name, e
                )


class ServiceNowCleanup:
    """Remembers the projects and cost centers a test may have created and removes them."""

    def __init__(self, budget_utils: ServiceNowBudgetUtils):
        self._utils = budget_utils
        self._project_names: list[str] = []
        self._cost_center_names: list[str] = []

    def track_project(self, project_name: str) -> str:
        self._project_names.append(project_name)
        return project_name

    def track_cost_center(self, cost_center_name: str) -> str:
        self._cost_center_names.append(cost_center_name)
        return cost_center_name

    def cleanup(self) -> None:
        for project_name in reversed(self._project_names):
            self._utils.delete_project(project_name)
        for cost_center_name in reversed(self._cost_center_names):
            self._utils.delete_cost_center(cost_center_name)
