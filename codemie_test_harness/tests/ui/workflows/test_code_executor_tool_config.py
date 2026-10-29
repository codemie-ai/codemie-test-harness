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

MULTILINE_CODE = "line1 = 'hello'\nline2 = 'world'\nprint(line1, line2)"


@pytest.mark.workflow
@pytest.mark.ui
def test_code_executor_code_field_is_textarea_and_persists_multiline_code(
    page, test_workflow
):
    """Code Executor 'Code' field: verify textarea rendering and multiline save/reload."""
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)

    # Add a Tool node — config panel opens automatically on add
    edit_page.add_tool_node()
    page.locator('[role="application"]').get_by_text("Tool_1").wait_for(
        state="visible", timeout=5000
    )
    page.locator('[role="application"]').get_by_text("Tool_1").click()

    tool_panel = ToolNodeConfigPanel(page)
    tool_panel.should_be_visible()

    # Select Code Executor and assert the Code field is a <textarea> (not <input>)
    tool_panel.select_tool("FileSystem", "Code Executor")
    tool_panel.code_field_should_be_textarea()

    # Fill multiline code and save
    tool_panel.fill_code(MULTILINE_CODE)
    tool_panel.save()

    # Save the workflow at the header level
    edit_page.click_save()

    # Reload the workflow edit page and reopen the tool node config panel
    edit_page.navigate_to(test_workflow.id)
    page.locator('[role="application"]').get_by_text("Tool_1").wait_for(
        state="visible", timeout=5000
    )
    page.locator('[role="application"]').get_by_text("Tool_1").click()

    tool_panel.should_be_visible()
    tool_panel.should_have_code_value(MULTILINE_CODE)
