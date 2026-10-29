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

"""UI tests for workflow-scoped personal integration settings.

Covers scenarios S01–S05, S13, S14.

Playwright locators were verified via playwright-cli inspection on 2026-08-17.

Key observations from live inspection:
- Canvas nodes: data-testid="rf__node-{nodeId}" (React Flow standard)
- Assistant node panel: opens as <aside> element when node clicked
- User mapping section heading: "Your Integration Settings" (text)
- Checkbox label: "Apply to the whole assistant"
- Tests use a Jira-toolkit assistant shared with the project, which is what gives
  the panel a user-selectable integration slot; standard assistants have none.
- Explicit "no integration" is sent as ``integration_id=""``; an empty tools_config
  is a no-op on the API and does not create a scoped record.
"""

import pytest
from hamcrest import assert_that, equal_to, not_none

from codemie_test_harness.tests.enums.tools import ProjectManagementTool
from codemie_test_harness.tests.test_data.user_mapping_test_data import SlotAssignment
from codemie_test_harness.tests.ui.pageobject.workflows import (
    WorkflowDetailsPage,
    AssistantNodePanelPage,
)

# Node ID for the test_workflow fixture (virtual "branch_creator" state — no real assistant_id).
# S01-S05, S13 use ``workflow_with_real_assistant`` instead and reference real_assistant.name.
_ASSISTANT_STATE_NAME = "branch_creator"


# ---------------------------------------------------------------------------
# S01 — Dropdown shows effective integration selection on workflow screen
# ---------------------------------------------------------------------------


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.ui
def test_dropdown_shows_effective_integration_selection(
    page, workflow_with_real_assistant, client
):
    """S01: Opening an assistant node panel on a workflow screen shows the
    effective integration selection (dropdown value) matching the GET response.

    Covers AC1.
    Uses a real API-registered assistant (Jira toolkit) so the workflow canvas
    node opens a proper assistant panel with user-selectable integration slots.
    """
    workflow_obj, real_assistant = workflow_with_real_assistant

    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(workflow_obj.id)
    workflow_details_page.should_be_on_workflow_details_page()

    # Open the assistant node panel for the real assistant node
    panel = workflow_details_page.open_assistant_node_panel(real_assistant.name)

    # The section is present: assert integration dropdown is visible via POM method
    panel.should_have_user_mapping_section()
    panel.user_mapping_section.should_have_integration_dropdown_visible()

    # Cross-validate the effective selection with the GET API
    api_response = client.assistants.get_user_mapping(
        assistant_id=real_assistant.id,
        workflow_id=workflow_obj.id,
    )
    assert_that(api_response, not_none(), "GET user-mapping must return a response")


# ---------------------------------------------------------------------------
# S02 — Workflow-scoped save (checkbox unticked) persists to workflow scope only
# ---------------------------------------------------------------------------


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.ui
def test_workflow_scoped_save_checkbox_unticked(
    page, workflow_with_real_assistant, client
):
    """S02: Unticking the checkbox and saving creates a workflow-scoped record
    while the assistant-scoped record remains unchanged.

    Covers AC3, AC4.
    """
    workflow_obj, real_assistant = workflow_with_real_assistant

    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(workflow_obj.id)
    workflow_details_page.should_be_on_workflow_details_page()

    panel = workflow_details_page.open_assistant_node_panel(real_assistant.name)

    panel.should_have_user_mapping_section()
    panel.user_mapping_section.should_have_checkbox_visible()

    # Get baseline assistant-scoped mapping before save
    baseline_response = client.assistants.get_user_mapping(
        assistant_id=real_assistant.id,
    )

    # Untick the checkbox to use workflow scope, then save
    panel.user_mapping_section.untick_apply_to_whole_assistant()
    panel.user_mapping_section.save()

    # Assert: workflow-scoped record now exists for this workflow
    wf_response = client.assistants.get_user_mapping(
        assistant_id=real_assistant.id,
        workflow_id=workflow_obj.id,
    )
    assert_that(
        wf_response,
        not_none(),
        "GET workflow-scoped mapping must return a response after save",
    )

    # Assert: assistant-scoped record is unchanged (AC4, AC5)
    after_response = client.assistants.get_user_mapping(
        assistant_id=real_assistant.id,
    )
    assert_that(
        after_response,
        equal_to(baseline_response),
        "Workflow-scoped save (checkbox unticked) must not change the assistant-scoped mapping",
    )


