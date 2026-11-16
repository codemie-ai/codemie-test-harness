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

"""UI tests for the Cost center filter of Projects Management.

The filter is a checkbox multi-select in the filter row next to Search; it is shown only
with the `features:costCenters` flag on, which these tests expect on the target environment.
Selecting cost centers lists only the projects assigned to any of them, and the selection is
kept in the stored project filters.

Cost centers and projects are created through the API and removed by their fixtures.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.test_data.project_cost_center_filter_test_data import (
    NO_MATCH_SEARCH_TERM,
    distinctive_fragment,
)
from codemie_test_harness.tests.utils.cost_center_utils import (
    get_random_cost_center_name,
)


@pytest.mark.project
@pytest.mark.ui
def test_cost_center_filter_is_visible_in_project_filter_row(page):
    # @case cost-center-filter-project-management_TC_001
    projects_page = ProjectManagementPage(page).navigate_to()

    projects_page.should_see_search_and_budget_filters()
    projects_page.should_see_cost_center_filter()


@pytest.mark.project
@pytest.mark.ui
def test_typing_narrows_cost_center_options_and_selected_names_are_comma_separated(
    page, cost_center
):
    # @case cost-center-filter-project-management_TC_002
    first_name, second_name = (
        get_random_cost_center_name(),
        get_random_cost_center_name(),
    )
    cost_center(name=first_name)
    cost_center(name=second_name)
    projects_page = ProjectManagementPage(page).navigate_to()

    projects_page.open_cost_center_filter()
    projects_page.search_cost_centers(distinctive_fragment(first_name))
    projects_page.should_offer_cost_center_option(first_name)
    projects_page.should_not_offer_cost_center_option(second_name)
    projects_page.select_cost_center(first_name)
    projects_page.clear_cost_center_search()
    projects_page.search_cost_centers(second_name)
    projects_page.select_cost_center(second_name)
    projects_page.close_cost_center_filter()

    projects_page.should_show_selected_cost_centers([first_name, second_name])


@pytest.mark.project
@pytest.mark.ui
def test_cost_center_filter_narrows_project_list_and_clearing_restores_it(
    page, cost_center, project
):
    # @case cost-center-filter-project-management_TC_004
    first_name, second_name = (
        get_random_cost_center_name(),
        get_random_cost_center_name(),
    )
    first_id, second_id = cost_center(name=first_name), cost_center(name=second_name)
    first_project = project(cost_center_id=first_id).name
    second_project = project(cost_center_id=second_id).name
    projects_page = ProjectManagementPage(page).navigate_to()

    projects_page.filter_by_cost_centers(
        [first_name, second_name], [first_id, second_id]
    )
    projects_page.should_list_only_projects([first_project, second_project])

    projects_page.remove_cost_center_from_filter(second_name, [first_id])
    projects_page.should_list_only_projects([first_project])

    projects_page.clear_cost_center_filter()
    projects_page.should_show_no_cost_center_selected()
    projects_page.should_list_more_than(1)


@pytest.mark.project
@pytest.mark.ui
def test_cost_center_filter_shows_no_match_message_for_unmatched_search(page):
    # @case cost-center-filter-project-management_TC_007
    projects_page = ProjectManagementPage(page).navigate_to()

    projects_page.open_cost_center_filter()
    projects_page.search_cost_centers(NO_MATCH_SEARCH_TERM)

    projects_page.should_see_no_cost_center_match_message()


@pytest.mark.project
@pytest.mark.ui
def test_cost_center_selection_survives_reload_and_deleted_cost_center_is_pruned(
    page, cost_center, cost_center_utils
):
    # @case cost-center-filter-project-management_TC_008
    name = get_random_cost_center_name()
    cost_center_id = cost_center(name=name)
    projects_page = ProjectManagementPage(page).navigate_to()
    projects_page.filter_by_cost_centers([name], [cost_center_id])

    projects_page.reload()

    projects_page.should_show_selected_cost_centers([name])

    cost_center_utils.delete_cost_center(cost_center_id)
    projects_page.navigate_to()

    projects_page.should_show_no_cost_center_selected()
    projects_page.should_see_projects_listed()
