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

"""UI tests for the project-count badge of the Cost Centers management list.

For a platform admin the badge of a row is a link named 'Projects' to Projects management
filtered to that cost center. Both screens are shown only with the `features:costCenters`
flag on, which these tests expect on the target environment.

Cost centers and projects are created through the API with unique names and removed by their
fixtures; the tests never assert on counts of shared data.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.cost_centers_management_page import (
    CostCentersManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.test_data.cost_center_project_count_test_data import (
    PROJECT_COUNTS,
    LinkedCostCenter,
)
from codemie_test_harness.tests.utils.cost_center_utils import (
    get_random_cost_center_name,
)


def _linked_cost_center(cost_center, project, project_count: int) -> LinkedCostCenter:
    """Create a cost center with `project_count` projects linked to it."""
    name = get_random_cost_center_name()
    cost_center_id = cost_center(name=name)
    projects = [project(cost_center_id=cost_center_id) for _ in range(project_count)]
    return LinkedCostCenter(
        id=str(cost_center_id), name=name, project_names=[p.name for p in projects]
    )


@pytest.fixture
def cost_center_with_projects(request, cost_center, project):
    """A cost center with `request.param` projects linked to it (indirect parameter).

    `cost_center` is requested first, so the projects are deleted before the cost center.
    """
    return _linked_cost_center(cost_center, project, request.param)


@pytest.fixture
def two_linked_cost_centers(cost_center, project):
    """Two cost centers with one project each."""
    return (
        _linked_cost_center(cost_center, project, 1),
        _linked_cost_center(cost_center, project, 1),
    )


@pytest.mark.project
@pytest.mark.ui
@pytest.mark.prod_regression
@pytest.mark.parametrize("cost_center_with_projects", PROJECT_COUNTS, indirect=True)
def test_project_count_badge_links_to_projects_filtered_by_cost_center(
    page, cost_center_with_projects
):
    # @case cost-center-project-count-redirect_TC_001
    linked = cost_center_with_projects
    cost_centers_page = CostCentersManagementPage(page).navigate_to()

    cost_centers_page.should_show_project_count_link(
        linked.name, linked.project_count, linked.id
    )
    cost_centers_page.click_project_count_badge(linked.name)

    projects_page = ProjectManagementPage(page)
    projects_page.should_be_open()
    projects_page.should_have_cost_center_in_url(linked.id)
    projects_page.should_show_selected_cost_centers([linked.name])
    projects_page.should_list_cost_center_projects(linked.project_names)


@pytest.mark.project
@pytest.mark.ui
@pytest.mark.prod_regression
def test_cost_center_filter_set_by_badge_can_be_changed_and_cleared(
    page, two_linked_cost_centers
):
    # @case cost-center-project-count-redirect_TC_002
    first, second = two_linked_cost_centers
    CostCentersManagementPage(page).navigate_to().click_project_count_badge(first.name)
    projects_page = ProjectManagementPage(page)

    projects_page.should_be_open()
    projects_page.should_have_cost_center_in_url(first.id)
    projects_page.should_show_selected_cost_centers([first.name])
    projects_page.should_list_only_projects(first.project_names)

    projects_page.remove_cost_center_from_filter(first.name, [])
    projects_page.should_show_no_cost_center_selected()
    projects_page.should_not_have_cost_center_in_url()
    projects_page.should_list_more_than(1)

    projects_page.filter_by_cost_centers([second.name], [second.id])
    projects_page.should_have_cost_center_in_url(second.id)
    projects_page.should_show_selected_cost_centers([second.name])
    projects_page.should_list_only_projects(second.project_names)

    projects_page.clear_cost_center_filter()
    projects_page.should_show_no_cost_center_selected()
    projects_page.should_not_have_cost_center_in_url()
    projects_page.should_list_more_than(1)


# Intended behaviour: an auditor-only user can open the Cost Centers list and, like an admin or
# maintainer, sees the project-count badge as a link to Projects management filtered to the cost
# center. Today the list cannot be read by an auditor-only user, so the test is expected to fail;
# strict, so it turns red once access is fixed and this marker has to come off.
@pytest.mark.xfail(
    reason="Auditor-only user has no read access to cost centers", strict=True
)
@pytest.mark.auditor
@pytest.mark.project
@pytest.mark.ui
@pytest.mark.parametrize("acting_credentials", ["cli_auditor"], indirect=True)
@pytest.mark.parametrize("cost_center_with_projects", [1], indirect=True)
def test_auditor_sees_project_count_as_link_to_filtered_projects(
    page, cost_center_with_projects
):
    # @case cost-center-project-count-redirect_TC_003
    linked = cost_center_with_projects
    cost_centers_page = CostCentersManagementPage(page).navigate_to()

    cost_centers_page.should_show_project_count_link(
        linked.name, linked.project_count, linked.id
    )
