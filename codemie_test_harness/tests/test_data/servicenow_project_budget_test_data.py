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

"""Test data for the ServiceNow project budget integration API tests."""

import secrets
from dataclasses import dataclass, field

import pytest

from codemie_sdk.models.servicenow_integration import (
    ServiceNowBudgetAction,
    ServiceNowBudgetRequest,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.cost_center_utils import (
    get_random_cost_center_name,
)

SET = ServiceNowBudgetAction.SET
ADJUST = ServiceNowBudgetAction.ADJUST
CANCEL = ServiceNowBudgetAction.CANCEL

# Amounts come back as derived from percentages and can drift by a float epsilon.
AMOUNT_TOLERANCE = 1e-6
BUDGET_DURATION = "30d"
BUDGET_CATEGORIES = ("platform", "cli", "premium_models")
BUDGET_GROUP_NAME_TEMPLATE = "ServiceNow {request_id}"

# Error contract of the integration endpoints.
ACCESS_DENIED_MESSAGE = "Access denied"
SERVICE_ACCOUNT_SCOPE_DETAILS = (
    "This service account may only call the ServiceNow integration endpoints."
)
INTEGRATION_ROUTE_GUARD_DETAILS = (
    "This endpoint is reserved for the ServiceNow integration service account."
)
INVALID_COST_CENTER_NAME_MESSAGE = "Invalid cost center name"
PERSONAL_PROJECT_MESSAGE = "Budgets cannot be managed for personal projects"
PLATFORM_MUST_BE_POSITIVE_MESSAGE = "Platform budget must be greater than 0"
PERSONAL_PROJECT_TYPE = "personal"


def project_missing_message(project_name: str) -> str:
    return f"Project '{project_name}' does not exist"


def cost_center_deleted_message(cost_center_name: str) -> str:
    return f"Cost center '{cost_center_name}' has been deleted"


# Amounts of a budget as sent by ServiceNow (USD per month).
ALL_CATEGORY_AMOUNTS = {"platform": 100.0, "cli": 40.0, "premium_models": 10.0}
PLATFORM_ONLY_AMOUNTS = {"platform": 70.0}
PLATFORM_AMOUNT = {"platform": 100.0}

# Amounts of a budget group created by an admin, with the soft limit the admin API needs.
ALL_CATEGORY_GROUP = {
    "platform": {"max_budget": 100.0, "soft_budget": 50.0},
    "cli": {"max_budget": 40.0, "soft_budget": 20.0},
    "premium_models": {"max_budget": 10.0, "soft_budget": 5.0},
}
PLATFORM_AND_CLI_GROUP = {
    "platform": {"max_budget": 100.0, "soft_budget": 50.0},
    "cli": {"max_budget": 40.0, "soft_budget": 20.0},
}
PLATFORM_ONLY_GROUP = {"platform": {"max_budget": 100.0, "soft_budget": 50.0}}

ADJUSTED_PLATFORM_AMOUNT = 150.0

# Display names for the lookup projects; the middle project has none.
LOOKUP_DISPLAY_NAMES = ("Autotest lookup A", None, "Autotest lookup C")


def new_request_id() -> str:
    return f"RITM{secrets.token_hex(4)}"


def budget_request(
    action: ServiceNowBudgetAction = SET, **fields
) -> ServiceNowBudgetRequest:
    """A valid set request for a fresh project code; ``fields`` override any of its parts."""
    defaults = {
        "request_id": new_request_id(),
        "epam_project_code": get_random_cost_center_name(),
        "amounts": dict(PLATFORM_AMOUNT),
    }
    return ServiceNowBudgetRequest(action=action, **{**defaults, **fields})


def cancel_request(project_name: str) -> ServiceNowBudgetRequest:
    return budget_request(CANCEL, codemie_project_name=project_name, amounts=None)


@dataclass(frozen=True)
class ProjectIdentity:
    """The project code and optional project name of a budget request for a new project."""

    code: str
    name: str | None

    @property
    def project_name(self) -> str:
        """The project the request resolves to: the name, else the code."""
        return self.name or self.code

    @property
    def cost_center_name(self) -> str | None:
        """The cost center the request creates: named after the code, only when a name differs."""
        return self.code if self.name else None


def new_project_identity(name_provided: bool) -> ProjectIdentity:
    return ProjectIdentity(
        code=get_random_cost_center_name(),
        name=get_random_name() if name_provided else None,
    )


@dataclass(frozen=True)
class ProjectResolutionCase:
    name_provided: bool
    created_cost_center: bool


PROJECT_RESOLUTION_CASES = [
    pytest.param(
        ProjectResolutionCase(name_provided=True, created_cost_center=True),
        id="name_differs_from_code",
    ),
    pytest.param(
        ProjectResolutionCase(name_provided=False, created_cost_center=False),
        id="name_omitted",
    ),
]


@dataclass(frozen=True)
class InvalidBudgetPayload:
    action: ServiceNowBudgetAction
    amounts: dict | None


INVALID_BUDGET_PAYLOADS = [
    pytest.param(
        InvalidBudgetPayload(SET, {"platform": 10.0, "unknown_category": 5.0}),
        id="unknown_category",
    ),
    pytest.param(InvalidBudgetPayload(SET, {"platform": -5.0}), id="negative_amount"),
    pytest.param(
        InvalidBudgetPayload(SET, {"platform": float("nan")}), id="nan_amount"
    ),
    pytest.param(
        InvalidBudgetPayload(SET, {"platform": float("inf")}), id="infinite_amount"
    ),
    pytest.param(InvalidBudgetPayload(SET, None), id="set_without_amounts"),
    pytest.param(InvalidBudgetPayload(ADJUST, None), id="adjust_without_amounts"),
    pytest.param(InvalidBudgetPayload(SET, {"cli": 10.0}), id="set_without_platform"),
]

# Overrides of a valid set request that break exactly one field.
INVALID_FIELD_OVERRIDES = [
    pytest.param({"request_id": ""}, id="empty_request_id"),
    pytest.param({"request_id": "r" * 65}, id="request_id_65_chars"),
    pytest.param({"epam_project_code": "ab"}, id="project_code_2_chars"),
    pytest.param({"epam_project_code": "c" * 101}, id="project_code_101_chars"),
    pytest.param(
        {"action": CANCEL, "amounts": {"platform": -1.0}},
        id="cancel_with_negative_amount",
    ),
    pytest.param(
        {"action": CANCEL, "amounts": None, "admin_emails": ["not-an-email"]},
        id="cancel_with_invalid_admin_email",
    ),
]


@dataclass
class RejectedBudgetRequest:
    """A request the integration must refuse, with what must be left untouched."""

    request: ServiceNowBudgetRequest
    status_code: int
    message: str
    project_name: str
    project_exists: bool
    member_ids: list[str] = field(default_factory=list)


REJECTED_BUDGET_REQUESTS = [
    pytest.param("rejected_invalid_cost_center_name", id="invalid_cost_center_name"),
    pytest.param("rejected_personal_project", id="personal_project"),
    pytest.param("rejected_deleted_cost_center", id="deleted_cost_center"),
]

# Methods of ServiceNowServiceAccount that call endpoints outside the integration.
OUT_OF_SCOPE_REQUESTS = [
    pytest.param("request_admin_users", id="get_admin_users"),
    pytest.param("request_projects", id="get_projects"),
]

NON_SERVICE_ACCOUNT_CALLERS = [
    pytest.param("admin_client", id="admin"),
    pytest.param("regular_client", id="regular_user"),
]


def request_project_lookup(service) -> None:
    service.list_projects([f"autotest_sn_{secrets.token_hex(4)}@email.com"])


def request_budget_cancel(service) -> None:
    service.submit_budget_request(cancel_request(get_random_name()))


INTEGRATION_REQUESTS = [
    pytest.param(request_project_lookup, id="get_projects"),
    pytest.param(request_budget_cancel, id="post_budgets"),
]
