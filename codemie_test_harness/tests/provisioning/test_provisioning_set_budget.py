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

"""Provisioning API: setting a project budget (PUT /v1/provisioning/projects/{name}/budget)."""

import pytest
from hamcrest import (
    assert_that,
    close_to,
    equal_to,
    has_entries,
    has_item,
    is_,
    is_in,
    is_not,
    none,
)

from codemie_sdk.models.provisioning import ProvisioningProjectBlock
from codemie_test_harness.cli.constants import PROVISIONING_FULL_CLIENT_KEYS
from codemie_test_harness.tests.test_data.provisioning_test_data import (
    DEFAULT_SOFT_LIMIT_FRACTION,
    SOFT_BUDGET_CATEGORIES,
    TWO_CATEGORIES,
    budget_request,
    change_reference,
    unknown_email,
)

AMOUNT_TOLERANCE = 0.01


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_creates_project_cost_center_admins_and_budget(
    provisioning_full,
    provisioning_client_names,
    provisioning_client_user_id,
    non_admin_user,
    provisioning_utils,
):
    # @case provisioning-api-for-third-party_TC_001
    member_email, member_id, _ = non_admin_user
    project_name = provisioning_utils.new_project_name()
    cost_center = provisioning_utils.new_cost_center_name()
    unknown = unknown_email()
    reference = change_reference()

    result = provisioning_full.set_budget(
        project_name,
        reference,
        budget_request(
            {"platform": 100.0, "cli": 40.0},
            ProvisioningProjectBlock(
                cost_center=cost_center, admin_emails=[member_email, unknown]
            ),
        ),
    )

    assert_that(result.status_code, equal_to(201), "creating a budget answers 201")
    body = result.budget
    assert_that(body.project_name, equal_to(project_name))
    assert_that(body.cost_center, equal_to(cost_center))
    assert_that(body.created_project, is_(True), "the call created the project")
    assert_that(body.created_cost_center, is_(True), "the call created the cost center")
    assert_that(body.created_budget, is_(True), "the call created the budget")
    assert_that(body.admins_assigned, equal_to([member_email]))
    assert_that(body.admins_not_assigned, equal_to([unknown]))

    assert_that(provisioning_utils.project_exists(project_name), is_(True))
    assert_that(provisioning_utils.cost_center_exists(cost_center), is_(True))
    assert_that(provisioning_utils.cost_center_of(project_name), equal_to(cost_center))
    assert_that(
        provisioning_utils.admin_ids(project_name),
        has_item(member_id),
        "the active user is a project admin",
    )
    assert_that(
        provisioning_utils.member_ids(project_name),
        is_not(has_item(provisioning_client_user_id)),
        "the calling client did not become a member of the project it created",
    )
    group = provisioning_utils.active_budget_group(project_name)
    provisioning_client_names.observe(group["name"], reference)
    assert_that(group["budget_duration"], equal_to("30d"))
    assert_that(
        provisioning_utils.category_budgets(project_name),
        has_entries(
            platform=close_to(100.0, AMOUNT_TOLERANCE),
            cli=close_to(40.0, AMOUNT_TOLERANCE),
        ),
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_creates_budget_for_existing_project_without_one_and_adds_no_member(
    provisioning_full,
    provisioning_client_names,
    provisioning_client_user_id,
    provisioning_utils,
):
    # @case provisioning-api-for-third-party_TC_001
    project_name = provisioning_utils.create_project()
    members_before = provisioning_utils.member_ids(project_name)
    assert_that(
        provisioning_utils.active_budget_group(project_name),
        none(),
        "the project starts without a budget",
    )
    reference = change_reference()

    result = provisioning_full.set_budget(
        project_name, reference, budget_request({"platform": 100.0})
    )

    assert_that(result.status_code, equal_to(201), "creating a budget answers 201")
    assert_that(result.budget.created_budget, is_(True))
    assert_that(
        result.budget.created_project, is_(False), "the project existed already"
    )
    group = provisioning_utils.active_budget_group(project_name)
    provisioning_client_names.observe(group["name"], reference)
    members_after = provisioning_utils.member_ids(project_name)
    assert_that(members_after, equal_to(members_before), "no member was added")
    assert_that(
        members_after,
        is_not(has_item(provisioning_client_user_id)),
        "the calling client is not a member of the project",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_replaces_amounts_and_removes_categories_not_sent(
    provisioning_full, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_002
    project_name = provisioning_utils.create_project(TWO_CATEGORIES)
    before = provisioning_utils.active_budget_group(project_name)

    result = provisioning_full.set_budget(
        project_name, change_reference(), budget_request({"platform": 150.0})
    )

    assert_that(result.status_code, equal_to(200), "replacing a budget answers 200")
    assert_that(result.budget.created_budget, is_(False))
    after = provisioning_utils.active_budget_group(project_name)
    assert_that(after["group_id"], equal_to(before["group_id"]), "same budget replaced")
    assert_that(after["budget_duration"], equal_to(before["budget_duration"]))
    categories = provisioning_utils.category_budgets(project_name)
    assert_that(list(categories), equal_to(["platform"]), "category not sent is gone")
    assert_that(categories["platform"], close_to(150.0, AMOUNT_TOLERANCE))


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_resend_converges_to_the_same_state(
    provisioning_full, non_admin_user, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_011
    member_email, _, _ = non_admin_user
    project_name = provisioning_utils.new_project_name()
    request = budget_request(
        {"platform": 100.0, "cli": 40.0},
        ProvisioningProjectBlock(
            cost_center=provisioning_utils.new_cost_center_name(),
            admin_emails=[member_email],
        ),
    )

    first = provisioning_full.set_budget(project_name, change_reference(), request)
    state_after_first = provisioning_utils.state(project_name)
    second = provisioning_full.set_budget(project_name, change_reference(), request)

    assert_that(first.status_code, equal_to(201))
    assert_that(second.status_code, is_in([200, 201]), "a resend answers 200 or 201")
    assert_that(second.budget.created_project, is_(False), "the project exists already")
    assert_that(
        provisioning_utils.state(project_name),
        equal_to(state_after_first),
        "project, cost center, admins and budget are the same after the resend",
    )
    assert_that(second.budget.cost_center, equal_to(first.budget.cost_center))
    assert_that(second.budget.admins_assigned, equal_to(first.budget.admins_assigned))


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_keeps_soft_budget_of_unchanged_category_and_resets_changed_one(
    provisioning_full, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_026
    project_name = provisioning_utils.create_project(SOFT_BUDGET_CATEGORIES)
    soft_before = provisioning_utils.soft_budgets(project_name)
    unchanged_soft = soft_before["platform"]
    changed_soft = soft_before["cli"]
    new_cli_amount = 80.0

    result = provisioning_full.set_budget(
        project_name,
        change_reference(),
        budget_request(
            {
                "platform": SOFT_BUDGET_CATEGORIES["platform"]["max_budget"],
                "cli": new_cli_amount,
            }
        ),
    )

    assert_that(result.status_code, equal_to(200))
    soft_after = provisioning_utils.soft_budgets(project_name)
    assert_that(
        soft_after["platform"],
        close_to(unchanged_soft, AMOUNT_TOLERANCE),
        "unchanged category keeps its soft budget",
    )
    assert_that(
        soft_after["cli"],
        close_to(new_cli_amount * DEFAULT_SOFT_LIMIT_FRACTION, AMOUNT_TOLERANCE),
        "changed category soft budget is reset to the default share of its new amount",
    )
    assert_that(
        soft_after["cli"],
        is_not(close_to(changed_soft, AMOUNT_TOLERANCE)),
        "changed category no longer has the soft budget set before the call",
    )
