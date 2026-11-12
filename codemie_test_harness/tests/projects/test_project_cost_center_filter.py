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

"""API tests for the cost center filter of the project list (GET /v1/projects).

The filter is a repeated `cost_center_ids` query parameter: a project is listed when it is
assigned to any of the selected cost centers, and the filter is ANDed with the search and
budget filters. Projects and cost centers are created through the API and removed by their
fixtures; the admin sees every project, so a result is exact because only the cost centers
created by the test hold projects of the filtered set.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_inanyorder,
    equal_to,
    has_item,
    not_,
)

from codemie_test_harness.tests.test_data.cost_center_rollup_test_data import (
    SINGLE_PROJECT_PLATFORM,
)
from codemie_test_harness.tests.test_data.projects_test_data import (
    cost_center_filter_selection_test_data,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize(
    "selected_positions, listed_positions", cost_center_filter_selection_test_data
)
def test_list_projects_returns_only_projects_of_selected_cost_centers(
    project_utils, cost_center, project, selected_positions, listed_positions
):
    """Projects assigned to any selected cost center are listed; a project of an
    unselected cost center and a project without a cost center are not."""
    # @case cost-center-filter-project-management_TC_003
    cost_center_ids = [cost_center(), cost_center()]
    assigned_names = [project(cost_center_id=cc_id).name for cc_id in cost_center_ids]
    unassigned_name = project().name
    selected_ids = [cost_center_ids[position] for position in selected_positions]
    expected_names = [assigned_names[position] for position in listed_positions]

    response = project_utils.list_projects(cost_center_ids=selected_ids)

    assert_that(
        [item.name for item in response.data],
        contains_inanyorder(*expected_names),
        "Only the projects of the selected cost centers must be listed",
    )
    assert_that(
        [item.name for item in response.data],
        not_(has_item(unassigned_name)),
        "A project without a cost center must not be listed when a cost center is selected",
    )
    assert_that(
        response.pagination.total,
        equal_to(len(expected_names)),
        "The pagination total must count the filtered projects, not all projects",
    )


@pytest.mark.project
@pytest.mark.api
def test_list_projects_cost_center_filter_combines_with_search(
    project_utils, cost_center, project
):
    """A project is listed only when it is in the selected cost center AND matches the
    search: a non-matching project of that cost center and a matching project of another
    cost center are both excluded."""
    # @case cost-center-filter-project-management_TC_005
    search_term = get_random_name()
    selected_cc_id, other_cc_id = cost_center(), cost_center()
    matching = project(cost_center_id=selected_cc_id, description=search_term).name
    non_matching = project(cost_center_id=selected_cc_id).name
    other_cost_center = project(
        cost_center_id=other_cc_id, description=search_term
    ).name

    response = project_utils.list_projects(
        search=search_term, cost_center_ids=[selected_cc_id]
    )

    names = [item.name for item in response.data]
    assert_that(
        names,
        contains_inanyorder(matching),
        "Only the project of the selected cost center that matches the search must be listed",
    )
    assert_that(
        names,
        not_(has_item(non_matching)),
        "A project of the selected cost center that does not match the search is excluded",
    )
    assert_that(
        names,
        not_(has_item(other_cost_center)),
        "A project matching the search but in another cost center is excluded",
    )
    assert_that(response.pagination.total, equal_to(1))


@pytest.mark.project
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_list_projects_cost_center_filter_combines_with_assigned_budgets_filter(
    project_utils, cost_center, project, cost_center_budget_projects
):
    """With has_assigned_budgets the selected cost center lists only its projects that
    have an assigned budget: its unbudgeted project and a budgeted project of another cost
    center are both excluded."""
    # @case cost-center-filter-project-management_TC_005
    selected_cc_id, other_cc_id = cost_center(), cost_center()
    budgeted = cost_center_budget_projects.create(
        selected_cc_id, SINGLE_PROJECT_PLATFORM
    ).project_name
    unbudgeted = project(cost_center_id=selected_cc_id).name
    other_cost_center = cost_center_budget_projects.create(
        other_cc_id, SINGLE_PROJECT_PLATFORM
    ).project_name

    response = project_utils.list_projects(
        has_assigned_budgets=True, cost_center_ids=[selected_cc_id]
    )

    names = [item.name for item in response.data]
    assert_that(
        names,
        contains_inanyorder(budgeted),
        "Only the budgeted project of the selected cost center must be listed",
    )
    assert_that(
        names,
        not_(has_item(unbudgeted)),
        "A project of the selected cost center without an assigned budget is excluded",
    )
    assert_that(
        names,
        not_(has_item(other_cost_center)),
        "A budgeted project of another cost center is excluded",
    )
    assert_that(response.pagination.total, equal_to(1))
