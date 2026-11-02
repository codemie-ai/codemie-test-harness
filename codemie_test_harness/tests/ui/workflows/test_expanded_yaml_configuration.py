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

"""UI tests for the expanded YAML configuration dialog.

The dialog is opened from two places and must look and behave the same in both:
the YAML panel of the workflow editor (editable) and the Configuration sidebar of
execution details (read-only, with Copy and Download).
"""

import pytest
from codemie_sdk.models.workflow import WorkflowMode
from hamcrest import assert_that, contains_string, equal_to

from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflow_executions_page import (
    WorkflowExecutionsPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)
from codemie_test_harness.tests.ui.test_data.expanded_yaml_test_data import (
    EDITED_LINE_MARKER,
    EDITOR_CONTEXT,
    EXECUTION_DETAILS_CONTEXT,
    EXPANDED_YAML_CONTEXTS,
    EXPANDED_YAML_FRAME_TITLE,
    INVALID_YAML_LINE,
    LONG_YAML_FIRST_NODE,
    build_long_workflow_yaml,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.fixture
def clipboard_permissions(context):
    """Let the page read and write the clipboard so Copy can be verified."""
    context.grant_permissions(["clipboard-read", "clipboard-write"])


@pytest.fixture
def long_yaml_workflow(workflow_utils, default_llm):
    """A separate workflow whose YAML is long, multi-node and has a line wider than the dialog."""
    created = workflow_utils.create_workflow(
        workflow_name=get_random_name(),
        workflow_type=WorkflowMode.SEQUENTIAL,
        shared=True,
        workflow_yaml=build_long_workflow_yaml(default_llm.base_name),
    )
    workflow = workflow_utils.get_workflow(created.id)
    yield workflow
    try:
        workflow_utils.delete_workflow(workflow)
    except Exception:
        pass


@pytest.fixture
def open_expanded_yaml(request, page, test_workflow, executions, workflow_utils):
    """Factory: open the expanded YAML dialog in the given context.

    Uses ``test_workflow``; with ``long_yaml=True`` it uses ``long_yaml_workflow`` instead.
    """

    def _open(yaml_context, long_yaml=False):
        workflow = (
            request.getfixturevalue("long_yaml_workflow")
            if long_yaml
            else test_workflow
        )

        if yaml_context.is_editor:
            edit_page = EditWorkflowPage(page)
            edit_page.navigate_to(workflow.id)
            return edit_page.open_yaml_panel().expand_yaml_editor()

        if long_yaml:
            workflow_utils.execute_workflow(
                workflow=workflow.id,
                execution_name=LONG_YAML_FIRST_NODE,
                user_input="Say hello",
            )
            execution = workflow_utils.get_executions(workflow)[0]
        else:
            execution = executions(1)[0]
        executions_page = WorkflowExecutionsPage(page)
        executions_page.navigate_to(execution.workflow_id, execution.execution_id)
        executions_page.click_configuration()
        return executions_page.expand_yaml_configuration()

    return _open


# @case workflow-editor-expanded-yaml-configuration_TC_001
@pytest.mark.parametrize(
    "yaml_context", EXPANDED_YAML_CONTEXTS, ids=[c.name for c in EXPANDED_YAML_CONTEXTS]
)
@pytest.mark.workflow
@pytest.mark.ui
def test_expanded_yaml_dialog_has_shared_structure(open_expanded_yaml, yaml_context):
    """Label, Collapse, frame header and editor are the same; Copy/Download only in execution details."""
    dialog = open_expanded_yaml(yaml_context)

    dialog.should_have_shell()
    dialog.should_have_frame(EXPANDED_YAML_FRAME_TITLE)
    dialog.should_have_copy_and_download(yaml_context.has_copy_and_download)


# @case workflow-editor-expanded-yaml-configuration_TC_001
@pytest.mark.workflow
@pytest.mark.ui
def test_expanded_yaml_dialog_has_equal_size_in_editor_and_execution_details(
    open_expanded_yaml,
):
    """The dialog and the frame measure the same in the editor and in execution details."""
    editor_dialog = open_expanded_yaml(EDITOR_CONTEXT)
    editor_size = editor_dialog.get_size()
    editor_dialog.collapse()
    editor_dialog.should_be_hidden()

    execution_dialog = open_expanded_yaml(EXECUTION_DETAILS_CONTEXT)

    execution_dialog.should_have_size(editor_size)


# @case workflow-editor-expanded-yaml-configuration_TC_003
@pytest.mark.xfail(
    strict=True,
    reason="Known product defect: typed text in the expanded YAML editor keeps only its last character",
)
@pytest.mark.workflow
@pytest.mark.ui
def test_expanded_yaml_edit_syncs_to_inline_editor_and_persists_on_save(
    page, test_workflow, workflow_utils
):
    """An edit typed in the expanded editor shows in the inline editor and is saved.

    The edit extends the system prompt line: it is a value the visual editor keeps
    when it regenerates the YAML on Save, unlike a comment line.
    """
    edit_suffix = get_random_name()
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)
    yaml_panel = edit_page.open_yaml_panel()

    dialog = yaml_panel.expand_yaml_editor()
    dialog.should_be_readonly(False)
    dialog.append_to_line_containing(EDITED_LINE_MARKER, f" {edit_suffix}")
    dialog.should_have_content_containing(edit_suffix)
    dialog.collapse()
    dialog.should_be_hidden()

    yaml_panel.should_have_yaml_editor_containing(edit_suffix)

    yaml_panel.click_save()
    edit_page.click_save()
    WorkflowsPage(page).should_be_on_workflows_page()

    persisted = workflow_utils.get_workflow(test_workflow.id)
    assert_that(
        persisted.yaml_config,
        contains_string(edit_suffix),
        "Saved workflow yaml_config is missing the edit typed in the expanded editor",
    )


