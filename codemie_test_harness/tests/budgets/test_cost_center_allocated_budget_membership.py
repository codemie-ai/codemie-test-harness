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

"""API tests for the cost center Allocated Budget after project membership changes.

The Allocated Budget (``allocated_member_budget_total`` of the cost center budget rollup) is
summed from the members' stored equal shares. Adding or removing a project member re-splits
those shares in the same request, so the figure must keep matching the project budget without
a manual rebalance. Needs ENABLE_USER_MANAGEMENT and a build that includes the rollup endpoint.

Covered cases:
    TC-001  Allocated Budget follows a member being added and removed (AC-1, AC-2)
"""

import pytest
from hamcrest import assert_that, close_to, equal_to, not_none

from codemie_test_harness.tests.test_data.cost_center_rollup_test_data import (
    AMOUNT_TOLERANCE,
    MEMBERSHIP_SHARE_PLATFORM,
)


def _platform_rollup(cost_center_utils, cc_id):
    """The cost center's platform rollup entry, read fresh from the rollup endpoint."""
    summary = cost_center_utils.get_budget_rollup(cc_id)
    platform = cost_center_utils.rollup_category(summary, "platform")
    assert_that(platform, not_none(), "The rollup must list the platform category.")
    return platform


@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
@pytest.mark.api
def test_cost_center_allocated_budget_follows_member_add_and_remove_without_rebalance(
    user1_project_utils,
    user2_id,
    cost_center,
    cost_center_budget_projects,
    cost_center_utils,
):
    # @case cost-center-page-shows-incorrect_TC_001
    max_budget = MEMBERSHIP_SHARE_PLATFORM["platform"]["max_budget"]
    cc_id = cost_center()
    budget = cost_center_budget_projects.create(
        cc_id,
        MEMBERSHIP_SHARE_PLATFORM,
        creator_utils=user1_project_utils,
        track_members=True,
    )
    cost_center_budget_projects.wait_until_budgets_usable(budget)

    initial = _platform_rollup(cost_center_utils, cc_id)
    assert_that(
        initial.member_count, equal_to(1), "The project starts with one member."
    )
    assert_that(
        initial.allocated_member_budget_total,
        close_to(max_budget, AMOUNT_TOLERANCE),
        "The one member's share must be the whole project budget.",
    )

    user1_project_utils.assign_user_to_project(
        budget.project_name, user2_id, is_project_admin=False
    )

    after_add = _platform_rollup(cost_center_utils, cc_id)
    assert_that(
        after_add.member_count,
        equal_to(2),
        "The added user must be counted as a member of the project budget.",
    )
    assert_that(
        after_add.allocated_member_budget_total,
        close_to(max_budget, AMOUNT_TOLERANCE),
        "After a member is added the equal shares must be re-split across both members "
        "and still sum to the project budget.",
    )

    user1_project_utils.remove_user_from_project(budget.project_name, user2_id)

    after_remove = _platform_rollup(cost_center_utils, cc_id)
    assert_that(
        after_remove.member_count,
        equal_to(1),
        "The removed user must no longer be counted as a member of the project budget.",
    )
    assert_that(
        after_remove.allocated_member_budget_total,
        close_to(max_budget, AMOUNT_TOLERANCE),
        "After a member is removed the remaining member's share must be re-split to the "
        "whole project budget.",
    )
