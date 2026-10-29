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

import pytest
from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests import TEST_USER


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.ui
def test_workflows_page_basic_functionality(page):
    """Test basic workflows page functionality."""
    workflow_page = WorkflowsPage(page)
    workflow_page.navigate_to()
    workflow_page.sidebar.navigate_to_all_workflows()
    workflow_page.should_be_on_workflows_page()
    workflow_page.should_see_workflow_cards()


@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_card_interactions(page):
    """Test individual workflow card interactions."""
    workflow_page = WorkflowsPage(page)
    workflow_page.navigate_to()
    workflow_page.sidebar.navigate_to_all_workflows()
    workflow_card = workflow_page.get_workflow_card_by_index(0)

    workflow_card.should_be_visible()
    workflow_card.should_have_avatar()
    workflow_card.should_have_run_button()
    workflow_card.should_have_menu_button()


@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_search_functionality(page):
    """Test workflow search functionality."""
    workflow_page = WorkflowsPage(page)
    workflow_page.navigate_to()
    workflow_page.sidebar.navigate_to_all_workflows()
    workflow_page.search_workflows("123")
    workflow_page.should_see_workflow_cards()
    workflow_page.should_not_see_new_release_popup()


@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_card_by_name(page, workflow_with_virtual_assistant):
    """Test getting and interacting with a specific workflow card."""
    workflow = workflow_with_virtual_assistant(get_random_name())

    workflow_page = WorkflowsPage(page)
    workflow_page.navigate_to()
    workflow_page.sidebar.navigate_to_all_workflows()
    workflow_page.should_see_workflow_card(workflow.name)
    workflow_page.should_see_workflow_author(workflow.name, TEST_USER)
    workflow_page.should_see_shared_workflow(workflow.name)


@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_pagination(page, ensure_enough_workflows):
    """Test workflow pagination functionality."""
    workflow_page = WorkflowsPage(page)
    workflow_page.navigate_to()
    workflow_page.sidebar.navigate_to_all_workflows()
    workflow_page.should_see_pagination()
    workflow_page.should_be_on_page(1)
    workflow_page.change_items_per_page(24)
    workflow_page.should_see_workflow_cards(minimum_count=12)


@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_filtering(page):
    """Test workflow filtering functionality."""
    workflow_page = WorkflowsPage(page)
    workflow_page.navigate_to()
    workflow_page.sidebar.navigate_to_all_workflows()
    workflow_page.sidebar.select_with_project_filter()
    workflow_page.should_see_workflow_cards()
    workflow_page.clear_all_filters()


@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_navigation(page):
    """Test navigation between different workflow sections."""
    workflow_page = WorkflowsPage(page)
    workflow_page.navigate_to()
    workflow_page.sidebar.navigate_to_my_workflows()
    workflow_page.sidebar.navigate_to_all_workflows()
    workflow_page.sidebar.navigate_to_templates()


@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_card_fluent_interface(page):
    """Test the fluent interface of WorkflowCard component."""
    workflow_page = WorkflowsPage(page)
    workflow_page.navigate_to()
    workflow_page.sidebar.navigate_to_all_workflows()

    workflow_card = workflow_page.get_workflow_card_by_index(0)
    workflow_card.should_be_visible()
    workflow_card.should_have_avatar()
    workflow_card.should_have_run_button()
    workflow_card.should_have_menu_button()
    workflow_card.hover()
    workflow_card.should_be_visible()
