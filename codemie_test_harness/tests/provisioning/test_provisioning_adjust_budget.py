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

"""Provisioning API: adjusting a project budget (PATCH /v1/provisioning/projects/{name}/budget)."""

import pytest
from hamcrest import (
    assert_that,
    close_to,
    contains_string,
    equal_to,
    has_entries,
    has_key,
    is_,
    not_none,
)
from requests import HTTPError

from codemie_test_harness.cli.constants import PROVISIONING_FULL_CLIENT_KEYS
from codemie_test_harness.tests.test_data.budget_member_override_test_data import (
    MEMBER_OVERRIDE_MAX,
    MEMBER_OVERRIDE_SOFT,
)
from codemie_test_harness.tests.test_data.budget_test_data import (
    PLATFORM_BUDGET_CATEGORIES,
)
from codemie_test_harness.tests.test_data.provisioning_test_data import (
    AMOUNT_BELOW_MEMBER_LIMIT,
    MEMBER_LIMITS_EXCEED_MESSAGE,
    PLATFORM_MUST_BE_POSITIVE,
    TWO_CATEGORIES,
    budget_request,
    change_reference,
)
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.budget_usage_utils import (
    get_member_allocations,
    wait_for_member_allocation,
)
from codemie_test_harness.tests.utils.user_utils import UserUtils

AMOUNT_TOLERANCE = 0.01


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_adjust_budget_changes_only_the_named_category_and_zero_removes_it(
    provisioning_full, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_003
    project_name = provisioning_utils.create_project(TWO_CATEGORIES)
    platform_before = provisioning_utils.category_budgets(project_name)["platform"]

    changed = provisioning_full.adjust_budget(
        project_name, change_reference(), budget_request({"cli": 80.0})
    )

    assert_that(changed.status_code, equal_to(200), "adjust always answers 200")
    assert_that(
        provisioning_utils.category_budgets(project_name),
        has_entries(
            platform=close_to(platform_before, AMOUNT_TOLERANCE),
            cli=close_to(80.0, AMOUNT_TOLERANCE),
        ),
    )

    removed = provisioning_full.adjust_budget(
        project_name, change_reference(), budget_request({"cli": 0.0})
    )

    assert_that(removed.status_code, equal_to(200))
    categories = provisioning_utils.category_budgets(project_name)
    assert_that(list(categories), equal_to(["platform"]), "zero removes the category")
    assert_that(categories["platform"], close_to(platform_before, AMOUNT_TOLERANCE))


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_adjust_budget_rejects_platform_left_at_zero_and_changes_nothing(
    provisioning_full, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_004
    project_name = provisioning_utils.create_project(PLATFORM_BUDGET_CATEGORIES)
    state_before = provisioning_utils.state(project_name)

    with pytest.raises(HTTPError) as error:
        provisioning_full.adjust_budget(
            project_name, change_reference(), budget_request({"platform": 0.0})
        )

    assert_that(error.value.response.status_code, equal_to(400))
    assert_that(
        UserUtils.error_text(error.value), contains_string(PLATFORM_MUST_BE_POSITIVE)
    )
    assert_that(
        provisioning_utils.state(project_name),
        equal_to(state_before),
        "the rejected call left the budget unchanged",
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_adjust_budget_creates_project_and_budget_and_answers_200(
    provisioning_full, provisioning_utils
):
    # @case provisioning-api-for-third-party_TC_003
    project_name = provisioning_utils.new_project_name()

    result = provisioning_full.adjust_budget(
        project_name, change_reference(), budget_request({"platform": 100.0})
    )

    assert_that(
        result.status_code, equal_to(200), "adjust answers 200 even when it creates"
    )
    assert_that(result.budget.created_project, is_(True))
    assert_that(result.budget.created_budget, is_(True))
    assert_that(provisioning_utils.project_exists(project_name), is_(True))
    assert_that(
        provisioning_utils.category_budgets(project_name)["platform"],
        close_to(100.0, AMOUNT_TOLERANCE),
    )


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_adjust_budget_below_fixed_member_limits_is_rejected_and_changes_nothing(
    provisioning_full,
    platform_user,
    user_utils,
    admin_project_budget_utils,
    lite_llm_budget_utils,
    provisioning_utils,
):
    # @case provisioning-api-for-third-party_TC_004
    member_id = platform_user.user_id
    project_name = provisioning_utils.create_project()
    user_utils.assign_user_to_project(member_id, project_name)
    budget = provisioning_utils.create_budget(project_name, PLATFORM_BUDGET_CATEGORIES)
    budget_id = budget.budget_ids["platform"]
    override_budget_id = f"{budget_id}:user:{member_id}"
    provisioning_utils.track_override_user(project_name, member_id)
    allocations = poll_until(
        lambda: get_member_allocations(admin_project_budget_utils, budget_id),
        lambda found: member_id in found,
        timeout=60.0,
        interval=2.0,
    )
    assert_that(allocations, has_key(member_id), "the member has a share of the budget")
    admin_project_budget_utils.override_member(
        budget_id, member_id, MEMBER_OVERRIDE_MAX, MEMBER_OVERRIDE_SOFT
    )
    allocation_before = wait_for_member_allocation(
        admin_project_budget_utils, budget_id, member_id, MEMBER_OVERRIDE_MAX
    )[member_id]
    override_before = lite_llm_budget_utils.wait_for_budget_max_budget(
        override_budget_id, MEMBER_OVERRIDE_MAX
    )
    assert_that(
        override_before, not_none(), "the member's fixed limit reached the provider"
    )
    row_before = admin_project_budget_utils.get_budget(budget_id)
    key_before = lite_llm_budget_utils.get_key_info_by_alias(budget.alias())
    state_before = provisioning_utils.state(project_name)

    with pytest.raises(HTTPError) as error:
        provisioning_full.adjust_budget(
            project_name,
            change_reference(),
            budget_request({"platform": AMOUNT_BELOW_MEMBER_LIMIT}),
        )

    assert_that(error.value.response.status_code, equal_to(400))
    assert_that(
        UserUtils.error_text(error.value), contains_string(MEMBER_LIMITS_EXCEED_MESSAGE)
    )
    row_after = admin_project_budget_utils.get_budget(budget_id)
    assert_that(
        (row_after["max_budget"], row_after["soft_budget"]),
        equal_to((row_before["max_budget"], row_before["soft_budget"])),
        "the budget row is unchanged",
    )
    allocation_after = get_member_allocations(admin_project_budget_utils, budget_id)[
        member_id
    ]
    assert_that(
        (
            allocation_after["allocation_mode"],
            allocation_after["allocated_max_budget"],
            allocation_after["allocated_soft_budget"],
        ),
        equal_to(
            (
                allocation_before["allocation_mode"],
                allocation_before["allocated_max_budget"],
                allocation_before["allocated_soft_budget"],
            )
        ),
        "the member's fixed limits are unchanged",
    )
    assert_that(
        provisioning_utils.state(project_name),
        equal_to(state_before),
        "the project's budget group is unchanged",
    )
    key_after = lite_llm_budget_utils.get_key_info_by_alias(budget.alias())
    assert_that(
        key_after["max_budget"],
        equal_to(key_before["max_budget"]),
        "the provider's key limit is unchanged",
    )
    override_after = lite_llm_budget_utils.get_budget_info(override_budget_id)
    assert_that(
        (override_after["max_budget"], override_after["soft_budget"]),
        equal_to((override_before["max_budget"], override_before["soft_budget"])),
        "the provider's limits of the member are unchanged",
    )
