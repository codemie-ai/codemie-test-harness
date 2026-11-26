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

"""Save-time contract findings in the workflow editor: the Issues panel and save outcomes.

A save, Check or restore returns contract findings as ERROR, WARNING or UNVERIFIED:

- ERROR rejects the save: the panel opens and the header keeps Cancel / Save / Save and Run.
- WARNING saves, and the page stays open "Saved with warnings" with Done / Saved / Run anyway.
- UNVERIFIED alone (or no finding) saves as before: the success toast and back to the list.

Workflows that save are seeded through the API (``workflow_factory``); outcomes that reject
are typed into the YAML panel of a seeded workflow, since the API refuses to store them.
Frontend evidence: EditWorkflowPage.tsx, NewWorkflowPage.tsx, IssueGroups.tsx,
IssuesPanel.tsx, EditorActions.tsx, useContractCheck.ts, useWorkflowHistoryRestore.ts,
contractProtocol.ts.
"""

import pytest
from hamcrest import assert_that, empty, has_length

from codemie_test_harness.tests.ui.pageobject.components import UnsavedChangesDialog
from codemie_test_harness.tests.ui.pageobject.workflows.create_workflow_page import (
    CreateWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)
from codemie_test_harness.tests.ui.test_data.workflow_contracts_test_data import (
    CLEAN_WORKFLOW_COVERAGE,
    CREATED_WITH_WARNINGS_NOTE,
    DECLARED_REMOVED_KEY_INPUT_CONTRACT,
    DECLARING_STATE_ID,
    DOC_CONSUMER_STATE_ID,
    ERRORS_GROUP,
    NAVIGATING_SAVE_CASES,
    NO_ISSUES_FOUND_TOAST,
    NOT_SAVED_NOTE,
    REMOVED_KEY_FIELD_WARNING,
    REMOVED_KEY_MESSAGE,
    SAVED_WITH_ONE_WARNING_TOAST,
    SAVED_WITH_WARNINGS_NOTE,
    SEVERITY_AMBER,
    SEVERITY_GREY,
    SEVERITY_RED,
    STRICT_CASES,
    TRANSFORM_FORM_ERROR_MESSAGE,
    TRANSFORM_OUTPUT_SCHEMA_YAML_KEY,
    TRUNCATED_WARNINGS_LINE,
    LISTED_WARNINGS_CAP,
    UNVERIFIED_GROUP,
    UNVERIFIED_KEY_MESSAGE,
    UNVERIFIED_ONLY_TOAST,
    WARNED_SAVE_TOAST_PREFIX,
    WARNING_STATE_ID,
    WARNINGS_GROUP,
    WORKFLOW_STRICT_LINE,
    build_all_severities_yaml,
    build_clean_yaml,
    build_error_and_unverified_yaml,
    build_truncated_warnings_yaml,
    build_unverified_only_yaml,
    build_warning_and_unverified_yaml,
    build_warning_only_yaml,
    build_warning_resolved_yaml,
    build_transform_example_output_yaml,
)


