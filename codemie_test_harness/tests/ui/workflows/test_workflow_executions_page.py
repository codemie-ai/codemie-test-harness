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

"""Tests for Workflow Executions page showing detailed execution history.

This module contains UI tests for the Workflow Executions page functionality including:
- Page structure and main elements visibility
- Execution history sidebar navigation
- Main content status and metadata display
- Prompt section and interaction
- Execution steps display and step detail (Input + Result)
- Configuration sidebar functionality
- Navigation and user interactions
- Info dialog (status, runtime, ID, spending metrics)
- Workflow graph control panel
"""

import pytest
import pytz
from playwright.sync_api import expect
from tzlocal import get_localzone

from codemie_test_harness.tests.ui.pageobject.workflows import WorkflowExecutionsPage
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.fixture
def open_execution(page, executions):
    """Factory fixture to create executions and navigate to the first one.

    Usage:
        executions_page = open_execution()  # Creates 1 execution (default)
        executions_page = open_execution(2)  # Creates 2 executions

    Args:
        page: Playwright page fixture
        executions: Executions factory fixture

    Returns:
        Callable: Function that creates executions and returns WorkflowExecutionsPage
    """

    def _open_execution(count=1):
        _executions = executions(count)
        executions_page = WorkflowExecutionsPage(page)
        executions_page.navigate_to(
            _executions[0].workflow_id,
            _executions[0].execution_id,
        )
        return executions_page, _executions

    return _open_execution


# ==================== PAGE STRUCTURE & VISIBILITY TESTS ====================


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_workflow_executions_page_structure(open_execution, test_workflow):
    """Test that all main page elements are visible and properly structured."""
    executions_page, _ = open_execution()

    executions_page.should_be_on_workflow_executions_page()
    executions_page.should_have_all_main_sections_visible()
    executions_page.should_have_workflow_title(test_workflow.name)


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_header_elements_visibility(open_execution):
    """Test that all header elements are visible and functional."""
    executions_page, _ = open_execution()

    executions_page.should_have_header_elements_visible()


# ==================== EXECUTION HISTORY SIDEBAR TESTS ====================


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_execution_history_sidebar_content(open_execution):
    """Test execution history sidebar content and structure."""
    executions_page, _ = open_execution()

    executions_page.should_have_sidebar_visible()
    executions_page.should_have_execution_history_items()


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_execution_history_item_interactions(open_execution):
    """Test interactions with individual execution history items."""
    executions_page, _ = open_execution()

    first_execution = executions_page.get_first_execution_history_item()
    first_execution.should_be_visible()
    first_execution.should_have_proper_status_styling()
    first_execution.should_have_all_elements_visible()


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_execution_history_status_display(open_execution):
    """Test execution status display and styling in sidebar."""
    executions_page, _ = open_execution(3)

    execution_items = executions_page.get_all_execution_history_items()
    for item in execution_items[:3]:
        item.should_be_visible()
        item.should_have_proper_status_styling()


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_execution_history_item_details(open_execution):
    """Test execution history item shows status, sequential ID, and timestamp labels."""
    executions_page, _ = open_execution()

    item = executions_page.get_first_execution_history_item()
    item.should_have_status("Succeeded")
    item.should_have_execution_id_pattern(r"^\d+$")
    item.should_have_timestamp("Started:")
    item.should_have_timestamp("Finished:")
    item.should_have_timestamp("Runtime:")
    item.should_be_clickable()


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_execution_history_item_menu_options(open_execution):
    """Test that the three-dots context menu on an execution item shows Remove option."""
    executions_page, _ = open_execution()

    item = executions_page.get_first_execution_history_item()
    item.should_have_menu_button()
    item.click_menu()
    item.should_have_menu_remove_option()


# ==================== MAIN CONTENT STATUS & METADATA TESTS ====================


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_execution_status_and_metadata_display(open_execution):
    """Test execution status and metadata display in Info dialog."""
    executions_page, executions = open_execution()

    executions_page.open_info_dialog()

    executions_page.should_have_succeeded_status()
    executions_page.should_have_triggered_by(
        CredentialsManager.get_parameter("TEST_USER_FULL_NAME")
    )

    utc_created = pytz.utc.localize(executions[0].created_date)
    utc_updated = pytz.utc.localize(executions[0].updated_date)

    executions_page.should_have_started_time(
        utc_created.astimezone(get_localzone()).strftime("%m/%d/%Y, %H:%M")
    )
    executions_page.should_have_finished_time(
        utc_updated.astimezone(get_localzone()).strftime("%m/%d/%Y, %H:%M")
    )


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_info_dialog_runtime_and_id(open_execution):
    """Test that Info dialog shows runtime duration and execution ID with copy button."""
    executions_page, executions = open_execution()

    executions_page.open_info_dialog()

    expect(executions_page.runtime_in_dialog).to_be_visible()
    expect(executions_page.execution_id_in_dialog).to_contain_text(
        executions[0].execution_id
    )
    expect(executions_page.execution_id_copy_button_in_dialog).to_be_visible()
    expect(executions_page.execution_id_copy_button_in_dialog).to_be_enabled()


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_info_dialog_spending_metrics(open_execution):
    """Test that Info dialog shows the Spending metrics section."""
    executions_page, _ = open_execution()

    executions_page.open_info_dialog()
    executions_page.should_have_info_dialog_spending_metrics()


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_execution_action_buttons(open_execution):
    """Test execution action buttons functionality."""
    executions_page, _ = open_execution()

    executions_page.should_have_action_buttons_visible()


