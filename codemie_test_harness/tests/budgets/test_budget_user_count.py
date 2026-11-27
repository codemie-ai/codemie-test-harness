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

"""API tests for the user_count of GET /v1/admin/budgets.

The list sets user_count on every budget of the page (budget_router.py:102): the number of
distinct users assigned to it, 0 when there are none (budget_service.py:340), soft-deleted
users not counted (budget_repository.py:219). Counts are asserted only on budgets the test
creates, since shared budgets on a stand carry any number of users.
"""

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    only_contains,
    has_entry,
    instance_of,
    is_not,
    empty,
)


# @case budget-user-count-redirect_TC_002
@pytest.mark.budget
@pytest.mark.api
def test_budget_list_returns_user_count_and_skips_soft_deleted_users(
    manual_budget,
    assign_budget_user,
    manual_budget_factory,
    platform_user,
    second_platform_user,
    maintainer_budget_utils,
    user_utils,
):
    """AC-2/AC-4: every budget of the list carries an integer user_count, 0 for a budget with
    no users and 2 for one with two; soft-deleting one of the two users through
    DELETE /v1/admin/users/{id} drops the count to 1."""
    empty_budget_id = manual_budget_factory()["budget_id"]
    budget_id = manual_budget["budget_id"]
    assign_budget_user(platform_user.user_id)
    assign_budget_user(second_platform_user.user_id)

    listed_page = maintainer_budget_utils.list_budgets(page=0, per_page=100)

    assert_that(
        listed_page, is_not(empty()), "GET /v1/admin/budgets should list budgets"
    )
    assert_that(
        listed_page,
        only_contains(has_entry("user_count", instance_of(int))),
        "every listed budget should carry an integer user_count",
    )
    assert_that(
        maintainer_budget_utils.find_budget_in_list(empty_budget_id)["user_count"],
        equal_to(0),
        "a budget with no assigned users should list user_count 0",
    )
    assert_that(
        maintainer_budget_utils.find_budget_in_list(budget_id)["user_count"],
        equal_to(2),
        "a budget with two assigned users should list user_count 2",
    )

    user_utils.deactivate_user(second_platform_user.user_id)

    assert_that(
        maintainer_budget_utils.find_budget_in_list(budget_id)["user_count"],
        equal_to(1),
        "a soft-deleted user should no longer be counted in user_count",
    )
