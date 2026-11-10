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

"""Create the projects, cost centers and budgets provisioning tests need, read back what a
provisioning call changed, and remove everything afterwards."""

import base64
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import requests
from hamcrest import assert_that, empty, has_length, is_not
from pydantic import ValidationError

from codemie_test_harness.tests.utils.admin_project_budget_group_utils import (
    AdminProjectBudgetGroupUtils,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils, get_random_name
from codemie_test_harness.tests.utils.cost_center_utils import (
    get_random_cost_center_name,
)
from codemie_test_harness.tests.utils.project_budget_groups import ProjectBudget

logger = logging.getLogger(__name__)

PROVISIONING_PATH_PREFIX = "/v1/provisioning"
TOKEN_REFRESH_MARGIN_SECONDS = 60
TOKEN_REQUEST_TIMEOUT_SECONDS = 30
# The registry caps a client name so that "<name> <reference>" fits a budget name.
MAX_CLIENT_NAME_LENGTH = 35
PERSONAL_PROJECT_TYPE = "personal"


class ClientCredentialsTokenSource:
    """Mints Keycloak access tokens for a service account with the client-credentials grant and
    renews them shortly before they expire. ``token`` is the callable to hand to the SDK."""

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


def token_claims(token: str) -> dict:
    """Claims of a JWT access token, read from its payload without verifying the signature."""
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def resolve_client_email(user_utils, token: str, client_id: str) -> str | None:
    """The CodeMie e-mail of the user behind a service account, or None when it cannot be confirmed.

    The user is the one whose id equals the token's ``sub``. Its e-mail is read from the admin
    user record. When that record has no e-mail, the client id or the token's e-mail claim is
    used only if the admin user list shows that address belongs to the user with that id.
    """
    claims = token_claims(token)
    user_id = claims.get("sub")
    if not user_id or user_utils.get_admin_user_status_code(user_id) != 200:
        return None
    try:
        email = user_utils.get_admin_user(user_id).email
    except ValidationError:
        email = None
    if email:
        return email
    for candidate in (client_id, claims.get("email"), claims.get("preferred_username")):
        matches = (
            user_utils.list_all_admin_users(search=candidate)
            if candidate and "@" in candidate
            else []
        )
        if any(
            user.id == user_id and user.email.lower() == candidate.lower()
            for user in matches
        ):
            return candidate
    return None


class ClientNameRecorder:
    """Derives the registered client name from the budget names the client creates.

    A budget the client creates is named "<client name> <change reference>". The name is not
    configured in the harness, so it is read back from those budgets, and every budget seen in
    the session must give the same one.
    """

    def __init__(self):
        self._names: set[str] = set()

    def observe(self, budget_name: str, reference: str) -> str:
        suffix = f" {reference}"
        assert_that(
            budget_name.endswith(suffix),
            f"budget name {budget_name!r} ends with the change reference {reference!r}",
        )
        name = budget_name.removesuffix(suffix)
        assert_that(name, is_not(empty()), "the client name part is not empty")
        assert_that(
            len(name) <= MAX_CLIENT_NAME_LENGTH,
            f"client name {name!r} is at most {MAX_CLIENT_NAME_LENGTH} characters",
        )
        self._names.add(name)
        assert_that(
            self._names,
            has_length(1),
            "every budget the client creates carries the same client name",
        )
        return name


@dataclass(frozen=True)
class ProjectState:
    """What a provisioning call can change on a project; equal states mean nothing changed."""

    exists: bool
    cost_center: str | None = None
    admin_ids: frozenset[str] = field(default_factory=frozenset)
    member_ids: frozenset[str] = field(default_factory=frozenset)
    group_id: str | None = None
    categories: tuple[tuple[str, float], ...] = ()


class ProvisioningUtils(BaseUtils):
    """Admin-side helper for provisioning tests.

    Every project and cost center name it hands out is remembered, so ``cleanup`` also removes
    what a provisioning call created under that name. Request this fixture after the user
    fixtures a test uses, so the users still exist when their projects are removed.
    """

    def __init__(
        self,
        client,
        project_utils,
        cost_center_utils,
        project_budget_groups,
        user_utils,
        lite_llm_budget_utils,
    ):
        super().__init__(client)
        self._projects = project_utils
        self._cost_centers = cost_center_utils
        self._budget_groups = project_budget_groups
        self._users = user_utils
        self._lite_llm = lite_llm_budget_utils
        self._override_users: dict[str, list[str]] = {}
        self._admin_budgets = AdminProjectBudgetUtils(client)
        self._group_utils = AdminProjectBudgetGroupUtils(client)
        self._project_names: list[str] = []
        self._cost_center_names: list[str] = []

    # --- names and setup -------------------------------------------------------------

    def new_project_name(self) -> str:
        """A valid new project name that does not exist yet; removed on cleanup if used."""
        name = get_random_name()
        self._project_names.append(name)
        return name

    def new_cost_center_name(self) -> str:
        """A valid new cost center name that does not exist yet; removed on cleanup if used."""
        name = get_random_cost_center_name()
        self._cost_center_names.append(name)
        return name

    def track_cost_center(self, name: str) -> str:
        """Remove the cost center on cleanup, whatever created it."""
        self._cost_center_names.append(name)
        return name

    def track_project(self, name: str) -> str:
        """Remove the project on cleanup, whatever created it."""
        self._project_names.append(name)
        return name

    def create_project(
        self,
        categories: dict | None = None,
        cost_center_id: UUID | None = None,
        name: str | None = None,
    ) -> str:
        """Create a project as the admin, with a budget group when ``categories`` is given."""
        name = self.track_project(name) if name else self.new_project_name()
        self._projects.create_project(
            name=name,
            description="Autotest provisioning project",
            cost_center_id=cost_center_id,
        )
        if categories:
            self._budget_groups.create(name, categories, name_prefix="autotest-prov")
        return name

    def create_budget(self, project_name: str, categories: dict) -> ProjectBudget:
        """Give an existing project a budget group as the admin."""
        return self._budget_groups.create(
            project_name, categories, name_prefix="autotest-prov"
        )

    def track_override_user(self, project_name: str, user_id: str) -> None:
        """Remove the member's fixed-limit LiteLLM objects of the project's budget on cleanup."""
        self._override_users.setdefault(project_name, []).append(user_id)

    # --- reads -----------------------------------------------------------------------

    def project_exists(self, name: str) -> bool:
        found = self._projects.list_projects(search=name, per_page=100)
        return any(project.name == name for project in found.data)

    def cost_center_exists(self, name: str | None) -> bool:
        return name is not None and any(
            cost_center.name == name
            for cost_center in self._cost_centers.list_cost_centers()
        )

    def active_budget_group(self, project_name: str) -> dict | None:
        """The project's budget group that is not deleted, or None."""
        return next(
            (
                group
                for group in self._admin_budgets.list_budget_groups(project_name)
                if group.get("deleted_at") is None
            ),
            None,
        )

    def category_budgets(self, project_name: str) -> dict[str, float]:
        """Category to max budget of the project's active budget group; empty without one."""
        group = self.active_budget_group(project_name)
        return (
            self._group_utils.get_category_budgets(group["group_id"]) if group else {}
        )

    def soft_budgets(self, project_name: str) -> dict[str, float]:
        """Category to soft budget of the project's active budget group; empty without one."""
        group = self.active_budget_group(project_name)
        return (
            self._group_utils.get_category_soft_budgets(group["group_id"])
            if group
            else {}
        )

    def member_ids(self, project_name: str) -> frozenset[str]:
        detail = self._projects.get_project_detail(project_name)
        return frozenset(m.user_id for m in detail.members)

    def personal_projects(self, user_id: str, email: str) -> list[str]:
        """Names of the personal projects of a user, as the admin sees them.

        Looks at the user's project memberships and at the projects named after the user's
        e-mail, and keeps those whose type is personal.
        """
        names = set(self._users.get_user_project_names(user_id))
        names.update(
            project.name
            for project in self._projects.list_projects(search=email, per_page=100).data
            if project.name.lower() == email.lower()
        )
        return sorted(
            name
            for name in names
            if self._projects.get_project_detail(name).project_type
            == PERSONAL_PROJECT_TYPE
        )

    def admin_ids(self, project_name: str) -> frozenset[str]:
        detail = self._projects.get_project_detail(project_name)
        return frozenset(m.user_id for m in detail.members if m.is_project_admin)

    def cost_center_of(self, project_name: str) -> str | None:
        return self._projects.get_project_detail(project_name).cost_center_name

    def state(self, project_name: str) -> ProjectState:
        """Everything a provisioning call can change on the project."""
        if not self.project_exists(project_name):
            return ProjectState(exists=False)
        detail = self._projects.get_project_detail(project_name)
        group = self.active_budget_group(project_name)
        return ProjectState(
            exists=True,
            cost_center=detail.cost_center_name,
            admin_ids=frozenset(
                m.user_id for m in detail.members if m.is_project_admin
            ),
            member_ids=frozenset(m.user_id for m in detail.members),
            group_id=group["group_id"] if group else None,
            categories=tuple(sorted(self.category_budgets(project_name).items())),
        )

    # --- cleanup ---------------------------------------------------------------------

    def cleanup(self) -> None:
        for name in reversed(self._project_names):
            self._cleanup_project(name)
        for name in self._cost_center_names:
            self._cleanup_cost_center(name)

    def _cleanup_project(self, name: str) -> None:
        try:
            if not self.project_exists(name):
                return
            override_users = self._override_users.get(name, [])
            for group in self._admin_budgets.list_budget_groups(name):
                if group.get("deleted_at") is None:
                    self._budget_groups.delete(
                        ProjectBudget(
                            project_name=name,
                            group_id=group["group_id"],
                            budget_ids=AdminProjectBudgetUtils.budget_ids_by_category(
                                group
                            ),
                        ),
                        override_users[0] if override_users else None,
                    )
            for user_id in override_users:
                self._lite_llm.delete_override_customers_for_project(name, user_id)
            # The project's creator cannot be unassigned (400); deleting the project removes it.
            self._projects.remove_all_project_members(name)
            self._projects.delete_project(name)
        except Exception as e:
            logger.warning(f"Failed to remove provisioning project {name}: {e}")

    def _cleanup_cost_center(self, name: str) -> None:
        try:
            for cost_center in self._cost_centers.list_cost_centers():
                if cost_center.name == name:
                    self._cost_centers.delete_cost_center(cost_center.id)
        except Exception as e:
            logger.warning(f"Failed to remove provisioning cost center {name}: {e}")


def openapi_names(spec: dict, path_prefix: str = PROVISIONING_PATH_PREFIX) -> list[str]:
    """Paths, parameter names and request/response field names of the routes under a prefix."""
    names: list[str] = []
    for path, operations in spec.get("paths", {}).items():
        if not path.startswith(path_prefix):
            continue
        names.append(path)
        for operation in operations.values():
            names.extend(
                parameter["name"] for parameter in operation.get("parameters", [])
            )
            names.extend(_operation_field_names(spec, operation))
    return names


def _operation_field_names(spec: dict, operation: dict) -> list[str]:
    schemas = [
        content.get("schema", {})
        for body in [operation.get("requestBody", {})]
        + list(operation.get("responses", {}).values())
        for content in body.get("content", {}).values()
    ]
    seen: set[str] = set()
    names: list[str] = []
    for schema in schemas:
        names.extend(_schema_field_names(spec, schema, seen))
    return names


def _schema_field_names(spec: dict, schema: Any, seen: set[str]) -> list[str]:
    if not isinstance(schema, dict):
        return []
    ref = schema.get("$ref")
    if ref:
        if ref in seen:
            return []
        seen.add(ref)
        target: Any = spec
        for part in ref.removeprefix("#/").split("/"):
            target = target[part]
        return _schema_field_names(spec, target, seen)
    properties = schema.get("properties", {})
    nested = [
        *properties.values(),
        schema.get("items"),
        schema.get("additionalProperties"),
        *schema.get("anyOf", []),
        *schema.get("allOf", []),
        *schema.get("oneOf", []),
    ]
    names = list(properties)
    for child in nested:
        names.extend(_schema_field_names(spec, child, seen))
    return names


def names_with_vendor(names: list[str], vendors: tuple[str, ...]) -> list[str]:
    """The names that contain any vendor name, ignoring case."""
    return [name for name in names if any(v in name.lower() for v in vendors)]
