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

"""Tests for Workflow Details page.

This module contains UI tests for the Workflow Details page functionality including:
- Page elements visibility
- Action buttons (Edit, Run workflow, Run Chat)
- Navigation (back button)
- Menu navigation
- Configuration sidebar (workflow info and Configure button)
- Configuration sidebar copy button for workflow ID
"""

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.ui.pageobject.workflows import (
    WorkflowDetailsPage,
    WorkflowsPage,
)


@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_details_page_elements_visibility(page, test_workflow):
    """Test that all main elements are visible on Workflow Details page."""
    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(test_workflow.id)

    workflow_details_page.should_be_on_workflow_details_page()
    workflow_details_page.should_have_header_elements_visible()
    workflow_details_page.should_have_workflow_name(test_workflow.name)
    workflow_details_page.should_have_action_buttons_visible()
    workflow_details_page.should_have_edit_button_enabled()
    workflow_details_page.should_have_run_workflow_button_enabled()
    workflow_details_page.should_have_run_chat_button_enabled()
    workflow_details_page.should_have_no_executions_message()
    workflow_details_page.should_have_menu_visible()


@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_details_action_buttons(page, test_workflow):
    """Test workflow action buttons functionality."""
    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(test_workflow.id)

    workflow_details_page.click_edit()
    workflow_details_page.should_have_url_containing(
        f"/workflows/{test_workflow.id}/edit"
    )

    workflow_details_page.navigate_to(test_workflow.id)
    workflow_details_page.click_run_workflow()
    workflow_details_page.should_have_new_execution_dialog_visible()
    workflow_details_page.close_new_execution_dialog()

    workflow_details_page.click_run_chat()
    workflow_details_page.should_have_url_containing("/chats")


@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_details_navigation_buttons(page, test_workflow):
    """Test back button navigation from Workflow Details page."""
    # Navigate to workflows list first so Back has it in history
    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()

    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(test_workflow.id)
    workflow_details_page.should_be_on_workflow_details_page()
    workflow_details_page.should_have_url_containing(f"/workflows/{test_workflow.id}")

    workflow_details_page.click_back()
    workflow_details_page.should_have_url_containing("/workflows")


@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_details_menu_navigation(page, test_workflow):
    """Test menu navigation from Workflow Details page."""
    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(test_workflow.id)

    workflow_details_page.should_have_menu_visible()
    workflow_details_page.menu.should_be_visible()
    workflow_details_page.menu.should_have_complete_navigation_structure()

    workflow_details_page.menu.navigate_to_chats()
    workflow_details_page.should_have_url_containing("/chats")

    workflow_details_page.navigate_to(test_workflow.id)
    workflow_details_page.menu.navigate_to_ai_katas()
    workflow_details_page.should_have_url_containing("/katas")

    workflow_details_page.navigate_to(test_workflow.id)
    workflow_details_page.menu.navigate_to_skills()
    workflow_details_page.should_have_url_containing("/skills")

    workflow_details_page.navigate_to(test_workflow.id)
    workflow_details_page.menu.navigate_to_integrations()
    workflow_details_page.should_have_url_containing("/integrations")

    workflow_details_page.navigate_to(test_workflow.id)
    workflow_details_page.menu.navigate_to_data_sources()
    workflow_details_page.should_have_url_containing("/data-sources")

    workflow_details_page.navigate_to(test_workflow.id)
    workflow_details_page.menu.navigate_to_analytics()
    workflow_details_page.should_have_url_containing("/analytics")

    workflow_details_page.navigate_to(test_workflow.id)
    workflow_details_page.menu.navigate_to_applications()
    workflow_details_page.should_have_url_containing("/applications")


# ==================== CONFIGURATION SIDEBAR TESTS ====================


@pytest.mark.workflow
@pytest.mark.ui
def test_configuration_sidebar_elements(page, test_workflow):
    """Test that all configuration sidebar elements are visible and correct."""
    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(test_workflow.id)

    workflow_details_page.should_have_configuration_sidebar_closed()

    workflow_details_page.click_configuration()
    workflow_details_page.should_have_configuration_sidebar_open()

    workflow_details_page.should_have_workflow_info_in_sidebar(
        test_workflow.id, test_workflow.name
    )
    workflow_details_page.should_have_configure_button_visible()

    workflow_details_page.click_configuration()
    workflow_details_page.should_have_configuration_sidebar_closed()


@pytest.mark.workflow
@pytest.mark.ui
def test_configuration_copy_workflow_id(page, test_workflow):
    """Test copy functionality for workflow ID in configuration sidebar."""
    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(test_workflow.id)

    workflow_details_page.click_configuration()

    page.context.grant_permissions(["clipboard-read", "clipboard-write"])

    def read_clipboard():
        return page.evaluate("async () => await navigator.clipboard.readText()")

    workflow_details_page.click_copy_workflow_id()
    page.wait_for_timeout(500)
    clipboard_content = read_clipboard()
    assert_that(
        clipboard_content,
        equal_to(test_workflow.id),
        "Workflow ID should be copied to clipboard",
    )
