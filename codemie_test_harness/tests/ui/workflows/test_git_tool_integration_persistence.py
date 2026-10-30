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

from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.tool_node_config_panel import (
    ToolNodeConfigPanel,
)


@pytest.mark.gitlab
@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_git_tool_integration_persists_after_toggling_second_tool(
    page, test_workflow, gitlab_integration
):
    """Git toolkit integration selection persists after toggling a second tool and saving.

    Regression check for the `toggleSingleTool` bug where toggling a second tool within an
    already-configured toolkit unconditionally wiped the toolkit's saved integration settings.
    """
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)

    # Add a Tool node — its config panel opens automatically on add
    edit_page.add_tool_node()
    page.locator('[role="application"]').get_by_text("Tool_1").wait_for(
        state="visible", timeout=5000
    )
    page.locator('[role="application"]').get_by_text("Tool_1").click()

    tool_panel = ToolNodeConfigPanel(page)
    tool_panel.should_be_visible()

    # Select a first Git tool and set the toolkit-level integration
    tool_panel.select_tool(
        "Git", "Create Branch", integration_alias=gitlab_integration.alias
    )
    # Create Branch requires a design-time "Branch Name" argument; leaving it empty
    # silently blocks the workflow Save action.
    tool_panel.fill_required_tool_arguments()

    # Toggle a second tool within the same Git toolkit — this is the exact regression
    # trigger: it must not wipe the toolkit's already-saved integration settings.
    tool_panel.select_tool("Git", "Set Active Branch")
    tool_panel.fill_required_tool_arguments()

    # Save the panel, then save the workflow at the header level
    tool_panel.save()
    edit_page.click_save()
    edit_page.wait_for_save_redirect()

    # Reload the workflow edit page (fresh navigation, not page.reload()) and reopen the
    # tool node config panel to verify the integration selection survived the round trip.
    edit_page.navigate_to(test_workflow.id)
    page.locator('[role="application"]').get_by_text("Tool_1").wait_for(
        state="visible", timeout=5000
    )
    page.locator('[role="application"]').get_by_text("Tool_1").click()

    tool_panel.should_be_visible()
    tool_panel.open_available_tools_panel("Git")
    tool_panel.should_have_integration_selected(gitlab_integration.alias)
