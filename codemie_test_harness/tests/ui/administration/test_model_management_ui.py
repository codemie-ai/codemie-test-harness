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

"""UI tests for the Model management administration page.

The browser runs as the configured account, which is an administrator. A status
changed here is platform-wide: the tests that change one restore it in a fixture
teardown through the API. Those tests cannot overlap each other, so they share one worker.
They carry ``xdist_group(name="model_status")``, so they run one after another on one worker.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.administration.models_management_page import (
    ModelsManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.settings_sidebar_page import (
    SettingsSidebarPage,
)
from codemie_test_harness.tests.ui.test_data.model_management_test_data import (
    ALL_STATUSES_LABEL,
    BULK_ACTION_LABELS,
    CHANGED_STATUSES,
    LIST_FILTERS,
    MODEL_TABLE_COLUMNS,
    STATUS_LABELS,
    expected_summary,
    pick_filter_target,
)


# @case platform-model-management_TC_010
@pytest.mark.llm
@pytest.mark.ui
def test_admin_reaches_model_management_and_sees_the_admin_model_list(
    page, llm_model_status_utils
):
    # The Projects page renders the settings sidebar the tab is clicked in.
    ProjectManagementPage(page).navigate_to()
    SettingsSidebarPage(page).navigate_to_model_management()

    models_page = ModelsManagementPage(page)
    models_page.should_be_on_models_management_page()
    models_page.should_show_columns(MODEL_TABLE_COLUMNS)
    models_page.should_list_exactly_models(
        [model.base_name for model in llm_model_status_utils.list_statuses()]
    )


# @case platform-model-management_TC_011
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.llm
@pytest.mark.ui
@pytest.mark.parametrize("status", CHANGED_STATUSES, ids=lambda s: s.value)
def test_admin_changes_a_model_status_in_the_row_select_and_applies_it(
    page, llm_model_status_utils, status_test_model, status
):
    base_name = status_test_model.base_name
    models_page = ModelsManagementPage(page)
    models_page.navigate_to()

    models_page.open_status_select(base_name)
    models_page.should_offer_status_options(STATUS_LABELS.values())
    models_page.choose_status(STATUS_LABELS[status])
    models_page.apply_changes()
    models_page.should_show_settings_updated_toast()

    models_page.navigate_to()
    models_page.should_show_row_status(base_name, STATUS_LABELS[status])
    llm_model_status_utils.wait_until_status_listed(base_name, status)


# @case platform-model-management_TC_012
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.llm
@pytest.mark.ui
@pytest.mark.parametrize("status", CHANGED_STATUSES, ids=lambda s: s.value)
def test_admin_changes_statuses_with_the_bulk_actions_menu(
    page, llm_model_status_utils, status_test_model, status
):
    base_name = status_test_model.base_name
    models_page = ModelsManagementPage(page)
    models_page.navigate_to()

    models_page.select_model_row(base_name)
    models_page.open_bulk_actions()
    models_page.should_offer_bulk_actions(BULK_ACTION_LABELS.values())
    models_page.choose_bulk_action(BULK_ACTION_LABELS[status])
    models_page.apply_changes()
    models_page.should_show_settings_updated_toast()

    models_page.navigate_to()
    models_page.should_show_row_status(base_name, STATUS_LABELS[status])
    llm_model_status_utils.wait_until_status_listed(base_name, status)


# @case platform-model-management_TC_019
@pytest.mark.llm
@pytest.mark.ui
@pytest.mark.parametrize(
    "list_filter", list(LIST_FILTERS.values()), ids=list(LIST_FILTERS)
)
def test_management_list_filters_narrow_the_list_and_update_the_summary(
    page, llm_model_status_utils, list_filter
):
    models = llm_model_status_utils.list_statuses()
    target = pick_filter_target(models)
    kept = [model for model in models if list_filter.keeps(model, target)]
    models_page = ModelsManagementPage(page)
    models_page.navigate_to()

    list_filter.apply(models_page, target)

    models_page.should_list_exactly_models([model.base_name for model in kept])
    models_page.should_show_summary(expected_summary(kept, len(models)))


# @case platform-model-management_TC_019
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.llm
@pytest.mark.ui
@pytest.mark.parametrize("status", CHANGED_STATUSES, ids=lambda s: s.value)
def test_management_status_filter_narrows_the_list_and_clearing_restores_it(
    page, llm_model_status_utils, status_test_model, status
):
    llm_model_status_utils.set_status(status_test_model.base_name, status)
    llm_model_status_utils.wait_until_status_listed(status_test_model.base_name, status)
    models = llm_model_status_utils.list_statuses()
    kept = [model for model in models if model.status == status]
    models_page = ModelsManagementPage(page)
    models_page.navigate_to()

    models_page.toggle_status_filter_option(STATUS_LABELS[status])

    models_page.should_show_status_filter_value(STATUS_LABELS[status])
    models_page.should_list_exactly_models([model.base_name for model in kept])
    models_page.should_show_summary(expected_summary(kept, len(models)))

    models_page.toggle_status_filter_option(STATUS_LABELS[status])

    models_page.should_show_status_filter_value(ALL_STATUSES_LABEL)
    models_page.should_list_exactly_models([model.base_name for model in models])
    models_page.should_show_summary(expected_summary(models, len(models)))
