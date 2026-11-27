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

"""API tests for the budget category filter of the project list (GET /v1/projects).

The filter only selects which projects are listed: every listed project keeps all of its own
budget rows, with the same values as in the unfiltered list. The projects and their budget groups
are created through the API with zero spend (no LLM traffic) and removed by the fixture.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_inanyorder,
    empty,
    equal_to,
    greater_than,
    has_item,
    is_not,
)

from codemie_test_harness.tests.test_data.project_budget_category_filter_test_data import (
    CATEGORY_FILTERS,
    EXPECTED_LISTED_BY_FILTER,
    LISTED_PROJECT_PAIRS,
    PROJECT_BUDGETS,
)
from codemie_test_harness.tests.utils.project_budget_category_filter_utils import (
    ProjectBudgetCategoryFilterUtils,
)
from codemie_test_harness.tests.utils.project_budget_groups import ProjectBudgetGroups

PROJECT_WITHOUT_BUDGETS = "none"


@pytest.fixture(scope="module")
def filter_utils(
    client, project_utils, admin_project_budget_utils, lite_llm_budget_utils
):
    """Projects with every budget layout of the filter, created once for the module's tests."""
    groups = ProjectBudgetGroups(admin_project_budget_utils, lite_llm_budget_utils)
    utils = ProjectBudgetCategoryFilterUtils(
        client, project_utils, groups, lite_llm_budget_utils
    )
    try:
        utils.names = {
            label: utils.create_project(label, categories)
            for label, categories in PROJECT_BUDGETS.items()
        }
        utils.names[PROJECT_WITHOUT_BUDGETS] = utils.create_project(
            PROJECT_WITHOUT_BUDGETS
        )
        yield utils
    finally:
        groups.cleanup()
        utils.cleanup()


def _listed_labels(filter_utils, listing):
    by_name = {name: label for label, name in filter_utils.names.items()}
    return {by_name[name] for name in listing if name in by_name}


# @case projects-budget-category-filter_TC_001
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.parametrize("budget_category", CATEGORY_FILTERS)
def test_category_filter_lists_only_matching_projects(filter_utils, budget_category):
    listing = filter_utils.list_projects(budget_category)

    assert_that(
        _listed_labels(filter_utils, listing),
        equal_to(EXPECTED_LISTED_BY_FILTER[budget_category]),
        f"projects listed under budget_category={budget_category}",
    )


# @case projects-budget-category-filter_TC_001
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.parametrize("budget_category, label", LISTED_PROJECT_PAIRS)
def test_category_filter_keeps_each_projects_rows_and_hard_limits(
    filter_utils, budget_category, label
):
    name = filter_utils.names[label]
    rows = filter_utils.rows_by_category

    unfiltered = rows(filter_utils.list_projects()[name])
    filtered = rows(filter_utils.list_projects(budget_category)[name])

    assert_that(
        filtered,
        equal_to(unfiltered),
        f"budget rows of {label} under budget_category={budget_category}",
    )
    assert_that(
        list(filtered),
        contains_inanyorder(*PROJECT_BUDGETS[label]),
        f"categories of {label} under budget_category={budget_category}",
    )


# @case projects-budget-category-filter_TC_002
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.parametrize("budget_category, label", LISTED_PROJECT_PAIRS)
def test_category_filter_adds_no_row_for_an_unassigned_category(
    filter_utils, budget_category, label
):
    name = filter_utils.names[label]

    filtered = filter_utils.list_projects(budget_category)[name]

    assert_that(
        set(filter_utils.rows_by_category(filtered)),
        equal_to(set(PROJECT_BUDGETS[label])),
        f"only the assigned categories of {label} under {budget_category}",
    )


# @case projects-budget-category-filter_TC_002
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
def test_project_without_budgets_is_listed_unfiltered_with_empty_budgets(
    filter_utils,
):
    name = filter_utils.names[PROJECT_WITHOUT_BUDGETS]

    unfiltered = filter_utils.list_projects()

    assert_that(list(unfiltered), has_item(name), "listed without a filter")
    assert_that(unfiltered[name]["budgets"], empty(), "no budget rows")


# @case projects-budget-category-filter_TC_002
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.parametrize("budget_category", CATEGORY_FILTERS)
def test_project_without_budgets_is_excluded_by_every_category_filter(
    filter_utils, budget_category
):
    name = filter_utils.names[PROJECT_WITHOUT_BUDGETS]

    assert_that(
        list(filter_utils.list_projects(budget_category)),
        is_not(has_item(name)),
        f"excluded under budget_category={budget_category}",
    )


# @case projects-budget-category-filter_TC_003
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.parametrize("budget_category", CATEGORY_FILTERS)
def test_category_filter_keeps_the_sum_of_all_rows_of_a_project(
    filter_utils, budget_category
):
    name = filter_utils.names["all"]
    rows = filter_utils.rows_by_category

    reference = rows(filter_utils.list_projects()[name])
    filtered = rows(filter_utils.list_projects(budget_category)[name])

    limit_sum = sum(limit for limit, _ in filtered.values())
    spend_sum = sum(spend for _, spend in filtered.values())
    assert_that(
        limit_sum,
        equal_to(sum(limit for limit, _ in reference.values())),
        "sum of hard limits equals the unfiltered sum",
    )
    assert_that(
        spend_sum,
        equal_to(sum(spend for _, spend in reference.values())),
        "sum of spend equals the unfiltered sum",
    )
    assert_that(
        limit_sum,
        greater_than(filtered[budget_category][0]),
        "the sum is larger than the filtered category's own limit",
    )
