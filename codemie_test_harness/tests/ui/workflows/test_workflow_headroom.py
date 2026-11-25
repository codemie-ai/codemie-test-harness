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

"""Workflow editor 'Context compression (Headroom)' settings (needs features:headroom on)."""

import pytest
from codemie_sdk import HeadroomStrategy
from hamcrest import assert_that, equal_to, has_entry, is_, none

from codemie_test_harness.tests.test_data.headroom_test_data import (
    WORKFLOW_HEADROOM_AGGRESSIVE,
)
from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.test_data.headroom_test_data import (
    STRATEGY_LOSSLESS,
    assistant_node_headroom_block,
    workflow_headroom_block,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


# @case headroom-per-assistant-workflow-configuration_TC_006
@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_editor_saves_headroom_at_workflow_scope(
    page, workflow_with_virtual_assistant, workflow_utils
):
    target = workflow_with_virtual_assistant(get_random_name())
    other = workflow_with_virtual_assistant(get_random_name())

    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(target.id)
    config_panel = edit_page.open_workflow_config_panel()
    headroom = config_panel.open_headroom_settings()
    headroom.should_have_enabled(False)

    headroom.set_enabled(True)
    headroom.select_strategy(STRATEGY_LOSSLESS)
    config_panel.save_configuration()
    edit_page.save_workflow()

    stored = workflow_utils.get_workflow(target.id).headroom_config
    assert_that(
        stored.enabled,
        is_(True),
        "Workflow saved from the editor does not store Headroom enabled",
    )
    assert_that(
        stored.strategy,
        equal_to(HeadroomStrategy.LOSSLESS),
        "Workflow saved from the editor does not store the Lossless strategy",
    )
    assert_that(
        workflow_utils.get_workflow(other.id).headroom_config,
        none(),
        "Saving one workflow's Headroom settings changed another workflow",
    )


# @case headroom-per-assistant-workflow-configuration_TC_007
@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_assistant_node_saves_its_own_headroom_override(
    page, workflow_with_virtual_assistant, workflow_utils
):
    node_id = get_random_name()
    workflow = workflow_with_virtual_assistant(
        node_id, headroom=WORKFLOW_HEADROOM_AGGRESSIVE
    )

    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)
    node_panel = edit_page.open_assistant_node_config_panel()
    node_panel.should_have_headroom_accordion_collapsed()

    node_panel.open_headroom_settings().set_enabled(False)
    node_panel.save_node()
    edit_page.save_workflow()

    yaml_config = workflow_utils.get_workflow(workflow.id).yaml_config
    assert_that(
        assistant_node_headroom_block(yaml_config, node_id),
        has_entry("enabled", False),
        "The assistant node does not store its own Headroom override (enabled false)",
    )
    assert_that(
        workflow_headroom_block(yaml_config),
        has_entry("enabled", True),
        "The workflow-level Headroom block lost enabled true after the node override",
    )
