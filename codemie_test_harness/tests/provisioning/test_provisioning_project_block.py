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

"""Provisioning API: the project block of a budget request (cost center link and admins)."""

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    has_items,
    is_,
    is_not,
    has_item,
)
from requests import HTTPError

from codemie_sdk.models.provisioning import ProvisioningProjectBlock
from codemie_test_harness.cli.constants import PROVISIONING_FULL_CLIENT_KEYS
from codemie_test_harness.tests.test_data.provisioning_test_data import (
    COST_CENTER_LINK_ROWS,
    INVALID_COST_CENTER_NAME,
    budget_request,
    change_reference,
    late_user_email,
    unknown_email,
)
from codemie_test_harness.tests.utils.cost_center_utils import (
    get_random_cost_center_name,
)


@pytest.mark.parametrize(("linked", "requested", "expected"), COST_CENTER_LINK_ROWS)
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_links_cost_center_once_and_never_changes_an_existing_link(
    provisioning_full,
    provisioning_client_names,
    cost_center,
    provisioning_utils,
    linked,
    requested,
    expected,
):
    # @case provisioning-api-for-third-party_TC_013
    name_a = get_random_cost_center_name()
    name_b = get_random_cost_center_name()
    cost_center_ids = {"A": cost_center(name=name_a), "B": cost_center(name=name_b)}
    names = {
        "A": name_a,
        "B": name_b,
        "invalid": INVALID_COST_CENTER_NAME,
        None: None,
    }
    project_name = provisioning_utils.create_project(
        cost_center_id=cost_center_ids.get(linked)
    )

    reference = change_reference()

    result = provisioning_full.set_budget(
        project_name,
        reference,
        budget_request(
            {"platform": 100.0},
            ProvisioningProjectBlock(cost_center=names[requested]),
        ),
    )

    assert_that(result.budget.cost_center, equal_to(names[expected]))
    assert_that(
        result.budget.created_cost_center,
        is_(False),
        "the named cost center existed already",
    )
    assert_that(
        provisioning_utils.cost_center_of(project_name),
        equal_to(names[expected]),
        "the stored link is the one expected",
    )
    provisioning_client_names.observe(
        provisioning_utils.active_budget_group(project_name)["name"], reference
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_only_adds_admins_and_reports_unknown_emails(
    provisioning_full,
    platform_user,
    admin_user,
    user_utils,
    provisioning_utils,
):
    # @case provisioning-api-for-third-party_TC_014
    member_email, member_id = platform_user.email, platform_user.user_id
    admin_id = admin_user.user_id
    unknown = unknown_email()
    project_name = provisioning_utils.create_project()
    user_utils.assign_user_to_project(admin_id, project_name, is_project_admin=True)
    user_utils.assign_user_to_project(member_id, project_name)
    assert_that(
        provisioning_utils.admin_ids(project_name),
        is_not(has_item(member_id)),
        "the member starts as a plain member",
    )

    result = provisioning_full.set_budget(
        project_name,
        change_reference(),
        budget_request(
            {"platform": 100.0},
            ProvisioningProjectBlock(admin_emails=[member_email, unknown]),
        ),
    )

    assert_that(result.budget.admins_assigned, equal_to([member_email]))
    assert_that(
        result.budget.admins_not_assigned,
        equal_to([unknown]),
        "an unknown email is not made an admin",
    )
    assert_that(
        provisioning_utils.admin_ids(project_name),
        has_items(member_id, admin_id),
        "the member was promoted and the original admin is still an admin",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_reports_registered_client_email_as_not_assigned(
    provisioning_full,
    provisioning_client_email,
    provisioning_utils,
):
    # @case provisioning-api-for-third-party_TC_014
    project_name = provisioning_utils.create_project()
    admins_before = provisioning_utils.admin_ids(project_name)

    result = provisioning_full.set_budget(
        project_name,
        change_reference(),
        budget_request(
            {"platform": 100.0},
            ProvisioningProjectBlock(admin_emails=[provisioning_client_email]),
        ),
    )

    assert_that(
        result.budget.admins_not_assigned,
        equal_to([provisioning_client_email]),
        "a registered client is a service account and is not made an admin",
    )
    assert_that(result.budget.admins_assigned, equal_to([]))
    assert_that(
        provisioning_utils.admin_ids(project_name),
        equal_to(admins_before),
        "no project admin was added",
    )


@pytest.mark.xfail(
    reason=(
        "Adding the first member to a project created via the provisioning API "
        "returns 500 (FK violation on fk_pmba_shared_budget_id)"
    ),
    raises=HTTPError,
    strict=True,
)
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_set_budget_resend_assigns_admin_who_did_not_exist_at_the_first_call(
    provisioning_full, late_user, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_014
    admin_email = late_user_email()
    project_name = provisioning_utils.new_project_name()
    request = budget_request(
        {"platform": 100.0}, ProvisioningProjectBlock(admin_emails=[admin_email])
    )

    first = provisioning_full.set_budget(project_name, change_reference(), request)
    assert_that(first.budget.admins_not_assigned, equal_to([admin_email]))
    assert_that(first.budget.admins_assigned, equal_to([]))
    admin_id = late_user(admin_email)
    second = provisioning_full.set_budget(project_name, change_reference(), request)

    assert_that(
        second.budget.admins_assigned,
        equal_to([admin_email]),
        "the same request assigns the admin once the user exists",
    )
    assert_that(second.budget.admins_not_assigned, equal_to([]))
    assert_that(
        provisioning_utils.admin_ids(project_name),
        has_item(admin_id),
        "the user is a project admin",
    )
