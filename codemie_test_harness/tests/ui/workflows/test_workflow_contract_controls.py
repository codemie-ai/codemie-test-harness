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

"""Contract controls of the workflow editor.

- Condition, switch and iterator nodes have no contract controls (registry in
  frontend CommonStateFields.tsx excludes them).
- Workflow settings, Advanced tab, "Contracts": the workflow-level "Save validation"
  select and the "Require input contracts" switch (AdvancedConfigTab.tsx); the selector
  writes the top-level YAML key ``save_validation``.

Node panels of the other node types are covered in ``test_node_state_settings.py``.
"""

import pytest
import yaml
from hamcrest import assert_that, equal_to, is_not, has_key

from codemie_test_harness.tests.ui.pageobject.workflows.create_workflow_page import (
    CreateWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.test_data.workflow_contracts_test_data import (
    LEGACY_VALIDATION_KEY,
    NO_CONTRACT_NODE_CASES,
    SAVE_VALIDATION_KEY,
    WARN_MODE,
)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize(
    "case",
    NO_CONTRACT_NODE_CASES,
    ids=[case.case_id for case in NO_CONTRACT_NODE_CASES],
)
def test_flow_control_node_panel_has_no_contract_controls(page, case):
    # @case save-time-contract-editor-controls_TC_002
    """Condition, switch and iterator panels show no Contracts accordion, Input contract,
    Output contract or node Save validation."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    create_page.add_node_from_sidebar(case.sidebar_button)
    panel = create_page.get_node_config_panel()

    # A text only this node type's panel shows: the panel rendered before the absence checks.
    panel.should_show_panel_text(case.panel_anchor_text)
    panel.should_have_no_contract_controls()


@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_settings_expose_save_validation_and_require_input_contracts(
    page, test_workflow, workflow_utils
):
    # @case save-time-contract-editor-controls_TC_003
    """The Advanced tab's Contracts section holds the workflow-level Save validation select
    and the Require input contracts switch; choosing a mode stores it as ``save_validation``."""
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)

    config_panel = edit_page.open_workflow_config_panel()
    config_panel.open_contracts_settings()
    config_panel.should_have_contracts_controls()

    config_panel.select_workflow_save_validation(WARN_MODE)
    config_panel.save_configuration()
    edit_page.save_workflow()

    stored = yaml.safe_load(workflow_utils.get_workflow(test_workflow.id).yaml_config)
    assert_that(
        stored.get(SAVE_VALIDATION_KEY),
        equal_to(WARN_MODE),
        f"stored YAML must carry the workflow-level '{SAVE_VALIDATION_KEY}' key",
    )
    assert_that(
        stored,
        is_not(has_key(LEGACY_VALIDATION_KEY)),
        f"the selector must not write a '{LEGACY_VALIDATION_KEY}' key",
    )
