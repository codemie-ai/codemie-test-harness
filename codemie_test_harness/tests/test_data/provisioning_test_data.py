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

"""Test data for the provisioning API tests."""

import secrets
from dataclasses import dataclass
from typing import Callable

import pytest

from codemie_sdk.models.provisioning import (
    ProvisioningBudgetRequest,
    ProvisioningProjectBlock,
)
from codemie_sdk.services.assistant import AssistantService
from codemie_sdk.services.project import ProjectService
from codemie_sdk.services.user import UserService
from codemie_test_harness.tests.test_data.budget_test_data import (
    PLATFORM_BUDGET_CATEGORIES,
)
from codemie_test_harness.tests.utils.provisioning_utils import ProvisioningUtils

MANAGE_BUDGETS = "provisioning:manage-budgets"
READ_PROJECTS = "provisioning:read-projects"
PLATFORM_MUST_BE_POSITIVE = "Platform budget must be greater than 0"
CLIENT_LOCKED_MESSAGE = "A provisioning client may only call the provisioning API"
# Worded in terms of CodeMie, not of any caller; the OpenAPI document must not name these.
VENDOR_NAMES = ("servicenow", "service_now", "service-now")
# A changed category gets this share of its new max budget as soft budget (the backend default).
DEFAULT_SOFT_LIMIT_FRACTION = 0.8

TWO_CATEGORIES = {
    "platform": {"max_budget": 100.0, "soft_budget": 50.0},
    "cli": {"max_budget": 60.0, "soft_budget": 30.0},
}
SOFT_BUDGET_CATEGORIES = {
    "platform": {"max_budget": 100.0, "soft_budget": 30.0},
    "cli": {"max_budget": 50.0, "soft_budget": 25.0},
}


def change_reference() -> str:
    """A unique change reference, 1-64 characters."""
    return f"CHG-{secrets.token_hex(4)}"


def unknown_email() -> str:
    """An email no CodeMie user has."""
    return f"autotest_unknown_{secrets.token_hex(4)}@email.com"


def budget_request(
    amounts: dict[str, float], project: ProvisioningProjectBlock | None = None
) -> ProvisioningBudgetRequest:
    return ProvisioningBudgetRequest(amounts=amounts, project=project)


# --- one call per route, all taking (service, project_name, reference) -----------------


def put_budget(service, project_name, reference):
    return service.set_budget(
        project_name, reference, budget_request({"platform": 120.0})
    )


def patch_budget(service, project_name, reference):
    return service.adjust_budget(
        project_name, reference, budget_request({"platform": 130.0})
    )


def put_budget_with_empty_project_block(service, project_name, reference):
    return service.set_budget(
        project_name,
        reference,
        budget_request({"platform": 140.0}, ProvisioningProjectBlock()),
    )


def delete_budget(service, project_name, reference):
    return service.cancel_budget(project_name, reference)


def lookup_projects(service, project_name, reference):
    return service.list_projects([unknown_email()])


WRITE_CALLS = [
    pytest.param(put_budget, id="PUT"),
    pytest.param(patch_budget, id="PATCH"),
    pytest.param(delete_budget, id="DELETE"),
]

# --- project setups, each taking the ProvisioningUtils and returning a project name ----


def missing_project(utils: ProvisioningUtils) -> str:
    return utils.new_project_name()


def project_with_budget(utils: ProvisioningUtils) -> str:
    return utils.create_project(PLATFORM_BUDGET_CATEGORIES)


def project_without_budget(utils: ProvisioningUtils) -> str:
    return utils.create_project()


# --- TC-005: cancel ------------------------------------------------------------------

CANCEL_EXISTING_PROJECT_ROWS = [
    pytest.param(project_with_budget, id="project_with_budget"),
    pytest.param(project_without_budget, id="project_without_budget"),
]

# --- TC-009: rejected business checks ------------------------------------------------


@dataclass(frozen=True)
class RejectedNames:
    """Names of a request the backend must refuse with 400."""

    project_name: Callable[[], str]
    cost_center: Callable[[], str]


def _valid_project_name() -> str:
    return f"autotest-{secrets.token_hex(6)}"


def _valid_cost_center() -> str:
    return f"aut-{secrets.token_hex(5)}"


REJECTED_NAME_ROWS = [
    pytest.param(
        RejectedNames(lambda: f"INVALID-{secrets.token_hex(4)}", _valid_cost_center),
        id="invalid_new_project_name",
    ),
    pytest.param(
        RejectedNames(_valid_project_name, lambda: f"nodash{secrets.token_hex(4)}"),
        id="invalid_cost_center_name",
    ),
]

# --- TC-013: cost center link --------------------------------------------------------