# ==================== PROMPT SECTION TESTS ====================


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_prompt_action_buttons(open_execution):
    """Test prompt section display, content, and full-prompt dialog."""
    executions_page, executions = open_execution()

    executions_page.should_have_prompt_section_visible()
    executions_page.should_have_prompt_text(executions[0].prompt)
    executions_page.should_have_prompt_buttons_visible()
    executions_page.view_full_prompt()
    executions_page.should_have_full_prompt_dialog_visible()
    executions_page.close_full_prompt_dialog()
    executions_page.should_not_have_full_prompt_dialog_visible()


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_full_prompt_dialog_shows_prompt_content(open_execution):
    """Test that the full-prompt dialog displays the actual prompt text."""
    executions_page, executions = open_execution()

    executions_page.view_full_prompt()
    executions_page.should_have_full_prompt_dialog_visible()
    expect(executions_page.full_prompt_dialog_code).to_contain_text(
        executions[0].prompt
    )
    executions_page.close_full_prompt_dialog()


# ==================== EXECUTION STEPS TESTS ====================


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_execution_steps_display(open_execution):
    """Test execution steps section display."""
    executions_page, _ = open_execution()

    executions_page.should_have_execution_steps()


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_execution_step_detail_input_result(open_execution):
    """Test clicking a non-Starting-Prompt step shows both Input and Result sections."""
    executions_page, _ = open_execution()

    executions_page.should_have_execution_steps()
    executions_page.click_execution_step_by_index(1)
    executions_page.should_have_step_result_visible()


# ==================== WORKFLOW GRAPH TESTS ====================


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_workflow_graph_control_panel_elements(open_execution):
    """Test that the workflow graph and all control panel buttons are visible."""
    executions_page, _ = open_execution()

    executions_page.should_have_workflow_graph_visible()


# ==================== CONFIGURATION SIDEBAR TESTS ====================


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_configuration_sidebar(open_execution, test_workflow):
    """Test configuration sidebar functionality."""
    executions_page, executions = open_execution()

    executions_page.should_have_configuration_sidebar_closed()

    executions_page.click_configuration()
    executions_page.should_have_configuration_sidebar_open()

    executions_page.should_have_workflow_info_in_sidebar(
        executions[0].workflow_id, test_workflow.name
    )

    executions_page.should_have_yaml_configuration_visible()

    executions_page.click_configuration()
    executions_page.should_have_configuration_sidebar_closed()


# ==================== NAVIGATION TESTS ====================


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_edit_button_navigates_to_edit_workflow(open_execution):
    """Test that the Edit button navigates to the workflow edit page."""
    executions_page, executions = open_execution()

    executions_page.click_edit()
    executions_page.should_have_url_containing(
        f"/workflows/{executions[0].workflow_id}/edit"
    )


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_hide_sidebar_collapses_execution_history(open_execution):
    """Test that clicking Hide Sidebar collapses the execution history sidebar."""
    executions_page, _ = open_execution()

    executions_page.should_have_sidebar_visible()
    executions_page.click_hide_sidebar()
    executions_page.should_have_sidebar_collapsed()


# ==================== BARE ROUTE (NO EXECUTION ID) TESTS ====================
# Regression coverage for /workflows/:workflowId/workflow-executions
# (no trailing executionId) used to 404 because the router only defined the
# ":executionId"-suffixed route variant.


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_bare_executions_route_renders_executions_list(page, executions, test_workflow):
    """Opening the bare executions route (no executionId) must render the
    executions page instead of 404ing."""
    _executions = executions(1)
    executions_page = WorkflowExecutionsPage(page)
    executions_page.navigate_to_executions_list(_executions[0].workflow_id)

    executions_page.should_be_on_workflow_executions_page()
    executions_page.should_have_workflow_title(test_workflow.name)
    executions_page.should_have_sidebar_visible()
    executions_page.should_have_execution_history_items()


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_bare_executions_route_auto_selects_execution(page, executions):
    """Opening the bare executions route auto-selects the (only) execution and
    updates the URL to the ":executionId"-suffixed route."""
    _executions = executions(1)
    executions_page = WorkflowExecutionsPage(page)
    executions_page.navigate_to_executions_list(_executions[0].workflow_id)

    executions_page.should_have_url_containing(
        f"/workflows/{_executions[0].workflow_id}/workflow-executions/"
        f"{_executions[0].execution_id}"
    )
    executions_page.should_have_active_execution_item()

    executions_page.open_info_dialog()
    expect(executions_page.execution_id_in_dialog).to_contain_text(
        _executions[0].execution_id
    )


@pytest.mark.workflow
@pytest.mark.workflow_execution
@pytest.mark.ui
def test_execution_history_navigation(open_execution):
    """Test navigation between different executions in history."""
    executions_page, _ = open_execution(2)

    execution_items = executions_page.get_all_execution_history_items()
    if len(execution_items) > 1:
        execution_items[1].click()
        executions_page.should_have_active_execution_item()

        execution_items[0].click()
        executions_page.should_have_active_execution_item()

    executions_page.should_preserve_state_after_interactions()
