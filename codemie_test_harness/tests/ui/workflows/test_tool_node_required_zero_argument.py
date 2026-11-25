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
import yaml
from hamcrest import assert_that, equal_to, not_none

from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.test_data.workflows_test_data import (
    EXCHANGE_READ_COUNT,
    EXCHANGE_READ_FOLDER,
    EXCHANGE_READ_START,
    EXCHANGE_READ_TOOL_ID,
    EXCHANGE_READ_TOOL_NAME,
    EXCHANGE_TOOLKIT_NAME,
    WORKFLOW_UPDATED_TOAST,
)


# @case workflow-editor-rejects-0-false_TC_001
@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_tool_node_required_number_argument_accepts_zero(
    page, test_workflow, ms_exchange_integration, workflow_utils
):
    """A required number tool argument left empty blocks the workflow Save, while the
    value 0 counts as present: Save succeeds and 0 is persisted as an integer.

    The editor header's Save is used (not the tool node panel's), since it is the one
    that validates the node and persists the workflow.
    """
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)
    tool_panel = edit_page.add_tool_node_and_open_config_panel()

    tool_panel.select_tool(
        EXCHANGE_TOOLKIT_NAME,
        EXCHANGE_READ_TOOL_NAME,
        integration_alias=ms_exchange_integration.alias,
    )
    tool_panel.should_have_read_messages_arguments_required()

    # Start stays empty: the refused Save must point at Start only.
    tool_panel.fill_folder_argument(EXCHANGE_READ_FOLDER)
    tool_panel.fill_count_argument(EXCHANGE_READ_COUNT)

    edit_page.click_save()
    tool_panel.should_have_start_argument_error()

    tool_panel.fill_start_argument(EXCHANGE_READ_START)
    tool_panel.should_not_have_required_value_error()

    edit_page.click_save()
    edit_page.toast.should_show(WORKFLOW_UPDATED_TOAST)
    edit_page.wait_for_save_redirect()

    saved = workflow_utils.get_workflow(test_workflow.id)
    assert_that(saved.yaml_config, not_none(), "yaml_config missing after save")
    tools = yaml.safe_load(saved.yaml_config).get("tools") or []
    tool_entry = next(
        (t for t in tools if t.get("tool") == EXCHANGE_READ_TOOL_ID), None
    )
    assert_that(
        tool_entry,
        not_none(),
        f"'{EXCHANGE_READ_TOOL_ID}' tool not found in workflow YAML after save",
    )
    tool_args = tool_entry.get("tool_args") or {}
    # type() check, not isinstance(): bool is an int subclass and False == 0.
    assert_that(
        type(tool_args.get("start")),
        equal_to(int),
        f"'start' should be persisted as an integer, got {tool_args.get('start')!r}",
    )
    assert_that(
        tool_args.get("start"),
        equal_to(EXCHANGE_READ_START),
        "'start' should be persisted as the 0 entered before the second Save",
    )
    assert_that(
        tool_args.get("folder"),
        equal_to(EXCHANGE_READ_FOLDER),
        "'folder' was not persisted with the value filled before Save",
    )
    assert_that(
        tool_args.get("count"),
        equal_to(EXCHANGE_READ_COUNT),
        "'count' was not persisted with the value filled before Save",
    )
