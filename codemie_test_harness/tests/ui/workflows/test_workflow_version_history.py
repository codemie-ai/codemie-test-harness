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

"""UI E2E tests for the Workflow Version History popup.

Covers:
    TC_006 — Version History button accessible from the visual editor YAML panel.
"""

import pytest
from playwright.sync_api import expect

from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflow_version_history_popup import (
    WorkflowVersionHistoryPopup,
)


# ---------------------------------------------------------------------------
# TC_006
# ---------------------------------------------------------------------------


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.prod_regression
def test_version_history_button_accessible_from_visual_editor(page, test_workflow):
    """Version History button is present and opens the popup from the visual editor YAML panel.


    Preconditions (from cases.json):
        - user authenticated with edit access
        - workflow has at least one version
        - workflow editing page open in visual (YAML) editor view

    Evidence: src/pages/workflows/editor/configPanels/YamlPanel.tsx:139
        WorkflowYamlHeaderActions wired with aria-label 'Version History (visual editor)'
        so users in the visual editor can also access version history.
    """
    edit_page = EditWorkflowPage(page)

    # Navigate to the edit workflow page (= visual editor by default).
    edit_page.navigate_to(test_workflow.id)
    edit_page.should_be_on_edit_workflow_page()

    # Open the visual editor's YAML panel via the toolbar YAML button.
    # YamlPanel.tsx renders WorkflowYamlHeaderActions with
    # aria-label='Version History (visual editor)' (YamlPanel.tsx:139).
    config_panel = edit_page.open_yaml_panel()

    # Step 1: Assert the 'Version History (visual editor)' button is present and visible.
    expect(config_panel.version_history_visual_editor_button).to_be_visible()

    # Step 2: Click the button — WorkflowVersionHistoryPopup should open.
    config_panel.version_history_visual_editor_button.click()

    popup = WorkflowVersionHistoryPopup(page)
    popup.should_be_visible()
