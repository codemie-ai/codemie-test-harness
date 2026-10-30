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

"""UI tests for the "Generate Workflow with AI" popup.

Happy-path coverage only (TC-01..TC-03, TC-08 UI half of the reduced test plan):
- TC-01: submitting a NL description renders the generated workflow in the
  visual editor.
- TC-02: a generated node's field can be edited and the workflow saved.
- TC-03: a generated node can be drag-and-drop repositioned on the canvas.
- TC-08 (UI half): generate a workflow via the popup, save it, run it via
  the workflow's chat, and verify the chat produces a response.
  See test_generate_workflow.py for the API half.

Generation is LLM-driven and non-deterministic, so assertions only ever check
structure (node presence/count, position change, response presence) — never exact
generated content, per the test plan's non-determinism guidance.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.pageobject.workflows.assistant_node_config_panel import (
    AssistantNodeConfigPanel,
)
from codemie_test_harness.tests.ui.pageobject.workflows.create_workflow_page import (
    CreateWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.generate_workflow_ai_page import (
    GenerateWorkflowAIPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflow_details_page import (
    WorkflowDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)
from codemie_test_harness.tests.ui.test_data.workflows_test_data import (
    GENERATE_WORKFLOW_DESCRIPTION,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    wait_for_entity,
)


@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.not_for_parallel_run
@pytest.mark.prod_regression
def test_generate_workflow_renders_in_visual_editor(page, clear_workflow_ai_popup):
    """TC-01: submitting a NL description renders the workflow in the visual editor."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    ai_page = GenerateWorkflowAIPage(page)
    ai_page.should_be_visible()
    ai_page.generate_workflow(GENERATE_WORKFLOW_DESCRIPTION)

    # Popup closed and the generated workflow was fed into the visual editor.
    ai_page.should_not_be_visible()
    create_page.should_have_canvas_visible()
    create_page.should_have_generated_nodes()


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.not_for_parallel_run
@pytest.mark.prod_regression
def test_edit_generated_node_field_saves_successfully(
    page, clear_workflow_ai_popup, cleanup_generated_workflow
):
    """TC-02: after generation, edit a node field and save successfully."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    GenerateWorkflowAIPage(page).generate_workflow(GENERATE_WORKFLOW_DESCRIPTION)
    create_page.should_have_generated_nodes()

    # Capture the generated name up front so it can be cleaned up afterward,
    # regardless of what the LLM named the workflow. The "Collapse panel"
    # button only collapses the panel to a small pill (it stays in the DOM
    # with the same accessible name), it does not close/hide it, so there is
    # no need to close it before interacting with the canvas below.
    config_panel = create_page.open_workflow_config_panel()
    config_panel.switch_to_basic_tab()
    generated_name = config_panel.get_name_value()
    cleanup_generated_workflow(generated_name)

    # Edit a field on the first generated node.
    create_page.click_first_generated_node()
    node_panel = AssistantNodeConfigPanel(page)
    node_panel.should_be_visible()

    updated_task = f"Updated generated task {get_random_name()}"
    node_panel.fill_task(updated_task)
    node_panel.should_have_task_value(updated_task)
    node_panel.click_save()
    node_panel.should_not_be_visible()

    # Save the workflow.
    create_page.click_save()

    workflows_page = WorkflowsPage(page)
    workflows_page.should_be_on_workflows_page()
    workflows_page.should_see_workflow_card(generated_name)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.not_for_parallel_run
@pytest.mark.prod_regression
def test_drag_generated_node_repositions_on_canvas(page, clear_workflow_ai_popup):
    """TC-03: a generated node can be drag-and-drop repositioned on the canvas."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    GenerateWorkflowAIPage(page).generate_workflow(GENERATE_WORKFLOW_DESCRIPTION)
    create_page.should_have_generated_nodes()

    node = create_page.non_default_canvas_nodes.first
    original_box = create_page.drag_node_by_offset(node, dx=150, dy=100)

    create_page.should_have_node_moved(node, original_box)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.not_for_parallel_run
@pytest.mark.prod_regression
def test_generate_and_run_workflow_via_ui(
    page, client, clear_workflow_ai_popup, cleanup_generated_workflow
):
    """TC-08 (UI half): generate, save, and run a workflow entirely via the UI,
    then verify the chat produces a response.
    See test_generate_workflow.py for the API half.
    """
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()

    GenerateWorkflowAIPage(page).generate_workflow(GENERATE_WORKFLOW_DESCRIPTION)
    create_page.should_have_generated_nodes()

    # Capture the generated name before saving (regardless of what the LLM
    # named the workflow) so it can be cleaned up afterward.
    config_panel = create_page.open_workflow_config_panel()
    config_panel.switch_to_basic_tab()
    generated_name = config_panel.get_name_value()
    cleanup_generated_workflow(generated_name)

    create_page.click_save()

    workflows_page = WorkflowsPage(page)
    workflows_page.should_be_on_workflows_page()
    workflows_page.should_see_workflow_card(generated_name)

    workflow = wait_for_entity(
        lambda: client.workflows.list(per_page=200, filter_by_user=True),
        entity_name=generated_name,
    )

    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(workflow.id)
    workflow_details_page.click_run_chat()
    workflow_details_page.should_have_url_containing("/chats")

    chat_page = ChatPage(page)
    chat_page.send_message(f"Run the workflow. [{get_random_name()}]")
    chat_page.wait_for_assistant_response()
    chat_page.should_have_assistant_response()