@pytest.mark.workflow
@pytest.mark.ui
def test_rejected_save_shows_errors_warnings_and_unverified_in_severity_groups(
    page, workflow_factory, default_llm
):
    # @case save-time-contract-editor-controls_TC_004
    """A save rejected by a declared input contract opens the Issues panel with Errors,
    Warnings and a collapsed Unverified group, coverage, and no saved note or error toast."""
    # assumed: the WARNING + UNVERIFIED seed and the ERROR typed into c2 compose recipes 1
    # and 3 of the recon walk (see build_warning_and_unverified_yaml).
    workflow = workflow_factory(
        build_warning_and_unverified_yaml(default_llm.base_name)
    )
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    node_panel = edit_page.open_node_config_panel(DECLARING_STATE_ID)
    node_panel.fill_input_contract(DECLARED_REMOVED_KEY_INPUT_CONTRACT)
    node_panel.click_save()
    edit_page.click_save()

    issues = edit_page.issues_panel
    issues.should_have_group(ERRORS_GROUP, 1, expanded=True)
    issues.should_have_group(WARNINGS_GROUP, 1, expanded=True)
    issues.should_have_group(UNVERIFIED_GROUP, 1, expanded=False)
    issues.should_have_cards_with_test_ids()
    issues.should_show_coverage()
    issues.should_not_have_context_note()
    issues.should_have_line_visibility(WORKFLOW_STRICT_LINE, False)
    issues.should_have_strict_tag_visibility(False)
    issues.should_have_issues_button(SEVERITY_RED, 3)
    issues.should_have_card(REMOVED_KEY_MESSAGE, "Warning")
    issues.toggle_group(UNVERIFIED_GROUP)
    issues.should_have_group(UNVERIFIED_GROUP, 1, expanded=True)
    issues.should_have_card(UNVERIFIED_KEY_MESSAGE, "Unverified")

    edit_page.should_have_editing_header()
    edit_page.should_have_node_outline(DECLARING_STATE_ID, "error")
    edit_page.should_have_no_issue_outline(DOC_CONSUMER_STATE_ID)
    edit_page.toast.should_not_show(variants=("error",))


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize(
    "case", STRICT_CASES, ids=[case.case_id for case in STRICT_CASES]
)
def test_strict_rejection_shows_workflow_strict_line_or_node_strict_tag(
    page, workflow_factory, default_llm, case
):
    # @case save-time-contract-editor-controls_TC_005
    """Workflow-level strict shows the panel line 'Blocked by the workflow-level save
    validation (strict)'; state-level strict tags the card 'node save validation (strict)'."""
    workflow = workflow_factory(build_clean_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    edit_page.replace_yaml_config(case.yaml_builder(default_llm.base_name))
    edit_page.click_save()

    issues = edit_page.issues_panel
    issues.should_have_group(ERRORS_GROUP, 1, expanded=True)
    issues.should_have_card(REMOVED_KEY_MESSAGE, "Error")
    issues.should_have_line_visibility(WORKFLOW_STRICT_LINE, case.strict_line_visible)
    issues.should_have_strict_tag_visibility(case.strict_tag_visible)
    issues.should_have_issues_button(SEVERITY_RED, 1)
    edit_page.should_have_editing_header()


@pytest.mark.workflow
@pytest.mark.ui
def test_save_with_contract_warning_stays_open_in_saved_with_warnings_state(
    page, workflow_factory, default_llm
):
    # @case save-time-contract-editor-controls_TC_006
    """A save with a contract WARNING stays on the editor: 'Saved with warnings' note,
    coverage, one count toast without the warning text, Done / Saved / Run anyway, amber
    Issues button and node outline; Done then leaves with no unsaved-changes dialog."""
    workflow = workflow_factory(build_warning_only_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    edit_page.toast.start_recording()
    edit_page.click_save()

    issues = edit_page.issues_panel
    issues.should_have_context_note(SAVED_WITH_WARNINGS_NOTE)
    issues.should_show_coverage()
    issues.should_have_group(WARNINGS_GROUP, 1, expanded=True)
    edit_page.toast.should_show_only_one(SAVED_WITH_ONE_WARNING_TOAST, "info")
    edit_page.toast.should_have_recorded_none_with(REMOVED_KEY_MESSAGE)
    edit_page.should_have_saved_with_warnings_header()
    issues.should_have_issues_button(SEVERITY_AMBER, 1)
    edit_page.should_have_node_outline(WARNING_STATE_ID, "warning")

    edit_page.click_done()
    UnsavedChangesDialog(page).should_not_be_visible()
    edit_page.should_have_left_editor()
    WorkflowsPage(page).should_be_on_workflows_page()


@pytest.mark.workflow
@pytest.mark.ui
def test_edit_after_warned_save_restores_header_and_marks_card_resolved(
    page, workflow_factory, default_llm
):
    # @case save-time-contract-editor-controls_TC_007
    """Editing the flagged field after a warned save brings back Cancel / Save / Save and
    Run, and the Issues panel marks the warning card Resolved."""
    workflow = workflow_factory(build_warning_only_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)
    edit_page.click_save()
    edit_page.issues_panel.should_have_context_note(SAVED_WITH_WARNINGS_NOTE)
    edit_page.should_have_saved_with_warnings_header()

    # Recon: the YAML-panel edit of the flagged task keeps the card and marks it Resolved.
    edit_page.replace_yaml_config(build_warning_resolved_yaml(default_llm.base_name))

    edit_page.should_have_editing_header()
    issues = edit_page.issues_panel.open()
    issues.should_have_resolved_card(REMOVED_KEY_MESSAGE)


@pytest.mark.workflow
@pytest.mark.ui
def test_go_to_issue_on_warning_opens_task_field_with_amber_warning(
    page, workflow_factory, default_llm
):
    # @case save-time-contract-editor-controls_TC_008
    """Go to Issue on a WARNING card opens the node panel at the flagged field with the
    amber border and inline warning text; the node keeps its amber outline."""
    workflow = workflow_factory(build_warning_only_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)
    edit_page.click_save()
    edit_page.issues_panel.should_have_context_note(SAVED_WITH_WARNINGS_NOTE)

    edit_page.issues_panel.click_go_to_issue(REMOVED_KEY_MESSAGE)

    node_panel = edit_page.get_node_config_panel()
    node_panel.should_be_visible()
    node_panel.should_have_task_warning(REMOVED_KEY_FIELD_WARNING)
    edit_page.should_have_node_outline(WARNING_STATE_ID, "warning")


@pytest.mark.workflow
@pytest.mark.ui
def test_go_to_issue_on_error_opens_input_contract_with_red_error(
    page, workflow_factory, default_llm
):
    # @case save-time-contract-editor-controls_TC_008
    """Go to Issue on an ERROR card opens the node panel at the Input contract with the red
    border and inline error text; the node keeps its red outline."""
    workflow = workflow_factory(build_clean_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)
    edit_page.replace_yaml_config(
        build_error_and_unverified_yaml(default_llm.base_name)
    )
    edit_page.click_save()
    edit_page.issues_panel.should_have_group(ERRORS_GROUP, 1, expanded=True)

    edit_page.issues_panel.click_go_to_issue(REMOVED_KEY_MESSAGE)

    node_panel = edit_page.get_node_config_panel()
    node_panel.should_be_visible()
    # assumed: the declared-ERROR message carries the same text as the strict ERROR recon saw.
    node_panel.should_have_input_contract_error(REMOVED_KEY_MESSAGE)
    edit_page.should_have_node_outline(WARNING_STATE_ID, "error")


@pytest.mark.workflow
@pytest.mark.ui
def test_go_to_issue_without_visual_control_opens_yaml_editor_line(
    page, workflow_factory, default_llm
):
    # @case save-time-contract-editor-controls_TC_009
    """A finding on a Transform node's output contract has no panel control: Go to Issue
    opens the YAML tab with the cursor on the ``output_schema`` line."""
    workflow = workflow_factory(build_clean_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)
    edit_page.replace_yaml_config(
        build_transform_example_output_yaml(default_llm.base_name)
    )
    edit_page.click_save()
    edit_page.issues_panel.should_have_card(TRANSFORM_FORM_ERROR_MESSAGE, "Error")

    edit_page.issues_panel.click_go_to_issue(TRANSFORM_FORM_ERROR_MESSAGE)

    config_panel = edit_page.workflow_config_panel
    config_panel.should_have_yaml_tab_selected()
    config_panel.should_have_yaml_cursor_on_line_containing(
        TRANSFORM_OUTPUT_SCHEMA_YAML_KEY
    )


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize(
    "case", NAVIGATING_SAVE_CASES, ids=[case.case_id for case in NAVIGATING_SAVE_CASES]
)
def test_clean_or_unverified_only_save_shows_update_toast_and_navigates_back(
    page, workflow_factory, default_llm, case
):
    # @case save-time-contract-editor-controls_TC_010
    """With no finding or only UNVERIFIED ones, Save shows 'Workflow has been updated
    successfully!' and returns to the list, with no warnings toast and no Issues panel."""
    workflow = workflow_factory(case.yaml_builder(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)
    edit_page.toast.start_recording()

    edit_page.save_workflow()

    edit_page.should_have_left_editor()
    WorkflowsPage(page).should_be_on_workflows_page()
    edit_page.toast.should_have_recorded_none_with(WARNED_SAVE_TOAST_PREFIX)
    edit_page.issues_panel.should_not_be_visible()


@pytest.mark.workflow
@pytest.mark.ui
def test_save_and_run_with_warning_skips_run_popup_and_run_anyway_opens_it(
    page, workflow_factory, default_llm
):
    # @case save-time-contract-editor-controls_TC_012
    """Save and Run with a WARNING saves once and opens no run popup; Run anyway opens the
    popup without sending a second update."""
    workflow = workflow_factory(build_warning_only_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)
    edit_page.start_counting_update_requests(workflow.id)

    edit_page.click_save_and_run()

    edit_page.issues_panel.should_have_context_note(SAVED_WITH_WARNINGS_NOTE)
    edit_page.should_have_saved_with_warnings_header()
    edit_page.should_not_show_run_popup()
    edit_page.should_have_sent_update_requests(1)

    edit_page.click_run_anyway()

    edit_page.should_show_run_popup()
    edit_page.should_have_sent_update_requests(1)


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize(
    "case", NAVIGATING_SAVE_CASES, ids=[case.case_id for case in NAVIGATING_SAVE_CASES]
)
def test_save_and_run_with_clean_or_unverified_only_result_opens_run_popup(
    page, workflow_factory, default_llm, case
):
    # @case save-time-contract-editor-controls_TC_013
    """Save and Run with no finding or only UNVERIFIED ones opens the run popup."""
    workflow = workflow_factory(case.yaml_builder(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    edit_page.click_save_and_run()

    edit_page.should_show_run_popup()
    edit_page.issues_panel.should_not_be_visible()


@pytest.mark.workflow
@pytest.mark.ui
def test_save_and_run_with_rejected_save_opens_issues_and_starts_no_run(
    page, workflow_factory, workflow_utils, default_llm
):
    # @case save-time-contract-editor-controls_TC_013
    """Save and Run of a draft the save rejects opens the Issues panel and no run popup;
    no execution of the workflow exists."""
    workflow = workflow_factory(build_clean_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)
    edit_page.replace_yaml_config(
        build_error_and_unverified_yaml(default_llm.base_name)
    )

    edit_page.click_save_and_run()

    edit_page.issues_panel.should_have_group(ERRORS_GROUP, 1, expanded=True)
    edit_page.should_not_show_run_popup()
    edit_page.should_have_editing_header()
    assert_that(
        workflow_utils.get_executions(workflow),
        empty(),
        "a rejected Save and Run must not start an execution",
    )


@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize("save_and_run", [False, True], ids=["save", "save-and-run"])
def test_new_workflow_save_with_warning_lands_on_edit_page_in_created_state(
    page, ui_workflow_name, workflow_utils, default_llm, save_and_run
):
    # @case save-time-contract-editor-controls_TC_014
    """Creating a workflow whose save warns replaces the route with its edit page: 'Workflow
    created with warnings', Saved disabled, no run popup, one stored workflow, and Done does
    not return to the new-workflow page."""
    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()
    create_page = workflows_page.click_create_workflow()

    create_page.create_workflow(
        name=ui_workflow_name,
        yaml_config=build_warning_only_yaml(default_llm.base_name),
        save_and_run=save_and_run,
    )

    edit_page = EditWorkflowPage(page)
    edit_page.should_be_on_edit_page_of_new_workflow()
    edit_page.issues_panel.should_have_context_note(CREATED_WITH_WARNINGS_NOTE)
    edit_page.should_have_saved_with_warnings_header()
    edit_page.should_not_show_run_popup()
    assert_that(
        workflow_utils.find_workflows_by_name(ui_workflow_name),
        has_length(1),
        "the warned create must store exactly one workflow with this name",
    )

    edit_page.click_done()
    edit_page.should_have_left_editor()


@pytest.mark.workflow
@pytest.mark.ui
def test_check_on_new_workflow_opens_panel_with_every_severity_and_saves_nothing(
    page, ui_workflow_name, workflow_utils, default_llm
):
    # @case save-time-contract-editor-controls_TC_015
    """Check on an unsaved new workflow opens the panel with Errors, Warnings, Unverified,
    coverage and 'Changes not saved yet'; the header is unchanged and nothing is created."""
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()
    # assumed: composition of recipes 1 and 3 (see build_all_severities_yaml).
    create_page.fill_draft(
        ui_workflow_name, build_all_severities_yaml(default_llm.base_name)
    )

    create_page.click_check()

    issues = create_page.issues_panel
    issues.should_have_group(ERRORS_GROUP, 1, expanded=True)
    issues.should_have_group(WARNINGS_GROUP, 1, expanded=True)
    issues.should_have_group(UNVERIFIED_GROUP, 1, expanded=False)
    issues.should_show_coverage()
    issues.should_have_context_note(NOT_SAVED_NOTE)
    create_page.should_have_editing_header()
    create_page.should_be_on_create_workflow_page()
    assert_that(
        workflow_utils.find_workflows_by_name(ui_workflow_name),
        empty(),
        "Check must not create the workflow",
    )


@pytest.mark.xfail(
    strict=True,
    reason="Product defect: Check on an unchanged saved workflow does not show the 'Changes not saved yet' note",
)
@pytest.mark.workflow
@pytest.mark.ui
def test_check_on_saved_workflow_with_findings_shows_not_saved_note(
    page, workflow_factory, default_llm
):
    # @case save-time-contract-editor-controls_TC_015
    """Check on a saved, unchanged workflow with findings opens the panel with coverage and,
    per the acceptance criterion, the 'Changes not saved yet' note; the header is unchanged.

    The frontend shows no note on an unchanged edit page (useContractCheck.ts resultContext),
    which contradicts the criterion; this test asserts the criterion.
    """
    workflow = workflow_factory(build_warning_only_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    edit_page.click_check()

    issues = edit_page.issues_panel
    issues.should_have_group(WARNINGS_GROUP, 1, expanded=True)
    issues.should_show_coverage()
    issues.should_have_context_note(NOT_SAVED_NOTE)
    edit_page.should_have_editing_header()


@pytest.mark.workflow
@pytest.mark.ui
def test_check_with_no_findings_toasts_coverage_and_keeps_panel_closed(
    page, workflow_factory, default_llm
):
    # @case save-time-contract-editor-controls_TC_016
    """Check with no finding toasts 'No issues found' with the coverage count and leaves the
    Issues panel closed."""
    workflow = workflow_factory(build_clean_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    edit_page.click_check()

    edit_page.toast.should_show(NO_ISSUES_FOUND_TOAST, ("success",))
    edit_page.toast.should_show(CLEAN_WORKFLOW_COVERAGE, ("success",))
    edit_page.issues_panel.should_not_be_visible()
    edit_page.issues_panel.should_not_have_issues_button()


@pytest.mark.workflow
@pytest.mark.ui
def test_check_with_unverified_only_toasts_state_count_and_opens_unverified(
    page, workflow_factory, default_llm
):
    # @case save-time-contract-editor-controls_TC_016
    """Check with only UNVERIFIED findings toasts '<N> states could not be verified' and
    opens the panel with the Unverified group expanded."""
    workflow = workflow_factory(build_unverified_only_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    edit_page.click_check()

    edit_page.toast.should_show(UNVERIFIED_ONLY_TOAST, ("info",))
    issues = edit_page.issues_panel
    issues.should_have_group(UNVERIFIED_GROUP, 1, expanded=True)
    issues.should_have_card(UNVERIFIED_KEY_MESSAGE, "Unverified")
    issues.should_have_issues_button(SEVERITY_GREY, 1)


@pytest.mark.xfail(
    strict=True,
    reason="Product defect: restoring a version with contract warnings does not open the Issues panel",
)
@pytest.mark.workflow
@pytest.mark.ui
def test_restore_version_with_contract_warning_shows_it_in_issues_panel(
    page, workflow_factory, workflow_utils, default_llm
):
    # @case save-time-contract-editor-controls_TC_017
    """Restoring a version whose YAML has a contract WARNING dry-runs it and lists the
    warning in the Issues panel with 'Changes not saved yet', without a warning toast."""
    workflow = workflow_factory(build_warning_only_yaml(default_llm.base_name))
    workflow_utils.update_workflow(
        workflow, yaml_config=build_clean_yaml(default_llm.base_name)
    )
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    popup = edit_page.open_yaml_panel().open_version_history_popup()
    popup.should_have_version_entries(min_count=1)
    edit_page.toast.start_recording()
    popup.click_restore()
    popup.confirm_restore()
    popup.should_not_be_visible()

    issues = edit_page.issues_panel
    issues.should_have_context_note(NOT_SAVED_NOTE)
    issues.should_have_card(REMOVED_KEY_MESSAGE, "Warning")
    edit_page.toast.should_have_recorded_none_with(REMOVED_KEY_MESSAGE)


@pytest.mark.workflow
@pytest.mark.ui
def test_truncated_contract_warnings_show_more_not_shown_line(
    page, workflow_factory, default_llm
):
    # @case save-time-contract-editor-controls_TC_020
    """More than 100 contract findings: the panel lists 100 and adds '<N> more warnings not
    shown'."""
    workflow = workflow_factory(build_truncated_warnings_yaml(default_llm.base_name))
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow.id)

    edit_page.click_check()

    issues = edit_page.issues_panel
    issues.should_show_line(TRUNCATED_WARNINGS_LINE)
    issues.should_have_group(UNVERIFIED_GROUP, LISTED_WARNINGS_CAP, expanded=True)
    issues.should_have_issues_button(SEVERITY_GREY, LISTED_WARNINGS_CAP)
