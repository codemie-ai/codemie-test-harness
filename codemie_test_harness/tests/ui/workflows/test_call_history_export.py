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

"""UI tests for the Download and Copy actions of the Calls history popup.

The popup is opened from the Call history button of a node in the execution details. Both
actions export exactly the calls the popup shows, as JSON indented with 2 spaces.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.workflows.workflow_executions_page import (
    WorkflowExecutionsPage,
)
from codemie_test_harness.tests.ui.test_data.call_history_export_test_data import (
    COPY_SUCCESS_TOAST,
    COPY_UNAVAILABLE_TOAST,
    DOWNLOAD_SUCCESS_TOAST,
)


@pytest.fixture
def clipboard_permissions(context):
    """Let the page read and write the clipboard so Copy can be verified."""
    context.grant_permissions(["clipboard-read", "clipboard-write"])


@pytest.fixture
def clipboard_unavailable(page):
    """Remove ``navigator.clipboard`` from every page load, as in an insecure context."""
    page.add_init_script(
        "Object.defineProperty(Navigator.prototype, 'clipboard', "
        "{ get: () => undefined, configurable: true });"
    )


@pytest.fixture
def open_call_history(page, executions):
    """Factory: run a workflow once and open the Calls history popup of its node.

    Returns the finished execution and the popup.
    """

    def _open():
        execution = executions(1)[0]
        executions_page = WorkflowExecutionsPage(page)
        executions_page.navigate_to(execution.workflow_id, execution.execution_id)
        return execution, executions_page.open_call_history()

    return _open


# @case enable-export-and-clipboard-copy_TC_001
@pytest.mark.workflow
@pytest.mark.ui
def test_download_call_history_exports_popup_calls_as_json_file(open_call_history):
    """Download saves call-history-<node-slug>-<execution_id>.json holding the popup's calls."""
    execution, popup = open_call_history()
    node_name = popup.get_node_name()
    popup_call_labels = popup.get_call_labels()

    download = popup.click_download()

    popup.should_have_download_named(download, node_name, execution.execution_id)
    exported_text = popup.read_downloaded_text(download)
    popup.should_be_indented_json(exported_text)
    popup.should_have_export_matching_popup(
        exported_text, execution.execution_id, node_name, popup_call_labels
    )
    popup.should_show_toast(DOWNLOAD_SUCCESS_TOAST)


# @case enable-export-and-clipboard-copy_TC_002
@pytest.mark.usefixtures("clipboard_permissions")
@pytest.mark.workflow
@pytest.mark.ui
def test_copy_call_history_puts_indented_json_on_clipboard(open_call_history):
    """Copy to clipboard puts the popup's calls on the clipboard as JSON indented with 2 spaces."""
    execution, popup = open_call_history()
    node_name = popup.get_node_name()
    popup_call_labels = popup.get_call_labels()

    popup.click_copy()

    popup.should_show_toast(COPY_SUCCESS_TOAST)
    clipboard_text = popup.read_clipboard()
    popup.should_be_indented_json(clipboard_text)
    popup.should_have_export_matching_popup(
        clipboard_text, execution.execution_id, node_name, popup_call_labels
    )


# @case enable-export-and-clipboard-copy_TC_004
@pytest.mark.usefixtures("clipboard_unavailable")
@pytest.mark.workflow
@pytest.mark.ui
def test_copy_call_history_without_clipboard_access_shows_error_toast(
    open_call_history,
):
    """With navigator.clipboard missing, Copy tells the user to use Download instead."""
    _, popup = open_call_history()

    popup.click_copy()

    popup.should_show_toast(COPY_UNAVAILABLE_TOAST)


# @case enable-export-and-clipboard-copy_TC_005
@pytest.mark.workflow
@pytest.mark.ui
def test_call_history_popup_shows_title_and_call_list(open_call_history):
    """The popup keeps its 'Calls history for <node>' title and renders the call list."""
    _, popup = open_call_history()

    popup.should_have_title_with_node_name()
    popup.should_have_call_list()