# (cost center the project is linked to, cost center the request names, cost center expected)
COST_CENTER_LINK_ROWS = [
    pytest.param("A", "B", "A", id="linked_project_keeps_its_link"),
    pytest.param(None, "B", "B", id="unlinked_project_gets_the_named_link"),
    pytest.param("A", "invalid", "A", id="invalid_name_ignored_for_linked_project"),
]
INVALID_COST_CENTER_NAME = "nodash"

# --- TC-015 / TC-016: budget-only client ---------------------------------------------

BUDGET_ONLY_ALLOWED_ROWS = [
    pytest.param(put_budget, 200, id="PUT_without_project_block"),
    pytest.param(patch_budget, 200, id="PATCH_without_project_block"),
    pytest.param(
        put_budget_with_empty_project_block, 200, id="PUT_empty_project_block"
    ),
    pytest.param(delete_budget, 204, id="DELETE"),
]


# A valid cost center name the budget-only client must not be able to create.
BUDGET_ONLY_COST_CENTER = f"aut-{secrets.token_hex(5)}"


def put_naming_cost_center(service, project_name, reference):
    return service.set_budget(
        project_name,
        reference,
        budget_request(
            {"platform": 120.0},
            ProvisioningProjectBlock(cost_center=BUDGET_ONLY_COST_CENTER),
        ),
    )


def patch_naming_admins(service, project_name, reference):
    return service.adjust_budget(
        project_name,
        reference,
        budget_request(
            {"platform": 130.0},
            ProvisioningProjectBlock(admin_emails=[unknown_email()]),
        ),
    )


BUDGET_ONLY_FORBIDDEN_ROWS = [
    pytest.param(missing_project, put_budget, id="create_missing_project"),
    pytest.param(
        project_with_budget,
        put_naming_cost_center,
        id="existing_project_with_cost_center",
    ),
    pytest.param(
        project_with_budget,
        patch_naming_admins,
        id="existing_project_with_admin_emails",
    ),
]

# --- TC-017: missing permission ------------------------------------------------------

# (fixture of the client, call, permission the 403 names)
MISSING_PERMISSION_ROWS = [
    pytest.param("provisioning_read", put_budget, MANAGE_BUDGETS, id="PUT"),
    pytest.param("provisioning_read", patch_budget, MANAGE_BUDGETS, id="PATCH"),
    pytest.param("provisioning_read", delete_budget, MANAGE_BUDGETS, id="DELETE"),
    pytest.param("provisioning_full", lookup_projects, READ_PROJECTS, id="GET_lookup"),
]

# --- TC-018: a registered client is locked to the provisioning API ---------------------

# Each takes (api_domain, client token, verify_ssl) and calls a route outside /v1/provisioning.
LOCKED_OUT_ROWS = [
    pytest.param(
        lambda domain, token, verify: ProjectService(
            domain, token, verify
        ).list_projects(),
        id="projects_list",
    ),
    pytest.param(
        lambda domain, token, verify: AssistantService(domain, token, verify).list(),
        id="assistants_list",
    ),
    pytest.param(
        lambda domain, token, verify: UserService(domain, token, verify).about_me(),
        id="user_profile",
    ),
]

# --- TC-019: non-registered callers --------------------------------------------------

# (fixture of the caller, call)
NON_REGISTERED_ROWS = [
    pytest.param("client", lookup_projects, id="admin_GET_lookup"),
    pytest.param("client", put_budget, id="admin_PUT_budget"),
    pytest.param("regular_client", put_budget, id="regular_user_PUT_budget"),
]

# --- TC-025: malformed set requests --------------------------------------------------


@dataclass(frozen=True)
class MalformedSet:
    """A set request the backend must refuse with 422: the path name it uses and its body."""

    rename: Callable[[str], str]
    request: ProvisioningBudgetRequest


def _same(name: str) -> str:
    return name


MALFORMED_SET_ROWS = [
    pytest.param(MalformedSet(_same, budget_request({"cli": 10.0})), id="no_platform"),
    pytest.param(
        MalformedSet(_same, budget_request({"platform": 0.0})), id="platform_zero"
    ),
    pytest.param(MalformedSet(_same, budget_request({})), id="empty_amounts"),
    pytest.param(
        MalformedSet(_same, budget_request({"platform": 100.0, "cli": -5.0})),
        id="negative_amount",
    ),
    pytest.param(
        MalformedSet(
            _same,
            ProvisioningBudgetRequest(
                amounts={"platform": 100.0}, unexpected_field="x"
            ),
        ),
        id="unknown_field",
    ),
    pytest.param(
        MalformedSet(lambda name: name[:2], budget_request({"platform": 100.0})),
        id="two_character_project_name",
    ),
]
