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

"""UI tests for the paged model list of the Model management administration page.

The page pages its list in the browser: the rows each page is expected to show are
computed from the admin status list (``llm_model_status_utils.list_statuses()``) in
API order. The status-change test changes a platform-wide status; it restores it in
the ``status_test_model`` teardown and carries ``xdist_group(name="model_status")``.
"""

import pytest
from hamcrest import assert_that, greater_than

from codemie_test_harness.tests.ui.pageobject.administration.models_management_page import (
    ModelsManagementPage,
)
from codemie_test_harness.tests.ui.test_data.model_management_pagination_test_data import (
    DEFAULT_PAGE_SIZE,
    NO_MATCH_SEARCH,
    PAGED_FILTERS,
    PAGED_STATUS_CHANGE,
    WALKED_PAGE_SIZES,
    base_names,
    is_selectable,
    listed_models,
    matches_search,
    other_page,
    page_count,
    page_of,
    page_slice,
    search_text_with_one_page,
)
from codemie_test_harness.tests.ui.test_data.model_management_test_data import (
    STATUS_LABELS,
)


# @case add-pagination-model-management-list_TC_001
@pytest.mark.llm
@pytest.mark.ui
@pytest.mark.parametrize("per_page", WALKED_PAGE_SIZES, ids=lambda n: f"{n}_per_page")
def test_model_list_pages_show_every_model_once_in_list_order(
    page, llm_model_status_utils, per_page
):
    names = base_names(listed_models(llm_model_status_utils.list_statuses()))
    assert_that(len(names), greater_than(per_page), "precondition: more than one page")
    models_page = ModelsManagementPage(page)
    models_page.navigate_to()

    models_page.should_show_models_page(names, 1, DEFAULT_PAGE_SIZE)
    models_page.set_page_size(per_page)

    models_page.should_page_through_models(names, per_page)


# @case add-pagination-model-management-list_TC_002
@pytest.mark.llm
@pytest.mark.ui
@pytest.mark.parametrize(
    "paged_filter", list(PAGED_FILTERS.values()), ids=list(PAGED_FILTERS)
)
def test_model_list_filter_applied_on_page_two_returns_to_page_one(
    page, llm_model_status_utils, paged_filter
):
    models = listed_models(llm_model_status_utils.list_statuses())
    target = paged_filter.pick(models)
    kept = base_names([model for model in models if paged_filter.keeps(model, target)])
    assert_that(
        len(kept), greater_than(DEFAULT_PAGE_SIZE), "precondition: filtered list pages"
    )
    models_page = ModelsManagementPage(page)
    models_page.navigate_to()
    models_page.go_to_page(2)

    paged_filter.apply(models_page, target)

    models_page.should_show_models_page(kept, 1, DEFAULT_PAGE_SIZE)

    models_page.go_to_page(2)

    models_page.should_show_models_page(kept, 2, DEFAULT_PAGE_SIZE)


# @case add-pagination-model-management-list_TC_002
@pytest.mark.llm
@pytest.mark.ui
def test_model_list_search_with_one_page_of_matches_shows_no_page_buttons(
    page, llm_model_status_utils
):
    models = listed_models(llm_model_status_utils.list_statuses())
    text = search_text_with_one_page(models)
    kept = base_names([model for model in models if matches_search(model, text)])
    models_page = ModelsManagementPage(page)
    models_page.navigate_to()
    models_page.go_to_page(2)

    models_page.search_models(text)

    models_page.should_show_models_page(kept, 1, DEFAULT_PAGE_SIZE)
    models_page.should_show_no_page_buttons()


# @case add-pagination-model-management-list_TC_002
@pytest.mark.llm
@pytest.mark.ui
def test_model_list_search_with_no_match_shows_empty_list_without_page_buttons(page):
    models_page = ModelsManagementPage(page)
    models_page.navigate_to()
    models_page.go_to_page(2)

    models_page.search_models(NO_MATCH_SEARCH)

    models_page.should_show_empty_list()
    models_page.should_show_no_page_buttons()


# @case add-pagination-model-management-list_TC_003
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.llm
@pytest.mark.ui
def test_staged_status_change_on_a_later_page_survives_a_page_change_and_applies(
    page, llm_model_status_utils, status_test_model
):
    base_name = status_test_model.base_name
    status_label = STATUS_LABELS[PAGED_STATUS_CHANGE]
    names = base_names(listed_models(llm_model_status_utils.list_statuses()))
    model_page = page_of(names, base_name, DEFAULT_PAGE_SIZE)
    assert_that(model_page, greater_than(1), "precondition: model beyond row 10")
    models_page = ModelsManagementPage(page)
    models_page.navigate_to()
    models_page.go_to_page(model_page)

    models_page.open_status_select(base_name)
    models_page.choose_status(status_label)

    models_page.should_show_row_status(base_name, status_label)
    models_page.should_show_unsaved_change_marker(base_name)
    models_page.should_have_apply_changes_enabled()

    models_page.go_to_page(other_page(model_page))
    models_page.go_to_page(model_page)

    models_page.should_show_row_status(base_name, status_label)
    models_page.should_show_unsaved_change_marker(base_name)
    models_page.should_have_apply_changes_enabled()

    models_page.apply_changes()

    models_page.should_show_settings_updated_toast()
    llm_model_status_utils.wait_until_status_listed(base_name, PAGED_STATUS_CHANGE)

    names_after = base_names(listed_models(llm_model_status_utils.list_statuses()))
    models_page.navigate_to()
    models_page.go_to_page(page_of(names_after, base_name, DEFAULT_PAGE_SIZE))

    models_page.should_show_row_status(base_name, status_label)
    models_page.should_not_show_unsaved_change_marker(base_name)


# @case add-pagination-model-management-list_TC_006
@pytest.mark.llm
@pytest.mark.ui
def test_select_all_selects_only_the_current_page_and_a_page_change_clears_it(
    page, llm_model_status_utils
):
    models = listed_models(llm_model_status_utils.list_statuses())
    last_page = page_count(len(models), DEFAULT_PAGE_SIZE)
    assert_that(last_page, greater_than(1), "precondition: more than one page")
    selectable = [
        model
        for model in page_slice(models, last_page, DEFAULT_PAGE_SIZE)
        if is_selectable(model)
    ]
    models_page = ModelsManagementPage(page)
    models_page.navigate_to()
    models_page.go_to_page(last_page)

    models_page.select_all_on_page()

    models_page.should_show_selected_count(len(selectable))

    models_page.go_to_page(last_page - 1)

    models_page.should_show_no_selection()