# @case workflow-editor-expanded-yaml-configuration_TC_003
@pytest.mark.xfail(
    strict=True,
    reason="Known product defect: typed text in the expanded YAML editor keeps only its last character",
)
@pytest.mark.workflow
@pytest.mark.ui
def test_expanded_yaml_edit_is_discarded_on_cancel(page, test_workflow, workflow_utils):
    """Cancel after an edit in the expanded editor leaves the YAML as it was."""
    edit_suffix = get_random_name()
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(test_workflow.id)
    yaml_panel = edit_page.open_yaml_panel()
    original_yaml = yaml_panel.get_yaml_content()

    dialog = yaml_panel.expand_yaml_editor()
    dialog.append_to_line_containing(EDITED_LINE_MARKER, f" {edit_suffix}")
    dialog.collapse()
    dialog.should_be_hidden()
    yaml_panel.should_have_yaml_editor_containing(edit_suffix)

    yaml_panel.click_cancel()

    reopened_panel = edit_page.open_yaml_panel()
    reopened_panel.should_have_yaml_editor_with_content(original_yaml)
    persisted = workflow_utils.get_workflow(test_workflow.id)
    assert_that(
        persisted.yaml_config,
        equal_to(test_workflow.yaml_config),
        "Persisted yaml_config changed although the edit was cancelled",
    )


# @case workflow-editor-expanded-yaml-configuration_TC_005
@pytest.mark.xfail(
    strict=True,
    reason="Known product defect: typed text in the expanded YAML editor keeps only its last character",
)
@pytest.mark.workflow
@pytest.mark.ui
def test_expanded_yaml_invalid_yaml_shows_error_and_failed_border(open_expanded_yaml):
    """Invalid YAML typed in the expanded editor shows 'YAML Error:' and the failed border."""
    dialog = open_expanded_yaml(EDITOR_CONTEXT)
    dialog.should_not_show_yaml_error()
    dialog.should_have_failed_border(False)

    dialog.append_line(INVALID_YAML_LINE)

    dialog.should_show_yaml_error()
    dialog.should_have_failed_border(True)


# @case workflow-editor-expanded-yaml-configuration_TC_006
@pytest.mark.usefixtures("clipboard_permissions")
@pytest.mark.workflow
@pytest.mark.ui
def test_execution_details_expanded_yaml_is_readonly_with_copy_and_download(
    open_expanded_yaml, test_workflow
):
    """The execution-details dialog ignores typing; Copy and Download deliver the YAML."""
    expected_yaml = test_workflow.yaml_config
    dialog = open_expanded_yaml(EXECUTION_DETAILS_CONTEXT)

    dialog.should_be_readonly(True)
    dialog.should_have_content(expected_yaml)

    dialog.type_into_editor(get_random_name())
    dialog.should_have_content(expected_yaml)

    dialog.click_copy()
    dialog.should_show_copied_toast()
    dialog.should_have_copied_to_clipboard(expected_yaml)

    download = dialog.click_download()
    dialog.should_show_download_toast(download)
    dialog.should_have_downloaded_content(download, expected_yaml)


# @case workflow-editor-expanded-yaml-configuration_TC_009
@pytest.mark.parametrize(
    "yaml_context", EXPANDED_YAML_CONTEXTS, ids=[c.name for c in EXPANDED_YAML_CONTEXTS]
)
@pytest.mark.workflow
@pytest.mark.ui
def test_expanded_yaml_highlights_scrolls_to_end_and_wraps_long_lines(
    open_expanded_yaml, yaml_context
):
    """A long multi-node YAML keeps its highlighting, reaches its last line and wraps wide lines."""
    dialog = open_expanded_yaml(yaml_context, long_yaml=True)

    dialog.should_have_syntax_highlighting()
    dialog.should_wrap_long_lines()

    last_line = dialog.scroll_to_end()

    dialog.should_show_last_line(last_line)
