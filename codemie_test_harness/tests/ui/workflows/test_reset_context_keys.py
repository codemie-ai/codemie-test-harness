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

"""Regression tests for the Reset Context Keys field.

SC-01: Comma-separated keys entered via the UI are saved and reflected in workflow YAML.
Covers AC-1, AC-2, AC-3, AC-5.

The bug was in CommonStateFields.tsx where the onChange handler eagerly parsed
the raw typed string on every keystroke, silently discarding any trailing comma.
The fix defers array parsing to onBlur and adds an isFocused ref guard.
"""

import yaml
import pytest
from hamcrest import assert_that, equal_to, not_none

from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)

# The raw string typed into the field and the expected parsed array after blur.
RESET_KEYS_RAW = "user_data,analysis_result"
RESET_KEYS_EXPECTED = ["user_data", "analysis_result"]

# The state ID created by the test_workflow fixture (see ui/workflows/conftest.py).
_ASSISTANT_STATE_ID = "branch_creator"


@pytest.mark.sanity
@pytest.mark.workflow
@pytest.mark.ui
def test_reset_context_keys_comma_entry_saved_to_yaml(
    page, test_workflow, workflow_utils
):
    """Verify that comma-separated Reset Context Keys entered via the UI are saved to YAML.

    Steps:
    1. Navigate to the Edit Workflow page for test_workflow.
    2. Click the assistant node to open AssistantNodeConfigPanel.
    3. Expand the Transition Settings accordion.
    4. Type 'user_data,analysis_result' into the Reset Context Keys input.
    5. Assert the raw value (with comma) is visible while still focused (AC-1, AC-5).
    6. Press Tab to blur and trigger onBlur array parse.
    7. Click Save in the node config panel; click Save on the page.
    8. Fetch the workflow YAML via API.
    9. Assert reset_keys_in_context_store equals ["user_data", "analysis_result"] (AC-2, AC-3).
    """
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)

    # Step 2: Open the assistant node config panel.
    panel = edit_page.open_assistant_node_config_panel()

    # Step 3: Expand Transition Settings accordion.
    panel.expand_transition_settings()

    # Step 4: Type the comma-separated value into the input.
    panel.fill_reset_context_keys(RESET_KEYS_RAW)

    # Step 5 (AC-1 / AC-5): Comma must be preserved in the input while it is focused.
    panel.should_have_reset_context_keys_value(RESET_KEYS_RAW)

    # Step 6: Blur triggers onBlur parse — array is committed to form state.
    panel.blur_reset_context_keys()

    # Step 7: Save the node config panel, then save the whole workflow.
    panel.click_save()
    edit_page.click_save()

    # Wait for the save to complete and the page to navigate away.
    edit_page.wait_for_save_redirect()

    # Step 8: Fetch the updated workflow via API.
    updated_workflow = workflow_utils.get_workflow(test_workflow.id)
    assert_that(
        updated_workflow.yaml_config, not_none(), "yaml_config missing after save"
    )

    # Step 9: Parse YAML and assert reset_keys_in_context_store.
    parsed = yaml.safe_load(updated_workflow.yaml_config)
    states = parsed.get("states", [])
    target_state = next((s for s in states if s.get("id") == _ASSISTANT_STATE_ID), None)
    assert_that(
        target_state,
        not_none(),
        f"State '{_ASSISTANT_STATE_ID}' not found in workflow YAML after save",
    )
    state_next = target_state.get("next", {})

    # AC-2, AC-3: reset_keys_in_context_store must equal the parsed array — no trailing-comma artefact.
    assert_that(
        state_next.get("reset_keys_in_context_store"),
        equal_to(RESET_KEYS_EXPECTED),
        "reset_keys_in_context_store must be saved as a trimmed string array",
    )
