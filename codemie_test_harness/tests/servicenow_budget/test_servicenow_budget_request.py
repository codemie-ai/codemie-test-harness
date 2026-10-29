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

"""API tests for applying ServiceNow budget requests (POST /v1/integrations/servicenow/budgets)."""

import secrets

import pytest
from hamcrest import (
    assert_that,
    close_to,
    contains_inanyorder,
    empty,
    equal_to,
    has_length,
    is_,
    none,
    not_none,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.servicenow_project_budget_test_data import (
    ADJUST,
    ADJUSTED_PLATFORM_AMOUNT,
    ALL_CATEGORY_AMOUNTS,
    ALL_CATEGORY_GROUP,
    AMOUNT_TOLERANCE,
    BUDGET_CATEGORIES,
    BUDGET_DURATION,
    BUDGET_GROUP_NAME_TEMPLATE,
    PLATFORM_AND_CLI_GROUP,
    PLATFORM_ONLY_AMOUNTS,
    PROJECT_RESOLUTION_CASES,
    budget_request,
    cancel_request,
    new_project_identity,
    project_missing_message,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.cost_center_utils import (
    get_random_cost_center_name,
)
from codemie_test_harness.tests.utils.servicenow_budget_utils import (
    amounts_close_to,
    budget_amounts,
    error_body,
    group_amounts,
)


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.parametrize("case", PROJECT_RESOLUTION_CASES)
def test_set_budget_creates_project_and_cost_center_only_when_name_differs_from_code(
    servicenow_account, servicenow_budget_utils, servicenow_cleanup, case
):
    # @case servicenow-project-budget-integration-api_TC_003
    identity = new_project_identity(case.name_provided)
    servicenow_cleanup.track_project(identity.project_name)
    servicenow_cleanup.track_cost_center(identity.code)

    response = servicenow_account.integration.submit_budget_request(
        budget_request(
            epam_project_code=identity.code, codemie_project_name=identity.name
        )
    )

    assert_that(
        response.project_name,
        equal_to(identity.project_name),
        "The request must resolve to the project name, else to the project code",
    )
    assert_that(response.created_project, is_(True), "The project is new")
    assert_that(
        response.created_cost_center,
        equal_to(case.created_cost_center),
        "A cost center is created only when the project name differs from the code",
    )
    assert_that(
        response.cost_center,
        equal_to(identity.cost_center_name),
        "The cost center is named after the project code, and is null without one",
    )
    project = servicenow_budget_utils.find_project(identity.project_name)
    assert_that(project, not_none(), "The project must exist after the request")
    assert_that(
        project.cost_center_name,
        equal_to(identity.cost_center_name),
        "The new project must be linked to the cost center the response names",
    )
    assert_that(
        servicenow_budget_utils.cost_centers_named(identity.code),
        has_length(int(case.created_cost_center)),
        "The cost center must exist exactly when the response says it was created",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_set_budget_reuses_existing_project_without_renaming_or_relinking_it(
    servicenow_account,
    servicenow_budget_utils,
    servicenow_cleanup,
    cost_center,
    shared_project,
):
    # @case servicenow-project-budget-integration-api_TC_004
    name_a, name_b = get_random_cost_center_name(), get_random_cost_center_name()
    cost_center_a, cost_center_b = cost_center(name=name_a), cost_center(name=name_b)
    project_a = shared_project(cost_center_id=cost_center_a)
    project_b = shared_project(cost_center_id=cost_center_b)
    other_code = servicenow_cleanup.track_cost_center(get_random_cost_center_name())

    response = servicenow_account.integration.submit_budget_request(
        budget_request(codemie_project_name=project_a, epam_project_code=other_code)
    )

    assert_that(response.project_name, equal_to(project_a), "Project A is reused")
    assert_that(response.created_project, is_(False), "Project A already existed")
    assert_that(
        response.created_cost_center,
        is_(False),
        "A project code that differs from the project name creates nothing for a reused project",
    )
    assert_that(
        response.cost_center,
        equal_to(name_a),
        "The reused project keeps its own cost center",
    )
    detail_a = servicenow_budget_utils.find_project(project_a)
    detail_b = servicenow_budget_utils.find_project(project_b)
    assert_that(
        (detail_a.name, detail_a.cost_center_id, detail_a.cost_center_name),
        equal_to((project_a, cost_center_a, name_a)),
        "Project A must keep its name and cost center link",
    )
    assert_that(
        (detail_b.name, detail_b.cost_center_id, detail_b.cost_center_name),
        equal_to((project_b, cost_center_b, name_b)),
        "The unrelated project B must keep its name and cost center link",
    )
    assert_that(
        [cc.project_count for cc in servicenow_budget_utils.cost_centers_named(name_a)],
        equal_to([1]),
        "Cost center A must still have exactly project A linked",
    )
    assert_that(
        [cc.project_count for cc in servicenow_budget_utils.cost_centers_named(name_b)],
        equal_to([1]),
        "Cost center B must still have exactly project B linked",
    )
    assert_that(
        servicenow_budget_utils.cost_centers_named(other_code),
        empty(),
        "The differing project code must not create a cost center",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_rejected_budget_request_is_refused_and_writes_nothing(
    servicenow_account, servicenow_budget_utils, rejected_budget_request
):
    # @case servicenow-project-budget-integration-api_TC_005
    rejected = rejected_budget_request

    with pytest.raises(HTTPError) as exc_info:
        servicenow_account.integration.submit_budget_request(rejected.request)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(rejected.status_code),
        "The request must be refused with the documented status",
    )
    assert_that(
        error_body(exc_info)["message"],
        equal_to(rejected.message),
        "The refusal must carry the documented message",
    )
    assert_that(
        servicenow_budget_utils.find_project(rejected.project_name) is not None,
        equal_to(rejected.project_exists),
        "A refused request must not create the project",
    )
    assert_that(
        servicenow_budget_utils.member_ids(rejected.project_name),
        equal_to(rejected.member_ids),
        "A refused request must not grant the requested admin any membership",
    )
    assert_that(
        servicenow_budget_utils.active_budget_groups(rejected.project_name),
        empty(),
        "A refused request must not create a budget",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_set_budget_creates_budget_per_category_and_response_reflects_it(
    servicenow_account, servicenow_budget_utils, shared_project
):
    # @case servicenow-project-budget-integration-api_TC_006
    project_name = shared_project()
    request = budget_request(
        codemie_project_name=project_name, amounts=dict(ALL_CATEGORY_AMOUNTS)
    )

    response = servicenow_account.integration.submit_budget_request(request)

    assert_that(
        [category.category for category in response.budget.categories],
        equal_to(list(BUDGET_CATEGORIES)),
        "Categories must be listed in the order platform, cli, premium_models",
    )
    assert_that(
        budget_amounts(response.budget),
        amounts_close_to(ALL_CATEGORY_AMOUNTS),
        "Each category must carry the amount that was sent",
    )
    assert_that(
        response.budget.total_amount,
        close_to(sum(ALL_CATEGORY_AMOUNTS.values()), AMOUNT_TOLERANCE),
        "The total must be the sum of the categories",
    )
    assert_that(
        response.budget.budget_duration,
        equal_to(BUDGET_DURATION),
        "A new budget lasts 30 days",
    )
    groups = servicenow_budget_utils.active_budget_groups(project_name)
    assert_that(groups, has_length(1), "Exactly one active budget group is expected")
    assert_that(
        groups[0]["name"],
        equal_to(BUDGET_GROUP_NAME_TEMPLATE.format(request_id=request.request_id)),
        "The group is named after the request",
    )
    assert_that(
        group_amounts(groups[0]),
        amounts_close_to(ALL_CATEGORY_AMOUNTS),
        "The stored group must hold the same categories and amounts as the response",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_set_budget_replaces_existing_budget_and_drops_categories_not_sent(
    servicenow_account, servicenow_budget_utils, budgeted_project
):
    # @case servicenow-project-budget-integration-api_TC_007
    project = budgeted_project(ALL_CATEGORY_GROUP)

    response = servicenow_account.integration.submit_budget_request(
        budget_request(
            codemie_project_name=project.name, amounts=dict(PLATFORM_ONLY_AMOUNTS)
        )
    )

    assert_that(
        budget_amounts(response.budget),
        amounts_close_to(PLATFORM_ONLY_AMOUNTS),
        "Only platform may remain; cli and premium_models were not sent",
    )
    assert_that(
        response.budget.total_amount,
        close_to(PLATFORM_ONLY_AMOUNTS["platform"], AMOUNT_TOLERANCE),
        "The total must equal the platform amount",
    )
    groups = servicenow_budget_utils.active_budget_groups(project.name)
    assert_that(
        [group["group_id"] for group in groups],
        equal_to([project.group_id]),
        "The existing group must be replaced in place, leaving a single group",
    )
    assert_that(
        group_amounts(groups[0]),
        amounts_close_to(PLATFORM_ONLY_AMOUNTS),
        "The stored group must hold platform only",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_adjust_budget_merges_keeps_unsent_categories_and_removes_category_sent_as_zero(
    servicenow_account, servicenow_budget_utils, budgeted_project
):
    # @case servicenow-project-budget-integration-api_TC_008
    project = budgeted_project(PLATFORM_AND_CLI_GROUP)
    cli_amount = PLATFORM_AND_CLI_GROUP["cli"]["max_budget"]

    platform_adjusted = servicenow_account.integration.submit_budget_request(
        budget_request(
            ADJUST,
            codemie_project_name=project.name,
            amounts={"platform": ADJUSTED_PLATFORM_AMOUNT},
        )
    )

    assert_that(
        budget_amounts(platform_adjusted.budget),
        amounts_close_to({"platform": ADJUSTED_PLATFORM_AMOUNT, "cli": cli_amount}),
        "Platform must take the new amount and cli, which was not sent, must keep its own",
    )

    cli_removed = servicenow_account.integration.submit_budget_request(
        budget_request(ADJUST, codemie_project_name=project.name, amounts={"cli": 0.0})
    )

    assert_that(
        budget_amounts(cli_removed.budget),
        amounts_close_to({"platform": ADJUSTED_PLATFORM_AMOUNT}),
        "Sending cli as 0 must remove it and keep platform",
    )
    groups = servicenow_budget_utils.active_budget_groups(project.name)
    assert_that(
        [group["group_id"] for group in groups],
        equal_to([project.group_id]),
        "Adjusting must update the existing group, not add another",
    )
    assert_that(
        group_amounts(groups[0]),
        amounts_close_to({"platform": ADJUSTED_PLATFORM_AMOUNT}),
        "The stored group must hold platform only",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_cancel_deletes_active_budget_and_second_cancel_is_noop(
    servicenow_account, servicenow_budget_utils, budgeted_project
):
    # @case servicenow-project-budget-integration-api_TC_010
    project = budgeted_project(PLATFORM_AND_CLI_GROUP)

    first = servicenow_account.integration.submit_budget_request(
        cancel_request(project.name)
    )

    assert_that(
        first.project_name, equal_to(project.name), "Cancel targets the project"
    )
    assert_that(first.budget, none(), "A cancelled project has no budget")
    assert_that(
        servicenow_budget_utils.active_budget_groups(project.name),
        empty(),
        "The active budget group must be deleted by cancel",
    )

    second = servicenow_account.integration.submit_budget_request(
        cancel_request(project.name)
    )

    assert_that(
        second.project_name, equal_to(project.name), "Cancel targets the project"
    )
    assert_that(second.budget, none(), "A second cancel must be a successful no-op")
    assert_that(
        servicenow_budget_utils.active_budget_groups(project.name),
        empty(),
        "A second cancel must not bring a budget back",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_cancel_for_project_that_does_not_exist_returns_404_and_creates_nothing(
    servicenow_account, servicenow_budget_utils, servicenow_cleanup
):
    # @case servicenow-project-budget-integration-api_TC_010
    project_name = servicenow_cleanup.track_project(get_random_name())

    with pytest.raises(HTTPError) as exc_info:
        servicenow_account.integration.submit_budget_request(
            cancel_request(project_name)
        )

    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "Cancelling a budget of a missing project must be reported as not found",
    )
    assert_that(
        error_body(exc_info)["message"],
        equal_to(project_missing_message(project_name)),
        "The message must name the missing project",
    )
    assert_that(
        servicenow_budget_utils.find_project(project_name),
        none(),
        "Cancel must not create the missing project",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_set_budget_makes_requested_emails_project_admins_and_reports_unresolved_ones(
    servicenow_account,
    servicenow_budget_utils,
    shared_project,
    registered_user,
    user_utils,
):
    # @case servicenow-project-budget-integration-api_TC_011
    project_name = shared_project()
    new_admin, existing_admin = registered_user(), registered_user()
    unregistered_email = f"autotest_sn_unknown_{secrets.token_hex(4)}@email.com"
    user_utils.assign_user_to_project(
        existing_admin.user_id, project_name, is_project_admin=True
    )
    members_before = {
        member.user_id: member
        for member in servicenow_budget_utils.find_project(project_name).members
    }
    assert_that(
        members_before[existing_admin.user_id].is_project_admin,
        is_(True),
        "Precondition: one user is already a project admin",
    )
    assert_that(
        new_admin.user_id in members_before,
        is_(False),
        "Precondition: the other user is not yet a member",
    )

    response = servicenow_account.integration.submit_budget_request(
        budget_request(
            codemie_project_name=project_name,
            admin_emails=[
                new_admin.email,
                existing_admin.email,
                unregistered_email,
            ],
        )
    )

    assert_that(
        response.admins_assigned,
        contains_inanyorder(new_admin.email, existing_admin.email),
        "Both registered users must be reported as admins, the one that already was included",
    )
    assert_that(
        response.admins_pending,
        equal_to([unregistered_email]),
        "The email with no CodeMie user must be reported as pending",
    )
    members_after = {
        member.user_id: member
        for member in servicenow_budget_utils.find_project(project_name).members
    }
    assert_that(
        members_after[new_admin.user_id].is_project_admin,
        is_(True),
        "The newly assigned user must be a project admin",
    )
    assert_that(
        members_after[existing_admin.user_id],
        equal_to(members_before[existing_admin.user_id]),
        "The user who already was a project admin must be left unchanged",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_repeated_identical_budget_request_leaves_single_consistent_result(
    servicenow_account, servicenow_budget_utils, servicenow_cleanup, registered_user
):
    # @case servicenow-project-budget-integration-api_TC_014
    identity = new_project_identity(name_provided=True)
    servicenow_cleanup.track_project(identity.project_name)
    servicenow_cleanup.track_cost_center(identity.code)
    request = budget_request(
        epam_project_code=identity.code,
        codemie_project_name=identity.name,
        amounts=dict(ALL_CATEGORY_AMOUNTS),
        admin_emails=[registered_user().email],
    )

    first = servicenow_account.integration.submit_budget_request(request)
    second = servicenow_account.integration.submit_budget_request(request)

    assert_that(
        (first.created_project, first.created_cost_center),
        equal_to((True, True)),
        "The first request creates the project and its cost center",
    )
    assert_that(
        (second.created_project, second.created_cost_center),
        equal_to((False, False)),
        "The retry must reuse the project and cost center",
    )
    assert_that(
        second.model_dump(exclude={"created_project", "created_cost_center"}),
        equal_to(first.model_dump(exclude={"created_project", "created_cost_center"})),
        "The retry must return the same project, cost center, budget and admins",
    )

    recased = servicenow_account.integration.submit_budget_request(
        request.model_copy(update={"codemie_project_name": identity.name.upper()})
    )

    assert_that(
        recased.project_name,
        equal_to(identity.name),
        "A different letter case must resolve to the same project",
    )
    assert_that(
        (recased.created_project, recased.created_cost_center),
        equal_to((False, False)),
        "A different letter case must not create a second project or cost center",
    )
    assert_that(recased.budget, equal_to(first.budget), "The budget is unchanged")
    assert_that(
        servicenow_budget_utils.projects_named(identity.name),
        has_length(1),
        "Exactly one project is expected",
    )
    assert_that(
        servicenow_budget_utils.cost_centers_named(identity.code),
        has_length(1),
        "Exactly one cost center is expected",
    )
    assert_that(
        servicenow_budget_utils.active_budget_groups(identity.name),
        has_length(1),
        "Exactly one active budget group is expected",
    )
