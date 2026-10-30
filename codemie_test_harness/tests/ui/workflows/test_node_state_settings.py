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

"""State Settings of the workflow node configuration panels.

The Task and Output Schema fields are shown only for node types whose backend
behaviour uses them:

- Tool and Sub-workflow: neither field.
- Custom: never Output Schema; Task only for the state-processor type, and not
  before a type is chosen.
- Assistant: both fields.
- Transform: neither, and also none of the four State Settings switches.

Values stored in a field the panel hides must survive editing another setting.
"""

import pytest
import yaml
from hamcrest import assert_that, equal_to, not_none

from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.test_data.workflow_node_state_settings_test_data import (
    CUSTOM_NODE_TYPE_LABELS,
    CUSTOM_NODE_VISIBILITY_CASES,
    HIDDEN_VALUE_CASES,
    NODE_STATE_ID,
    NON_CUSTOM_NODE_VISIBILITY_CASES,
    RENAMED_NODE_STATE_ID,
    SEEDED_OUTPUT_SCHEMA,
    SEEDED_TASK,
    CustomNodeType,
    NodeKind,
)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize(
    "case",
    NON_CUSTOM_NODE_VISIBILITY_CASES,
    ids=[case.case_id for case in NON_CUSTOM_NODE_VISIBILITY_CASES],
)
def test_non_custom_node_panel_shows_task_and_output_schema_only_where_used(
    page, create_node_workflow, case
):
    # @case workflow-editor-task-output-schema_TC_001
    """Tool and Sub-workflow hide Task and Output Schema, Assistant shows both,
    Transform hides both and the four State Settings switches."""
    workflow = create_node_workflow(case.node_kind)
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    panel = edit_page.open_node_config_panel(NODE_STATE_ID)

    panel.should_be_visible()
    panel.should_show_node_section(case.section_title)
    panel.should_have_task_visibility(case.task_visible)
    panel.should_have_output_schema_visibility(case.output_schema_visible)
    panel.should_have_other_state_settings_visibility(case.other_settings_visible)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize(
    "case",
    CUSTOM_NODE_VISIBILITY_CASES,
    ids=[case.case_id for case in CUSTOM_NODE_VISIBILITY_CASES],
)
def test_custom_node_panel_hides_output_schema_and_shows_task_only_for_state_processor(
    page, create_node_workflow, case
):
    # @case workflow-editor-task-output-schema_TC_001
    """Custom panel: Output Schema is hidden for every type, Task only for state-processor."""
    workflow = create_node_workflow(NodeKind.CUSTOM, case.custom_node_type)
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    panel = edit_page.open_node_config_panel(NODE_STATE_ID)

    panel.should_be_visible()
    panel.should_have_selected_custom_node_type(case.type_label)
    panel.should_have_task_visibility(case.task_visible)
    panel.should_have_output_schema_visibility(False)
    panel.should_have_other_state_settings_visibility(True)


@pytest.mark.workflow
@pytest.mark.ui
def test_custom_node_task_field_follows_type_selection_before_save(page, test_workflow):
    # @case workflow-editor-task-output-schema_TC_001
    """A new Custom node hides Task until a type that uses it is chosen; Task then
    appears and disappears as the type changes, with nothing saved."""
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)

    edit_page.add_custom_node()
    panel = edit_page.get_node_config_panel()

    panel.should_be_visible()
    panel.should_have_selected_custom_node_type(None)
    panel.should_have_task_visibility(False)
    panel.should_have_output_schema_visibility(False)

    panel.select_custom_node_type(
        CUSTOM_NODE_TYPE_LABELS[CustomNodeType.STATE_PROCESSOR]
    )
    panel.should_have_selected_custom_node_type(
        CUSTOM_NODE_TYPE_LABELS[CustomNodeType.STATE_PROCESSOR]
    )
    panel.should_have_task_visibility(True)
    panel.should_have_output_schema_visibility(False)

    panel.select_custom_node_type(
        CUSTOM_NODE_TYPE_LABELS[CustomNodeType.GENERATE_DOCUMENTS_TREE]
    )
    panel.should_have_selected_custom_node_type(
        CUSTOM_NODE_TYPE_LABELS[CustomNodeType.GENERATE_DOCUMENTS_TREE]
    )
    panel.should_have_task_visibility(False)
    panel.should_have_output_schema_visibility(False)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize(
    "case", HIDDEN_VALUE_CASES, ids=[case.case_id for case in HIDDEN_VALUE_CASES]
)
def test_hidden_task_and_output_schema_survive_editing_another_setting(
    page, create_node_workflow, workflow_utils, case
):
    # @case workflow-editor-task-output-schema_TC_006
    """Editing only the State ID and saving keeps the stored Task and Output Schema,
    including the ones the panel does not display."""
    workflow = create_node_workflow(
        case.node_kind, case.custom_node_type, with_hidden_values=True
    )
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    panel = edit_page.open_node_config_panel(NODE_STATE_ID)
    panel.should_be_visible()
    panel.should_have_task_visibility(case.task_visible)
    panel.should_have_output_schema_visibility(False)

    panel.fill_state_id(RENAMED_NODE_STATE_ID)
    panel.click_save()
    edit_page.click_save()
    edit_page.wait_for_save_redirect()

    saved = workflow_utils.get_workflow(workflow.id)
    assert_that(saved.yaml_config, not_none(), "yaml_config missing after save")
    states = yaml.safe_load(saved.yaml_config).get("states", [])
    state = next((s for s in states if s.get("id") == RENAMED_NODE_STATE_ID), None)
    assert_that(
        state,
        not_none(),
        f"State '{RENAMED_NODE_STATE_ID}' not found in the workflow YAML after save",
    )
    assert_that(
        state.get("task"),
        equal_to(SEEDED_TASK),
        "stored task must be unchanged after saving an unrelated edit",
    )
    assert_that(
        state.get("output_schema"),
        equal_to(SEEDED_OUTPUT_SCHEMA),
        "stored output_schema must be unchanged after saving an unrelated edit",
    )


@pytest.mark.workflow
@pytest.mark.ui
def test_custom_node_save_blocked_when_required_config_is_missing(
    page, create_node_workflow
):
    # @case workflow-editor-task-output-schema_TC_011
    """Saving a state-processor Custom node without its required Output Template config
    is rejected: the panel stays open and flags the missing field."""
    workflow = create_node_workflow(
        NodeKind.CUSTOM, CustomNodeType.STATE_PROCESSOR, with_required_config=False
    )
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    panel = edit_page.open_node_config_panel(NODE_STATE_ID)
    panel.should_be_visible()
    # The required-field rule is only known once the type's config schema has loaded.
    panel.should_show_required_config_field()

    panel.click_save()

    panel.should_show_required_field_error()
    panel.should_remain_open()