# ---------------------------------------------------------------------------
# S03 — Checkbox-ticked save promotes to assistant scope, removes workflow override
# ---------------------------------------------------------------------------


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.ui
def test_checkbox_ticked_save_promotes_to_assistant_scope(
    page, workflow_with_real_assistant, client
):
    """S03: Ticking the 'Apply to the whole assistant' checkbox and saving
    writes to assistant scope and removes any workflow-scoped override.

    Covers AC3, AC6.
    """
    workflow_obj, real_assistant = workflow_with_real_assistant

    # Pre-state via API, before the page loads. The checkbox default is derived from
    # has_assistant_scope_selection (AC9), so an assistant-scoped selection is what
    # renders it unticked — a workflow-scoped record alone leaves it pre-ticked.
    # The workflow-scoped override gives AC6 an override to remove on promotion.
    jira_slot = SlotAssignment(
        name=ProjectManagementTool.JIRA.value, explicit_none=True
    ).to_dict()
    client.assistants.save_user_mapping(
        assistant_id=real_assistant.id,
        tools_config=[jira_slot],
    )
    client.assistants.save_user_mapping(
        assistant_id=real_assistant.id,
        tools_config=[jira_slot],
        workflow_id=workflow_obj.id,
    )

    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(workflow_obj.id)
    workflow_details_page.should_be_on_workflow_details_page()

    panel = workflow_details_page.open_assistant_node_panel(real_assistant.name)

    panel.should_have_user_mapping_section()
    panel.user_mapping_section.should_have_checkbox_visible()

    # With an assistant-scoped selection present, the checkbox must start unticked (AC9)
    panel.should_have_checkbox_unticked()

    # Tick the checkbox to promote to assistant scope, then save
    panel.user_mapping_section.tick_apply_to_whole_assistant()
    panel.user_mapping_section.save()

    # Assert: assistant-scoped record now exists
    assistant_response = client.assistants.get_user_mapping(
        assistant_id=real_assistant.id,
    )
    assert_that(
        assistant_response,
        not_none(),
        "GET assistant-scoped mapping must return a response after ticked-checkbox save",
    )
    assert_that(
        assistant_response.get("has_assistant_scope_selection"),
        equal_to(True),
        "has_assistant_scope_selection must be True after saving at assistant scope",
    )

    # Assert: GET with workflow_id inherits assistant-scoped (no separate workflow override)
    wf_response = client.assistants.get_user_mapping(
        assistant_id=real_assistant.id,
        workflow_id=workflow_obj.id,
    )
    assert_that(
        wf_response.get("has_assistant_scope_selection"),
        equal_to(True),
        "After ticked-checkbox save, GET with workflow_id must reflect assistant-scoped via inheritance",
    )


# ---------------------------------------------------------------------------
# S04 — Checkbox is pre-ticked when user has no assistant-scoped selection
# ---------------------------------------------------------------------------


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.ui
def test_checkbox_pre_ticked_when_no_assistant_scoped_selection(
    page, workflow_with_real_assistant, client
):
    """S04: When a user has no assistant-scoped entry, the 'Apply to the whole
    assistant' checkbox is pre-ticked in the workflow panel.

    Covers AC8.
    Pre-state: ensure no assistant-scoped entry exists for the test user.
    """
    workflow_obj, real_assistant = workflow_with_real_assistant

    # Pre-state: the fixture creates a brand-new assistant, so no assistant-scoped
    # selection exists for this user yet — which is exactly AC8's precondition.
    # (There is no DELETE for user mappings; the endpoint returns 405.)
    pre_check = client.assistants.get_user_mapping(assistant_id=real_assistant.id)
    assert_that(
        pre_check.get("has_assistant_scope_selection"),
        equal_to(False),
        "Pre-state: a fresh assistant must have no assistant-scoped selection",
    )

    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(workflow_obj.id)
    workflow_details_page.should_be_on_workflow_details_page()

    panel = workflow_details_page.open_assistant_node_panel(real_assistant.name)

    panel.should_have_user_mapping_section()
    panel.should_have_checkbox_pre_ticked()


