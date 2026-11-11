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
from codemie_test_harness.tests.ui.pageobject.workflows.tool_node_config_panel import (
    ToolNodeConfigPanel,
)

# Both tools' "to" argument is a required free-entry list: codemie's args_schema
# extraction (ToolConfigExtractor.get_config_schema, used by
# ToolSchemaExtractor.extract_args_schema) marks every args_schema field without a
# frozen pydantic default as required=True, and neither ForwardInput.to nor
# SendInput.to has one (codemie_tools.ms_exchange.tools).
EXCHANGE_TOOLS = ["Exchange: Forward message", "Exchange: Send message"]
EXCHANGE_TOOL_IDS = ["exchange_forward", "exchange_send"]

# Technical tool identifier behind each display name (tools_vars.py labels), needed
# to find the right entry in the workflow's persisted YAML.
TOOL_INTERNAL_NAME = {
    "Exchange: Forward message": "exchange_forward",
    "Exchange: Send message": "exchange_send",
}


def _open_tool_node_config_panel(page, edit_page, test_workflow) -> ToolNodeConfigPanel:
    """Open a fresh workflow editor, add a Tool node and return its config panel."""
    edit_page.navigate_to(test_workflow.id)

    edit_page.add_tool_node()
    page.locator('[role="application"]').get_by_text("Tool_1").wait_for(
        state="visible", timeout=5000
    )
    page.locator('[role="application"]').get_by_text("Tool_1").click()

    tool_panel = ToolNodeConfigPanel(page)
    tool_panel.should_be_visible()
    return tool_panel


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize("tool_name", EXCHANGE_TOOLS, ids=EXCHANGE_TOOL_IDS)
def test_required_list_argument_shows_persistent_asterisk_and_aria_required(
    page, test_workflow, ms_exchange_integration, tool_name
):
    """Each of exchange_forward.to and exchange_send.to is a required free-entry list
    argument: its label carries the persistent asterisk and its (empty) row
    placeholder exposes aria-required="true" as soon as the tool is bound.

    # @case workflow-editor-required-list-arguments_TC_001
    """
    edit_page = EditWorkflowPage(page)
    tool_panel = _open_tool_node_config_panel(page, edit_page, test_workflow)

    tool_panel.select_tool(
        "Microsoft Exchange",
        tool_name,
        integration_alias=ms_exchange_integration.alias,
    )

    tool_panel.should_have_to_argument_required()


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize("tool_name", EXCHANGE_TOOLS, ids=EXCHANGE_TOOL_IDS)
def test_required_list_argument_blocks_save_until_populated(
    page, test_workflow, ms_exchange_integration, workflow_utils, tool_name
):
    """Each of exchange_forward.to and exchange_send.to blocks the workflow-level Save
    while empty (inline "Field is required" error in the Tool Configuration region,
    and the workflow is not persisted) and allows it once a value is added.

    The tool node panel's own Save button only commits the node locally — it never
    reaches the API by itself — so this asserts against the editor header's Save,
    which is what actually attempts to persist the workflow.

    # @case workflow-editor-required-list-arguments_TC_002
    """
    edit_page = EditWorkflowPage(page)
    tool_panel = _open_tool_node_config_panel(page, edit_page, test_workflow)

    tool_panel.select_tool(
        "Microsoft Exchange",
        tool_name,
        integration_alias=ms_exchange_integration.alias,
    )
    # Fill every other required argument (e.g. Message Id for Forward; Subject, Body
    # and Body Type for Send) so the blocked-save assertion below isolates "To".
    tool_panel.fill_required_tool_arguments()

    before_refused_save = workflow_utils.get_workflow(test_workflow.id)

    # Leave "To" empty and attempt to save at the workflow level (the editor header's
    # own Save button, not the tool node panel's) — refused with an inline
    # required-value error in the Tool Configuration region.
    edit_page.click_save()
    tool_panel.should_have_to_argument_error()
    tool_panel.should_be_visible()

    # The workflow itself was never persisted by the refused Save.
    after_refused_save = workflow_utils.get_workflow(test_workflow.id)
    assert_that(
        after_refused_save.update_date,
        equal_to(before_refused_save.update_date),
        "workflow should not be persisted while the required 'To' argument is empty",
    )

    # Fill "To" and save again at the workflow level — this time it succeeds.
    tool_panel.fill_to_argument("qa-automation@example.com")
    edit_page.click_save()
    edit_page.wait_for_save_redirect()

    saved = workflow_utils.get_workflow(test_workflow.id)
    assert_that(saved.yaml_config, not_none(), "yaml_config missing after save")
    tools = yaml.safe_load(saved.yaml_config).get("tools") or []
    tool_entry = next(
        (t for t in tools if t.get("tool") == TOOL_INTERNAL_NAME[tool_name]), None
    )
    assert_that(
        tool_entry,
        not_none(),
        f"'{TOOL_INTERNAL_NAME[tool_name]}' tool not found in workflow YAML after save",
    )
    assert_that(
        (tool_entry.get("tool_args") or {}).get("to"),
        equal_to(["qa-automation@example.com"]),
        "'to' argument was not persisted with the value filled before the second Save",
    )
