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

"""UI test for the datasource default tools in the workflow Virtual Assistant panel.

The panel lists Search Knowledge Base for a virtual assistant with a knowledge base
datasource and lets the author deselect it; the choice is kept after save.
"""

import pytest
import yaml
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.test_data.default_datasource_tools_test_data import (
    SEARCH_KB,
)
from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.test_data.default_datasource_tools_ui_test_data import (
    CODEBASE_TOOLS_GROUP,
    SEARCH_KB_LABEL,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.workflow
@pytest.mark.datasource
@pytest.mark.ui
def test_workflow_virtual_assistant_keeps_deselected_search_kb_after_save(
    page, workflow_with_virtual_assistant, workflow_utils, file_datasource
):
    # @case deselect-default-datasource-tools_TC_009
    workflow = workflow_with_virtual_assistant(
        get_random_name().replace("_", "-"), datasource_ids=[file_datasource.id]
    )

    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)
    panel = edit_page.open_assistant_node_config_panel()
    panel.open_tools_group(CODEBASE_TOOLS_GROUP)
    panel.tools.should_have_tool_checked(SEARCH_KB_LABEL)

    panel.tools.deselect_tool(SEARCH_KB_LABEL)
    panel.tools.should_have_tool_unchecked(SEARCH_KB_LABEL)
    panel.close_tools_dialog()
    panel.click_save()
    edit_page.click_save()
    edit_page.wait_for_save_redirect()

    saved = yaml.safe_load(workflow_utils.get_workflow(workflow.id).yaml_config)
    assert_that(saved["assistants"][0]["disabled_context_tools"], equal_to([SEARCH_KB]))

    edit_page.navigate_to(workflow.id)
    reopened_panel = edit_page.open_assistant_node_config_panel()
    reopened_panel.open_tools_group(CODEBASE_TOOLS_GROUP)
    reopened_panel.tools.should_have_tool_unchecked(SEARCH_KB_LABEL)