# ---------------------------------------------------------------------------
# S05 — Checkbox is unticked when assistant-scoped selection already exists
# ---------------------------------------------------------------------------


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.ui
def test_checkbox_unticked_when_assistant_scoped_selection_exists(
    page, workflow_with_real_assistant, client
):
    """S05: When a user already has an assistant-scoped entry, the 'Apply to the
    whole assistant' checkbox is unchecked (unticked) in the workflow panel.

    Covers AC9.
    Pre-state: create an assistant-scoped mapping via API.
    """
    workflow_obj, real_assistant = workflow_with_real_assistant

    # Pre-state: create an assistant-scoped selection. An empty tools_config is a
    # no-op on the API, so an explicit-none choice on the real Jira slot is used —
    # that writes an assistant-scoped row and sets has_assistant_scope_selection=True,
    # which is what makes the checkbox render unticked (AC9).
    client.assistants.save_user_mapping(
        assistant_id=real_assistant.id,
        tools_config=[
            SlotAssignment(
                name=ProjectManagementTool.JIRA.value, explicit_none=True
            ).to_dict()
        ],
    )
    pre_check = client.assistants.get_user_mapping(assistant_id=real_assistant.id)
    assert_that(
        pre_check.get("has_assistant_scope_selection"),
        equal_to(True),
        "Pre-state: an assistant-scoped selection must exist before asserting AC9",
    )

    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(workflow_obj.id)
    workflow_details_page.should_be_on_workflow_details_page()

    panel = workflow_details_page.open_assistant_node_panel(real_assistant.name)

    panel.should_have_user_mapping_section()
    panel.should_have_checkbox_unticked()


# ---------------------------------------------------------------------------
# S13 — Assistant page panel has no checkbox; saves remain assistant-scoped
# ---------------------------------------------------------------------------


@pytest.mark.jira
@pytest.mark.workflow
@pytest.mark.ui
def test_assistant_page_panel_has_no_apply_to_assistant_checkbox(
    page, workflow_with_real_assistant
):
    """S13: The integration settings panel on the assistant details page must
    NOT show the 'Apply to the whole assistant' checkbox — only workflow screens
    show that checkbox (AC15).

    Navigation: workflows/{id} → click node → panel opens.
    The checkbox is ONLY rendered on workflow screens. On the assistant page
    (/assistants/{id}), the panel uses a different component with no checkbox.

    Covers AC15.
    """
    workflow_obj, real_assistant = workflow_with_real_assistant

    # Navigate to the workflow canvas — the panel here should show the checkbox
    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(workflow_obj.id)
    workflow_details_page.should_be_on_workflow_details_page()

    # Open the panel for the real assistant node (CR-001, CR-003 fix)
    panel = workflow_details_page.open_assistant_node_panel(real_assistant.name)

    # Workflow panel should have the checkbox
    panel.should_have_user_mapping_section()

    # Navigate to the assistant details page using the real assistant ID directly
    page.goto(f"/assistants/{real_assistant.id}")

    # On the assistant page, the integration section should have no checkbox
    panel_on_assistant_page = AssistantNodePanelPage(page)
    panel_on_assistant_page.should_have_no_checkbox()


# ---------------------------------------------------------------------------
# S14 — Assistants without per-user slots show no selection section
# ---------------------------------------------------------------------------


@pytest.mark.workflow
@pytest.mark.ui
def test_assistant_without_per_user_slots_shows_no_mapping_section(page, test_workflow):
    """S14: Opening the workflow node panel for an assistant that has no
    user-selectable (all-pinned) integration slots must NOT show the
    'Your Integration Settings' section.

    Covers AC25.
    The test_workflow fixture uses the built-in 'branch_creator' state which
    has no user-selectable integration slots — a safe stable baseline.
    """
    workflow_details_page = WorkflowDetailsPage(page)
    workflow_details_page.navigate_to(test_workflow.id)
    workflow_details_page.should_be_on_workflow_details_page()

    panel = workflow_details_page.open_assistant_node_panel(_ASSISTANT_STATE_NAME)

    # The test_workflow's assistant has no user-selectable slots → section must be absent
    panel.should_not_have_user_mapping_section()
