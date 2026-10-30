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

"""UI tests for the workflow Categories field and sidebar filter."""

import pytest

from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)
from codemie_test_harness.tests.ui.test_data.workflows_test_data import (
    CATEGORIES_WORKFLOW_YAML,
    MAX_UI_CATEGORIES,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name, wait_for_entity


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_create_workflow_with_categories_saved_and_prefilled_on_edit(
    page, workflow_utils, workflow_categories, cleanup_generated_workflow
):
    workflow_name = get_random_name()
    selected_names = [category.name for category in workflow_categories[:2]]
    cleanup_generated_workflow(workflow_name)

    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()
    create_page = workflows_page.click_create_workflow()
    config_panel = create_page.open_workflow_config_panel()
    config_panel.switch_to_basic_tab()
    config_panel.should_have_categories_below_icon_url()

    create_page.create_workflow(
        name=workflow_name,
        yaml_config=CATEGORIES_WORKFLOW_YAML,
        categories=selected_names,
    )
    workflows_page.should_be_on_workflows_page()

    created = wait_for_entity(
        lambda: workflow_utils.client.workflows.list(per_page=200, filter_by_user=True),
        entity_name=workflow_name,
    )
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(created.id)
    edit_config_panel = edit_page.open_workflow_config_panel()
    edit_config_panel.switch_to_basic_tab()

    edit_config_panel.should_have_categories_selected(selected_names)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_edit_workflow_blocks_fourth_category(page, test_workflow, workflow_categories):
    names = [category.name for category in workflow_categories]
    allowed_names = names[:MAX_UI_CATEGORIES]
    fourth_name = names[MAX_UI_CATEGORIES]

    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)
    config_panel = edit_page.open_workflow_config_panel()
    config_panel.switch_to_basic_tab()
    config_panel.select_categories(allowed_names)
    config_panel.select_categories([fourth_name])

    config_panel.should_see_max_categories_error()
    config_panel.should_have_categories_selected(allowed_names)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize("scope", ["my", "all"])
@pytest.mark.prod_regression
def test_sidebar_category_filter_narrows_and_restores_workflow_list(
    page, categorized_workflows, scope
):
    data, category = categorized_workflows

    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()
    if scope == "my":
        workflows_page.sidebar.navigate_to_my_workflows()
    else:
        workflows_page.sidebar.navigate_to_all_workflows()
    workflows_page.sidebar.should_have_category_filter_visible()
    workflows_page.search_workflows(data.prefix)
    with_category_card = workflows_page.get_workflow_card_by_name(
        data.with_category_name
    )
    without_category_card = workflows_page.get_workflow_card_by_name(
        data.without_category_name
    )
    with_category_card.should_be_visible()
    without_category_card.should_be_visible()

    workflows_page.sidebar.select_category_filter(category.name)

    without_category_card.should_not_be_visible()
    with_category_card.should_be_visible()

    workflows_page.sidebar.clear_all_filters()

    with_category_card.should_be_visible()
    without_category_card.should_be_visible()
